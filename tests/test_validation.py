from datetime import date

import pytest

from validation import validate_row


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