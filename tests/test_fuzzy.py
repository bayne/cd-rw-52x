"""Unit tests for cdrw.fuzzy."""

import pytest
from cdrw.fuzzy import fuzzy_match


def test_empty_pattern_matches_anything():
    ok, indices = fuzzy_match("", "anything")
    assert ok is True
    assert indices == []


def test_empty_pattern_matches_empty_string():
    ok, indices = fuzzy_match("", "")
    assert ok is True
    assert indices == []


def test_exact_match():
    ok, indices = fuzzy_match("abc", "abc")
    assert ok is True
    assert indices == [0, 1, 2]


def test_subsequence_match():
    ok, indices = fuzzy_match("ac", "abc")
    assert ok is True
    assert indices == [0, 2]


def test_no_match():
    ok, indices = fuzzy_match("xyz", "abc")
    assert ok is False
    assert indices == []


def test_partial_no_match():
    ok, indices = fuzzy_match("az", "abc")
    assert ok is False
    assert indices == []


def test_case_insensitive():
    ok, indices = fuzzy_match("ABC", "abc")
    assert ok is True
    assert indices == [0, 1, 2]


def test_case_insensitive_mixed():
    ok, indices = fuzzy_match("aBc", "AbC")
    assert ok is True
    assert indices == [0, 1, 2]


def test_indices_are_ascending():
    ok, indices = fuzzy_match("ac", "abcdef")
    assert ok is True
    assert indices == sorted(indices)


def test_match_picks_first_occurrence():
    """Pattern 'aa' in 'abac' should match positions 0 and 2."""
    ok, indices = fuzzy_match("aa", "abac")
    assert ok is True
    assert indices == [0, 2]


def test_single_char_pattern():
    ok, indices = fuzzy_match("x", "foxes")
    assert ok is True
    assert indices == [2]  # 'x' is at index 2 in "foxes"


def test_pattern_longer_than_text():
    ok, indices = fuzzy_match("abcde", "ab")
    assert ok is False
    assert indices == []


def test_no_match_returns_empty_indices():
    ok, indices = fuzzy_match("z", "abc")
    assert ok is False
    assert indices == []


def test_match_with_spaces():
    ok, indices = fuzzy_match("my proj", "my-project")
    # 'm','y',' ','p','r','o','j' — space won't match '-', so should fail
    assert ok is False


def test_match_skips_characters():
    ok, indices = fuzzy_match("mpr", "my-project")
    assert ok is True
    assert len(indices) == 3
