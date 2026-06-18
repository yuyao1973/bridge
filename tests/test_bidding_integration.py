from __future__ import annotations

import unittest
from unittest.mock import patch

from bridge_trainer.bidding import (
    RuleSettings,
    recommend_opening,
    recommend_opener_rebid,
    recommend_responder_rebid,
    recommend_response,
)
from bridge_trainer.cards import Card, Hand
from bridge_trainer.evaluator import evaluate_hand
from bridge_trainer.training import generate_responder_rebid_question


VULNERABILITY = "双方无局"


def make_hand(cards: list[tuple[str, str]]) -> Hand:
    return [Card(suit, rank) for suit, rank in cards]


class WeakTwoOgustIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = RuleSettings()

    def test_full_auction_generates_ogust_invite_with_fit(self) -> None:
        opener_hand = make_hand(
            [
                ("S", "9"),
                ("S", "5"),
                ("H", "K"),
                ("H", "Q"),
                ("H", "10"),
                ("H", "8"),
                ("H", "6"),
                ("H", "3"),
                ("D", "Q"),
                ("D", "7"),
                ("D", "4"),
                ("C", "8"),
                ("C", "2"),
            ]
        )
        responder_hand = make_hand(
            [
                ("S", "A"),
                ("S", "8"),
                ("S", "4"),
                ("H", "A"),
                ("H", "9"),
                ("H", "5"),
                ("H", "2"),
                ("D", "K"),
                ("D", "6"),
                ("D", "3"),
                ("C", "Q"),
                ("C", "7"),
                ("C", "4"),
            ]
        )

        opener_evaluation = evaluate_hand(opener_hand)
        responder_evaluation = evaluate_hand(responder_hand)

        opening = recommend_opening(opener_evaluation, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_evaluation, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_evaluation, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(
            opening.bid,
            response.bid,
            opener_rebid.bid,
            responder_evaluation,
            self.settings,
            VULNERABILITY,
        )

        self.assertEqual(opening.bid, "2♥")
        self.assertEqual(response.bid, "2NT")
        self.assertEqual(opener_rebid.bid, "3♦")
        self.assertEqual(responder_rebid.bid, "3♥")

        with patch(
            "bridge_trainer.training.deal",
            return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []},
        ):
            question = generate_responder_rebid_question(
                seed=0,
                settings=self.settings,
                opener_bid="2♥",
                opener_category="阻击叫",
            )

        self.assertEqual(question.opener_bid, "2♥")
        self.assertEqual(question.response_bid, "2NT")
        self.assertEqual(question.opener_rebid_bid, "3♦")
        self.assertEqual(question.recommendation.bid, "3♥")
        self.assertEqual(question.auction, "2♥-Pass-2NT-Pass-3♦-Pass-? ")

    def test_full_auction_generates_ogust_three_nt_without_fit(self) -> None:
        opener_hand = make_hand(
            [
                ("S", "9"),
                ("S", "5"),
                ("H", "A"),
                ("H", "Q"),
                ("H", "10"),
                ("H", "8"),
                ("H", "6"),
                ("H", "3"),
                ("D", "Q"),
                ("D", "7"),
                ("D", "4"),
                ("C", "8"),
                ("C", "2"),
            ]
        )
        responder_hand = make_hand(
            [
                ("S", "A"),
                ("S", "8"),
                ("S", "4"),
                ("H", "J"),
                ("H", "2"),
                ("D", "K"),
                ("D", "6"),
                ("D", "3"),
                ("D", "2"),
                ("C", "Q"),
                ("C", "J"),
                ("C", "7"),
                ("C", "4"),
            ]
        )

        opener_evaluation = evaluate_hand(opener_hand)
        responder_evaluation = evaluate_hand(responder_hand)

        opening = recommend_opening(opener_evaluation, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_evaluation, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_evaluation, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(
            opening.bid,
            response.bid,
            opener_rebid.bid,
            responder_evaluation,
            self.settings,
            VULNERABILITY,
        )

        self.assertEqual(opening.bid, "2♥")
        self.assertEqual(response.bid, "2NT")
        self.assertEqual(opener_rebid.bid, "3♠")
        self.assertEqual(responder_rebid.bid, "3NT")

        with patch(
            "bridge_trainer.training.deal",
            return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []},
        ):
            question = generate_responder_rebid_question(
                seed=0,
                settings=self.settings,
                opener_bid="2♥",
                opener_category="阻击叫",
            )

        self.assertEqual(question.response_bid, "2NT")
        self.assertEqual(question.opener_rebid_bid, "3♠")
        self.assertEqual(question.recommendation.bid, "3NT")

    def test_full_auction_stops_after_ogust_minimum_without_fit(self) -> None:
        opener_hand = make_hand(
            [
                ("S", "9"),
                ("S", "5"),
                ("H", "K"),
                ("H", "Q"),
                ("H", "10"),
                ("H", "8"),
                ("H", "6"),
                ("H", "3"),
                ("D", "Q"),
                ("D", "7"),
                ("D", "4"),
                ("C", "8"),
                ("C", "2"),
            ]
        )
        responder_hand = make_hand(
            [
                ("S", "A"),
                ("S", "8"),
                ("S", "4"),
                ("H", "J"),
                ("H", "2"),
                ("D", "K"),
                ("D", "6"),
                ("D", "3"),
                ("D", "2"),
                ("C", "Q"),
                ("C", "J"),
                ("C", "7"),
                ("C", "4"),
            ]
        )

        opener_evaluation = evaluate_hand(opener_hand)
        responder_evaluation = evaluate_hand(responder_hand)

        opening = recommend_opening(opener_evaluation, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_evaluation, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_evaluation, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(
            opening.bid,
            response.bid,
            opener_rebid.bid,
            responder_evaluation,
            self.settings,
            VULNERABILITY,
        )

        self.assertEqual(opening.bid, "2♥")
        self.assertEqual(response.bid, "2NT")
        self.assertEqual(opener_rebid.bid, "3♦")
        self.assertEqual(responder_rebid.bid, "Pass")

        with patch(
            "bridge_trainer.training.deal",
            return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []},
        ):
            question = generate_responder_rebid_question(
                seed=0,
                settings=self.settings,
                opener_bid="2♥",
                opener_category="阻击叫",
            )

        self.assertEqual(question.response_bid, "2NT")
        self.assertEqual(question.opener_rebid_bid, "3♦")
        self.assertEqual(question.recommendation.bid, "Pass")


