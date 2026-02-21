from w2_agent.w2_validation import parse_w2_fields, validate_w2_fields


def test_parse_w2_fields_extracts_core_boxes_and_codes() -> None:
    text = """
    Form W-2
    1 Wages, tips, other compensation 52,345.67
    2 Federal income tax withheld 6,789.01
    3 Social security wages 52,345.67
    5 Medicare wages and tips 52,345.67
    12a D 2,000.00
    12b DD 426.83
    16 State wages, tips, etc. 52,345.67
    17 State income tax 1,250.00
    """
    parsed = parse_w2_fields(text)

    assert parsed["box1_wages"] == 52345.67
    assert parsed["box2_fed_withholding"] == 6789.01
    assert parsed["box3_ss_wages"] == 52345.67
    assert parsed["box5_medicare_wages"] == 52345.67
    assert parsed["state_wages"] == 52345.67
    assert parsed["state_withholding"] == 1250.00
    assert parsed["box12_codes"] == [("D", 2000.00), ("DD", 426.83)]


def test_parse_w2_fields_handles_split_number_format() -> None:
    text = """
    Box 1 of W-2 5 262 70
    Box 3 of W-2 5 262 70
    Box 5 of W-2 5 262 70
    """
    parsed = parse_w2_fields(text)

    assert parsed["box1_wages"] == 5262.70
    assert parsed["box3_ss_wages"] == 5262.70
    assert parsed["box5_medicare_wages"] == 5262.70


def test_validate_w2_fields_warns_for_missing_fields() -> None:
    parsed = {
        "box1_wages": 1000.00,
        "box2_fed_withholding": None,
        "box3_ss_wages": None,
        "box5_medicare_wages": None,
        "state_wages": None,
        "state_withholding": None,
        "local_wages": None,
        "local_withholding": None,
        "box12_codes": [],
    }

    issues = validate_w2_fields(parsed)
    codes = {issue.code for issue in issues}

    assert "MISSING_FIELD" in codes
    assert "BOX12_NOT_FOUND" in codes


def test_validate_w2_fields_flags_extreme_withholding_ratio() -> None:
    parsed = {
        "box1_wages": 1000.00,
        "box2_fed_withholding": 800.00,
        "box3_ss_wages": 1000.00,
        "box5_medicare_wages": 1000.00,
        "state_wages": None,
        "state_withholding": None,
        "local_wages": None,
        "local_withholding": None,
        "box12_codes": [("D", 50.0)],
    }

    issues = validate_w2_fields(parsed)
    codes = {issue.code for issue in issues}

    assert "HIGH_WITHHOLDING_RATIO" in codes
