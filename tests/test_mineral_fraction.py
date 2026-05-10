from fractions import Fraction

from velix.validators import parse_mineral_fraction


def test_simple_fraction():
    result = parse_mineral_fraction("an undivided 1/64 interest")
    assert result is not None
    assert result.fraction == Fraction(1, 64)
    assert result.is_power_of_two_denominator is True
    assert result.reduced == "1/64"


def test_unreduced_fraction_gets_reduced():
    result = parse_mineral_fraction("8/64")
    assert result is not None
    assert result.fraction == Fraction(1, 8)
    assert result.reduced == "1/8"


def test_non_power_of_two_flagged():
    # 5/192 reduces to 5/192, denominator 192 = 2^6 * 3 — not a power of two.
    result = parse_mineral_fraction("5/192")
    assert result is not None
    assert result.is_power_of_two_denominator is False


def test_decimal_form():
    result = parse_mineral_fraction("0.015625")
    assert result is not None
    assert result.fraction == Fraction(1, 64)


def test_word_form():
    result = parse_mineral_fraction("an undivided one sixty-fourth interest")
    assert result is not None
    assert result.fraction == Fraction(1, 64)


def test_zero_denominator_returns_none():
    assert parse_mineral_fraction("3/0") is None


def test_numerator_greater_than_denominator_returns_none():
    assert parse_mineral_fraction("3/2") is None


def test_no_fraction_in_text_returns_none():
    assert parse_mineral_fraction("the lessor hereby grants") is None
