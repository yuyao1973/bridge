"use strict";

const { SUITS, SUIT_NAMES } = require("./cards");

const HCP_VALUES = { A: 4, K: 3, Q: 2, J: 1 };
const BALANCED_SHAPES = new Set(["4-3-3-3", "4-4-3-2", "5-3-3-2"]);

function shapeKey(sortedLengths) {
  return sortedLengths.join("-");
}

function evaluate_hand(hand) {
  let hcp = 0;
  const lengths = { S: 0, H: 0, D: 0, C: 0 };
  const top_honors_by_suit = { S: 0, H: 0, D: 0, C: 0 };

  for (let i = 0; i < hand.length; i += 1) {
    const card = hand[i];
    hcp += HCP_VALUES[card.rank] || 0;
    lengths[card.suit] += 1;
    if (card.rank === "A" || card.rank === "K" || card.rank === "Q") {
      top_honors_by_suit[card.suit] += 1;
    }
  }

  const lengthValues = [lengths.S, lengths.H, lengths.D, lengths.C];
  const sortedLengths = lengthValues.slice().sort(function (a, b) {
    return b - a;
  });
  const maxLength = Math.max(lengths.S, lengths.H, lengths.D, lengths.C);
  const longest_suits = [];
  for (let i = 0; i < SUITS.length; i += 1) {
    if (lengths[SUITS[i]] === maxLength) {
      longest_suits.push(SUITS[i]);
    }
  }
  const shape = lengths.S + "-" + lengths.H + "-" + lengths.D + "-" + lengths.C;
  const balanced = BALANCED_SHAPES.has(shapeKey(sortedLengths));

  return {
    hcp: hcp,
    lengths: lengths,
    shape: shape,
    balanced: balanced,
    longest_suits: longest_suits,
    top_honors_by_suit: top_honors_by_suit,
    has_five_card_major: lengths.S >= 5 || lengths.H >= 5,
  };
}

function describe_lengths(evaluation) {
  const parts = [];
  for (let i = 0; i < SUITS.length; i += 1) {
    const suit = SUITS[i];
    parts.push(SUIT_NAMES[suit] + " " + evaluation.lengths[suit] + " 张");
  }
  return parts.join("，");
}

module.exports = {
  HCP_VALUES,
  BALANCED_SHAPES,
  evaluate_hand,
  describe_lengths,
};
