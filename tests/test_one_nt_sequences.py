from __future__ import annotations

import unittest

from bridge_trainer.bidding import (
    recommend_opener_rebid,
    recommend_responder_rebid,
)
from bridge_trainer.evaluator import HandEvaluation


VULNERABILITY = "双方无局"


def evaluation(hcp: int, spades: int, hearts: int, diamonds: int, clubs: int) -> HandEvaluation:
    lengths = {"S": spades, "H": hearts, "D": diamonds, "C": clubs}
    shape = f"{spades}-{hearts}-{diamonds}-{clubs}"
    longest = max(lengths.values())
    return HandEvaluation(
        hcp=hcp,
        lengths=lengths,
        shape=shape,
        balanced=tuple(sorted(lengths.values(), reverse=True)) in {(4, 3, 3, 3), (4, 4, 3, 2), (5, 3, 3, 2)},
        longest_suits=[suit for suit, length in lengths.items() if length == longest],
    )


class OneNtOpenerRebidTests(unittest.TestCase):
    def test_accepts_heart_transfer(self) -> None:
        hand = evaluation(16, 3, 3, 4, 3)
        recommendation = recommend_opener_rebid("1NT", "2♦", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "2♥")

    def test_accepts_spade_transfer(self) -> None:
        hand = evaluation(16, 3, 3, 4, 3)
        recommendation = recommend_opener_rebid("1NT", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "2♠")

    def test_stayman_answers_heart_before_spade(self) -> None:
        hand = evaluation(16, 4, 4, 3, 2)
        recommendation = recommend_opener_rebid("1NT", "2♣", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "2♥")

    def test_stayman_answers_spade_without_four_hearts(self) -> None:
        hand = evaluation(16, 4, 3, 3, 3)
        recommendation = recommend_opener_rebid("1NT", "2♣", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "2♠")

    def test_stayman_denies_without_four_card_major(self) -> None:
        hand = evaluation(16, 3, 3, 4, 3)
        recommendation = recommend_opener_rebid("1NT", "2♣", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "2♦")

    def test_accepts_two_nt_invite_with_maximum(self) -> None:
        hand = evaluation(17, 3, 3, 4, 3)
        recommendation = recommend_opener_rebid("1NT", "2NT", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "3NT")

    def test_rejects_two_nt_invite_with_minimum(self) -> None:
        hand = evaluation(15, 3, 3, 4, 3)
        recommendation = recommend_opener_rebid("1NT", "2NT", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "Pass")


class OneNtResponderRebidTests(unittest.TestCase):
    def test_stayman_negative_invites_with_eight_hcp(self) -> None:
        hand = evaluation(8, 4, 4, 3, 2)
        recommendation = recommend_responder_rebid("1NT", "2♣", "2♦", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "2NT")

    def test_stayman_negative_games_with_ten_hcp(self) -> None:
        hand = evaluation(10, 4, 4, 3, 2)
        recommendation = recommend_responder_rebid("1NT", "2♣", "2♦", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "3NT")

    def test_stayman_negative_passes_with_seven_hcp(self) -> None:
        hand = evaluation(7, 4, 4, 3, 2)
        recommendation = recommend_responder_rebid("1NT", "2♣", "2♦", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "Pass")

    def test_stayman_major_fit_games_with_ten_hcp(self) -> None:
        hand = evaluation(10, 3, 4, 3, 3)
        recommendation = recommend_responder_rebid("1NT", "2♣", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "4♥")

    def test_stayman_major_fit_invites_with_eight_hcp(self) -> None:
        hand = evaluation(8, 3, 4, 3, 3)
        recommendation = recommend_responder_rebid("1NT", "2♣", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "3♥")

    def test_stayman_major_response_without_fit_games_in_nt(self) -> None:
        hand = evaluation(10, 3, 3, 4, 3)
        recommendation = recommend_responder_rebid("1NT", "2♣", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "3NT")

    def test_stayman_major_response_without_fit_invites_in_nt(self) -> None:
        hand = evaluation(8, 3, 3, 4, 3)
        recommendation = recommend_responder_rebid("1NT", "2♣", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "2NT")

    def test_stayman_major_response_without_fit_passes_with_low_values(self) -> None:
        hand = evaluation(5, 3, 3, 4, 3)
        recommendation = recommend_responder_rebid("1NT", "2♣", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "Pass")

    def test_heart_transfer_invites_with_eight_hcp(self) -> None:
        hand = evaluation(8, 3, 5, 3, 2)
        recommendation = recommend_responder_rebid("1NT", "2♦", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "2NT")

    def test_heart_transfer_passes_with_seven_hcp(self) -> None:
        hand = evaluation(7, 3, 5, 3, 2)
        recommendation = recommend_responder_rebid("1NT", "2♦", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "Pass")

    def test_heart_transfer_games_in_major_with_six_hearts(self) -> None:
        hand = evaluation(10, 2, 6, 3, 2)
        recommendation = recommend_responder_rebid("1NT", "2♦", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "4♥")

    def test_heart_transfer_games_in_nt_without_six_hearts(self) -> None:
        hand = evaluation(10, 3, 5, 3, 2)
        recommendation = recommend_responder_rebid("1NT", "2♦", "2♥", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "3NT")

    def test_spade_transfer_invites_with_eight_hcp(self) -> None:
        hand = evaluation(8, 5, 3, 3, 2)
        recommendation = recommend_responder_rebid("1NT", "2♥", "2♠", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "2NT")

    def test_spade_transfer_games_in_major_with_six_spades(self) -> None:
        hand = evaluation(10, 6, 3, 2, 2)
        recommendation = recommend_responder_rebid("1NT", "2♥", "2♠", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "4♠")

    def test_spade_transfer_games_in_nt_without_six_spades(self) -> None:
        hand = evaluation(10, 5, 3, 3, 2)
        recommendation = recommend_responder_rebid("1NT", "2♥", "2♠", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "3NT")

    def test_spade_transfer_passes_with_low_values(self) -> None:
        hand = evaluation(5, 5, 3, 3, 2)
        recommendation = recommend_responder_rebid("1NT", "2♥", "2♠", hand, vulnerability=VULNERABILITY)
        self.assertEqual(recommendation.bid, "Pass")


if __name__ == "__main__":
    unittest.main()