class OneNtStaymanIntegrationTests(unittest.TestCase):
    """Full auction chain: 1NT → Stayman → major-fit response → responder decides."""

    def setUp(self) -> None:
        self.settings = RuleSettings()

    def test_stayman_heart_fit_invites_via_training_layer(self) -> None:
        # Opener: 15 HCP, 3-4-3-3 balanced, 4-card hearts → opens 1NT
        # KQ4 / AJ86 / K103 / Q72
        opener_hand = make_hand(
            [
                ("S", "K"), ("S", "Q"), ("S", "4"),
                ("H", "A"), ("H", "J"), ("H", "8"), ("H", "6"),
                ("D", "K"), ("D", "10"), ("D", "3"),
                ("C", "Q"), ("C", "7"), ("C", "2"),
            ]
        )
        # Responder: 8 HCP, 3-4-3-3, 4-card hearts → Stayman, invite
        # J97 / KJ97 / Q84 / J53
        responder_hand = make_hand(
            [
                ("S", "J"), ("S", "9"), ("S", "7"),
                ("H", "K"), ("H", "J"), ("H", "9"), ("H", "7"),
                ("D", "Q"), ("D", "8"), ("D", "4"),
                ("C", "J"), ("C", "5"), ("C", "3"),
            ]
        )

        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)

        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(
            opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY
        )

        self.assertEqual(opening.bid, "1NT")
        self.assertEqual(response.bid, "2♣")   # Stayman
        self.assertEqual(opener_rebid.bid, "2♥")   # 4-card heart fit
        self.assertEqual(responder_rebid.bid, "3♥")  # invite

        with patch(
            "bridge_trainer.training.deal",
            return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []},
        ):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="1NT")

        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.response_bid, "2♣")
        self.assertEqual(question.opener_rebid_bid, "2♥")
        self.assertEqual(question.recommendation.bid, "3♥")
        self.assertTrue(question.auction.startswith("1NT-Pass-2♣-Pass-2♥-Pass-?"))

    def test_stayman_negative_nt_game_via_training_layer(self) -> None:
        # Opener: 15 HCP, 3-3-4-3 balanced, no 4-card major → opens 1NT
        # KQ4 / A86 / J973 / KQ2
        opener_hand = make_hand(
            [
                ("S", "K"), ("S", "Q"), ("S", "4"),
                ("H", "A"), ("H", "8"), ("H", "6"),
                ("D", "J"), ("D", "9"), ("D", "7"), ("D", "3"),
                ("C", "K"), ("C", "Q"), ("C", "2"),
            ]
        )
        # Responder: 10 HCP, 4-3-3-3, 4-card spades → Stayman, no fit, 3NT
        # AJ97 / 863 / KQ4 / 532
        responder_hand = make_hand(
            [
                ("S", "A"), ("S", "J"), ("S", "9"), ("S", "7"),
                ("H", "8"), ("H", "6"), ("H", "3"),
                ("D", "K"), ("D", "Q"), ("D", "4"),
                ("C", "5"), ("C", "3"), ("C", "2"),
            ]
        )

        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)

        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(
            opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY
        )

        self.assertEqual(opening.bid, "1NT")
        self.assertEqual(response.bid, "2♣")   # Stayman
        self.assertEqual(opener_rebid.bid, "2♦")  # no major
        self.assertEqual(responder_rebid.bid, "3NT")  # game in NT


