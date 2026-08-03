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
  "3NT",
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

function hasSuitStopper(evaluation, suit) {
  return evaluation.lengths[suit] >= 2 && ((evaluation.top_honors_by_suit || {})[suit] || 0) >= 1;
}

function isSemiBalancedShape(lengths) {
  const key = Object.keys(lengths)
    .map(function (suit) {
      return lengths[suit];
    })
    .sort(function (a, b) {
      return b - a;
    })
    .join("-");
  return key === "5-4-2-2" || key === "6-3-2-2";
}

function qualifiesForNtOpeningShape(evaluation) {
  if (evaluation.balanced) {
    return true;
  }
  const lengths = evaluation.lengths;
  if (lengths.S >= 6 || lengths.H >= 6) {
    return false;
  }
  if (!isSemiBalancedShape(lengths)) {
    return false;
  }
  return ["S", "H", "D", "C"].every(function (suit) {
    return hasSuitStopper(evaluation, suit);
  });
}

function nsIsVulnerable(vulnerability) {
  return vulnerability === "南北有局" || vulnerability === "双方有局";
}

function preemptOverbidAllowance(vulnerability) {
  return nsIsVulnerable(vulnerability) ? 2 : 3;
}

function preemptMinTopHonors(vulnerability) {
  return nsIsVulnerable(vulnerability) ? 2 : 1;
}

function maxPreemptLevelForSuit(length, vulnerability, suit) {
  if (length < 6) {
    return null;
  }
  const level = length - 1 + preemptOverbidAllowance(vulnerability) - 6;
  if (level < 2) {
    return null;
  }
  if (suit === "S" || suit === "H") {
    return Math.min(level, 4);
  }
  return Math.min(level, 5);
}

function choosePreemptOpening(lengths, hcp, vulnerability, topHonorsBySuit) {
  if (!(hcp >= 5 && hcp <= 10)) {
    return null;
  }
  const honors = topHonorsBySuit || {};
  const minHonors = preemptMinTopHonors(vulnerability);
  const candidates = [];
  for (let i = 0; i < 4; i += 1) {
    const suit = ["S", "H", "D", "C"][i];
    const length = lengths[suit];
    if (length < 7 || (honors[suit] || 0) < minHonors) {
      continue;
    }
    const level = maxPreemptLevelForSuit(length, vulnerability, suit);
    if (level === null || level < 3) {
      continue;
    }
    candidates.push({ suit: suit, level: level });
  }
  if (!candidates.length) {
    return null;
  }
  candidates.sort(function (a, b) {
    if (lengths[b.suit] !== lengths[a.suit]) {
      return lengths[b.suit] - lengths[a.suit];
    }
    const rank = { S: 3, H: 2, D: 1, C: 0 };
    if (rank[b.suit] !== rank[a.suit]) {
      return rank[b.suit] - rank[a.suit];
    }
    return b.level - a.level;
  });
  return String(candidates[0].level) + suitSymbol(candidates[0].suit);
}

