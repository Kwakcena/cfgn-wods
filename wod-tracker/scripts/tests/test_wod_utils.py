"""Tests for wod_utils module."""

import pytest

from wod_utils import (
    extract_wod_date,
    strip_wod_date_prefix,
    clean_wod_text,
    process_wod_entry,
)


class TestExtractWodDate:
    """Tests for extract_wod_date() function."""

    @pytest.mark.unit
    def test_standard_format(self) -> None:
        assert extract_wod_date("20260206 W.O.D!!\n\nFor time of:") == "2026-02-06"

    @pytest.mark.unit
    def test_no_dots_in_wod(self) -> None:
        assert extract_wod_date("20260206 WOD!!\n\nFor time of:") == "2026-02-06"

    @pytest.mark.unit
    def test_single_dot_wod(self) -> None:
        assert extract_wod_date("20260206 W.O.D\n\nFor time of:") == "2026-02-06"

    @pytest.mark.unit
    def test_extra_spaces_before_wod(self) -> None:
        assert extract_wod_date("20260206   W.O.D!!\n\nFor time of:") == "2026-02-06"

    @pytest.mark.unit
    def test_no_wod_prefix(self) -> None:
        assert extract_wod_date("For time of: 21-15-9 thrusters") is None

    @pytest.mark.unit
    def test_empty_string(self) -> None:
        assert extract_wod_date("") is None

    @pytest.mark.unit
    def test_invalid_date_digits(self) -> None:
        assert extract_wod_date("99991399 W.O.D!!\n\nFor time") is None

    @pytest.mark.unit
    def test_double_date_content(self) -> None:
        text = "20230124 W.O.D!!\n\n20230125 \nComplete as many rounds"
        assert extract_wod_date(text) == "2023-01-24"

    @pytest.mark.unit
    def test_case_insensitive(self) -> None:
        assert extract_wod_date("20260206 w.o.d!!\n\nFor time") == "2026-02-06"

    @pytest.mark.unit
    def test_oldest_entry_format(self) -> None:
        assert extract_wod_date("20230102 W.O.D!!\n\n\"Fran\"") == "2023-01-02"

    @pytest.mark.unit
    def test_no_exclamation_marks(self) -> None:
        assert extract_wod_date("20260206 W.O.D\n\nFor time") == "2026-02-06"

    @pytest.mark.unit
    def test_only_digits_no_wod(self) -> None:
        assert extract_wod_date("20260206 some other text") is None


class TestStripWodDatePrefix:
    """Tests for strip_wod_date_prefix() function."""

    @pytest.mark.unit
    def test_standard_prefix_double_newline(self) -> None:
        text = "20260206 W.O.D!!\n\nFor time of: (in 23min)"
        assert strip_wod_date_prefix(text) == "For time of: (in 23min)"

    @pytest.mark.unit
    def test_standard_prefix_single_newline(self) -> None:
        text = "20260206 W.O.D!!\nFor time of:"
        assert strip_wod_date_prefix(text) == "For time of:"

    @pytest.mark.unit
    def test_prefix_with_extra_whitespace(self) -> None:
        text = "20260206 W.O.D!!  \n\n  For time of:"
        assert strip_wod_date_prefix(text) == "For time of:"

    @pytest.mark.unit
    def test_no_prefix(self) -> None:
        text = "For time of: 21-15-9 thrusters"
        assert strip_wod_date_prefix(text) == "For time of: 21-15-9 thrusters"

    @pytest.mark.unit
    def test_empty_string(self) -> None:
        assert strip_wod_date_prefix("") == ""

    @pytest.mark.unit
    def test_prefix_only(self) -> None:
        assert strip_wod_date_prefix("20260206 W.O.D!!") == ""

    @pytest.mark.unit
    def test_double_date_preserves_second(self) -> None:
        text = "20230124 W.O.D!!\n\n20230125 \nComplete as many rounds"
        assert strip_wod_date_prefix(text) == "20230125 \nComplete as many rounds"

    @pytest.mark.unit
    def test_without_exclamation(self) -> None:
        text = "20260206 W.O.D\n\nFor time of:"
        assert strip_wod_date_prefix(text) == "For time of:"

    @pytest.mark.unit
    def test_wod_no_dots(self) -> None:
        text = "20260206 WOD!!\n\nFor time of:"
        assert strip_wod_date_prefix(text) == "For time of:"

    @pytest.mark.unit
    def test_preserves_content_with_special_chars(self) -> None:
        text = "20260206 W.O.D!!\n\n♀ 24-inch box\n♂ 30-inch box"
        assert strip_wod_date_prefix(text) == "♀ 24-inch box\n♂ 30-inch box"

    @pytest.mark.unit
    def test_content_with_quoted_workout_name(self) -> None:
        text = '20260102 W.O.D!!\n\n"Fran"\nFor time of:\n21-15-9\nThrusters \npull ups'
        result = strip_wod_date_prefix(text)
        assert result.startswith('"Fran"')


