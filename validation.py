from datetime import datetime, date
from typing import Any, Dict, List, Optional

_REQUIRED_NUMERIC_LIMITS = {
    "monthly": (0, 5000),
    "due_at_signing": (0, 20000),
}

_VALID_TERMS = {24, 27, 36, 39, 48, 60, 72}

_EMPTY_VALUES = {"", "—", "N/A", None}


def _first_present(row: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None




def _normalize_scalar(value: Any) -> Optional[str]:
    """Convert empty-like values to None and return stripped string."""
    if value in _EMPTY_VALUES:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned in _EMPTY_VALUES:
            return None
        return cleaned
    return str(value)


def _normalize_money(value: Any) -> Optional[float]:
    normalized = _normalize_scalar(value)
    if normalized is None:
        return None
    stripped = normalized.replace("$", "").replace(",", "")
    try:
        return float(stripped)
    except (TypeError, ValueError):
        return None


def _normalize_term(value: Any) -> Optional[int]:
    normalized = _normalize_scalar(value)
    if normalized is None:
        return None
    try:
        return int(normalized)
    except (TypeError, ValueError):
        return None


def _normalize_expires(value: Any) -> Optional[date]:
    normalized = _normalize_scalar(value)
    if normalized is None:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except (TypeError, ValueError):
            continue
    return None


def validate_row(row: Dict[str, Any], run_date: date) -> Dict[str, Any]:
    normalized_row: Dict[str, Any] = {
        "due_at_signing": _normalize_money(row.get("due_at_signing")),
        "monthly": _normalize_money(row.get("monthly")),
        "model": _normalize_scalar(row.get("model")),
        "expires": _normalize_expires(row.get("expires")),
        "term_months": _normalize_term(row.get("term_months")),
        "msrp": _normalize_money(row.get("msrp")),
    }

    required_errors: List[str] = []
    moderate_warnings: List[str] = []

    for field, (lower, upper) in _REQUIRED_NUMERIC_LIMITS.items():
        value = normalized_row[field]
        if value is None:
            required_errors.append(f"{field} is required and must be a number")
            continue

        if field == "monthly":
            is_valid = lower < value < upper
            comparator = "> 0"
        else:
            is_valid = lower <= value < upper
            comparator = "≥ 0"

        if not is_valid:
            required_errors.append(
                f"{field} must be numeric {comparator} and under {upper}"
            )

    model_value = normalized_row["model"]
    if model_value is None or not str(model_value).strip():
        required_errors.append("model is required and must be a meaningful string")

    expires_value = normalized_row["expires"]
    if expires_value is None:
        moderate_warnings.append("expires date is missing or invalid")
    elif expires_value < run_date:
        moderate_warnings.append("expires date is before the run date")

    term_value = normalized_row["term_months"]
    if term_value is None:
        moderate_warnings.append("term_months is missing or invalid")
    elif term_value not in _VALID_TERMS:
        moderate_warnings.append("term_months is not in the expected set")

    msrp_value = row.get("msrp")
    if msrp_value is not None and msrp_value not in _EMPTY_VALUES:
        if normalized_row["msrp"] is None:
            moderate_warnings.append("msrp provided but invalid")

    if required_errors:
        row_status = "INVALID_REQUIRED"
    elif any(w for w in moderate_warnings if "expires" in w or "term_months" in w):
        row_status = "ATTENTION_MODERATE"
    else:
        row_status = "VALID"

    return {
        "normalized_row": normalized_row,
        "row_status": row_status,
        "required_errors": required_errors,
        "moderate_warnings": moderate_warnings,
    }


def compute_dealer_health(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_rows = len(rows)

    if total_rows == 0:
        return {
            "status": "FAIL",
            "total_rows": 0,
            "valid_rows": 0,
            "invalid_required_rows": 0,
            "attention_rows": 0,
            "top_issues": [],
        }

    valid_rows = 0
    invalid_required_rows = 0
    attention_rows = 0
    issue_counts: Dict[str, int] = {}

    for row in rows:
        status = row.get("row_status")
        if status == "VALID":
            valid_rows += 1
        elif status == "INVALID_REQUIRED":
            invalid_required_rows += 1
        elif status == "ATTENTION_MODERATE":
            attention_rows += 1

        for issue in row.get("required_errors", []) + row.get("moderate_warnings", []):
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    if valid_rows == 0:
        status = "FAIL"
    elif invalid_required_rows / total_rows > 0.5:
        status = "FAIL"
    elif attention_rows > 0:
        status = "NEEDS_ATTENTION"
    else:
        status = "OK"

    sorted_issues = sorted(issue_counts.items(), key=lambda item: (-item[1], item[0]))
    top_issues = [issue for issue, _ in sorted_issues[:3]]

    return {
        "status": status,
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "invalid_required_rows": invalid_required_rows,
        "attention_rows": attention_rows,
        "top_issues": top_issues,
    }