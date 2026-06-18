from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from api import check_answer, create_question, health, question_to_payload, settings_from_payload
from bridge_trainer.bidding import BidRecommendation, RuleSettings
from bridge_trainer.cards import Card
from bridge_trainer.evaluator import HandEvaluation
from bridge_trainer.training import (
    PREEMPT_OPENINGS,
    STRONG_OPENINGS,
    TrainingQuestion,
    build_acceptable_bids,
    choose_vulnerability,
    generate_opening_question,
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

    def test_opening_nt_band_accepts_two_nt_and_three_nt(self) -> None:
        bids = build_acceptable_bids("2NT", ["Pass", "2NT", "3NT"], mode="opening")
        self.assertIn("2NT", bids)
        self.assertIn("3NT", bids)

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

    def test_pass_recommended_without_pass_in_legal_choices_still_returns_pass(self) -> None:
        self.assertEqual(build_acceptable_bids("Pass", ["1♣"], mode="opening"), ["Pass"])

    def test_non_contract_recommended_bid_returns_itself(self) -> None:
        self.assertEqual(build_acceptable_bids("X", ["Pass", "X"], mode="response"), ["X"])

    def test_opener_rebid_nt_band_adds_adjacent_nt_levels(self) -> None:
        bids = build_acceptable_bids("2NT", ["Pass", "1NT", "2NT", "3NT"], mode="opener_rebid", response_bid="1♥")
        self.assertIn("1NT", bids)
        self.assertIn("2NT", bids)
        self.assertIn("3NT", bids)

    def test_responder_rebid_nt_over_opener_nt_adds_two_nt_and_three_nt(self) -> None:
        bids = build_acceptable_bids(
            "3NT",
            ["Pass", "2NT", "3NT", "4NT"],
            mode="responder_rebid",
            opener_rebid_bid="2NT",
        )
        self.assertIn("2NT", bids)
        self.assertIn("3NT", bids)

    def test_responder_rebid_major_support_adds_adjacent_raise_levels(self) -> None:
        bids = build_acceptable_bids(
            "3♥",
            ["Pass", "2♥", "3♥", "4♥"],
            mode="responder_rebid",
            response_bid="2♥",
            opener_rebid_bid="2♦",
        )
        self.assertIn("2♥", bids)
        self.assertIn("3♥", bids)
        self.assertIn("4♥", bids)

    def test_opener_rebid_one_nt_accepts_two_nt(self) -> None:
        bids = build_acceptable_bids("1NT", ["Pass", "1NT", "2NT"], mode="opener_rebid")
        self.assertEqual(bids, ["1NT", "2NT"])

    def test_opener_rebid_one_level_new_suit_accepts_one_nt(self) -> None:
        bids = build_acceptable_bids(
            "1♠",
            ["Pass", "1♠", "1NT", "2♣", "2♦", "2♥"],
            mode="opener_rebid",
            opener_bid="1♣",
            response_bid="1♥",
        )
        self.assertIn("1♠", bids)
        self.assertIn("1NT", bids)

    def test_opener_rebid_two_level_new_suit_accepts_one_nt_after_one_level_sequence(self) -> None:
        bids = build_acceptable_bids(
            "2♣",
            ["Pass", "1NT", "2♣", "2♦", "2♠", "2NT"],
            mode="opener_rebid",
            opener_bid="1♦",
            response_bid="1♥",
        )
        self.assertIn("2♣", bids)
        self.assertIn("1NT", bids)

    def test_opener_rebid_one_nt_after_one_level_sequence_accepts_two_clubs(self) -> None:
        bids = build_acceptable_bids(
            "1NT",
            ["Pass", "1NT", "2♣", "2♦", "2NT"],
            mode="opener_rebid",
            opener_bid="1♦",
            response_bid="1♥",
        )
        self.assertIn("1NT", bids)
        self.assertIn("2♣", bids)

    def test_opener_rebid_three_nt_accepts_two_nt(self) -> None:
        bids = build_acceptable_bids("3NT", ["Pass", "2NT", "3NT"], mode="opener_rebid")
        self.assertEqual(bids, ["3NT", "2NT"])

    def test_opener_rebid_three_nt_with_nt_response_contract(self) -> None:
        bids = build_acceptable_bids("3NT", ["Pass", "2NT", "3NT", "4NT"], mode="opener_rebid", response_bid="2NT")
        self.assertIn("2NT", bids)
        self.assertIn("3NT", bids)

    def test_opener_rebid_same_strain_adds_adjacent_levels(self) -> None:
        bids = build_acceptable_bids(
            "3♥",
            ["Pass", "2♥", "3♥", "4♥"],
            mode="opener_rebid",
            response_bid="2♥",
            opener_bid="1♥",
        )
        self.assertIn("2♥", bids)

    def test_responder_rebid_nt_with_response_nt_contract(self) -> None:
        bids = build_acceptable_bids(
            "3NT",
            ["Pass", "2NT", "3NT", "4NT"],
            mode="responder_rebid",
            response_bid="2NT",
            opener_rebid_bid="2NT",
        )
        self.assertIn("2NT", bids)
        self.assertIn("3NT", bids)

    def test_responder_rebid_same_as_opener_rebid_suit_adds_adjacent(self) -> None:
        bids = build_acceptable_bids(
            "3♦",
            ["Pass", "2♦", "3♦", "4♦"],
            mode="responder_rebid",
            opener_rebid_bid="2♦",
        )
        self.assertIn("2♦", bids)
        self.assertIn("3♦", bids)
        self.assertIn("4♦", bids)

    def test_neighbors_skip_non_contract_choices(self) -> None:
        bids = build_acceptable_bids("2NT", ["Pass", "2NT", "X", "3NT"], mode="response")
        self.assertIn("2NT", bids)
        self.assertIn("3NT", bids)


class TrainingGenerationTests(unittest.TestCase):
    def test_opening_question_generation_has_consistent_fields(self) -> None:
        question = generate_opening_question(seed=100, settings=RuleSettings())
        self.assertEqual(question.mode, "开叫训练")
        self.assertIn(question.recommendation.bid, question.choices)
        self.assertIn(question.recommendation.bid, question.acceptable_bids)

    def test_response_question_respects_requested_one_nt_opener(self) -> None:
        question = generate_response_question(seed=100, opener_bid="1NT", settings=RuleSettings())
        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.mode, "应叫训练")
        self.assertIn(question.recommendation.bid, question.choices)
    def test_supported_openings_for_one_level_category_matches_constant(self) -> None:
        self.assertEqual(supported_openings_for_category("一阶定约"), {"1♣", "1♦", "1♥", "1♠", "1NT"})

    def test_response_question_invalid_requested_opener_falls_back_to_supported(self) -> None:
        question = generate_response_question(seed=100, opener_bid="7NT", settings=RuleSettings())
        self.assertIn(question.opener_bid, supported_openings_for_category(None))

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

    def test_supported_openings_for_preempt_category_matches_constant(self) -> None:
        self.assertEqual(supported_openings_for_category("阻击叫"), PREEMPT_OPENINGS)

    def test_response_question_random_preempt_category_stays_in_preempts(self) -> None:
        question = generate_response_question(seed=100, settings=RuleSettings(), opener_category="阻击叫")
        self.assertIn(question.opener_bid, PREEMPT_OPENINGS)

    def test_generate_response_question_falls_back_to_opening_when_no_supported_opening_found(self) -> None:
        sentinel = generate_opening_question(seed=100, settings=RuleSettings())
        with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("Pass", "x", "x")):
            with patch("bridge_trainer.training.generate_opening_question", return_value=sentinel):
                question = generate_response_question(seed=100, settings=RuleSettings())
        self.assertIs(question, sentinel)

    def test_response_question_accepts_requested_preempt_opener(self) -> None:
        question = generate_response_question(seed=100, opener_bid="3♦", settings=RuleSettings(), opener_category="阻击叫")
        self.assertEqual(question.opener_bid, "3♦")

    def test_opener_rebid_question_respects_requested_one_nt_opener(self) -> None:
        question = generate_opener_rebid_question(seed=100, settings=RuleSettings(), opener_bid="1NT")
        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.mode, "开叫者再叫训练")
        self.assertTrue(question.auction.startswith("1NT-"))

    def test_generate_opener_rebid_question_skips_pass_response_for_non_preempt(self) -> None:
        sentinel = generate_opening_question(seed=100, settings=RuleSettings())
        with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("1♣", "x", "x")):
            with patch("bridge_trainer.training.recommend_response", return_value=BidRecommendation("Pass", "x", "x")):
                with patch("bridge_trainer.training.generate_response_question", return_value=sentinel):
                    question = generate_opener_rebid_question(seed=100, settings=RuleSettings())
        self.assertIs(question, sentinel)

    def test_opener_rebid_question_invalid_requested_opener_falls_back_to_supported(self) -> None:
        question = generate_opener_rebid_question(seed=100, settings=RuleSettings(), opener_bid="7NT")
        self.assertIn(question.opener_bid, supported_openings_for_category(None))

    def test_responder_rebid_question_respects_requested_one_nt_opener(self) -> None:
        question = generate_responder_rebid_question(seed=100, settings=RuleSettings(), opener_bid="1NT")
        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.mode, "应叫者第二次应叫训练")
        self.assertTrue(question.auction.startswith("1NT-Pass-"))

    def test_generate_responder_rebid_question_skips_when_opener_rebid_is_pass(self) -> None:
        sentinel = generate_opening_question(seed=100, settings=RuleSettings())
        with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("1♣", "x", "x")):
            with patch("bridge_trainer.training.recommend_response", return_value=BidRecommendation("1♥", "x", "x")):
                with patch("bridge_trainer.training.recommend_opener_rebid", return_value=BidRecommendation("Pass", "x", "x")):
                    with patch("bridge_trainer.training.generate_response_question", return_value=sentinel):
                        question = generate_responder_rebid_question(seed=100, settings=RuleSettings())
        self.assertIs(question, sentinel)

    def test_responder_rebid_question_invalid_requested_opener_falls_back_to_supported(self) -> None:
        question = generate_responder_rebid_question(seed=100, settings=RuleSettings(), opener_bid="7NT")
        self.assertIn(question.opener_bid, supported_openings_for_category(None))

    def test_vulnerability_is_deterministic_by_seed(self) -> None:
        self.assertEqual(choose_vulnerability(0), "双方无局")
        self.assertEqual(choose_vulnerability(1), "南北有局")
        self.assertEqual(choose_vulnerability(2), "东西有局")
        self.assertEqual(choose_vulnerability(3), "双方有局")
        self.assertEqual(choose_vulnerability(4), "双方无局")

    def test_supported_openings_for_unknown_category_returns_all_supported(self) -> None:
        self.assertEqual(
            supported_openings_for_category("未知分类"),
            supported_openings_for_category(None),
        )

    def test_choose_vulnerability_without_seed_uses_random_choice(self) -> None:
        with patch("random.choice", return_value="南北有局"):
            self.assertEqual(choose_vulnerability(None), "南北有局")

    def test_generate_opener_rebid_question_falls_back_to_response_question_when_no_sequence(self) -> None:
        sentinel = generate_opening_question(seed=1, settings=RuleSettings())
        with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("Pass", "x", "x")):
            with patch("bridge_trainer.training.generate_response_question", return_value=sentinel) as mock_fallback:
                result = generate_opener_rebid_question(seed=1, settings=RuleSettings())
        self.assertIs(result, sentinel)
        self.assertTrue(mock_fallback.called)

    def test_generate_responder_rebid_question_falls_back_when_response_is_pass(self) -> None:
        sentinel = generate_opening_question(seed=1, settings=RuleSettings())
        with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("1♣", "x", "x")):
            with patch("bridge_trainer.training.recommend_response", return_value=BidRecommendation("Pass", "x", "x")):
                with patch("bridge_trainer.training.generate_response_question", return_value=sentinel) as mock_fallback:
                    result = generate_responder_rebid_question(seed=1, settings=RuleSettings())
        self.assertIs(result, sentinel)
        self.assertTrue(mock_fallback.called)


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