const OPENING_RULE_PRINCIPLES = {
  "强 2♣": "开叫训练原则第1条：22+ HCP（或达到设置的强 2♣ 下限）开叫 2♣。",
  "20-21 均型 2NT":
    "开叫训练原则第2条：20-21 HCP 且均型或准均型门门有止（可能有5张高花/6张低花套）开叫 2NT。",
  "均型 1NT":
    "开叫训练原则第3条：15-17 HCP（可设置）且均型或准均型门门有止（可能有5张高花/6张低花套）开叫 1NT；如有5张高花，开叫一阶高花为次优。",
  "五张高花开叫": "开叫训练原则第4条：12+ HCP 且有5张以上高花，开叫较长高花；5-5 高花优先 1♠。",
  "低花开叫": "开叫训练原则第5条：12+ HCP 无5张高花，按较长低花开叫；3-3 低花开 1♣，4-4 低花开 1♦。",
  "11 点轻开叫":
    "开叫训练原则第6/7条：11 HCP 时，6+ 长套且有单缺开该长套；或 5-5 以上双套（等长开较高花色；高花短于低花时优先较短高花，较长低花为次优）。",
  "拼搏式 3NT":
    "开叫训练原则第8条：7张以上坚固低花（含 AKQ），边张无 A/K/Q，且未达一阶开叫点力时开拼搏式 3NT（优先于同档阻击）。",
  "阻击开叫":
    "开叫训练原则第9条：5-10 HCP 且7张以上长套，按套长作 3/4/5 阶阻击；无局至少1张顶张大牌，有局至少2张；并遵循有局宕二、无局宕三。",
  "弱二开叫":
    "开叫训练原则第10条：6-10 HCP 且6张以上套，二阶弱二开 2♦/2♥/2♠（不使用弱 2♣）；无局至少1张顶张大牌，有局至少2张；并遵循有局宕二、无局宕三。",
  "6-6 双套弱二":
    "开叫训练原则第11条：6-10 HCP 且6-6双套，在满足顶张质量的可开弱二花色中开质量最好的套。",
  "不叫": "开叫训练原则第12条：不满足以上开叫条件时 Pass。",
};

function lookupOpeningPrinciple(ruleName) {
  if (!ruleName) {
    return null;
  }
  if (OPENING_RULE_PRINCIPLES[ruleName]) {
    return OPENING_RULE_PRINCIPLES[ruleName];
  }
  const keys = Object.keys(OPENING_RULE_PRINCIPLES);
  for (let i = 0; i < keys.length; i += 1) {
    const key = keys[i];
    if (ruleName.length >= key.length && ruleName.slice(-key.length) === key) {
      return OPENING_RULE_PRINCIPLES[key];
    }
  }
  return null;
}

function withOpeningPrinciple(explanation, ruleName) {
  const principle = lookupOpeningPrinciple(ruleName);
  if (!principle) {
    return explanation;
  }
  return explanation + "\n\n依据原则：" + principle;
}

