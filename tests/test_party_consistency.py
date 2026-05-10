from velix.validators import check_party_chain_consistency


def test_clean_chain():
    chain = [
        ("Smith Family Trust", "ABC Minerals LLC"),
        ("ABC Minerals LLC", "XYZ Energy Corporation"),
        ("XYZ Energy Corp", "Permian Basin Holdings LP"),
    ]
    breaks = check_party_chain_consistency(chain)
    assert breaks == []


def test_broken_chain_detected():
    chain = [
        ("Smith Family Trust", "ABC Minerals LLC"),
        ("Totally Different LLC", "XYZ Energy Corp"),
    ]
    breaks = check_party_chain_consistency(chain)
    assert len(breaks) == 1
    assert breaks[0].from_doc_index == 0


def test_entity_suffix_normalization():
    chain = [
        ("X", "ABC Minerals, LLC"),
        ("ABC Minerals Inc.", "Y"),
    ]
    breaks = check_party_chain_consistency(chain)
    # Tokens overlap (ABC, Minerals), suffix differences should not break.
    assert breaks == []


def test_empty_chain():
    assert check_party_chain_consistency([]) == []


def test_single_doc_chain():
    assert check_party_chain_consistency([("A", "B")]) == []


def test_tolerates_ocr_noise_in_party_names():
    chain = [
        ("Smith Family Trust", "ABC Minerals LLC"),
        ("ABC Mineralz LLC", "XYZ Energy Corp"),
        ("XYZ Energ Corp", "Permian Basin Holdings LP"),
    ]
    breaks = check_party_chain_consistency(chain)
    assert breaks == []


def test_distinct_parties_still_break_under_fuzzy_match():
    chain = [
        ("X", "Permian Basin Holdings LP"),
        ("Delaware Basin Resources LLC", "Y"),
    ]
    breaks = check_party_chain_consistency(chain)
    assert len(breaks) == 1
