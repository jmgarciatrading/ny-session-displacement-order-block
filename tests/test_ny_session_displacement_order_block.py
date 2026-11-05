from __future__ import annotations

import pathlib
import unittest
from dataclasses import dataclass


ROOT = pathlib.Path(__file__).resolve().parents[1]
PINE = ROOT / "NY_Session_Displacement_Order_Block.pine"


@dataclass(frozen=True)
class Bar:
    open: float
    high: float
    low: float
    close: float


def is_order_block(bars: list[Bar]) -> int:
    anchor, displacement = bars
    bullish = (
        anchor.close < anchor.open
        and displacement.close > displacement.open
        and displacement.close > anchor.high
    )
    bearish = (
        anchor.close > anchor.open
        and displacement.close < displacement.open
        and displacement.close < anchor.low
    )
    return 1 if bullish else -1 if bearish else 0


def in_window(now_minutes: int, start: int, end: int) -> bool:
    if start < end:
        return start <= now_minutes < end
    if start > end:
        return now_minutes >= start or now_minutes < end
    return True


def can_replace(active_direction: int, candidate_direction: int, mitigated: bool) -> bool:
    return active_direction == 0 or mitigated or candidate_direction != active_direction


def prior_swing(pivots: list[tuple[int, float]], order_block_bar: int):
    eligible = [pivot for pivot in pivots if pivot[0] < order_block_bar]
    return eligible[-1] if eligible else None


class DetectionTests(unittest.TestCase):
    def test_bullish_order_block(self):
        bars = [
            Bar(10.0, 10.2, 8.8, 9.0),
            Bar(9.1, 11.0, 9.0, 10.8),
        ]
        self.assertEqual(is_order_block(bars), 1)

    def test_bearish_order_block(self):
        bars = [
            Bar(9.0, 10.2, 8.8, 10.0),
            Bar(9.9, 10.0, 7.0, 7.2),
        ]
        self.assertEqual(is_order_block(bars), -1)

    def test_wrong_anchor_is_rejected(self):
        bars = [
            Bar(9.0, 10.2, 8.8, 10.0),
            Bar(10.1, 11.0, 10.0, 10.8),
        ]
        self.assertEqual(is_order_block(bars), 0)

    def test_candle_that_does_not_close_through_anchor_is_rejected(self):
        bars = [
            Bar(10.0, 10.2, 8.8, 9.0),
            Bar(9.1, 10.3, 9.0, 10.1),
        ]
        self.assertEqual(is_order_block(bars), 0)

    def test_window_is_half_open_and_supports_overnight(self):
        self.assertTrue(in_window(570, 570, 660))
        self.assertFalse(in_window(660, 570, 660))
        self.assertTrue(in_window(1380, 1320, 120))
        self.assertTrue(in_window(60, 1320, 120))
        self.assertFalse(in_window(720, 1320, 120))

    def test_unmitigated_same_direction_origin_is_retained(self):
        self.assertFalse(can_replace(-1, -1, mitigated=False))
        self.assertFalse(can_replace(1, 1, mitigated=False))

    def test_mitigated_origin_can_be_replaced(self):
        self.assertTrue(can_replace(-1, -1, mitigated=True))

    def test_opposite_direction_starts_new_move(self):
        self.assertTrue(can_replace(-1, 1, mitigated=False))

    def test_nearest_prior_swing_is_selected(self):
        self.assertEqual(prior_swing([(5, 12.0), (9, 15.0)], 10), (9, 15.0))

    def test_order_block_pivot_is_excluded(self):
        self.assertEqual(prior_swing([(5, 12.0), (10, 15.0)], 10), (5, 12.0))


class SourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PINE.read_text(encoding="utf-8")

    def test_is_v6_indicator_with_one_box(self):
        self.assertIn("//@version=6", self.source)
        self.assertIn('indicator("NY Window Displacement Order Block"', self.source)
        self.assertIn("max_boxes_count = 1", self.source)
        self.assertIn("max_labels_count = 1", self.source)

    def test_timezone_is_fixed_to_new_york(self):
        self.assertIn('const string NY_TIMEZONE = "America/New_York"', self.source)
        self.assertNotIn('input.string("America/New_York"', self.source)

    def test_entire_pattern_must_be_inside_window(self):
        self.assertIn(
            "f_isWithinNyWindow(1) and f_isWithinNyWindow(0)",
            self.source,
        )

    def test_entire_pattern_must_be_on_active_chart_day(self):
        self.assertIn("f_nyDateKey(last_bar_time)", self.source)
        self.assertIn(
            "f_isActiveChartDay(1) and f_isActiveChartDay(0)",
            self.source,
        )
        self.assertIn("patternInsideActiveDay and", self.source)
        self.assertNotIn("timenow", self.source)
        self.assertNotIn("chart.right_visible_bar_time", self.source)

    def test_stale_box_is_cleared_when_active_chart_day_changes(self):
        self.assertIn(
            "latestOrderBlockDateKey != activeChartNyDateKey", self.source
        )
        self.assertIn("latestOrderBlockDateKey := na", self.source)
        self.assertIn(
            "latestOrderBlockDateKey := activeChartNyDateKey", self.source
        )

    def test_previous_box_is_deleted_only_inside_replacement_policy(self):
        self.assertIn(
            "na(latestOrderBlock) or latestOrderBlockMitigated or directionChanged",
            self.source,
        )
        policy_at = self.source.index("if canReplace")
        delete_at = self.source.index("box.delete(latestOrderBlock)")
        create_at = self.source.index("latestOrderBlock := box.new")
        replacement_delete_at = self.source.index(
            "box.delete(latestOrderBlock)", policy_at
        )
        self.assertLess(replacement_delete_at, create_at)

    def test_mitigation_starts_after_creation(self):
        self.assertIn("bar_index > latestOrderBlockCreationBar", self.source)
        self.assertIn("high >= latestOrderBlockBottom", self.source)
        self.assertIn("low <= latestOrderBlockTop", self.source)

    def test_prior_swing_marker_excludes_order_block_candle(self):
        self.assertIn("latestSwingHighBar < orderBlockBar", self.source)
        self.assertIn("previousSwingHighBar < orderBlockBar", self.source)
        self.assertIn("latestSwingLowBar < orderBlockBar", self.source)
        self.assertIn("previousSwingLowBar < orderBlockBar", self.source)

    def test_marker_direction_matches_order_block(self):
        self.assertIn("label.style_arrowdown : label.style_arrowup", self.source)
        self.assertIn("label.delete(latestSwingMarker)", self.source)

    def test_detection_is_close_confirmed(self):
        self.assertGreaterEqual(self.source.count("barstate.isconfirmed"), 2)


if __name__ == "__main__":
    unittest.main()
