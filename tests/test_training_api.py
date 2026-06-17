from __future__ import annotations

import unittest

from api import question_to_payload, settings_from_payload
from bridge_trainer.bidding import BidRecommendation, RuleSettings
from bridge_trainer.cards import Card
from bridge_trainer.evaluator import HandEvaluation
from bridge_trainer.training import (
    PREEMPT_OPENINGS,
    STRONG_OPENINGS,
    TrainingQuestion,
    build_acceptable_bids,
    choose_vulnerability,
    generate_opener_rebid_question,
    generate_responder_rebid_question,
    generate_response_question,
    supported_openings_for_category,
)


class AcceptableBidTests(unittest.TestCase):
    def test_opening_low_minors_are_mutually_acceptable(self) -> None:
        bids = build_acceptable_bids("1♣", ["Pass", "1♣", "1♦"], mode="opening")
        self.assertIn("1♣", bids)
        self.assertIn("1♦", bids)

    def test_opening_major_alternative_is_acceptable(self) -> None:
        bids = build_acceptable_bids("1♥", ["Pass", "1♥", "1♠"], mode="opening")
        self.assertIn("1♥", bids)
        self.assertIn("1♠", bids)

    def test_response_to_one_nt_accepts_two_nt_and_three_nt_band(self) -> None:
        bids = build_acceptable_bids("3NT", ["Pass", "2NT", "3NT"], mode="response", opener_bid="1NT")
        self.assertEqual(bids, ["3NT", "2NT"])

    def test_response_major_raise_accepts_adjacent_levels(self) -> None:
        bids = build_acceptable_bids("3♥", ["Pass", "2♥", "3♥", "4♥"], mode="response", opener_bid="1♥")
        self.assertIn("2♥", bids)
        self.assertIn("3♥", bids)
        self.assertIn("4♥", bids)

    def test_response_bergen_weak_over_one_heart_accepts_three_club_alias(self) -> None:
        bids = build_acceptable_bids("3♣", ["Pass", "2♥", "3♣", "3♦", "3♥", "4♥"], mode="response", opener_bid="1♥")
        self.assertIn("2♥", bids)
        self.assertIn("3♣", bids)

    def test_pass_has_no_extra_acceptable_bid(self) -> None:
        self.assertEqual(build_acceptable_bids("Pass", ["Pass", "1♣"], mode="opening"), ["Pass"])


class TrainingGenerationTests(unittest.TestCase):
    def test_response_question_respects_requested_one_nt_opener(self) -> None:
        question = generate_response_question(seed=100, opener_bid="1NT", settings=RuleSettings())
        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.mode, "应叫训练")
        self.assertIn(question.recommendation.bid, question.choices)

    def test_response_question_respects_requested_strong_two_club_opener(self) -> None:
        question = generate_response_question(seed=100, opener_bid="2♣", settings=RuleSettings())
        self.assertEqual(question.opener_bid, "2♣")
        self.assertEqual(question.recommendation.bid, "2♦")

    def test_response_question_respects_requested_two_nt_opener(self) -> None:
        question = generate_response_question(seed=100, opener_bid="2NT", settings=RuleSettings())
        self.assertEqual(question.opener_bid, "2NT")

    def test_supported_openings_for_strong_category_has_no_random_and_no_two_diamond(self) -> None:
        self.assertEqual(supported_openings_for_category("强开叫"), STRONG_OPENINGS)
        self.assertNotIn("2♦", supported_openings_for_category("强开叫"))

    def test_response_question_random_preempt_category_stays_in_preempts(self) -> None:
        question = generate_response_question(seed=100, settings=RuleSettings(), opener_category="阻击叫")
        self.assertIn(question.opener_bid, PREEMPT_OPENINGS)

    def test_response_question_accepts_requested_preempt_opener(self) -> None:
        question = generate_response_question(seed=100, opener_bid="3♦", settings=RuleSettings(), opener_category="阻击叫")
        self.assertEqual(question.opener_bid, "3♦")

    def test_opener_rebid_question_respects_requested_one_nt_opener(self) -> None:
        question = generate_opener_rebid_question(seed=100, settings=RuleSettings(), opener_bid="1NT")
        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.mode, "开叫者再叫训练")
        self.assertTrue(question.auction.startswith("1NT-Pass-"))

    def test_responder_rebid_question_respects_requested_one_nt_opener(self) -> None:
        question = generate_responder_rebid_question(seed=100, settings=RuleSettings(), opener_bid="1NT")
        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.mode, "应叫者第二次应叫训练")
        self.assertTrue(question.auction.startswith("1NT-Pass-"))

    def test_vulnerability_is_deterministic_by_seed(self) -> None:
        self.assertEqual(choose_vulnerability(0), "双方无局")
        self.assertEqual(choose_vulnerability(1), "南北有局")
        self.assertEqual(choose_vulnerability(2), "东西有局")
        self.assertEqual(choose_vulnerability(3), "双方有局")
        self.assertEqual(choose_vulnerability(4), "双方无局")


class ApiHelperTests(unittest.TestCase):
    def test_settings_from_payload_clamps_aggressiveness_and_applies_overrides(self) -> None:
        settings = settings_from_payload(
            {
                "opening_min_hcp": 11,
                "one_nt_min": 14,
                "one_nt_max": 16,
                "scoring_mode": "MP",
                "respect_vulnerability": False,
                "game_aggressiveness": 9,
            }
        )
        self.assertEqual(settings.opening_min_hcp, 11)
        self.assertEqual(settings.one_nt_min, 14)
        self.assertEqual(settings.one_nt_max, 16)
        self.assertEqual(settings.scoring_mode, "MP")
        self.assertFalse(settings.respect_vulnerability)
        self.assertEqual(settings.game_aggressiveness, 1)

    def test_question_to_payload_contains_frontend_contract_fields(self) -> None:
        hand = [
            Card("S", "A"),
            Card("S", "K"),
            Card("S", "2"),
            Card("H", "Q"),
            Card("H", "3"),
            Card("H", "4"),
            Card("D", "J"),
            Card("D", "5"),
            Card("D", "6"),
            Card("D", "7"),
            Card("C", "8"),
            Card("C", "9"),
            Card("C", "10"),
        ]
        evaluation = HandEvaluation(
            hcp=10,
            lengths={"S": 3, "H": 3, "D": 4, "C": 3},
            shape="3-3-4-3",
            balanced=True,
            longest_suits=["D"],
        )
        question = TrainingQuestion(
            hand=hand,
            evaluation=evaluation,
            recommendation=BidRecommendation("1NT", "说明", "规则"),
            vulnerability="双方无局",
            choices=["Pass", "1NT"],
            legal_choices=["Pass", "1NT"],
            acceptable_bids=["1NT"],
            mode="测试模式",
            auction="1♣-Pass-?",
            opener_bid="1♣",
        )
        payload = question_to_payload(question, seed=123)
        self.assertEqual(payload["seed"], 123)
        self.assertEqual(payload["app_version"], "v0.1.0")
        self.assertIn("build_time", payload)
        self.assertEqual(payload["recommendation"]["bid"], "1NT")
        self.assertEqual(payload["evaluation"]["lengths"], {"S": 3, "H": 3, "D": 4, "C": 3})
        self.assertEqual(payload["acceptable_bids"], ["1NT"])
        self.assertEqual(len(payload["hand"]), 13)


if __name__ == "__main__":
    unittest.main()
