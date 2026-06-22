from __future__ import annotations

import unittest

from bridge_trainer.bidding import (
    RuleSettings,
    choose_raise_level,
    choose_two_over_one_suit,
    choose_one_level_major_response,
    find_splinter_suit,
    game_threshold_adjustment,
    is_negative_double_available,
    is_legal_response_bid,
    legal_response_bids_with_interference,
    legal_rebid_bids,
    legal_response_bids,
    legal_responder_rebid_bids,
    negative_double_target_majors,
    next_legal_contract,
    parse_contract_bid,
    is_reverse_second_suit,
    recommend_opener_rebid,
    recommend_opening,
    recommend_responder_rebid,
    recommend_response,
    recommend_response_to_preempt,
    recommend_response_to_weak_two,
    should_make_negative_double,
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
    def test_unknown_opener_falls_back_to_pass(self) -> None:
        result = recommend_response("6♣", evaluation(10, 3, 3, 4, 3), vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "Pass")
        self.assertEqual(result.rule_name, "未覆盖的开叫")

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
        self.assertEqual(recommend_response("1♠", evaluation(10, 3, 2, 4, 4), vulnerability=VULNERABILITY).bid, "1NT")

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

    def test_minor_opening_balanced_without_invite_values_uses_one_nt(self) -> None:
        self.assertEqual(recommend_response("1♦", evaluation(7, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "1NT")

    def test_minor_opening_balanced_invite_values_uses_two_nt(self) -> None:
        self.assertEqual(recommend_response("1♦", evaluation(11, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "2NT")

    def test_minor_opening_with_five_card_support_and_ten_hcp_raises_to_three(self) -> None:
        self.assertEqual(recommend_response("1♦", evaluation(10, 3, 3, 5, 2, balanced=False), vulnerability=VULNERABILITY).bid, "3♦")

    def test_minor_opening_without_inverted_minors_ten_hcp_support_raises_to_three(self) -> None:
        settings = RuleSettings(inverted_minors_enabled=False)
        self.assertEqual(
            recommend_response("1♦", evaluation(10, 3, 3, 5, 2, balanced=False), settings=settings, vulnerability=VULNERABILITY).bid,
            "3♦",
        )

    def test_minor_opening_with_inverted_minors_ten_hcp_support_uses_two_minor(self) -> None:
        settings = RuleSettings(inverted_minors_enabled=True)
        result = recommend_response("1♦", evaluation(10, 3, 3, 5, 2, balanced=False), settings=settings, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "2♦")
        self.assertEqual(result.rule_name, "低花反加叫（逼叫）")

    def test_minor_opening_with_inverted_minors_eight_hcp_support_uses_three_minor(self) -> None:
        settings = RuleSettings(inverted_minors_enabled=True)
        result = recommend_response("1♣", evaluation(8, 3, 3, 2, 5, balanced=False), settings=settings, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "3♣")
        self.assertEqual(result.rule_name, "低花反加叫（弱）")

    def test_minor_opening_low_values_pass(self) -> None:
        self.assertEqual(recommend_response("1♦", evaluation(5, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "Pass")

    def test_strong_two_club_response_uses_two_diamond_waiting(self) -> None:
        self.assertEqual(recommend_response("2♣", evaluation(4, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "2♦")

    def test_two_nt_response_uses_stayman_with_four_card_major(self) -> None:
        self.assertEqual(recommend_response("2NT", evaluation(2, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "3♣")

    def test_two_nt_response_uses_transfer_with_five_card_major(self) -> None:
        self.assertEqual(recommend_response("2NT", evaluation(2, 3, 5, 3, 2), vulnerability=VULNERABILITY).bid, "3♦")

    def test_two_nt_response_uses_spade_transfer_with_five_spades(self) -> None:
        self.assertEqual(recommend_response("2NT", evaluation(2, 5, 3, 3, 2), vulnerability=VULNERABILITY).bid, "3♥")

    def test_two_nt_response_uses_three_nt_without_major(self) -> None:
        self.assertEqual(recommend_response("2NT", evaluation(2, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "3NT")

    def test_preempt_response_passes_without_clear_action(self) -> None:
        self.assertEqual(recommend_response("3♦", evaluation(6, 4, 3, 2, 4, balanced=False), vulnerability=VULNERABILITY).bid, "Pass")

    def test_minor_opening_unbalanced_without_clear_action_defaults_to_one_nt(self) -> None:
        self.assertEqual(recommend_response("1♦", evaluation(8, 3, 3, 6, 1, balanced=False), vulnerability=VULNERABILITY).bid, "2♦")

    def test_preempt_response_with_support_can_make_obstructive_raise(self) -> None:
        self.assertEqual(recommend_response("3♥", evaluation(6, 3, 3, 4, 3, balanced=False), vulnerability=VULNERABILITY).bid, "4♥")

    def test_preempt_response_balanced_game_values_prefers_three_nt(self) -> None:
        settings = RuleSettings(august_2nt_enabled=False)
        self.assertEqual(recommend_response("2♦", evaluation(13, 3, 3, 4, 3), settings=settings, vulnerability=VULNERABILITY).bid, "3NT")

    def test_preempt_response_major_support_can_raise_to_game(self) -> None:
        self.assertEqual(recommend_response("2♥", evaluation(10, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "4♥")

    def test_preempt_response_minor_support_can_raise_to_five_level(self) -> None:
        self.assertEqual(recommend_response("2♦", evaluation(10, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "5♦")

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
        self.assertEqual(recommend_response("1♥", evaluation(6, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "3♥")

    def test_four_heart_support_eight_hcp_prefers_four_card_convention(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(8, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "2♥")

    def test_bergen_medium_support_four_hearts_ten_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(10, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "3♦")

    def test_simple_raise_three_hearts_six_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(6, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "2♥")

    def test_three_hearts_support_four_hcp_should_pass(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(4, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "Pass")

    def test_three_hearts_support_three_hcp_should_pass(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(3, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "Pass")

    def test_limit_raise_three_hearts_ten_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(10, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "1NT")

    def test_game_raise_four_hearts_thirteen_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(13, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "2♣")

    def test_jacoby_2nt_four_support_thirteen_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(13, 3, 4, 4, 2), vulnerability=VULNERABILITY).bid, "2NT")

    def test_major_opening_five_card_support_weak_hand_prefers_preemptive_game_raise(self) -> None:
        result = recommend_response("1♥", evaluation(8, 3, 5, 3, 2, balanced=False), vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "4♥")
        self.assertEqual(result.rule_name, "高花关煞加叫")

    def test_major_opening_four_card_support_ten_hcp_non_balanced_uses_bergen_three_diamond(self) -> None:
        result = recommend_response("1♠", evaluation(10, 4, 3, 5, 1, balanced=False), vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "3♠")

    def test_bergen_weak_support_four_spades_nine_hcp(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(9, 4, 3, 3, 3), vulnerability=VULNERABILITY).bid, "2♠")

    def test_four_spade_support_eight_hcp_prefers_four_card_convention(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(8, 4, 3, 3, 3), vulnerability=VULNERABILITY).bid, "2♠")

    def test_bergen_medium_support_four_spades_twelve_hcp(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(12, 4, 3, 3, 3), vulnerability=VULNERABILITY).bid, "3♦")

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
        self.assertEqual(recommend_response("1♥", evaluation(12, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "1NT")

    def test_custom_simple_raise_max_ten_makes_ten_hcp_simple(self) -> None:
        settings = RuleSettings(responder_simple_raise_max=10, responder_limit_raise_min=11, responder_limit_raise_max=12)
        self.assertEqual(
            recommend_response("1♥", evaluation(10, 3, 3, 4, 3), settings=settings, vulnerability=VULNERABILITY).bid,
            "1NT",
        )

    def test_custom_limit_range_eleven_to_twelve_forces_ten_hcp_simple(self) -> None:
        settings = RuleSettings(responder_simple_raise_max=10, responder_limit_raise_min=11, responder_limit_raise_max=12)
        self.assertEqual(
            recommend_response("1♠", evaluation(10, 3, 2, 4, 4), settings=settings, vulnerability=VULNERABILITY).bid,
            "1NT",
        )

    def test_custom_bergen_weak_max_eight_moves_nine_hcp_to_simple_raise(self) -> None:
        settings = RuleSettings(responder_bergen_weak_max=8, responder_simple_raise_max=9)
        self.assertEqual(
            recommend_response("1♠", evaluation(9, 4, 3, 3, 3), settings=settings, vulnerability=VULNERABILITY).bid,
            "2♠",
        )

    def test_bergen_weak_boundary_at_nine_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(9, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "2♥")

    def test_bergen_medium_boundary_at_ten_hcp(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(10, 4, 3, 3, 3), vulnerability=VULNERABILITY).bid, "3♦")

    def test_simple_raise_three_hearts_at_boundary_nine_hcp(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(9, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "2♥")

    def test_limit_raise_three_spades_at_boundary_ten_hcp(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(10, 3, 2, 3, 5), vulnerability=VULNERABILITY).bid, "1NT")

    def test_four_hearts_support_six_hcp_bergen_weak(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(6, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "3♥")

    def test_four_spades_support_ten_hcp_bergen_medium(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(10, 4, 3, 3, 3), vulnerability=VULNERABILITY).bid, "3♦")

    def test_three_hearts_support_eleven_hcp_invite(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(11, 3, 3, 4, 3), vulnerability=VULNERABILITY).bid, "1NT")

    def test_custom_aggressive_simple_raise_max_eleven(self) -> None:
        settings = RuleSettings(responder_simple_raise_max=11, responder_limit_raise_min=12, responder_limit_raise_max=12)
        self.assertEqual(
            recommend_response("1♥", evaluation(11, 3, 3, 4, 3), settings=settings, vulnerability=VULNERABILITY).bid,
            "1NT",
        )

    def test_custom_conservative_limit_raise_min_nine(self) -> None:
        settings = RuleSettings(responder_simple_raise_max=8, responder_limit_raise_min=9, responder_limit_raise_max=11)
        self.assertEqual(
            recommend_response("1♠", evaluation(9, 3, 2, 4, 4), settings=settings, vulnerability=VULNERABILITY).bid,
            "2♠",
        )

    def test_multiple_four_card_suits_chooses_longest(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(8, 4, 4, 3, 2), vulnerability=VULNERABILITY).bid, "2♥")

    def test_game_raise_hearts_thirteen_hcp_three_card_support(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(13, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "2♣")

    def test_game_raise_spades_fourteen_hcp_three_card_support(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(14, 3, 2, 4, 4), vulnerability=VULNERABILITY).bid, "2♦")

    def test_jacoby_2nt_fourteen_hcp_four_card_hearts(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(14, 3, 4, 3, 3), vulnerability=VULNERABILITY).bid, "2NT")

    def test_jacoby_2nt_fifteen_hcp_four_card_spades(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(15, 4, 3, 3, 3), vulnerability=VULNERABILITY).bid, "2NT")

    def test_responder_five_card_hearts_support_over_spade_open(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(8, 2, 5, 3, 3, balanced=False), vulnerability=VULNERABILITY).bid, "1NT")

    def test_responder_balanced_no_support_forces_one_nt(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(8, 3, 3, 3, 2), vulnerability=VULNERABILITY).bid, "2♠")

    def test_major_opening_three_card_support_ten_hcp_with_bergen_uses_one_nt(self) -> None:
        result = recommend_response("1♠", evaluation(10, 3, 3, 4, 3, balanced=False), vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "1NT")

    def test_responder_twelve_hcp_limit_raise_not_game(self) -> None:
        self.assertEqual(recommend_response("1♥", evaluation(12, 3, 3, 3, 4), vulnerability=VULNERABILITY).bid, "1NT")

    def test_responder_thirteen_hcp_game_not_limit_raise(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(13, 3, 2, 3, 5), vulnerability=VULNERABILITY).bid, "2♣")

    def test_splinter_hearts_club_singleton_thirteen_hcp(self) -> None:
        # 1♥开叫，13 HCP，4张心支持，单张方块 -> 3♦ Splinter
        self.assertEqual(recommend_response("1♥", evaluation(13, 3, 4, 1, 5), vulnerability=VULNERABILITY).bid, "3♦")

    def test_splinter_spades_heart_singleton_twelve_hcp(self) -> None:
        # 1♠开叫，12 HCP，4张黑桃支持，单张红心 -> 3♥ Splinter
        self.assertEqual(recommend_response("1♠", evaluation(12, 4, 1, 3, 5), vulnerability=VULNERABILITY).bid, "3♥")

    def test_splinter_hearts_spade_void_fourteen_hcp(self) -> None:
        # 1♥开叫，14 HCP，4张心支持，无黑桃（void） -> 3♠ Splinter
        self.assertEqual(recommend_response("1♥", evaluation(14, 0, 4, 4, 5), vulnerability=VULNERABILITY).bid, "3♠")

    def test_splinter_disabled_falls_back_to_jacoby(self) -> None:
        # 禁用Splinter时，存在短门不走Jacoby，改走高限新花进程
        settings = RuleSettings(splinter_enabled=False)
        self.assertEqual(
            recommend_response("1♥", evaluation(13, 3, 4, 1, 5), settings=settings, vulnerability=VULNERABILITY).bid,
            "2♣",
        )

    def test_splinter_below_min_hcp_uses_bergen_medium(self) -> None:
        # 10 HCP，4张支持，单张方块，当前分支优先弱支持跳加叫
        settings = RuleSettings(responder_splinter_min_hcp=11)
        self.assertEqual(
            recommend_response("1♥", evaluation(10, 3, 4, 1, 5), settings=settings, vulnerability=VULNERABILITY).bid,
            "3♥",
        )

    def test_splinter_above_max_hcp_uses_jacoby(self) -> None:
        # 16 HCP，4张支持，单张方块，不走Jacoby，改走高限新花进程
        settings = RuleSettings(responder_splinter_max_hcp=15)
        self.assertEqual(
            recommend_response("1♥", evaluation(16, 3, 4, 1, 5), settings=settings, vulnerability=VULNERABILITY).bid,
            "2♣",
        )

    def test_splinter_requires_singleton_void(self) -> None:
        self.assertEqual(recommend_response("1♠", evaluation(12, 4, 3, 3, 3), vulnerability=VULNERABILITY).bid, "3♦")

    def test_splinter_diamond_singleton_with_hearts(self) -> None:
        # 1♥开叫，11 HCP，4张心支持，单张方块（最小Splinter） -> 3♦
        self.assertEqual(recommend_response("1♥", evaluation(11, 3, 4, 1, 5), vulnerability=VULNERABILITY).bid, "3♦")

    def test_splinter_club_singleton_with_spades(self) -> None:
        # 1♠开叫，13 HCP，4张黑桃支持，单张方块 -> 3♦ Splinter
        self.assertEqual(recommend_response("1♠", evaluation(13, 4, 3, 1, 5), vulnerability=VULNERABILITY).bid, "3♦")

    def test_negative_double_after_one_club_one_heart_with_spades(self) -> None:
        self.assertEqual(
            recommend_response("1♣", evaluation(8, 4, 2, 3, 4), vulnerability=VULNERABILITY, overcall_bid="1♥").bid,
            "X",
        )

    def test_negative_double_after_one_diamond_one_spade_with_hearts(self) -> None:
        self.assertEqual(
            recommend_response("1♦", evaluation(8, 2, 4, 3, 4), vulnerability=VULNERABILITY, overcall_bid="1♠").bid,
            "X",
        )

    def test_negative_double_disabled_falls_back_to_natural_bid(self) -> None:
        settings = RuleSettings(negative_double_enabled=False)
        self.assertEqual(
            recommend_response(
                "1♣",
                evaluation(8, 4, 2, 3, 4),
                settings=settings,
                vulnerability=VULNERABILITY,
                overcall_bid="1♥",
            ).bid,
            "1♠",
        )

    def test_negative_double_below_min_hcp_does_not_double(self) -> None:
        settings = RuleSettings(negative_double_min_hcp=6)
        self.assertEqual(
            recommend_response(
                "1♣",
                evaluation(5, 4, 2, 3, 4),
                settings=settings,
                vulnerability=VULNERABILITY,
                overcall_bid="1♥",
            ).bid,
            "Pass",
        )

    def test_negative_double_requires_target_suit_length(self) -> None:
        self.assertNotEqual(
            recommend_response("1♦", evaluation(8, 3, 3, 4, 3), vulnerability=VULNERABILITY, overcall_bid="1♥").bid,
            "X",
        )

    def test_legal_response_bids_with_interference_includes_x(self) -> None:
        self.assertIn("X", legal_response_bids_with_interference("1♣", "1♥"))

    def test_legal_response_bids_with_interference_without_negative_double(self) -> None:
        self.assertNotIn("X", legal_response_bids_with_interference("1♠", "2♣"))


class RebidRecommendationTests(unittest.TestCase):
    def test_opener_rebid_invalid_response_defaults_pass(self) -> None:
        hand = evaluation(14, 4, 3, 3, 3)
        self.assertEqual(recommend_opener_rebid("1♦", "X", hand, vulnerability=VULNERABILITY).bid, "Pass")

    def test_opener_rebid_after_three_level_preempt_defaults_pass(self) -> None:
        hand = evaluation(9, 3, 7, 2, 1, balanced=False)
        self.assertEqual(recommend_opener_rebid("3♥", "3NT", hand, vulnerability=VULNERABILITY).bid, "Pass")

    def test_opener_rebid_after_weak_two_non_ogust_defaults_pass(self) -> None:
        hand = evaluation(9, 3, 6, 2, 2, balanced=False)
        self.assertEqual(recommend_opener_rebid("2♥", "3♥", hand, vulnerability=VULNERABILITY).bid, "Pass")

    def test_opener_rebid_after_weak_two_game_raise_defaults_pass(self) -> None:
        hand = evaluation(8, 6, 2, 3, 2, balanced=False)
        self.assertEqual(recommend_opener_rebid("2♠", "4♠", hand, vulnerability=VULNERABILITY).bid, "Pass")

    def test_opener_rebid_supports_responder_major(self) -> None:
        hand = evaluation(14, 4, 3, 3, 3)
        self.assertEqual(recommend_opener_rebid("1♦", "1♠", hand, vulnerability=VULNERABILITY).bid, "2♠")

    def test_opener_rebid_after_simple_major_raise_with_minimum_stops(self) -> None:
        hand = evaluation(12, 2, 5, 3, 3, balanced=False)
        result = recommend_opener_rebid("1♥", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "Pass")
        self.assertEqual(result.rule_name, "简单加叫后最低限止叫")

    def test_opener_rebid_balanced_minimum_one_nt(self) -> None:
        hand = evaluation(13, 3, 3, 4, 3)
        self.assertEqual(recommend_opener_rebid("1♦", "1♥", hand, vulnerability=VULNERABILITY).bid, "1NT")

    def test_opener_rebid_balanced_strong_two_nt(self) -> None:
        hand = evaluation(18, 3, 3, 4, 3)
        self.assertEqual(recommend_opener_rebid("1♦", "1♥", hand, vulnerability=VULNERABILITY).bid, "2NT")

    def test_opener_rebid_repeats_six_card_suit(self) -> None:
        hand = evaluation(13, 2, 3, 6, 2, balanced=False)
        self.assertEqual(recommend_opener_rebid("1♦", "1♥", hand, vulnerability=VULNERABILITY).bid, "2♦")

    def test_opener_rebid_chooses_second_suit_when_available(self) -> None:
        hand = evaluation(13, 3, 5, 1, 4, balanced=False)
        result = recommend_opener_rebid("1♥", "1♠", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "2♣")
        self.assertEqual(result.rule_name, "再叫第二套")

    def test_opener_rebid_after_one_club_one_heart_prefers_one_spade(self) -> None:
        hand = evaluation(12, 4, 1, 3, 5, balanced=False)
        result = recommend_opener_rebid("1♣", "1♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "1♠")
        self.assertEqual(result.rule_name, "再叫第二套")

    def test_opener_rebid_six_five_shape_prefers_second_suit_over_repeat(self) -> None:
        hand = evaluation(12, 0, 6, 2, 5, balanced=False)
        result = recommend_opener_rebid("1♥", "1♠", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "2♣")
        self.assertEqual(result.rule_name, "再叫第二套")

    def test_opener_rebid_after_one_diamond_one_heart_prefers_one_nt_over_two_clubs(self) -> None:
        hand = evaluation(14, 2, 2, 5, 4, balanced=False)
        result = recommend_opener_rebid("1♦", "1♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "1NT")
        self.assertEqual(result.rule_name, "一阶序列低限再叫 1NT")

    def test_reverse_second_suit_requires_extra_strength(self) -> None:
        hand = evaluation(14, 2, 2, 4, 5, balanced=False)
        result = recommend_opener_rebid("1♣", "1NT", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "2♣")

    def test_reverse_second_suit_allowed_with_sufficient_hcp(self) -> None:
        hand = evaluation(16, 2, 2, 4, 5, balanced=False)
        result = recommend_opener_rebid("1♣", "1NT", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "2♦")
        self.assertEqual(result.rule_name, "逆叫第二套")

    def test_reverse_detection_helper(self) -> None:
        self.assertTrue(is_reverse_second_suit("1♣", "1NT", "2♦"))
        self.assertFalse(is_reverse_second_suit("1♥", "1♠", "2♣"))

    def test_opener_rebid_fallbacks_to_lowest_legal_contract(self) -> None:
        hand = evaluation(10, 2, 3, 3, 5, balanced=False)
        result = recommend_opener_rebid("1NT", "4♠", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "4NT")
        self.assertEqual(result.rule_name, "最低合法再叫")

    def test_opener_rebid_after_responder_three_nt_stops(self) -> None:
        hand = evaluation(14, 2, 4, 2, 5, balanced=False)
        result = recommend_opener_rebid("1♣", "3NT", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "Pass")
        self.assertEqual(result.rule_name, "3NT 后止叫")

    def test_opener_rebid_after_one_diamond_one_nt_minimum_balanced_stops(self) -> None:
        hand = evaluation(14, 4, 4, 3, 2, balanced=True)
        result = recommend_opener_rebid("1♦", "1NT", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "Pass")
        self.assertEqual(result.rule_name, "1NT 应叫后最低限止叫")

    def test_opener_rebid_after_one_diamond_three_diamond_balanced_game_values_prefers_three_nt(self) -> None:
        hand = evaluation(13, 4, 3, 4, 2, balanced=True)
        result = recommend_opener_rebid("1♦", "3♦", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "3NT")
        self.assertEqual(result.rule_name, "低花限制加叫后 3NT")

    def test_opener_rebid_after_one_club_three_club_balanced_game_values_prefers_three_nt(self) -> None:
        hand = evaluation(13, 4, 3, 2, 4, balanced=True)
        result = recommend_opener_rebid("1♣", "3♣", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "3NT")
        self.assertEqual(result.rule_name, "低花限制加叫后 3NT")

    def test_opener_rebid_after_one_diamond_three_diamond_without_game_values_passes(self) -> None:
        hand = evaluation(12, 4, 3, 4, 2, balanced=True)
        result = recommend_opener_rebid("1♦", "3♦", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "Pass")
        self.assertEqual(result.rule_name, "低花限制加叫后止叫")

    def test_opener_rebid_after_one_club_three_club_without_game_values_passes(self) -> None:
        hand = evaluation(12, 4, 3, 2, 4, balanced=True)
        result = recommend_opener_rebid("1♣", "3♣", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "Pass")
        self.assertEqual(result.rule_name, "低花限制加叫后止叫")

    def test_opener_rebid_after_bergen_raise_with_strong_hand_goes_to_game(self) -> None:
        hand = evaluation(21, 2, 5, 2, 4, balanced=False)
        result = recommend_opener_rebid("1♥", "3♣", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "4♥")
        self.assertEqual(result.rule_name, "Bergen 后支持开叫高花")

    def test_opener_rebid_after_bergen_weak_raise_with_minimum_prefers_three_major(self) -> None:
        hand = evaluation(12, 4, 5, 2, 2, balanced=False)
        result = recommend_opener_rebid("1♥", "3♣", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "3♥")
        self.assertEqual(result.rule_name, "Bergen 后支持开叫高花")

    def test_opener_rebid_after_jacoby_two_nt_prefers_major_game(self) -> None:
        hand = evaluation(12, 2, 5, 3, 3, balanced=False)
        result = recommend_opener_rebid("1♥", "2NT", hand, vulnerability=VULNERABILITY)
        self.assertEqual(result.bid, "4♥")
        self.assertEqual(result.rule_name, "Jacoby 2NT 后高花进局")

    def test_two_nt_stayman_rebid_answers_hearts(self) -> None:
        hand = evaluation(20, 3, 4, 3, 3)
        self.assertEqual(recommend_opener_rebid("2NT", "3♣", hand, vulnerability=VULNERABILITY).bid, "3♥")

    def test_two_nt_stayman_rebid_answers_spades_without_hearts(self) -> None:
        hand = evaluation(20, 4, 3, 3, 3)
        self.assertEqual(recommend_opener_rebid("2NT", "3♣", hand, vulnerability=VULNERABILITY).bid, "3♠")

    def test_two_nt_stayman_rebid_denies_without_four_card_major(self) -> None:
        hand = evaluation(20, 3, 3, 4, 3)
        self.assertEqual(recommend_opener_rebid("2NT", "3♣", hand, vulnerability=VULNERABILITY).bid, "3♦")

    def test_two_nt_accepts_heart_transfer(self) -> None:
        hand = evaluation(20, 3, 3, 4, 3)
        self.assertEqual(recommend_opener_rebid("2NT", "3♦", hand, vulnerability=VULNERABILITY).bid, "3♥")

    def test_two_nt_accepts_spade_transfer(self) -> None:
        hand = evaluation(20, 3, 3, 4, 3)
        self.assertEqual(recommend_opener_rebid("2NT", "3♥", hand, vulnerability=VULNERABILITY).bid, "3♠")

    def test_two_nt_three_nt_sequence_stops(self) -> None:
        hand = evaluation(20, 3, 3, 4, 3)
        self.assertEqual(recommend_opener_rebid("2NT", "3NT", hand, vulnerability=VULNERABILITY).bid, "Pass")

    def test_one_nt_three_nt_sequence_stops(self) -> None:
        hand = evaluation(16, 3, 3, 4, 3)
        self.assertEqual(recommend_opener_rebid("1NT", "3NT", hand, vulnerability=VULNERABILITY).bid, "Pass")

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

    def test_responder_rebid_over_one_nt_passes_with_low_values(self) -> None:
        hand = evaluation(5, 3, 3, 4, 3)
        self.assertEqual(recommend_responder_rebid("1♦", "1♥", "1NT", hand, vulnerability=VULNERABILITY).bid, "Pass")

    def test_responder_rebid_defaults_to_three_nt_with_enough_hcp(self) -> None:
        hand = evaluation(12, 3, 5, 3, 2, balanced=False)
        self.assertEqual(recommend_responder_rebid("1♦", "1♥", "2♣", hand, vulnerability=VULNERABILITY).bid, "3NT")

    def test_responder_rebid_defaults_to_pass_without_clear_action(self) -> None:
        hand = evaluation(8, 3, 5, 3, 2, balanced=False)
        self.assertEqual(recommend_responder_rebid("1♦", "1♥", "2♣", hand, vulnerability=VULNERABILITY).bid, "Pass")

    def test_responder_rebid_after_three_level_preempt_defaults_pass(self) -> None:
        hand = evaluation(12, 4, 3, 3, 3)
        self.assertEqual(recommend_responder_rebid("3♥", "4♥", "5♥", hand, vulnerability=VULNERABILITY).bid, "Pass")

    def test_responder_rebid_after_weak_two_minimum_answer_invites_with_fit(self) -> None:
        hand = evaluation(13, 4, 3, 3, 3)
        self.assertEqual(recommend_responder_rebid("2♥", "2NT", "3♦", hand, vulnerability=VULNERABILITY).bid, "3♥")

    def test_responder_rebid_after_weak_two_minimum_answer_games_with_strong_fit(self) -> None:
        hand = evaluation(15, 4, 3, 3, 3)
        self.assertEqual(recommend_responder_rebid("2♥", "2NT", "3♦", hand, vulnerability=VULNERABILITY).bid, "4♥")

    def test_responder_rebid_after_ogust_maximum_can_bid_game(self) -> None:
        hand = evaluation(13, 4, 3, 3, 3)
        self.assertEqual(recommend_responder_rebid("2♠", "2NT", "3♠", hand, vulnerability=VULNERABILITY).bid, "4♠")

    def test_responder_rebid_after_ogust_maximum_balanced_values_can_bid_three_nt(self) -> None:
        hand = evaluation(11, 3, 2, 4, 4)
        self.assertEqual(recommend_responder_rebid("2♥", "2NT", "3♠", hand, vulnerability=VULNERABILITY).bid, "3NT")

    def test_responder_rebid_after_ogust_three_nt_stops(self) -> None:
        hand = evaluation(14, 3, 3, 4, 3)
        self.assertEqual(recommend_responder_rebid("2♥", "2NT", "3NT", hand, vulnerability=VULNERABILITY).bid, "Pass")

    def test_responder_rebid_invalid_contract_sequence_defaults_to_pass(self) -> None:
        hand = evaluation(8, 3, 3, 4, 3)
        self.assertEqual(recommend_responder_rebid("1♦", "1♥", "X", hand, vulnerability=VULNERABILITY).bid, "Pass")


class UtilityRuleTests(unittest.TestCase):
    def test_parse_contract_bid(self) -> None:
        self.assertEqual(parse_contract_bid("3NT"), (3, "NT"))
        self.assertEqual(parse_contract_bid("2♥"), (2, "♥"))
        self.assertIsNone(parse_contract_bid("2X"))
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

    def test_legal_response_bids_with_invalid_interference_does_not_add_double(self) -> None:
        self.assertNotIn("X", legal_response_bids_with_interference("1♣", "X"))

    def test_vulnerability_and_scoring_adjustment(self) -> None:
        self.assertEqual(game_threshold_adjustment("双方无局", RuleSettings(scoring_mode="IMP")), 0)
        self.assertEqual(game_threshold_adjustment("南北有局", RuleSettings(scoring_mode="IMP")), -1)
        self.assertEqual(game_threshold_adjustment("双方无局", RuleSettings(scoring_mode="MP")), 1)
        self.assertEqual(game_threshold_adjustment("双方无局", RuleSettings(scoring_mode="IMP", game_aggressiveness=1)), -1)

    def test_negative_double_availability_guard_branches(self) -> None:
        self.assertFalse(is_negative_double_available("2♣", "2♦"))
        self.assertFalse(is_negative_double_available("1♠", "2♣"))
        self.assertFalse(is_negative_double_available("1NT", "1♦"))
        self.assertFalse(is_negative_double_available("1♣", "1NT"))
        self.assertFalse(is_negative_double_available("1♥", "1♦"))

    def test_negative_double_target_majors_maps_sequences(self) -> None:
        self.assertEqual(negative_double_target_majors("1♣", "1♦"), ["H", "S"])
        self.assertEqual(negative_double_target_majors("1♣", "1♠"), ["H"])
        self.assertEqual(negative_double_target_majors("1♦", "1♥"), ["S"])
        self.assertEqual(negative_double_target_majors("1♥", "1♠"), ["D"])
        self.assertEqual(negative_double_target_majors("X", "1♠"), [])

    def test_should_make_negative_double_returns_false_when_unavailable(self) -> None:
        hand = evaluation(12, 4, 2, 4, 3, balanced=False)
        self.assertFalse(should_make_negative_double("1♠", "1NT", hand, RuleSettings()))

    def test_choose_raise_level_thresholds(self) -> None:
        self.assertEqual(choose_raise_level(2, 19), 4)
        self.assertEqual(choose_raise_level(1, 16), 3)

    def test_next_legal_contract_returns_none_when_no_legal_contract(self) -> None:
        self.assertIsNone(next_legal_contract("7NT", ["Pass", "1♣"]))

    def test_find_splinter_suit_boundaries(self) -> None:
        self.assertIsNone(find_splinter_suit("H", {"S": 4, "H": 3, "D": 3, "C": 3}))
        self.assertEqual(find_splinter_suit("H", {"S": 1, "H": 4, "D": 5, "C": 3}), "S")
        self.assertIsNone(find_splinter_suit("S", {"S": 4, "H": 3, "D": 3, "C": 3}))

    def test_choose_two_over_one_suit_returns_none_without_candidates(self) -> None:
        self.assertIsNone(choose_two_over_one_suit({"S": 5, "H": 3, "D": 3, "C": 2}, excluded="S"))

    def test_choose_one_level_major_response_returns_none_without_four_card_major(self) -> None:
        self.assertIsNone(choose_one_level_major_response({"S": 3, "H": 3, "D": 4, "C": 3}))

    def test_choose_one_level_major_response_prefers_spade_when_longer(self) -> None:
        self.assertEqual(choose_one_level_major_response({"S": 5, "H": 4, "D": 2, "C": 2}), "S")

    def test_response_to_weak_two_helper_asks_two_nt_when_strong_balanced(self) -> None:
        result = recommend_response_to_weak_two("H", evaluation(15, 3, 3, 4, 3, balanced=True))
        self.assertEqual(result.bid, "2NT")

    def test_response_to_weak_two_helper_passes_when_not_strong_balanced(self) -> None:
        result = recommend_response_to_weak_two("S", evaluation(10, 3, 3, 4, 3, balanced=True))
        self.assertEqual(result.bid, "Pass")

    def test_response_to_preempt_helper_invalid_bid_defaults_pass(self) -> None:
        result = recommend_response_to_preempt("X", evaluation(12, 3, 3, 4, 3, balanced=True))
        self.assertEqual(result.bid, "Pass")


if __name__ == "__main__":
    unittest.main()
