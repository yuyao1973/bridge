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

/** Cap Pass deals (below opening strength and no weak two) below 10%. */
const OPENING_PASS_MAX_RATE = 0.09;
const OPENING_PASS_RATE_DENOM = 100;
const OPENING_PASS_RATE_NUM = 9;
const OPENING_DEAL_SEARCH_ATTEMPTS = 50;

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

function oneNtSecondaryMajorOpeningBid(lengths) {
  if (lengths.S < 5 && lengths.H < 5) {
    return null;
  }
  const suit = lengths.S >= lengths.H ? "S" : "H";
  return "1" + suitSymbol(suit);
}

function hasSingletonOrVoid(lengths) {
  return Math.min(lengths.S, lengths.H, lengths.D, lengths.C) <= 1;
}

function chooseElevenHcpLongSuitWithShortage(lengths) {
  if (!hasSingletonOrVoid(lengths)) {
    return null;
  }
  const longSuits = ["S", "H", "D", "C"].filter(function (suit) {
    return lengths[suit] >= 6;
  });
  if (!longSuits.length) {
    return null;
  }
  return longSuits.slice().sort(function (a, b) {
    if (lengths[b] !== lengths[a]) {
      return lengths[b] - lengths[a];
    }
    const rank = { S: 3, H: 2, D: 1, C: 0 };
    return rank[b] - rank[a];
  })[0];
}

function chooseElevenHcpTwoSuiter(lengths) {
  const fivePlus = ["S", "H", "D", "C"].filter(function (suit) {
    return lengths[suit] >= 5;
  });
  if (fivePlus.length < 2) {
    return null;
  }

  const suitRank = { S: 4, H: 3, D: 2, C: 1 };
  const majors = fivePlus.filter(function (suit) {
    return suit === "S" || suit === "H";
  });
  const minors = fivePlus.filter(function (suit) {
    return suit === "D" || suit === "C";
  });

  if (majors.length && minors.length) {
    const maxMinorLen = Math.max.apply(
      null,
      minors.map(function (suit) {
        return lengths[suit];
      }),
    );
    const shortMajors = majors.filter(function (suit) {
      return lengths[suit] < maxMinorLen;
    });
    if (shortMajors.length) {
      return shortMajors.slice().sort(function (a, b) {
        if (lengths[a] !== lengths[b]) {
          return lengths[a] - lengths[b];
        }
        return suitRank[b] - suitRank[a];
      })[0];
    }
  }

  return fivePlus.slice().sort(function (a, b) {
    if (lengths[b] !== lengths[a]) {
      return lengths[b] - lengths[a];
    }
    return suitRank[b] - suitRank[a];
  })[0];
}

function elevenHcpSecondaryOpeningBid(lengths, primarySuit) {
  if (primarySuit !== "S" && primarySuit !== "H") {
    return null;
  }
  const fivePlus = ["S", "H", "D", "C"].filter(function (suit) {
    return lengths[suit] >= 5;
  });
  if (fivePlus.length < 2) {
    return null;
  }
  const minors = fivePlus.filter(function (suit) {
    return suit === "D" || suit === "C";
  });
  if (!minors.length) {
    return null;
  }
  const longerMinor = minors.slice().sort(function (a, b) {
    if (lengths[b] !== lengths[a]) {
      return lengths[b] - lengths[a];
    }
    const rank = { D: 1, C: 0 };
    return rank[b] - rank[a];
  })[0];
  if (lengths[primarySuit] < lengths[longerMinor]) {
    return "1" + suitSymbol(longerMinor);
  }
  return null;
}

