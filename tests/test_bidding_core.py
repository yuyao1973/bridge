from __future__ import annotations

import unittest

from bridge_trainer.bidding import (
    RuleSettings,
    game_threshold_adjustment,
    is_legal_response_bid,
    legal_rebid_bids,
    legal_response_bids,
    legal_responder_rebid_bids,
    parse_contract_bid,
    recommend_opener_rebid,
    recommend_opening,
    recommend_responder_rebid,
    recommend_response,
)
from bridge_trainer.evaluator import HandEvaluation


VULNERABILITY = "双方无局"


def evaluation(
    hcp: int,
    spades: int,
    hearts: int,
    diamonds: int,
    clubs: int,
    balanced: bool | None = None,
    top_honors_by_suit: dict[str, int] | None = None,
) -> HandEvaluation:
    lengths = {"S": spades, "H": hearts, "D": diamonds, "C": clubs}
    sorted_shape = tuple(sorted(lengths.values(), reverse=True))
    return HandEvaluation(
        hcp=hcp,
        lengths=lengths,
        shape=f"{spades}-{hearts}-{diamonds}-{clubs}",
        balanced=balanced if balanced is not None else sorted_shape in {(4, 3, 3, 3), (4, 4, 3, 2), (5, 3, 3, 2)},
        longest_suits=[suit for suit, length in lengths.items() if length == max(lengths.values())],
        top_honors_by_suit=top_honors_by_suit or {"S": 0, "H": 0, "D": 0, "C": 0},
    )


