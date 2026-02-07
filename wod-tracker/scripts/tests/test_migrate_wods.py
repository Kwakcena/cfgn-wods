"""Tests for migrate_wods module."""

import pytest

from migrate_wods import migrate_wods_data


class TestMigrateWodsData:
    """Tests for the wods.json migration function."""

    @pytest.mark.unit
    def test_strips_prefix_from_values(self) -> None:
        data = {
            "2026-02-06": "20260206 W.O.D!!\n\nFor time of: (in 23min)"
        }
        result = migrate_wods_data(data)
        assert result["2026-02-06"] == "For time of: (in 23min)"

    @pytest.mark.unit
    def test_rekeys_from_content_date(self) -> None:
        data = {
            "2023-01-25": "20230124 W.O.D!!\n\nFor time"
        }
        result = migrate_wods_data(data)
        assert "2023-01-24" in result
        assert "2023-01-25" not in result
        assert result["2023-01-24"] == "For time"

    @pytest.mark.unit
    def test_key_already_matches_content(self) -> None:
        data = {
            "2026-02-06": "20260206 W.O.D!!\n\nFor time"
        }
        result = migrate_wods_data(data)
        assert "2026-02-06" in result
        assert result["2026-02-06"] == "For time"

    @pytest.mark.unit
    def test_preserves_entry_without_prefix(self) -> None:
        data = {
            "2026-02-06": "For time of: 21-15-9 thrusters"
        }
        result = migrate_wods_data(data)
        assert result["2026-02-06"] == "For time of: 21-15-9 thrusters"

    @pytest.mark.unit
    def test_double_date_edge_case(self) -> None:
        data = {
            "2023-01-24": "20230124 W.O.D!!\n\n20230125 \nComplete as many rounds"
        }
        result = migrate_wods_data(data)
        assert result["2023-01-24"] == "20230125 \nComplete as many rounds"

    @pytest.mark.unit
    def test_sorted_descending(self) -> None:
        data = {
            "2023-01-02": "20230102 W.O.D!!\n\nFran",
            "2026-02-06": "20260206 W.O.D!!\n\nFor time",
            "2024-06-15": "20240615 W.O.D!!\n\nAmrap",
        }
        result = migrate_wods_data(data)
        keys = list(result.keys())
        assert keys == sorted(keys, reverse=True)

    @pytest.mark.unit
    def test_duplicate_key_conflict(self) -> None:
        data = {
            "2023-01-24": "20230124 W.O.D!!\n\nWorkout A",
            "2023-01-25": "20230124 W.O.D!!\n\nWorkout B",
        }
        result = migrate_wods_data(data)
        assert "2023-01-24" in result
        assert len(result) == 2
        # One should have -2 suffix
        assert "2023-01-24-2" in result or any(
            k.startswith("2023-01-24-") for k in result
        )

    @pytest.mark.unit
    def test_total_count_preserved(self) -> None:
        data = {
            "2026-02-06": "20260206 W.O.D!!\n\nA",
            "2026-02-05": "20260205 W.O.D!!\n\nB",
            "2026-02-04": "20260204 W.O.D!!\n\nC",
        }
        result = migrate_wods_data(data)
        assert len(result) == len(data)

    @pytest.mark.unit
    def test_empty_data(self) -> None:
        result = migrate_wods_data({})
        assert result == {}

    @pytest.mark.unit
    def test_mixed_with_and_without_prefix(self) -> None:
        data = {
            "2026-02-06": "20260206 W.O.D!!\n\nFor time",
            "2026-02-05": "Some workout without prefix",
        }
        result = migrate_wods_data(data)
        assert len(result) == 2
        assert result["2026-02-06"] == "For time"
        assert result["2026-02-05"] == "Some workout without prefix"
