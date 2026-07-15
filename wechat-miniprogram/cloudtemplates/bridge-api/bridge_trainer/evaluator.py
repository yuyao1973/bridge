from __future__ import annotations

from dataclasses import dataclass, field

from .cards import Hand, SUITS, SUIT_NAMES

HCP_VALUES = {"A": 4, "K": 3, "Q": 2, "J": 1}
BALANCED_SHAPES = {(4, 3, 3, 3), (4, 4, 3, 2), (5, 3, 3, 2)}


@dataclass(frozen=True)
class HandEvaluation:
    hcp: int
    lengths: dict[str, int]
    shape: str
    balanced: bool
    longest_suits: list[str]
    top_honors_by_suit: dict[str, int] = field(
        default_factory=lambda: {suit: 0 for suit in SUITS}
    )

    @property
    def has_five_card_major(self) -> bool:
        return self.lengths["S"] >= 5 or self.lengths["H"] >= 5


def evaluate_hand(hand: Hand) -> HandEvaluation:
    hcp = sum(HCP_VALUES.get(card.rank, 0) for card in hand)
    lengths = {suit: 0 for suit in SUITS}
    for card in hand:
        lengths[card.suit] += 1
    top_honors_by_suit = {suit: 0 for suit in SUITS}
    for card in hand:
        if card.rank in {"A", "K", "Q"}:
            top_honors_by_suit[card.suit] += 1

    sorted_lengths = tuple(sorted(lengths.values(), reverse=True))
    max_length = max(lengths.values())
    longest_suits = [suit for suit in SUITS if lengths[suit] == max_length]
    shape = "-".join(str(lengths[suit]) for suit in SUITS)

    return HandEvaluation(
        hcp=hcp,
        lengths=lengths,
        shape=shape,
        balanced=sorted_lengths in BALANCED_SHAPES,
        longest_suits=longest_suits,
        top_honors_by_suit=top_honors_by_suit,
    )


def describe_lengths(evaluation: HandEvaluation) -> str:
    return "，".join(f"{SUIT_NAMES[suit]} {evaluation.lengths[suit]} 张" for suit in SUITS)
