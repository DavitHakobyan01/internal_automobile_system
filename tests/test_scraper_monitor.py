from datetime import date, datetime


from scraper_monitor import SCRAPER_MONITOR, record_dealer_result, reset_monitor_state


def test_valid_row_passes_with_normalization():
    run_date = date(2024, 1, 1)
    result = validate_row(
        {
            "monthly": "$299",
            "due_at_signing": "$2,999",
            "model": "Camry LE ",
            "expires": "12/31/30",
            "term_months": "36",
            "msrp": "$28,000",
        },
        run_date,
    )

    normalized = result["normalized_row"]
    assert normalized["monthly"] == 299.0
    assert normalized["due_at_signing"] == 2999.0
    assert normalized["model"] == "Camry LE"
    assert normalized["expires"].year == 2030
    assert normalized["term_months"] == 36
    assert normalized["msrp"] == 28000.0
    assert result["row_status"] == "VALID"
    assert result["required_errors"] == []
    assert result["moderate_warnings"] == []


def test_required_validation_failure_marks_invalid():
    run_date = date(2024, 1, 1)
    result = validate_row(
        {
            "monthly": "0",
            "due_at_signing": "-100",
            "model": "",
            "expires": "12/31/30",
            "term_months": "36",
        },
        run_date,
    )

    assert result["row_status"] == "INVALID_REQUIRED"
    assert len(result["required_errors"]) == 3
    assert any("monthly" in message for message in result["required_errors"])
    assert any("due_at_signing" in message for message in result["required_errors"])
    assert any("model" in message for message in result["required_errors"])


def test_moderate_warning_for_expires_and_term():
    run_date = date(2024, 1, 2)
    result = validate_row(
        {
            "monthly": "$199",
            "due_at_signing": "$1,999",
            "model": "RAV4",
            "expires": "01/01/24",
            "term_months": "25",
        },
        run_date,
    )

    assert result["row_status"] == "ATTENTION_MODERATE"
    assert any("expires" in message for message in result["moderate_warnings"])
    assert any("term_months" in message for message in result["moderate_warnings"])


def test_msrp_invalid_adds_warning_but_keeps_valid_status():
    run_date = date(2024, 1, 1)
    result = validate_row(
        {
            "monthly": "$199",
            "due_at_signing": "$1,999",
            "model": "RAV4",
            "expires": "12/31/30",
            "term_months": "36",
            "msrp": "not-a-number",
        },
        run_date,
    )

    assert result["row_status"] == "VALID"
    assert "msrp provided but invalid" in result["moderate_warnings"]


def test_dealer_health_with_no_rows_fails():
    health = compute_dealer_health([])

    assert health == {
        "status": "FAIL",
        "total_rows": 0,
        "valid_rows": 0,
        "invalid_required_rows": 0,
        "attention_rows": 0,
        "top_issues": [],
    }


def test_dealer_health_counts_and_top_issues():
    rows = [
        {
            "row_status": "INVALID_REQUIRED",
            "required_errors": ["monthly is required and must be a number"],
            "moderate_warnings": ["expires date is missing or invalid"],
        },
        {
            "row_status": "INVALID_REQUIRED",
            "required_errors": ["monthly is required and must be a number"],
            "moderate_warnings": ["term_months is not in the expected set"],
        },
    ]

    health = compute_dealer_health(rows)

    assert health["status"] == "FAIL"
    assert health["total_rows"] == 2
    assert health["valid_rows"] == 0
    assert health["invalid_required_rows"] == 2
    assert health["attention_rows"] == 0
    assert health["top_issues"] == [
        "monthly is required and must be a number",
        "expires date is missing or invalid",
        "term_months is not in the expected set",
    ]


def test_dealer_health_needs_attention_when_attention_rows_exist():
    rows = [
        {
            "row_status": "VALID",
            "required_errors": [],
            "moderate_warnings": ["msrp provided but invalid"],
        },
        {
            "row_status": "ATTENTION_MODERATE",
            "required_errors": [],
            "moderate_warnings": ["expires date is before the run date"],
        },
    ]

    health = compute_dealer_health(rows)

    assert health["status"] == "NEEDS_ATTENTION"
    assert health["valid_rows"] == 1
    assert health["invalid_required_rows"] == 0
    assert health["attention_rows"] == 1
    assert set(health["top_issues"]) == {
        "msrp provided but invalid",
        "expires date is before the run date",
    }


def test_dealer_health_ok_when_majority_valid_and_no_attention():
    rows = [
        {"row_status": "VALID", "required_errors": [], "moderate_warnings": []},
        {"row_status": "VALID", "required_errors": [], "moderate_warnings": []},
    ]

    health = compute_dealer_health(rows)

    assert health["status"] == "OK"
    assert health["total_rows"] == 2
    assert health["valid_rows"] == 2
    assert health["invalid_required_rows"] == 0
    assert health["attention_rows"] == 0
    assert health["top_issues"] == []

def test_record_dealer_result_normalizes_common_aliases():
    fixed_now = datetime(2024, 1, 1)
    reset_monitor_state(now=fixed_now)

    record_dealer_result(
        "Dealer A",
        [
            {
                "Model": "Camry",
                "Monthly ($)": "$199",
                "Due at Signing ($)": "$1,999",
                "Term (months)": "36",
                "Expires": "01/05/2026",
                "MSRP ($)": "$28000",
            }
        ],
        run_date=date(2024, 1, 1),
        now=fixed_now,
    )

    dealer_state = SCRAPER_MONITOR["dealers"]["Dealer A"]

    assert dealer_state["status"] == "OK"
    assert dealer_state["total_rows"] == 1
    assert dealer_state["invalid_required_rows"] == 0
    assert dealer_state["attention_rows"] == 0