class ApiEndpointTests(unittest.TestCase):
    class _DummyRequest:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        async def json(self) -> dict:
            return self._payload

    def test_health_endpoint_returns_status_ok(self) -> None:
        response = asyncio.run(health(None))
        self.assertEqual(response.status_code, 200)
        data = response.body.decode("utf-8")
        self.assertIn('"status":"ok"', data)
        self.assertIn('"app_version"', data)
        self.assertIn('"build_time"', data)

    def test_create_question_response_mode_returns_required_fields(self) -> None:
        req = self._DummyRequest({"mode": "response", "seed": 100, "opener_bid": "1NT", "settings": {}})
        response = asyncio.run(create_question(req))
        self.assertEqual(response.status_code, 200)
        data = response.body.decode("utf-8")
        self.assertIn('"mode":"应叫训练"', data)
        self.assertIn('"seed":100', data)
        self.assertIn('"recommendation"', data)
        self.assertIn('"choices"', data)
        self.assertIn('"acceptable_bids"', data)

    def test_create_question_opener_rebid_mode(self) -> None:
        req = self._DummyRequest({"mode": "opener_rebid", "seed": 100, "opener_bid": "1NT", "settings": {}})
        response = asyncio.run(create_question(req))
        self.assertEqual(response.status_code, 200)
        data = response.body.decode("utf-8")
        self.assertIn('"mode":"开叫者再叫训练"', data)
        self.assertIn('"seed":100', data)

    def test_create_question_responder_rebid_mode(self) -> None:
        req = self._DummyRequest({"mode": "responder_rebid", "seed": 100, "opener_bid": "1NT", "settings": {}})
        response = asyncio.run(create_question(req))
        self.assertEqual(response.status_code, 200)
        data = response.body.decode("utf-8")
        self.assertIn('"mode":"应叫者第二次应叫训练"', data)
        self.assertIn('"seed":100', data)

    def test_create_question_unknown_mode_falls_back_to_opening(self) -> None:
        req = self._DummyRequest({"mode": "unknown", "seed": 100, "settings": {}})
        response = asyncio.run(create_question(req))
        self.assertEqual(response.status_code, 200)
        data = response.body.decode("utf-8")
        self.assertIn('"mode":"开叫训练"', data)
        self.assertIn('"seed":100', data)

    def test_check_answer_primary_grade(self) -> None:
        req = self._DummyRequest(
            {
                "selected_bid": "3NT",
                "recommended_bid": "3NT",
                "acceptable_bids": ["3NT", "2NT"],
                "explanation": "x",
                "rule_name": "r",
            }
        )
        response = asyncio.run(check_answer(req))
        self.assertEqual(response.status_code, 200)
        data = response.body.decode("utf-8")
        self.assertIn('"correct":true', data)
        self.assertIn('"grade":"primary"', data)

    def test_check_answer_acceptable_grade(self) -> None:
        req = self._DummyRequest(
            {
                "selected_bid": "2NT",
                "recommended_bid": "3NT",
                "acceptable_bids": ["3NT", "2NT"],
            }
        )
        response = asyncio.run(check_answer(req))
        self.assertEqual(response.status_code, 200)
        data = response.body.decode("utf-8")
        self.assertIn('"correct":true', data)
        self.assertIn('"grade":"acceptable"', data)

    def test_check_answer_incorrect_grade(self) -> None:
        req = self._DummyRequest(
            {
                "selected_bid": "Pass",
                "recommended_bid": "3NT",
                "acceptable_bids": ["3NT", "2NT"],
            }
        )
        response = asyncio.run(check_answer(req))
        self.assertEqual(response.status_code, 200)
        data = response.body.decode("utf-8")
        self.assertIn('"correct":false', data)
        self.assertIn('"grade":"incorrect"', data)


if __name__ == "__main__":
    unittest.main()
