from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable

SUITS = ["S", "H", "D", "C"]
SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
RANKS = ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"]
RANK_ORDER = {rank: index for index, rank in enumerate(RANKS)}
SUIT_NAMES = {"S": "黑桃", "H": "红心", "D": "方块", "C": "梅花"}


@dataclass(frozen=True, order=True)
class Card:
    suit: str
    rank: str

    def label(self) -> str:
        return f"{SUIT_SYMBOLS[self.suit]}{self.rank}"


Hand = list[Card]


def new_deck() -> list[Card]:
    return [Card(suit, rank) for suit in SUITS for rank in RANKS]


def deal(seed: int | None = None) -> dict[str, Hand]:
    deck = new_deck()
    rng = random.Random(seed)
    rng.shuffle(deck)
    players = ["N", "E", "S", "W"]
    return {player: sort_hand(deck[i * 13 : (i + 1) * 13]) for i, player in enumerate(players)}


def sort_hand(hand: Iterable[Card]) -> Hand:
    return sorted(hand, key=lambda card: (SUITS.index(card.suit), RANK_ORDER[card.rank]))


def cards_by_suit(hand: Iterable[Card]) -> dict[str, list[Card]]:
    grouped = {suit: [] for suit in SUITS}
    for card in sort_hand(hand):
        grouped[card.suit].append(card)
    return grouped


def format_hand_lines(hand: Iterable[Card]) -> list[str]:
    grouped = cards_by_suit(hand)
    lines: list[str] = []
    for suit in SUITS:
        ranks = " ".join(card.rank for card in grouped[suit]) or "—"
        lines.append(f"{SUIT_SYMBOLS[suit]} {ranks}")
    return lines
