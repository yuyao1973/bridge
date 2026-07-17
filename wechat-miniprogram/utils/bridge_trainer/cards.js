"use strict";

const { PythonRandom } = require("./random");

const SUITS = ["S", "H", "D", "C"];
const SUIT_SYMBOLS = { S: "♠", H: "♥", D: "♦", C: "♣" };
const RANKS = ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"];
const RANK_ORDER = {};
RANKS.forEach((rank, index) => {
  RANK_ORDER[rank] = index;
});
const SUIT_NAMES = { S: "黑桃", H: "红心", D: "方块", C: "梅花" };

function createCard(suit, rank) {
  return {
    suit,
    rank,
    label() {
      return `${SUIT_SYMBOLS[this.suit]}${this.rank}`;
    },
  };
}

function new_deck() {
  const deck = [];
  for (const suit of SUITS) {
    for (const rank of RANKS) {
      deck.push(createCard(suit, rank));
    }
  }
  return deck;
}

function sort_hand(hand) {
  return hand.slice().sort(function (a, b) {
    const suitDiff = SUITS.indexOf(a.suit) - SUITS.indexOf(b.suit);
    if (suitDiff !== 0) {
      return suitDiff;
    }
    return RANK_ORDER[a.rank] - RANK_ORDER[b.rank];
  });
}

function deal(seed) {
  const deck = new_deck();
  const rng = new PythonRandom(seed === undefined || seed === null ? Date.now() : seed);
  rng.shuffle(deck);
  const players = ["N", "E", "S", "W"];
  const hands = {};
  for (let i = 0; i < players.length; i += 1) {
    hands[players[i]] = sort_hand(deck.slice(i * 13, (i + 1) * 13));
  }
  return hands;
}

function cards_by_suit(hand) {
  const grouped = { S: [], H: [], D: [], C: [] };
  for (const card of sort_hand(hand)) {
    grouped[card.suit].push(card);
  }
  return grouped;
}

function format_hand_lines(hand) {
  const grouped = cards_by_suit(hand);
  const lines = [];
  for (const suit of SUITS) {
    const ranks = grouped[suit].map((card) => card.rank).join(" ") || "—";
    lines.push(`${SUIT_SYMBOLS[suit]} ${ranks}`);
  }
  return lines;
}

module.exports = {
  SUITS,
  SUIT_SYMBOLS,
  RANKS,
  RANK_ORDER,
  SUIT_NAMES,
  createCard,
  new_deck,
  deal,
  sort_hand,
  cards_by_suit,
  format_hand_lines,
};