class OneNtTransferIntegrationTests(unittest.TestCase):
    """Full auction chain: 1NT → Transfer → accept → responder decides."""

    def setUp(self) -> None:
        self.settings = RuleSettings()

    def test_heart_transfer_game_via_training_layer(self) -> None:
        # Opener: 16 HCP, 3-3-4-3 balanced → opens 1NT
        # AQ5 / KJ6 / KQ84 / J93
        opener_hand = make_hand(
            [
                ("S", "A"), ("S", "Q"), ("S", "5"),
                ("H", "K"), ("H", "J"), ("H", "6"),
                ("D", "K"), ("D", "Q"), ("D", "8"), ("D", "4"),
                ("C", "J"), ("C", "9"), ("C", "3"),
            ]
        )
        # Responder: 10 HCP, 2-6-2-3, 6-card hearts → transfer 2♦, game 4♥
        # 84 / AQ10987 / K5 / J43
        responder_hand = make_hand(
            [
                ("S", "8"), ("S", "4"),
                ("H", "A"), ("H", "Q"), ("H", "10"), ("H", "9"), ("H", "8"), ("H", "7"),
                ("D", "K"), ("D", "5"),
                ("C", "J"), ("C", "4"), ("C", "3"),
            ]
        )

        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)

        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(
            opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY
        )

        self.assertEqual(opening.bid, "1NT")
        self.assertEqual(response.bid, "2♦")   # heart transfer
        self.assertEqual(opener_rebid.bid, "2♥")  # accept
        self.assertEqual(responder_rebid.bid, "4♥")  # game with 6+ hearts

        with patch(
            "bridge_trainer.training.deal",
            return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []},
        ):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="1NT")

        self.assertEqual(question.response_bid, "2♦")
        self.assertEqual(question.opener_rebid_bid, "2♥")
        self.assertEqual(question.recommendation.bid, "4♥")
        self.assertTrue(question.auction.startswith("1NT-Pass-2♦-Pass-2♥-Pass-?"))

    def test_spade_transfer_invite_via_training_layer(self) -> None:
        # Opener: 17 HCP, 3-3-3-4 balanced → opens 1NT
        # KJ4 / AQ7 / K96 / A853
        opener_hand = make_hand(
            [
                ("S", "K"), ("S", "J"), ("S", "4"),
                ("H", "A"), ("H", "Q"), ("H", "7"),
                ("D", "K"), ("D", "9"), ("D", "6"),
                ("C", "A"), ("C", "8"), ("C", "5"), ("C", "3"),
            ]
        )
        # Responder: 8 HCP, 5-3-3-2, 5-card spades → transfer 2♥, invite 2NT
        # QJ1098 / 653 / K87 / Q4
        responder_hand = make_hand(
            [
                ("S", "Q"), ("S", "J"), ("S", "10"), ("S", "9"), ("S", "8"),
                ("H", "6"), ("H", "5"), ("H", "3"),
                ("D", "K"), ("D", "8"), ("D", "7"),
                ("C", "Q"), ("C", "4"),
            ]
        )

        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)

        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(
            opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY
        )

        self.assertEqual(opening.bid, "1NT")
        self.assertEqual(response.bid, "2♥")   # spade transfer
        self.assertEqual(opener_rebid.bid, "2♠")  # accept
        self.assertEqual(responder_rebid.bid, "2NT")  # invite (8 HCP, 5 spades)


if __name__ == "__main__":
    unittest.main()