function chooseElevenHcpOpening(lengths) {
  const twoSuiter = chooseElevenHcpTwoSuiter(lengths);
  if (twoSuiter) {
    return twoSuiter;
  }
  return chooseElevenHcpLongSuitWithShortage(lengths);
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
    const secondary = oneNtSecondaryMajorOpeningBid(lengths);
    if (secondary) {
      return {
        bid: "1NT",
        explanation:
          hcp +
          " HCP 均型，优先开叫 1NT；持有 5 张高花时，开叫 " +
          secondary +
          " 为次优。牌型：" +
          lengthText +
          "。",
        rule_name: settings.one_nt_min + "-" + settings.one_nt_max + " 均型 1NT",
      };
    }
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
  if (hcp === 11) {
    const lightSuit = chooseElevenHcpOpening(lengths);
    if (lightSuit) {
      const secondary = elevenHcpSecondaryOpeningBid(lengths, lightSuit);
      if (secondary) {
        return {
          bid: "1" + suitSymbol(lightSuit),
          explanation:
            hcp +
            " HCP，双套轻开叫优先开较短高花 1" +
            suitSymbol(lightSuit) +
            "；开叫较长低花 " +
            secondary +
            " 为次优。牌型：" +
            lengthText +
            "。",
          rule_name: "11 点轻开叫",
        };
      }
      return {
        bid: "1" + suitSymbol(lightSuit),
        explanation: hcp + " HCP，轻开叫 " + SUIT_NAMES[lightSuit] + "。牌型：" + lengthText + "。",
        rule_name: "11 点轻开叫",
      };
    }
  }
  if (settings.weak_two_enabled) {
    if (hcp >= 6 && hcp <= 10) {
      const candidates = ["S", "H", "D"].filter(function (suit) {
        return lengths[suit] >= 6;
      });
      if (candidates.length) {
        const honors = evaluation.top_honors_by_suit || {};
        const suit = candidates.slice().sort(function (a, b) {
          const ha = honors[a] || 0;
          const hb = honors[b] || 0;
          if (hb !== ha) {
            return hb - ha;
          }
          if (lengths[b] !== lengths[a]) {
            return lengths[b] - lengths[a];
          }
          const rank = { S: 2, H: 1, D: 0 };
          return rank[b] - rank[a];
        })[0];
        const sixCardSuits = ["S", "H", "D", "C"].filter(function (s) {
          return lengths[s] === 6;
        });
        if (sixCardSuits.length >= 2) {
          return {
            bid: "2" + suitSymbol(suit),
            explanation:
              hcp +
              " HCP，6-6 双套，按套质量开叫二阶 " +
              SUIT_NAMES[suit] +
              "。牌型：" +
              lengthText +
              "。",
            rule_name: "6-6 双套弱二",
          };
        }
        return {
          bid: "2" + suitSymbol(suit),
          explanation: "弱二开叫。牌型：" + lengthText + "。",
          rule_name: "弱二开叫",
        };
      }
    }
  }
  return {
    bid: "Pass",
    explanation: hcp + " HCP，建议 Pass。牌型：" + lengthText + "。",
    rule_name: "不叫",
  };
}

function buildOpeningQuestion(seed, settings) {
  const hands = deal(seed);
  const hand = hands.S;
  const evaluation = evaluate_hand(hand);
  const vulnerability = chooseVulnerability(seed);
  const recommendation = recommendOpening(evaluation, settings);
  const acceptable = [recommendation.bid];
  if (recommendation.rule_name === "11 点轻开叫") {
    const bid = recommendation.bid;
    let primary = null;
    if (bid === "1♠") primary = "S";
    else if (bid === "1♥") primary = "H";
    else if (bid === "1♦") primary = "D";
    else if (bid === "1♣") primary = "C";
    if (primary) {
      const secondary = elevenHcpSecondaryOpeningBid(evaluation.lengths, primary);
      if (secondary && acceptable.indexOf(secondary) < 0) {
        acceptable.push(secondary);
      }
    }
  }
  if (recommendation.bid === "1NT" && /均型 1NT$/.test(recommendation.rule_name)) {
    const secondary = oneNtSecondaryMajorOpeningBid(evaluation.lengths);
    if (secondary && acceptable.indexOf(secondary) < 0) {
      acceptable.push(secondary);
    }
  }
  return {
    hand: hand,
    evaluation: evaluation,
    recommendation: recommendation,
    vulnerability: vulnerability,
    choices: OPENING_BIDS,
    legal_choices: OPENING_BIDS,
    acceptable_bids: acceptable,
    mode: "开叫训练",
    position: "南",
    auction: "第一家开叫",
    opener_bid: null,
    response_bid: null,
    opener_rebid_bid: null,
  };
}

function generateOpeningLite(seed, settingsPayload) {
  const settings = Object.assign({}, defaultSettings(), settingsPayload || {});
  const baseSeed = seed == null ? Date.now() : Number(seed);
  const preferPass = (Math.abs(Math.floor(baseSeed)) % OPENING_PASS_RATE_DENOM) < OPENING_PASS_RATE_NUM;

  let fallback = null;
  if (preferPass) {
    for (let offset = 0; offset < OPENING_DEAL_SEARCH_ATTEMPTS; offset += 1) {
      const question = buildOpeningQuestion(baseSeed + offset, settings);
      if (fallback === null) {
        fallback = question;
      }
      if (question.recommendation.bid === "Pass") {
        return question;
      }
    }
    return fallback;
  }

  for (let offset = 0; offset < OPENING_DEAL_SEARCH_ATTEMPTS; offset += 1) {
    const question = buildOpeningQuestion(baseSeed + offset, settings);
    if (fallback === null) {
      fallback = question;
    }
    if (question.recommendation.bid !== "Pass") {
      return question;
    }
  }
  return fallback;
}

module.exports = {
  OPENING_BIDS,
  OPENING_PASS_MAX_RATE,
  OPENING_DEAL_SEARCH_ATTEMPTS,
  generateOpeningLite,
  recommendOpening,
};
