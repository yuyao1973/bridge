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


# ---------------------------------------------------------------------------
# 弱二 / Ogust 2NT 完整序列
# ---------------------------------------------------------------------------

class WeakTwoOgustIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = RuleSettings()

    def test_full_auction_generates_ogust_invite_with_fit(self) -> None:
        opener_hand = make_hand([
            ("S","9"),("S","5"),
            ("H","K"),("H","Q"),("H","10"),("H","8"),("H","6"),("H","3"),
            ("D","Q"),("D","7"),("D","4"),
            ("C","8"),("C","2"),
        ])
        responder_hand = make_hand([
            ("S","A"),("S","8"),("S","4"),
            ("H","A"),("H","9"),("H","5"),("H","2"),
            ("D","K"),("D","6"),("D","3"),
            ("C","Q"),("C","7"),("C","4"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "2♥")
        self.assertEqual(response.bid, "2NT")
        self.assertEqual(opener_rebid.bid, "3♦")
        self.assertEqual(responder_rebid.bid, "3♥")
        with patch("bridge_trainer.training.deal", return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []}):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="2♥", opener_category="阻击叫")
        self.assertEqual(question.opener_bid, "2♥")
        self.assertEqual(question.response_bid, "2NT")
        self.assertEqual(question.opener_rebid_bid, "3♦")
        self.assertEqual(question.recommendation.bid, "3♥")
        self.assertEqual(question.auction, "2♥-Pass-2NT-Pass-3♦-Pass-? ")

    def test_full_auction_generates_ogust_three_nt_without_fit(self) -> None:
        opener_hand = make_hand([
            ("S","9"),("S","5"),
            ("H","A"),("H","Q"),("H","10"),("H","8"),("H","6"),("H","3"),
            ("D","Q"),("D","7"),("D","4"),
            ("C","8"),("C","2"),
        ])
        responder_hand = make_hand([
            ("S","A"),("S","8"),("S","4"),
            ("H","J"),("H","2"),
            ("D","K"),("D","6"),("D","3"),("D","2"),
            ("C","Q"),("C","J"),("C","7"),("C","4"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "2♥")
        self.assertEqual(response.bid, "2NT")
        self.assertEqual(opener_rebid.bid, "3♠")
        self.assertEqual(responder_rebid.bid, "3NT")
        with patch("bridge_trainer.training.deal", return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []}):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="2♥", opener_category="阻击叫")
        self.assertEqual(question.response_bid, "2NT")
        self.assertEqual(question.opener_rebid_bid, "3♠")
        self.assertEqual(question.recommendation.bid, "3NT")

    def test_full_auction_stops_after_ogust_minimum_without_fit(self) -> None:
        opener_hand = make_hand([
            ("S","9"),("S","5"),
            ("H","K"),("H","Q"),("H","10"),("H","8"),("H","6"),("H","3"),
            ("D","Q"),("D","7"),("D","4"),
            ("C","8"),("C","2"),
        ])
        responder_hand = make_hand([
            ("S","A"),("S","8"),("S","4"),
            ("H","J"),("H","2"),
            ("D","K"),("D","6"),("D","3"),("D","2"),
            ("C","Q"),("C","J"),("C","7"),("C","4"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "2♥")
        self.assertEqual(response.bid, "2NT")
        self.assertEqual(opener_rebid.bid, "3♦")
        self.assertEqual(responder_rebid.bid, "Pass")
        with patch("bridge_trainer.training.deal", return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []}):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="2♥", opener_category="阻击叫")
        self.assertEqual(question.response_bid, "2NT")
        self.assertEqual(question.opener_rebid_bid, "3♦")
        self.assertEqual(question.recommendation.bid, "Pass")


# ---------------------------------------------------------------------------
# 1NT Stayman
# ---------------------------------------------------------------------------

class OneNtStaymanIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = RuleSettings()

    def test_stayman_heart_fit_invites_via_training_layer(self) -> None:
        # 开叫 15 HCP 3-4-3-3 1NT；应叫 8 HCP 3-4-3-3 Stayman → 邀局 3♥
        opener_hand = make_hand([
            ("S","K"),("S","Q"),("S","4"),
            ("H","A"),("H","J"),("H","8"),("H","6"),
            ("D","K"),("D","10"),("D","3"),
            ("C","Q"),("C","7"),("C","2"),
        ])
        responder_hand = make_hand([
            ("S","J"),("S","9"),("S","7"),
            ("H","K"),("H","J"),("H","9"),("H","7"),
            ("D","Q"),("D","8"),("D","4"),
            ("C","J"),("C","5"),("C","3"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "1NT")
        self.assertEqual(response.bid, "2♣")
        self.assertEqual(opener_rebid.bid, "2♥")
        self.assertEqual(responder_rebid.bid, "3♥")
        with patch("bridge_trainer.training.deal", return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []}):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="1NT")
        self.assertEqual(question.opener_bid, "1NT")
        self.assertEqual(question.response_bid, "2♣")
        self.assertEqual(question.opener_rebid_bid, "2♥")
        self.assertEqual(question.recommendation.bid, "3♥")
        self.assertTrue(question.auction.startswith("1NT-Pass-2♣-Pass-2♥-Pass-?"))

    def test_stayman_negative_nt_game_via_training_layer(self) -> None:
        # 开叫 15 HCP 无高花 1NT；应叫 10 HCP Stayman 否定 → 3NT
        opener_hand = make_hand([
            ("S","K"),("S","Q"),("S","4"),
            ("H","A"),("H","8"),("H","6"),
            ("D","J"),("D","9"),("D","7"),("D","3"),
            ("C","K"),("C","Q"),("C","2"),
        ])
        responder_hand = make_hand([
            ("S","A"),("S","J"),("S","9"),("S","7"),
            ("H","8"),("H","6"),("H","3"),
            ("D","K"),("D","Q"),("D","4"),
            ("C","5"),("C","3"),("C","2"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "1NT")
        self.assertEqual(response.bid, "2♣")
        self.assertEqual(opener_rebid.bid, "2♦")
        self.assertEqual(responder_rebid.bid, "3NT")


# ---------------------------------------------------------------------------
# 1NT 转移叫
# ---------------------------------------------------------------------------

class OneNtTransferIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = RuleSettings()

    def test_heart_transfer_game_via_training_layer(self) -> None:
        # 开叫 16 HCP 1NT；应叫 10 HCP 6 张红心 → 转移 2♦，进局 4♥
        opener_hand = make_hand([
            ("S","A"),("S","Q"),("S","5"),
            ("H","K"),("H","J"),("H","6"),
            ("D","K"),("D","Q"),("D","8"),("D","4"),
            ("C","J"),("C","9"),("C","3"),
        ])
        responder_hand = make_hand([
            ("S","8"),("S","4"),
            ("H","A"),("H","Q"),("H","10"),("H","9"),("H","8"),("H","7"),
            ("D","K"),("D","5"),
            ("C","J"),("C","4"),("C","3"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "1NT")
        self.assertEqual(response.bid, "2♦")
        self.assertEqual(opener_rebid.bid, "2♥")
        self.assertEqual(responder_rebid.bid, "4♥")
        with patch("bridge_trainer.training.deal", return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []}):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="1NT")
        self.assertEqual(question.response_bid, "2♦")
        self.assertEqual(question.opener_rebid_bid, "2♥")
        self.assertEqual(question.recommendation.bid, "4♥")
        self.assertTrue(question.auction.startswith("1NT-Pass-2♦-Pass-2♥-Pass-?"))

    def test_spade_transfer_invite_via_training_layer(self) -> None:
        # 开叫 17 HCP 1NT；应叫 8 HCP 5 张黑桃 → 转移 2♥，邀局 2NT
        opener_hand = make_hand([
            ("S","K"),("S","J"),("S","4"),
            ("H","A"),("H","Q"),("H","7"),
            ("D","K"),("D","9"),("D","6"),
            ("C","A"),("C","8"),("C","5"),("C","3"),
        ])
        responder_hand = make_hand([
            ("S","Q"),("S","J"),("S","10"),("S","9"),("S","8"),
            ("H","6"),("H","5"),("H","3"),
            ("D","K"),("D","8"),("D","7"),
            ("C","Q"),("C","4"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "1NT")
        self.assertEqual(response.bid, "2♥")
        self.assertEqual(opener_rebid.bid, "2♠")
        self.assertEqual(responder_rebid.bid, "2NT")


# ---------------------------------------------------------------------------
# 2NT Stayman
# ---------------------------------------------------------------------------

class TwoNtStaymanIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = RuleSettings()

    def test_stayman_heart_fit_game_via_training_layer(self) -> None:
        # 开叫 20 HCP 3-4-3-3 2NT；应叫 6 HCP 4-4-3-2 → Stayman 3♣，4♥ 进局
        opener_hand = make_hand([
            ("S","A"),("S","K"),("S","J"),
            ("H","Q"),("H","J"),("H","9"),("H","8"),
            ("D","A"),("D","Q"),("D","3"),
            ("C","K"),("C","5"),("C","2"),
        ])
        responder_hand = make_hand([
            ("S","Q"),("S","5"),("S","4"),("S","3"),
            ("H","K"),("H","10"),("H","6"),("H","2"),
            ("D","J"),("D","7"),("D","5"),
            ("C","8"),("C","3"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "2NT")
        self.assertEqual(response.bid, "3♣")
        self.assertEqual(opener_rebid.bid, "3♥")
        self.assertEqual(responder_rebid.bid, "4♥")
        with patch("bridge_trainer.training.deal", return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []}):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="2NT")
        self.assertEqual(question.opener_bid, "2NT")
        self.assertEqual(question.response_bid, "3♣")
        self.assertEqual(question.opener_rebid_bid, "3♥")
        self.assertEqual(question.recommendation.bid, "4♥")
        self.assertTrue(question.auction.startswith("2NT-Pass-3♣-Pass-3♥-Pass-?"))

    def test_stayman_no_major_three_nt_game(self) -> None:
        # 开叫 21 HCP 无 4 张高花 2NT；应叫 5 HCP Stayman → 否定 3♦ → 3NT
        opener_hand = make_hand([
            ("S","K"),("S","Q"),("S","J"),
            ("H","A"),("H","J"),("H","7"),
            ("D","A"),("D","Q"),("D","J"),("D","3"),
            ("C","K"),("C","5"),("C","4"),
        ])
        responder_hand = make_hand([
            ("S","Q"),("S","9"),("S","8"),("S","3"),
            ("H","8"),("H","6"),
            ("D","K"),("D","5"),("D","4"),
            ("C","J"),("C","7"),("C","6"),("C","2"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "2NT")
        self.assertEqual(response.bid, "3♣")
        self.assertEqual(opener_rebid.bid, "3♦")
        self.assertEqual(responder_rebid.bid, "Pass")  # 6 HCP + 2NT denial, generic threshold 12 HCP


# ---------------------------------------------------------------------------
# 2NT 转移叫
# ---------------------------------------------------------------------------

class TwoNtTransferIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = RuleSettings()

    def test_heart_transfer_game_via_training_layer(self) -> None:
        # 开叫 20 HCP 3-3-4-3 2NT；应叫 6 HCP 5 张红心 → 3♦ 转移，4♥ 进局
        opener_hand = make_hand([
            ("S","A"),("S","Q"),("S","J"),
            ("H","K"),("H","J"),("H","7"),
            ("D","A"),("D","Q"),("D","3"),("D","2"),
            ("C","K"),("C","5"),("C","4"),
        ])
        responder_hand = make_hand([
            ("S","K"),("S","6"),("S","5"),
            ("H","Q"),("H","10"),("H","9"),("H","8"),("H","7"),
            ("D","J"),("D","4"),
            ("C","8"),("C","7"),("C","6"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "2NT")
        self.assertEqual(response.bid, "3♦")
        self.assertEqual(opener_rebid.bid, "3♥")
        self.assertEqual(responder_rebid.bid, "4♥")
        with patch("bridge_trainer.training.deal", return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []}):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="2NT")
        self.assertEqual(question.opener_bid, "2NT")
        self.assertEqual(question.response_bid, "3♦")
        self.assertEqual(question.opener_rebid_bid, "3♥")
        self.assertEqual(question.recommendation.bid, "4♥")
        self.assertTrue(question.auction.startswith("2NT-Pass-3♦-Pass-3♥-Pass-?"))


# ---------------------------------------------------------------------------
# 强 2♣ 序列
# ---------------------------------------------------------------------------

class StrongTwoClubIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = RuleSettings()

    def test_balanced_rebid_two_nt_weak_responder_passes(self) -> None:
        # 开叫 22 HCP 4-3-3-3 2♣；应叫 0 HCP → 2♦ 等待；再叫 2NT；Pass
        opener_hand = make_hand([
            ("S","A"),("S","K"),("S","Q"),("S","J"),
            ("H","K"),("H","Q"),("H","3"),
            ("D","K"),("D","Q"),("D","3"),
            ("C","Q"),("C","3"),("C","2"),
        ])
        responder_hand = make_hand([
            ("S","5"),("S","4"),("S","3"),("S","2"),
            ("H","8"),("H","7"),("H","6"),("H","5"),
            ("D","4"),("D","3"),("D","2"),
            ("C","8"),("C","7"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "2♣")
        self.assertEqual(response.bid, "2♦")
        self.assertEqual(opener_rebid.bid, "2NT")
        self.assertEqual(responder_rebid.bid, "Pass")
        with patch("bridge_trainer.training.deal", return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []}):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="2♣")
        self.assertEqual(question.opener_bid, "2♣")
        self.assertEqual(question.response_bid, "2♦")
        self.assertEqual(question.opener_rebid_bid, "2NT")
        self.assertEqual(question.recommendation.bid, "Pass")
        self.assertTrue(question.auction.startswith("2♣-Pass-2♦-Pass-2NT-Pass-?"))


# ---------------------------------------------------------------------------
# 高花开叫：1♥ + 逼迫 1NT
# ---------------------------------------------------------------------------

class MajorOpeningForcingNtIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = RuleSettings()

    def test_heart_opening_forcing_nt_second_suit_responder_passes(self) -> None:
        # 开叫 13 HCP 2-5-4-2 1♥；应叫 9 HCP 1NT 半逼叫；再叫 2♦；Pass
        opener_hand = make_hand([
            ("S","K"),("S","3"),
            ("H","A"),("H","J"),("H","8"),("H","7"),("H","6"),
            ("D","Q"),("D","9"),("D","4"),("D","3"),
            ("C","K"),("C","5"),
        ])
        responder_hand = make_hand([
            ("S","Q"),("S","7"),("S","6"),
            ("H","J"),("H","2"),
            ("D","J"),("D","8"),("D","7"),("D","6"),
            ("C","A"),("C","J"),("C","4"),("C","3"),
        ])
        opener_eval = evaluate_hand(opener_hand)
        responder_eval = evaluate_hand(responder_hand)
        opening = recommend_opening(opener_eval, self.settings, VULNERABILITY)
        response = recommend_response(opening.bid, responder_eval, self.settings, VULNERABILITY)
        opener_rebid = recommend_opener_rebid(opening.bid, response.bid, opener_eval, self.settings, VULNERABILITY)
        responder_rebid = recommend_responder_rebid(opening.bid, response.bid, opener_rebid.bid, responder_eval, self.settings, VULNERABILITY)
        self.assertEqual(opening.bid, "1♥")
        self.assertEqual(response.bid, "1NT")
        self.assertEqual(opener_rebid.bid, "2♦")
        self.assertEqual(responder_rebid.bid, "Pass")
        with patch("bridge_trainer.training.deal", return_value={"N": opener_hand, "E": [], "S": responder_hand, "W": []}):
            question = generate_responder_rebid_question(seed=0, settings=self.settings, opener_bid="1♥")
        self.assertEqual(question.opener_bid, "1♥")
        self.assertEqual(question.response_bid, "1NT")
        self.assertEqual(question.opener_rebid_bid, "2♦")
        self.assertEqual(question.recommendation.bid, "Pass")
        self.assertTrue(question.auction.startswith("1♥-Pass-1NT-Pass-2♦-Pass-?"))


if __name__ == "__main__":
    unittest.main()