class OpeningRecommendationTests(unittest.TestCase):
    def test_strong_two_club_takes_precedence(self) -> None:
        self.assertEqual(recommend_opening(evaluation(23, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "2♣")

    def test_twenty_to_twenty_one_balanced_opens_two_nt(self) -> None:
        self.assertEqual(recommend_opening(evaluation(20, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "2NT")

    def test_balanced_fifteen_to_seventeen_opens_one_nt(self) -> None:
        self.assertEqual(recommend_opening(evaluation(16, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "1NT")

    def test_five_five_majors_open_spade(self) -> None:
        self.assertEqual(recommend_opening(evaluation(12, 5, 5, 2, 1, balanced=False), vulnerability=VULNERABILITY).bid, "1♠")

    def test_four_four_minors_open_diamond(self) -> None:
        self.assertEqual(recommend_opening(evaluation(12, 2, 3, 4, 4), vulnerability=VULNERABILITY).bid, "1♦")

    def test_weak_two_major(self) -> None:
        self.assertEqual(recommend_opening(evaluation(8, 2, 6, 3, 2, balanced=False), vulnerability=VULNERABILITY).bid, "2♥")

    def test_three_level_preempt_with_seven_card_suit(self) -> None:
        self.assertEqual(recommend_opening(evaluation(8, 2, 2, 7, 2, balanced=False), vulnerability=VULNERABILITY).bid, "3♦")

    def test_four_level_preempt_with_eight_card_major(self) -> None:
        self.assertEqual(recommend_opening(evaluation(8, 8, 2, 2, 1, balanced=False), vulnerability=VULNERABILITY).bid, "4♠")

    def test_five_level_preempt_with_nine_card_minor(self) -> None:
        self.assertEqual(recommend_opening(evaluation(8, 1, 1, 9, 2, balanced=False), vulnerability=VULNERABILITY).bid, "5♦")

    def test_pass_when_below_opening_and_no_weak_two(self) -> None:
        self.assertEqual(recommend_opening(evaluation(5, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "Pass")


class ResponseRecommendationTests(unittest.TestCase):
    def test_response_to_one_nt_uses_heart_transfer(self) -> None:
        self.assertEqual(recommend_response("1NT", evaluation(5, 3, 5, 3, 2), vulnerability=VULNERABILITY).bid, "2♦")

    def test_response_to_one_nt_uses_spade_transfer(self) -> None:
        self.assertEqual(recommend_response("1NT", evaluation(5, 5, 3, 3, 2), vulnerability=VULNERABILITY).bid, "2♥")

    def test_response_to_one_nt_uses_stayman_with_eight_hcp(self) -> None:
        self.assertEqual(recommend_response("1NT", evaluation(8, 4, 4, 3, 2), vulnerability=VULNERABILITY).bid, "2♣")

    def test_response_to_one_nt_games_without_major(self) -> None:
        self.assertEqual(recommend_response("1NT", evaluation(10, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "3NT")

    def test_response_to_one_nt_invites_without_major(self) -> None:
        self.assertEqual(recommend_response("1NT", evaluation(8, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "2NT")

    def test_response_to_one_nt_passes_without_invite_values(self) -> None:
        self.assertEqual(recommend_response("1NT", evaluation(7, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "Pass")

    def test_jacoby_two_nt_after_major_with_game_force_support(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(13, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "2NT")

    def test_limit_raise_after_major(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(10, 3, 2, 4, 4), vulnerability=VULNERABILITY).bid, "3♠")

    def test_one_spade_response_after_one_heart(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(8, 4, 2, 4, 3), vulnerability=VULNERABILITY).bid, "1♠")

    def test_two_over_one_response_after_major(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(12, 1, 4, 4, 4, balanced=False), vulnerability=VULNERABILITY).bid, "2♥")

    def test_forcing_nt_response_after_major(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(8, 1, 3, 5, 4, balanced=False), vulnerability=VULNERABILITY).bid, "1NT")

    def test_minor_opening_prefers_one_level_major(self) -> None:
        self.assertEqual(recommend_response("1♣", evaluation(7, 4, 4, 3, 2), vulnerability=VULNERABILITY).bid, "1♥")

    def test_minor_opening_balanced_game_to_three_nt(self) -> None:
        self.assertEqual(recommend_response("1♦", evaluation(13, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "3NT")

    def test_minor_opening_low_values_pass(self) -> None:
        self.assertEqual(recommend_response("1♦", evaluation(5, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "Pass")

    def test_strong_two_club_response_uses_two_diamond_waiting(self) -> None:
        self.assertEqual(recommend_response("2♣", evaluation(4, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "2♦")

    def test_two_nt_response_uses_stayman_with_four_card_major(self) -> None:
        self.assertEqual(recommend_response("2NT", evaluation(2, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "3♣")

    def test_two_nt_response_uses_transfer_with_five_card_major(self) -> None:
        self.assertEqual(recommend_response("2NT", evaluation(2, 3, 5, 3, 2), vulnerability=VULNERABILITY).bid, "3♦")

    def test_two_nt_response_uses_three_nt_without_major(self) -> None:
        self.assertEqual(recommend_response("2NT", evaluation(2, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "3NT")

    def test_preempt_response_passes_without_clear_action(self) -> None:
        self.assertEqual(recommend_response("3♦", evaluation(6, 4, 3, 2, 4, balanced=False), vulnerability=VULNERABILITY).bid, "Pass")

    def test_ogust_2nt_used_with_game_interest_over_weak_two(self) -> None:
        self.assertEqual(recommend_response("2♥", evaluation(12, 3, 2, 4, 4, balanced=False), vulnerability=VULNERABILITY).bid, "2NT")

    def test_ogust_2nt_not_used_when_disabled(self) -> None:
        settings = RuleSettings(august_2nt_enabled=False)
        result = recommend_response("2♥", evaluation(12, 3, 2, 4, 4, balanced=False), settings=settings, vulnerability=VULNERABILITY)
        self.assertNotEqual(result.bid, "2NT")

    def test_ogust_2nt_not_used_for_three_level_preempt(self) -> None:
        result = recommend_response("3♥", evaluation(12, 3, 2, 4, 4, balanced=False), vulnerability=VULNERABILITY)
        self.assertNotEqual(result.bid, "2NT")

    def test_bergen_weak_support_four_hearts_six_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(6, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "3♦")

    def test_bergen_medium_support_four_hearts_ten_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(10, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "3♠")

    def test_simple_raise_three_hearts_six_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(6, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "2♥")

    def test_limit_raise_three_hearts_ten_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(10, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "3♥")

    def test_game_raise_four_hearts_thirteen_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(13, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "4♥")

    def test_jacoby_2nt_four_support_thirteen_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(13, 3, 4, 4, 2), vulnerability=VULNERABILITY).bid, "2NT")

    def test_bergen_weak_support_four_spades_nine_hcp(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(9, 4, 3, 3, 3), vulnerability=VULNERABILITY).bid, "3♣")

    def test_bergen_medium_support_four_spades_twelve_hcp(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(12, 4, 3, 3, 3), vulnerability=VULNERABILITY).bid, "3♥")

    def test_bergen_disabled_falls_back_to_simple_raise(self) -> None:
        settings = RuleSettings(bergen_raises_enabled=False)
        self.assertEqual(
            recommend_response("1♥", evaluation(8, 3, 4, 3, 3), settings=settings, vulnerability=VULNERABILITY).bid,
            "2♥",
        )

    def test_jacoby_disabled_with_game_values_raises_to_game(self) -> None:
        settings = RuleSettings(jacoby_2nt_enabled=False)
        self.assertEqual(
            recommend_response("1♥", evaluation(13, 3, 4, 3, 3), settings=settings, vulnerability=VULNERABILITY).bid,
            "4♥",
        )

    def test_simple_raise_boundary_nine_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(9, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "2♥")

    def test_limit_raise_boundary_twelve_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(12, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "3♥")

    def test_custom_simple_raise_max_ten_makes_ten_hcp_simple(self) -> None:
        settings = RuleSettings(responder_simple_raise_max=10, responder_limit_raise_min=11, responder_limit_raise_max=12)
        self.assertEqual(
            recommend_response("1♥", evaluation(10, 3, 3, 4, 3), settings=settings, vulnerability=VULNERABILITY).bid,
            "2♥",
        )

    def test_custom_limit_range_eleven_to_twelve_forces_ten_hcp_simple(self) -> None:
        settings = RuleSettings(responder_simple_raise_max=10, responder_limit_raise_min=11, responder_limit_raise_max=12)
        self.assertEqual(
            recommend_response("1♠", evaluation(10, 3, 2, 4, 4), settings=settings, vulnerability=VULNERABILITY).bid,
            "2♠",
        )

    def test_custom_bergen_weak_max_eight_moves_nine_hcp_to_simple_raise(self) -> None:
        settings = RuleSettings(responder_bergen_weak_max=8, responder_simple_raise_max=9)
        self.assertEqual(
            recommend_response("1♠", evaluation(9, 4, 3, 3, 3), settings=settings, vulnerability=VULNERABILITY).bid,
            "2♠",
        )


class RebidRecommendationTests(unittest.TestCase):
    def test_opener_rebid_supports_responder_major(self) -> None:
        hand = evaluation(14, 4, 3, 3, 3)
        self.assertEqual(recommend_opener_rebid("1♦", "1♠", hand, vulnerability=VULNERABILITY).bid, "2♠")

    def test_opener_rebid_balanced_minimum_one_nt(self) -> None:
        hand = evaluation(13, 3, 3, 4, 3)
        self.assertEqual(recommend_opener_rebid("1♦", "1♥", hand, vulnerability=VULNERABILITY).bid, "1NT")

    def test_opener_rebid_balanced_strong_two_nt(self) -> None:
        hand = evaluation(18, 3, 3, 4, 3)
        self.assertEqual(recommend_opener_rebid("1♦", "1♥", hand, vulnerability=VULNERABILITY).bid, "2NT")

    def test_opener_rebid_repeats_six_card_suit(self) -> None:
        hand = evaluation(13, 2, 3, 6, 2, balanced=False)
        self.assertEqual(recommend_opener_rebid("1♦", "1♥", hand, vulnerability=VULNERABILITY).bid, "2♦")

    def test_ogust_rebid_minimum_poor_quality_answers_three_clubs(self) -> None:
        hand = evaluation(6, 2, 6, 3, 2, balanced=False, top_honors_by_suit={"S": 0, "H": 1, "D": 0, "C": 0})
        self.assertEqual(recommend_opener_rebid("2♥", "2NT", hand, vulnerability=VULNERABILITY).bid, "3♣")

    def test_ogust_rebid_minimum_good_quality_answers_three_diamonds(self) -> None:
        hand = evaluation(7, 2, 6, 3, 2, balanced=False, top_honors_by_suit={"S": 0, "H": 2, "D": 0, "C": 0})
        self.assertEqual(recommend_opener_rebid("2♥", "2NT", hand, vulnerability=VULNERABILITY).bid, "3♦")

    def test_ogust_rebid_maximum_poor_quality_answers_three_hearts(self) -> None:
        hand = evaluation(8, 2, 6, 3, 2, balanced=False, top_honors_by_suit={"S": 0, "H": 1, "D": 0, "C": 0})
        self.assertEqual(recommend_opener_rebid("2♥", "2NT", hand, vulnerability=VULNERABILITY).bid, "3♥")

    def test_ogust_rebid_maximum_good_quality_answers_three_spades(self) -> None:
        hand = evaluation(9, 2, 6, 3, 2, balanced=False, top_honors_by_suit={"S": 0, "H": 2, "D": 0, "C": 0})
        self.assertEqual(recommend_opener_rebid("2♥", "2NT", hand, vulnerability=VULNERABILITY).bid, "3♠")

    def test_ogust_rebid_maximum_top_three_honors_answers_three_nt(self) -> None:
        hand = evaluation(10, 2, 6, 3, 2, balanced=False, top_honors_by_suit={"S": 0, "H": 3, "D": 0, "C": 0})
        self.assertEqual(recommend_opener_rebid("2♥", "2NT", hand, vulnerability=VULNERABILITY).bid, "3NT")

    def test_responder_rebid_over_one_nt_invites_with_ten_hcp(self) -> None:
        hand = evaluation(10, 3, 3, 4, 3)
        self.assertEqual(recommend_responder_rebid("1♦", "1♥", "1NT", hand, vulnerability=VULNERABILITY).bid, "2NT")

    def test_responder_rebid_over_one_nt_games_with_thirteen_hcp(self) -> None:
        hand = evaluation(13, 3, 3, 4, 3)
        self.assertEqual(recommend_responder_rebid("1♦", "1♥", "1NT", hand, vulnerability=VULNERABILITY).bid, "3NT")

    def test_responder_rebid_supports_opener_rebid_major(self) -> None:
        hand = evaluation(10, 3, 3, 4, 3)
        self.assertEqual(recommend_responder_rebid("1♦", "1♥", "2♥", hand, vulnerability=VULNERABILITY).bid, "3♥")

    def test_responder_rebid_repeats_six_card_response_suit(self) -> None:
        hand = evaluation(9, 2, 6, 3, 2, balanced=False)
        self.assertEqual(recommend_responder_rebid("1♦", "1♥", "2♦", hand, vulnerability=VULNERABILITY).bid, "2♥")


class UtilityRuleTests(unittest.TestCase):
    def test_parse_contract_bid(self) -> None:
        self.assertEqual(parse_contract_bid("3NT"), (3, "NT"))
        self.assertEqual(parse_contract_bid("2♥"), (2, "♥"))
        self.assertIsNone(parse_contract_bid("Pass"))

    def test_legal_response_bid_ordering(self) -> None:
        self.assertTrue(is_legal_response_bid("1♥", "1♠"))
        self.assertTrue(is_legal_response_bid("1♠", "1NT"))
        self.assertFalse(is_legal_response_bid("1♠", "1♥"))
        self.assertTrue(is_legal_response_bid("3NT", "Pass"))

    def test_legal_choice_helpers_include_pass(self) -> None:
        self.assertIn("Pass", legal_response_bids("1NT"))
        self.assertIn("Pass", legal_rebid_bids("1♥"))
        self.assertIn("Pass", legal_responder_rebid_bids("2♥"))

    def test_vulnerability_and_scoring_adjustment(self) -> None:
        self.assertEqual(game_threshold_adjustment("双方无局", RuleSettings(scoring_mode="IMP")), 0)
        self.assertEqual(game_threshold_adjustment("南北有局", RuleSettings(scoring_mode="IMP")), -1)
        self.assertEqual(game_threshold_adjustment("双方无局", RuleSettings(scoring_mode="MP")), 1)
        self.assertEqual(game_threshold_adjustment("双方无局", RuleSettings(scoring_mode="IMP", game_aggressiveness=1)), -1)


if __name__ == "__main__":
    unittest.main()