class TestCleanWodText:
    """Tests for clean_wod_text() function."""

    @pytest.mark.unit
    def test_removes_promo_text(self) -> None:
        text = "For time:\n21-15-9#crossfit #크로스핏 crossfitgangnam  #크로스핏강남 cfgn cfgnej #언주역크로스핏 #크로스핏강남언주 언주역 학동역 역삼역 신논현역 논현로614  025556744"
        assert clean_wod_text(text) == "For time:\n21-15-9"

    @pytest.mark.unit
    def test_removes_promo_with_nbsp(self) -> None:
        text = "For time#crossfit #크로스핏 crossfitgangnam\xa0 #크로스핏강남 cfgn cfgnej #언주역크로스핏 #크로스핏강남언주 언주역 학동역 역삼역 신논현역 논현로614\xa0 025556744"
        assert clean_wod_text(text) == "For time"

    @pytest.mark.unit
    def test_strips_whitespace(self) -> None:
        assert clean_wod_text("  For time  ") == "For time"

    @pytest.mark.unit
    def test_no_promo_text(self) -> None:
        assert clean_wod_text("For time:\n21-15-9") == "For time:\n21-15-9"

    @pytest.mark.unit
    def test_removes_meta_description_prefix(self) -> None:
        text = '45 likes, 2 comments - cfgn_ej on January 6, 2026: "20260106 W.O.D!!\n\nFor time".'
        result = clean_wod_text(text)
        assert "likes" not in result
        assert "W.O.D" in result or "For time" in result

    @pytest.mark.unit
    def test_empty_string(self) -> None:
        assert clean_wod_text("") == ""


class TestProcessWodEntry:
    """Tests for process_wod_entry() function."""

    @pytest.mark.unit
    def test_standard_entry(self) -> None:
        text = "20260206 W.O.D!!\n\nFor time of: (in 23min)\n1000m bike erg"
        date_key, content = process_wod_entry(text)
        assert date_key == "2026-02-06"
        assert content == "For time of: (in 23min)\n1000m bike erg"
        assert "W.O.D" not in content

    @pytest.mark.unit
    def test_no_prefix_returns_none_key(self) -> None:
        text = "For time of: 21-15-9 thrusters"
        date_key, content = process_wod_entry(text)
        assert date_key is None
        assert content == "For time of: 21-15-9 thrusters"

    @pytest.mark.unit
    def test_double_date_entry(self) -> None:
        text = "20230124 W.O.D!!\n\n20230125 \nComplete as many rounds"
        date_key, content = process_wod_entry(text)
        assert date_key == "2023-01-24"
        assert content == "20230125 \nComplete as many rounds"

    @pytest.mark.unit
    def test_empty_content_after_prefix(self) -> None:
        text = "20260206 W.O.D!!"
        date_key, content = process_wod_entry(text)
        assert date_key == "2026-02-06"
        assert content == ""

    @pytest.mark.unit
    def test_preserves_workout_details(self) -> None:
        text = "20251231 W.O.D!!\n\nFor time:\n50 box jumps\n50 jumping pull ups"
        date_key, content = process_wod_entry(text)
        assert date_key == "2025-12-31"
        assert "50 box jumps" in content
        assert "50 jumping pull ups" in content