function recommendOpening(evaluation, settings, vulnerability) {
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const lengthText = describe_lengths(evaluation);

  function finish(rec) {
    rec.explanation = withOpeningPrinciple(rec.explanation, rec.rule_name);
    return rec;
  }

  if (hcp >= settings.strong_two_club_min) {
    return finish({
      bid: "2♣",
      explanation:
        "你有 " +
        hcp +
        " HCP，达到强开叫门槛（当前设置下限 " +
        settings.strong_two_club_min +
        " HCP），应开叫 2♣。牌型：" +
        lengthText +
        "。",
      rule_name: "强 2♣",
    });
  }
  if (qualifiesForNtOpeningShape(evaluation) && hcp >= 20 && hcp <= 21) {
    const shapeText = evaluation.balanced ? "均型" : "准均型且门门有止";
    return finish({
      bid: "2NT",
      explanation:
        "你有 " + hcp + " HCP，且为" + shapeText + "，符合 20-21 无将开叫，应开叫 2NT。牌型：" + lengthText + "。",
      rule_name: "20-21 均型 2NT",
    });
  }
  if (qualifiesForNtOpeningShape(evaluation) && hcp >= settings.one_nt_min && hcp <= settings.one_nt_max) {
    const shapeText = evaluation.balanced ? "均型" : "准均型且门门有止";
    const ruleName = settings.one_nt_min + "-" + settings.one_nt_max + " 均型 1NT";
    const secondary = oneNtSecondaryMajorOpeningBid(lengths);
    if (secondary) {
      return finish({
        bid: "1NT",
        explanation:
          "你有 " +
          hcp +
          " HCP，且为" +
          shapeText +
          "，优先开叫 1NT；因另有 5 张高花，开叫 " +
          secondary +
          " 为可接受次优。牌型：" +
          lengthText +
          "。",
        rule_name: ruleName,
      });
    }
    return finish({
      bid: "1NT",
      explanation:
        "你有 " +
        hcp +
        " HCP，且为" +
        shapeText +
        "，符合当前 " +
        settings.one_nt_min +
        "-" +
        settings.one_nt_max +
        " 无将开叫，应开叫 1NT。牌型：" +
        lengthText +
        "。",
      rule_name: ruleName,
    });
  }
  if (hcp >= settings.opening_min_hcp && (lengths.S >= 5 || lengths.H >= 5)) {
    const suit = lengths.S >= lengths.H ? "S" : "H";
    const fiveFiveNote =
      lengths.S >= 5 && lengths.H >= 5
        ? "两高花均为 5 张时优先开 1♠。"
        : "选择较长高花 " + SUIT_NAMES[suit] + "。";
    return finish({
      bid: "1" + suitSymbol(suit),
      explanation:
        "你有 " +
        hcp +
        " HCP（≥" +
        settings.opening_min_hcp +
        "），持有 5 张以上高花，应优先开叫高花。" +
        fiveFiveNote +
        "牌型：" +
        lengthText +
        "。",
      rule_name: "五张高花开叫",
    });
  }
  if (hcp >= settings.opening_min_hcp) {
    let suit = "D";
    let minorNote = "";
    if (lengths.D > lengths.C) {
      suit = "D";
      minorNote = "方块更长（♦" + lengths.D + "/♣" + lengths.C + "），应开 1♦。";
    } else if (lengths.C > lengths.D) {
      suit = "C";
      minorNote = "梅花更长（♣" + lengths.C + "/♦" + lengths.D + "），应开 1♣。";
    } else if (lengths.C === 3 && lengths.D === 3) {
      suit = "C";
      minorNote = "低花 3-3 等长，应开 1♣。";
    } else {
      suit = "D";
      minorNote = "低花 " + lengths.D + "-" + lengths.C + " 等长（含 4-4），应开 1♦。";
    }
    return finish({
      bid: "1" + suitSymbol(suit),
      explanation:
        "你有 " +
        hcp +
        " HCP（≥" +
        settings.opening_min_hcp +
        "），没有 5 张高花，应按较长低花开叫。" +
        minorNote +
        "牌型：" +
        lengthText +
        "。",
      rule_name: "低花开叫",
    });
  }
  if (hcp === 11) {
    const lightSuit = chooseElevenHcpOpening(lengths);
    if (lightSuit) {
      const secondary = elevenHcpSecondaryOpeningBid(lengths, lightSuit);
      if (secondary) {
        return finish({
          bid: "1" + suitSymbol(lightSuit),
          explanation:
            "你有 " +
            hcp +
            " HCP，属 5-5 以上双套轻开叫：优先开较短高花 1" +
            suitSymbol(lightSuit) +
            "；开叫较长低花 " +
            secondary +
            " 为可接受次优。牌型：" +
            lengthText +
            "。",
          rule_name: "11 点轻开叫",
        });
      }
      return finish({
        bid: "1" + suitSymbol(lightSuit),
        explanation:
          "你有 " +
          hcp +
          " HCP，符合轻开叫（6+ 长套且有单缺，或 5-5 以上双套），应开叫 1" +
          suitSymbol(lightSuit) +
          "。牌型：" +
          lengthText +
          "。",
        rule_name: "11 点轻开叫",
      });
    }
  }

  if (hcp < settings.opening_min_hcp) {
    const honors = evaluation.top_honors_by_suit || {};
    const gamblingCandidates = [];
    ["C", "D"].forEach(function (suit) {
      if (lengths[suit] < 7 || (honors[suit] || 0) < 3) {
        return;
      }
      let outsideTop = 0;
      ["S", "H", "D", "C"].forEach(function (other) {
        if (other !== suit) {
          outsideTop += honors[other] || 0;
        }
      });
      if (outsideTop === 0) {
        gamblingCandidates.push(suit);
      }
    });
    if (gamblingCandidates.length) {
      const gamblingSuit = gamblingCandidates.slice().sort(function (a, b) {
        if (lengths[b] !== lengths[a]) {
          return lengths[b] - lengths[a];
        }
        return (b === "D" ? 1 : 0) - (a === "D" ? 1 : 0);
      })[0];
      return finish({
        bid: "3NT",
        explanation:
          "你有 " +
          hcp +
          " HCP（未达一阶开叫点力），持有 " +
          lengths[gamblingSuit] +
          " 张坚固 " +
          SUIT_NAMES[gamblingSuit] +
          "（含 AKQ），边张无 A/K/Q，应开叫拼搏式 3NT（优先于同档阻击）。牌型：" +
          lengthText +
          "。",
        rule_name: "拼搏式 3NT",
      });
    }
  }

  if (settings.weak_two_enabled) {
    const preempt = choosePreemptOpening(lengths, hcp, vulnerability, evaluation.top_honors_by_suit);
    if (preempt) {
      const overbid = preemptOverbidAllowance(vulnerability);
      const minHonors = preemptMinTopHonors(vulnerability);
      return finish({
        bid: preempt,
        explanation:
          "你有 " +
          hcp +
          " HCP，持有 7 张以上长套，应按套长作 3/4/5 阶阻击；当前局况要求长套至少 " +
          minHonors +
          " 张顶张大牌，并遵循有局宕二无局宕三（本次可宕 " +
          overbid +
          "），因此开叫 " +
          preempt +
          "。牌型：" +
          lengthText +
          "。",
        rule_name: "阻击开叫",
      });
    }
    if (hcp >= 6 && hcp <= 10) {
      const honors = evaluation.top_honors_by_suit || {};
      const minHonors = preemptMinTopHonors(vulnerability);
      const candidates = ["S", "H", "D"].filter(function (suit) {
        return (
          lengths[suit] >= 6 &&
          (honors[suit] || 0) >= minHonors &&
          maxPreemptLevelForSuit(lengths[suit], vulnerability, suit) !== null
        );
      });
      if (candidates.length) {
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
        const overbid = preemptOverbidAllowance(vulnerability);
        if (sixCardSuits.length >= 2) {
          return finish({
            bid: "2" + suitSymbol(suit),
            explanation:
              "你有 " +
              hcp +
              " HCP，6-6 双套，应按套质量选择二阶弱二；当前局况要求长套至少 " +
              minHonors +
              " 张顶张大牌，并遵循有局宕二无局宕三（本次可宕 " +
              overbid +
              "），因此开叫 2" +
              suitSymbol(suit) +
              "。当前训练不使用弱 2♣。牌型：" +
              lengthText +
              "。",
            rule_name: "6-6 双套弱二",
          });
        }
        return finish({
          bid: "2" + suitSymbol(suit),
          explanation:
            "你有 " +
            hcp +
            " HCP，持有 " +
            lengths[suit] +
            " 张 " +
            SUIT_NAMES[suit] +
            "，可作二阶弱二；当前局况要求长套至少 " +
            minHonors +
            " 张顶张大牌，并遵循有局宕二无局宕三（本次可宕 " +
            overbid +
            "），因此开叫 2" +
            suitSymbol(suit) +
            "。当前训练不使用弱 2♣。牌型：" +
            lengthText +
            "。",
          rule_name: "弱二开叫",
        });
      }
    }
  }
  return finish({
    bid: "Pass",
    explanation:
      "你有 " +
      hcp +
      " HCP，未达到正常开叫、轻开叫、拼搏式 3NT 或弱二/阻击条件，应 Pass。牌型：" +
      lengthText +
      "。",
    rule_name: "不叫",
  });
}

function buildOpeningQuestion(seed, settings) {
  const hands = deal(seed);
  const hand = hands.S;
  const evaluation = evaluate_hand(hand);
  const vulnerability = chooseVulnerability(seed);
  const recommendation = recommendOpening(evaluation, settings, vulnerability);
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
