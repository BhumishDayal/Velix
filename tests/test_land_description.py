from velix.validators import parse_land_description


def test_full_canonical_form():
    desc = parse_land_description(
        "NE/4 of SE/4, Section 12, Township 5 North, Range 7 West"
    )
    assert desc is not None
    assert desc.section == 12
    assert desc.township_number == 5
    assert desc.township_dir == "N"
    assert desc.range_number == 7
    assert desc.range_dir == "W"
    assert desc.aliquots == ("NE/4", "SE/4")


def test_abbreviated_form():
    desc = parse_land_description("N/2 SW/4 NE/4 Sec. 12, T5N, R7W")
    assert desc is not None
    assert desc.section == 12
    assert desc.aliquots == ("N/2", "SW/4", "NE/4")


def test_word_form_quarter():
    desc = parse_land_description(
        "the Northeast Quarter of Section 3, T2S, R4E, 6th P.M."
    )
    assert desc is not None
    assert desc.section == 3
    assert desc.township_dir == "S"
    assert desc.range_dir == "E"
    assert "NE/4" in desc.aliquots


def test_invalid_section_returns_none():
    assert parse_land_description("Section 99, T5N, R7W") is None


def test_missing_township_returns_none():
    assert parse_land_description("NE/4 of Section 12, Range 7 West") is None


def test_invalid_township_direction():
    # Township must be N/S, range must be E/W. Reject swapped variants.
    assert parse_land_description("Section 12, T5E, R7W") is None


def test_zero_township_returns_none():
    assert parse_land_description("Section 12, T0N, R7W") is None
