"use strict";

/**
 * Minimal opening generator for WeChat.
 * Avoids loading the full bidding/training modules on first paint.
 */

const { deal } = require("./cards");
const { evaluate_hand, describe_lengths } = require("./evaluator");

const OPENING_BIDS = [
  "Pass",
  "1♣",
  "1♦",
  "1♥",
  "1♠",
  "1NT",
  "2♣",
  "2♦",
  "2♥",
  "2♠",
  "2NT",
  "3♣",
  "3♦",
  "3♥",
  "3♠",
  "4♣",
  "4♦",
  "4♥",
  "4♠",
  "5♣",
  "5♦",
];

const SUIT_NAMES = { S: "黑桃", H: "红心", D: "方块", C: "梅花" };
const SUIT_SYMBOL = { S: "♠", H: "♥", D: "♦", C: "♣" };

function defaultSettings() {
  return {
    opening_min_hcp: 12,
    one_nt_min: 15,
    one_nt_max: 17,
    strong_two_club_min: 22,
    weak_two_enabled: true,
  };
}

function chooseVulnerability(seed) {
  const options = ["双方无局", "南北有局", "东西有局", "双方有局"];
  const n = seed == null ? Date.now() : Number(seed);
  return options[Math.abs(Math.floor(n)) % options.length];
}

function suitSymbol(suit) {
  return SUIT_SYMBOL[suit];
}

function recommendOpening(evaluation, settings) {
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const lengthText = describe_lengths(evaluation);

  if (hcp >= settings.strong_two_club_min) {
    return {
      bid: "2♣",
      explanation: hcp + " HCP，强 2♣。牌型：" + lengthText + "。",
      rule_name: "强 2♣",
    };
  }
  if (evaluation.balanced && hcp >= 20 && hcp <= 21) {
    return {
      bid: "2NT",
      explanation: hcp + " HCP 均型 2NT。牌型：" + lengthText + "。",
      rule_name: "20-21 均型 2NT",
    };
  }
  if (evaluation.balanced && hcp >= settings.one_nt_min && hcp <= settings.one_nt_max) {
    return {
      bid: "1NT",
      explanation: hcp + " HCP 均型 1NT。牌型：" + lengthText + "。",
      rule_name: settings.one_nt_min + "-" + settings.one_nt_max + " 均型 1NT",
    };
  }
  if (hcp >= settings.opening_min_hcp && (lengths.S >= 5 || lengths.H >= 5)) {
    const suit = lengths.S >= lengths.H ? "S" : "H";
    return {
      bid: "1" + suitSymbol(suit),
      explanation: hcp + " HCP，开叫高花 " + SUIT_NAMES[suit] + "。牌型：" + lengthText + "。",
      rule_name: "五张高花开叫",
    };
  }
  if (hcp >= settings.opening_min_hcp) {
    const suit = lengths.C >= lengths.D ? "C" : "D";
    return {
      bid: "1" + suitSymbol(suit),
      explanation: hcp + " HCP，开叫低花 " + SUIT_NAMES[suit] + "。牌型：" + lengthText + "。",
      rule_name: "低花开叫",
    };
  }
  if (settings.weak_two_enabled) {
    if (hcp >= 5 && hcp <= 11) {
      if (lengths.S === 6) {
        return { bid: "2♠", explanation: "弱二开叫。牌型：" + lengthText + "。", rule_name: "弱二开叫" };
      }
      if (lengths.H === 6) {
        return { bid: "2♥", explanation: "弱二开叫。牌型：" + lengthText + "。", rule_name: "弱二开叫" };
      }
      if (lengths.D === 6) {
        return { bid: "2♦", explanation: "弱二开叫。牌型：" + lengthText + "。", rule_name: "弱二开叫" };
      }
    }
  }
  return {
    bid: "Pass",
    explanation: hcp + " HCP，建议 Pass。牌型：" + lengthText + "。",
    rule_name: "不叫",
  };
}

function generateOpeningLite(seed, settingsPayload) {
  const settings = Object.assign({}, defaultSettings(), settingsPayload || {});
  const hands = deal(seed);
  const hand = hands.S;
  const evaluation = evaluate_hand(hand);
  const vulnerability = chooseVulnerability(seed);
  const recommendation = recommendOpening(evaluation, settings);
  return {
    hand: hand,
    evaluation: evaluation,
    recommendation: recommendation,
    vulnerability: vulnerability,
    choices: OPENING_BIDS,
    legal_choices: OPENING_BIDS,
    acceptable_bids: [recommendation.bid],
    mode: "开叫训练",
    position: "南",
    auction: "第一家开叫",
    opener_bid: null,
    response_bid: null,
    opener_rebid_bid: null,
  };
}

module.exports = {
  OPENING_BIDS,
  generateOpeningLite,
  recommendOpening,
};
