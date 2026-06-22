from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from api import check_answer, create_question, health, question_to_payload, settings_from_payload
from bridge_trainer.bidding import BidRecommendation, RuleSettings
from bridge_trainer.cards import Card
from bridge_trainer.evaluator import HandEvaluation
from bridge_trainer.training import (
    DEFAULT_SEARCH_ATTEMPTS,
    DIRECTED_OPENER_REBID_SEARCH_ATTEMPTS,
    DIRECTED_RESPONDER_REBID_SEARCH_ATTEMPTS,
    PREEMPT_OPENINGS,
    RESPONSE_FILTER_SEARCH_ATTEMPTS,
    REBID_FILTER_SEARCH_ATTEMPTS,
    STRONG_OPENINGS,
    TrainingQuestion,
    build_acceptable_bids,
    choose_vulnerability,
    deal_targeted,
    directed_sequence_attempt_budget,
    generate_opening_question,
    generate_opener_rebid_question,
    generate_responder_rebid_question,
    generate_response_question,
    get_sequence_constraints,
    iter_role_pairs,
    matches_common_opener_rebid_prefilter,
    matches_common_responder_rebid_prefilter,
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

    def test_opener_rebid_two_level_new_suit_accepts_repeat_major(self) -> None:
        bids = build_acceptable_bids(
            "2♣",
            ["Pass", "2♣", "2♥", "2NT", "3♣"],
            mode="opener_rebid",
            opener_bid="1♥",
            response_bid="1♠",
        )
        self.assertIn("2♣", bids)
        self.assertIn("2♥", bids)

    def test_opener_rebid_jacoby_two_nt_major_game_accepts_three_nt(self) -> None:
        bids = build_acceptable_bids(
            "4♥",
            ["Pass", "3NT", "4♥", "4NT"],
            mode="opener_rebid",
            opener_bid="1♥",
            response_bid="2NT",
        )
        self.assertIn("4♥", bids)
        self.assertIn("3NT", bids)

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
    @staticmethod
    def _evaluation(hcp: int, spades: int, hearts: int, diamonds: int, clubs: int, balanced: bool = False) -> HandEvaluation:
        lengths = {"S": spades, "H": hearts, "D": diamonds, "C": clubs}
        longest = max(lengths.values())
        return HandEvaluation(
            hcp=hcp,
            lengths=lengths,
            shape=f"{spades}-{hearts}-{diamonds}-{clubs}",
            balanced=balanced,
            longest_suits=[suit for suit, length in lengths.items() if length == longest],
        )

    def test_common_opener_rebid_prefilter_matches_jacoby_two_nt_profile(self) -> None:
        opener = self._evaluation(13, 2, 5, 3, 3, balanced=False)
        responder = self._evaluation(13, 3, 4, 3, 3, balanced=True)
        self.assertTrue(matches_common_opener_rebid_prefilter("1♥", "2NT", opener, responder, RuleSettings()))

    def test_common_opener_rebid_prefilter_rejects_nontransfer_profile(self) -> None:
        opener = self._evaluation(16, 3, 3, 4, 3, balanced=True)
        responder = self._evaluation(8, 3, 4, 3, 3, balanced=True)
        self.assertFalse(matches_common_opener_rebid_prefilter("1NT", "2♦", opener, responder, RuleSettings()))

    def test_common_responder_rebid_prefilter_matches_stayman_deny_profile(self) -> None:
        opener = self._evaluation(16, 3, 3, 4, 3, balanced=True)
        responder = self._evaluation(9, 4, 4, 3, 2, balanced=False)
        self.assertTrue(matches_common_responder_rebid_prefilter("1NT", "2♣", "2♦", opener, responder, RuleSettings()))

    def test_common_responder_rebid_prefilter_rejects_wrong_stayman_answer_profile(self) -> None:
        opener = self._evaluation(16, 3, 4, 3, 3, balanced=True)
        responder = self._evaluation(9, 4, 4, 3, 2, balanced=False)
        self.assertFalse(matches_common_responder_rebid_prefilter("1NT", "2♣", "2♦", opener, responder, RuleSettings()))

    def test_directed_sequence_attempt_budget_for_two_bid_target(self) -> None:
        attempts = directed_sequence_attempt_budget(opener_bid="1NT", response_bid="2♣")
        self.assertGreaterEqual(attempts, DIRECTED_OPENER_REBID_SEARCH_ATTEMPTS)

    def test_directed_sequence_attempt_budget_for_three_bid_target(self) -> None:
        attempts = directed_sequence_attempt_budget(opener_bid="1NT", response_bid="2♣", opener_rebid_bid="2♦")
        self.assertGreaterEqual(attempts, DIRECTED_RESPONDER_REBID_SEARCH_ATTEMPTS)

    def test_iter_role_pairs_includes_all_pairs_when_prioritized(self) -> None:
        hands = {
            "N": [Card("S", "A")],
            "E": [Card("S", "K")],
            "S": [Card("S", "Q")],
            "W": [Card("S", "J")],
        }
        pairs = iter_role_pairs(hands, prioritize_sequence=True, default_opener="S", default_responder="N")
        self.assertEqual(len(pairs), 12)

    def test_iter_role_pairs_only_default_pair_without_priority(self) -> None:
        hands = {
            "N": [Card("S", "A")],
            "E": [Card("S", "K")],
            "S": [Card("S", "Q")],
            "W": [Card("S", "J")],
        }
        pairs = iter_role_pairs(hands, prioritize_sequence=False, default_opener="S", default_responder="N")
        self.assertEqual(len(pairs), 1)

    def test_deal_targeted_finds_nt1_stayman_pair(self) -> None:
        settings = RuleSettings()
        constraints = get_sequence_constraints("1NT", "2\u2663", None, settings)
        self.assertIsNotNone(constraints)
        opener_c, responder_c = constraints  # type: ignore[misc]
        result = deal_targeted(opener_c, responder_c, seed=42)
        self.assertIsNotNone(result)
        opener_hand, responder_hand = result  # type: ignore[misc]
        self.assertTrue(opener_c(opener_hand))
        self.assertTrue(responder_c(responder_hand))

    def test_deal_targeted_finds_transfer_to_hearts_pair(self) -> None:
        settings = RuleSettings()
        constraints = get_sequence_constraints("1NT", "2\u2666", None, settings)
        self.assertIsNotNone(constraints)
        opener_c, responder_c = constraints  # type: ignore[misc]
        result = deal_targeted(opener_c, responder_c, seed=7)
        self.assertIsNotNone(result)
        _, responder_hand = result  # type: ignore[misc]
        from bridge_trainer.evaluator import evaluate_hand as _ev
        self.assertGreaterEqual(_ev(responder_hand).lengths["H"], 5)

    def test_get_sequence_constraints_returns_none_for_unknown_sequence(self) -> None:
        constraints = get_sequence_constraints("1\u2663", "1\u2666", None, RuleSettings())
        self.assertIsNone(constraints)

    def test_get_sequence_constraints_returns_constraints_for_stayman_no_major(self) -> None:
        settings = RuleSettings()
        constraints = get_sequence_constraints("1NT", "2\u2663", "2\u2666", settings)
        self.assertIsNotNone(constraints)

    def test_generate_opener_rebid_question_fast_path_returns_matching_sequence(self) -> None:
        q = generate_opener_rebid_question(seed=1, opener_bid="1NT", response_bid="2\u2663", settings=RuleSettings())
        self.assertEqual(q.opener_bid, "1NT")
        self.assertEqual(q.response_bid, "2\u2663")
        self.assertEqual(q.mode, "\u5f00\u53eb\u8005\u518d\u53eb\u8bad\u7ec3")

    def test_generate_responder_rebid_question_fast_path_returns_matching_sequence(self) -> None:
        q = generate_responder_rebid_question(
            seed=1, opener_bid="1NT", response_bid="2\u2663", opener_rebid_bid="2\u2666",
            settings=RuleSettings(),
        )
        self.assertEqual(q.opener_bid, "1NT")
        self.assertEqual(q.response_bid, "2\u2663")
        self.assertEqual(q.opener_rebid_bid, "2\u2666")

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

    def test_opener_rebid_question_respects_requested_opening_response_sequence(self) -> None:
        question = generate_opener_rebid_question(
            seed=100,
            settings=RuleSettings(),
            opener_bid="1♥",
            response_bid="2NT",
        )
        self.assertEqual(question.opener_bid, "1♥")
        self.assertEqual(question.response_bid, "2NT")
        self.assertTrue(question.auction.startswith("1♥-2NT-"))

    def test_generate_opener_rebid_question_skips_pass_response_for_non_preempt(self) -> None:
        sentinel = generate_opening_question(seed=100, settings=RuleSettings())
        with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("1♣", "x", "x")):
            with patch("bridge_trainer.training.recommend_response", return_value=BidRecommendation("Pass", "x", "x")):
                with patch("bridge_trainer.training.generate_response_question", return_value=sentinel):
                    question = generate_opener_rebid_question(seed=100, settings=RuleSettings())
        self.assertIs(question, sentinel)

    def test_generate_opener_rebid_question_relaxes_unmatched_response_filter_without_downgrading_mode(self) -> None:
        with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("1♥", "x", "x")):
            with patch("bridge_trainer.training.recommend_response", return_value=BidRecommendation("2NT", "x", "x")):
                with patch("bridge_trainer.training.recommend_opener_rebid", return_value=BidRecommendation("4♥", "x", "x")):
                    question = generate_opener_rebid_question(
                        seed=100,
                        settings=RuleSettings(),
                        opener_bid="1♥",
                        response_bid="1♠",
                    )
        self.assertEqual(question.mode, "开叫者再叫训练")
        self.assertEqual(question.opener_bid, "1♥")
        self.assertEqual(question.response_bid, "2NT")

    def test_generate_opener_rebid_question_common_prefilter_can_hit_before_default_budget(self) -> None:
        target_offset = 25
        eval_calls = {"count": 0}
        good_opener = self._evaluation(13, 2, 5, 3, 3, balanced=False)
        good_responder = self._evaluation(13, 3, 4, 3, 3, balanced=True)
        bad_eval = self._evaluation(7, 3, 3, 4, 3, balanced=True)

        def evaluate_side_effect(_hand):
            current = eval_calls["count"]
            eval_calls["count"] += 1
            loop_index = current // 2
            if loop_index == target_offset:
                return good_opener if current % 2 == 0 else good_responder
            return bad_eval

        with patch("bridge_trainer.training.evaluate_hand", side_effect=evaluate_side_effect):
            with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("1♥", "x", "x")):
                with patch("bridge_trainer.training.recommend_response", return_value=BidRecommendation("2NT", "x", "x")):
                    with patch("bridge_trainer.training.recommend_opener_rebid", return_value=BidRecommendation("4♥", "x", "x")):
                        question = generate_opener_rebid_question(
                            seed=100,
                            settings=RuleSettings(),
                            opener_bid="1♥",
                            response_bid="2NT",
                        )
        self.assertEqual(question.mode, "开叫者再叫训练")
        self.assertEqual(question.opener_bid, "1♥")
        self.assertEqual(question.response_bid, "2NT")
        self.assertLess(eval_calls["count"], DEFAULT_SEARCH_ATTEMPTS * 2)

    def test_opener_rebid_question_invalid_requested_opener_falls_back_to_supported(self) -> None:
        question = generate_opener_rebid_question(seed=100, settings=RuleSettings(), opener_bid="7NT")
        self.assertIn(question.opener_bid, supported_openings_for_category(None))

    def test_responder_rebid_question_respects_requested_one_nt_opener(self) -> None:
        question = generate_responder_rebid_question(seed=100, settings=RuleSettings(), opener_bid="1NT")
        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.mode, "应叫者第二次应叫训练")
        self.assertTrue(question.auction.startswith("1NT-Pass-"))

    def test_responder_rebid_question_respects_requested_three_bid_sequence(self) -> None:
        baseline = generate_responder_rebid_question(seed=100, settings=RuleSettings(), opener_bid="1NT")
        question = generate_responder_rebid_question(
            seed=100,
            settings=RuleSettings(),
            opener_bid=baseline.opener_bid,
            response_bid=baseline.response_bid,
            opener_rebid_bid=baseline.opener_rebid_bid,
        )
        self.assertEqual(question.opener_bid, baseline.opener_bid)
        self.assertEqual(question.response_bid, baseline.response_bid)
        self.assertEqual(question.opener_rebid_bid, baseline.opener_rebid_bid)

    def test_generate_responder_rebid_question_skips_when_opener_rebid_is_pass(self) -> None:
        sentinel = generate_opening_question(seed=100, settings=RuleSettings())
        with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("1♣", "x", "x")):
            with patch("bridge_trainer.training.recommend_response", return_value=BidRecommendation("1♥", "x", "x")):
                with patch("bridge_trainer.training.recommend_opener_rebid", return_value=BidRecommendation("Pass", "x", "x")):
                    with patch("bridge_trainer.training.generate_response_question", return_value=sentinel):
                        question = generate_responder_rebid_question(seed=100, settings=RuleSettings())
        self.assertIs(question, sentinel)

    def test_generate_responder_rebid_question_relaxes_unmatched_response_filter_without_downgrading_mode(self) -> None:
        with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("1NT", "x", "x")):
            with patch("bridge_trainer.training.recommend_response", return_value=BidRecommendation("2♣", "x", "x")):
                with patch("bridge_trainer.training.recommend_opener_rebid", return_value=BidRecommendation("2♦", "x", "x")):
                    question = generate_responder_rebid_question(
                        seed=100,
                        settings=RuleSettings(),
                        opener_bid="1NT",
                        response_bid="2♦",
                    )
        self.assertEqual(question.mode, "应叫者第二次应叫训练")
        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.response_bid, "2♣")

    def test_generate_responder_rebid_question_common_prefilter_can_hit_before_default_budget(self) -> None:
        target_offset = 40
        eval_calls = {"count": 0}
        good_opener = self._evaluation(16, 3, 3, 4, 3, balanced=True)
        good_responder = self._evaluation(9, 4, 4, 3, 2, balanced=False)
        bad_eval = self._evaluation(7, 3, 3, 4, 3, balanced=True)

        def evaluate_side_effect(_hand):
            current = eval_calls["count"]
            eval_calls["count"] += 1
            loop_index = current // 2
            if loop_index == target_offset:
                return good_opener if current % 2 == 0 else good_responder
            return bad_eval

        with patch("bridge_trainer.training.evaluate_hand", side_effect=evaluate_side_effect):
            with patch("bridge_trainer.training.recommend_opening", return_value=BidRecommendation("1NT", "x", "x")):
                with patch("bridge_trainer.training.recommend_response", return_value=BidRecommendation("2♣", "x", "x")):
                    with patch("bridge_trainer.training.recommend_opener_rebid", return_value=BidRecommendation("2♦", "x", "x")):
                        with patch("bridge_trainer.training.recommend_responder_rebid", return_value=BidRecommendation("3NT", "x", "x")):
                            question = generate_responder_rebid_question(
                                seed=100,
                                settings=RuleSettings(),
                                opener_bid="1NT",
                                response_bid="2♣",
                                opener_rebid_bid="2♦",
                            )
        self.assertEqual(question.mode, "应叫者第二次应叫训练")
        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.response_bid, "2♣")
        self.assertEqual(question.opener_rebid_bid, "2♦")
        self.assertLess(eval_calls["count"], DEFAULT_SEARCH_ATTEMPTS * 2)

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
                "inverted_minors_enabled": True,
            }
        )
        self.assertEqual(settings.opening_min_hcp, 11)
        self.assertEqual(settings.one_nt_min, 14)
        self.assertEqual(settings.one_nt_max, 16)
        self.assertEqual(settings.scoring_mode, "MP")
        self.assertFalse(settings.respect_vulnerability)
        self.assertEqual(settings.game_aggressiveness, 1)
        self.assertTrue(settings.inverted_minors_enabled)

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

    def test_create_question_responder_rebid_mode_with_sequence_filters(self) -> None:
        req = self._DummyRequest(
            {
                "mode": "responder_rebid",
                "seed": 100,
                "opener_bid": "1NT",
                "response_bid": "2♣",
                "opener_rebid_bid": "2♦",
                "settings": {},
            }
        )
        response = asyncio.run(create_question(req))
        self.assertEqual(response.status_code, 200)
        data = response.body.decode("utf-8")
        self.assertIn('"mode":"应叫者第二次应叫训练"', data)
        self.assertIn('"response_bid":"2♣"', data)
        self.assertIn('"opener_rebid_bid":"2♦"', data)

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
