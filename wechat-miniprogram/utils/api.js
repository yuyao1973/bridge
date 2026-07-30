"use strict";

const { format_hand_lines } = require("./bridge_trainer/cards");
const { generateOpeningLite } = require("./bridge_trainer/opening_lite");
const { APP_VERSION, getBuildTime } = require("./version");

const DEFAULT_SETTINGS = {
  opening_min_hcp: 12,
  one_nt_min: 15,
  one_nt_max: 17,
  strong_two_club_min: 22,
  weak_two_enabled: true,
  stayman_enabled: true,
  transfers_enabled: true,
  jacoby_2nt_enabled: true,
  bergen_raises_enabled: true,
  two_over_one_min_hcp: 12,
  forcing_nt_min_hcp: 6,
  forcing_nt_max_hcp: 11,
  responder_simple_raise_max: 9,
  responder_limit_raise_min: 10,
  responder_limit_raise_max: 12,
  responder_bergen_weak_max: 9,
  splinter_enabled: true,
  responder_splinter_min_hcp: 11,
  responder_splinter_max_hcp: 15,
  negative_double_enabled: true,
  negative_double_min_hcp: 6,
  inverted_minors_enabled: false,
  forcing_nt_label: "半逼叫",
  scoring_mode: "IMP",
  respect_vulnerability: true,
  game_aggressiveness: 0,
  august_2nt_enabled: true,
};

function randomSeed() {
  return Math.floor(Math.random() * 1000000000) + 1;
}

function settingsFromPayload(payload) {
  const values = Object.assign({}, DEFAULT_SETTINGS, payload || {});
  values.game_aggressiveness = Math.max(-1, Math.min(1, Number(values.game_aggressiveness) || 0));
  values.opening_min_hcp = Number(values.opening_min_hcp);
  values.one_nt_min = Number(values.one_nt_min);
  values.one_nt_max = Number(values.one_nt_max);
  values.strong_two_club_min = Number(values.strong_two_club_min);
  values.two_over_one_min_hcp = Number(values.two_over_one_min_hcp);
  values.forcing_nt_min_hcp = Number(values.forcing_nt_min_hcp);
  values.forcing_nt_max_hcp = Number(values.forcing_nt_max_hcp);
  values.responder_simple_raise_max = Number(values.responder_simple_raise_max);
  values.responder_limit_raise_min = Number(values.responder_limit_raise_min);
  values.responder_limit_raise_max = Number(values.responder_limit_raise_max);
  values.responder_bergen_weak_max = Number(values.responder_bergen_weak_max);
  values.responder_splinter_min_hcp = Number(values.responder_splinter_min_hcp);
  values.responder_splinter_max_hcp = Number(values.responder_splinter_max_hcp);
  values.negative_double_min_hcp = Number(values.negative_double_min_hcp);
  return values;
}

function cardToPayload(card) {
  return {
    suit: card.suit,
    rank: card.rank,
    label: typeof card.label === "function" ? card.label() : card.suit + card.rank,
  };
}

function questionToPayload(question, seed) {
  const recommendation = question.recommendation;
  return {
    app_version: APP_VERSION,
    build_time: getBuildTime(),
    seed: seed,
    mode: question.mode,
    position: question.position,
    vulnerability: question.vulnerability,
    auction: question.auction,
    opener_bid: question.opener_bid,
    response_bid: question.response_bid,
    opener_rebid_bid: question.opener_rebid_bid,
    hand: question.hand.map(cardToPayload),
    hand_lines: format_hand_lines(question.hand),
    evaluation: {
      hcp: question.evaluation.hcp,
      shape: question.evaluation.shape,
      balanced: question.evaluation.balanced,
      lengths: question.evaluation.lengths,
    },
    choices: question.choices,
    legal_choices: question.legal_choices,
    acceptable_bids: question.acceptable_bids,
    recommendation: {
      bid: recommendation.bid,
      explanation: recommendation.explanation,
      rule_name: recommendation.rule_name,
    },
  };
}

function createOpeningQuestionLocal(payload) {
  const seed = (payload && payload.seed) || randomSeed();
  const settings = Object.assign({}, DEFAULT_SETTINGS, (payload && payload.settings) || {});
  const question = generateOpeningLite(seed, settings);
  return questionToPayload(question, seed);
}

function getTraining() {
  return require("./bridge_trainer/training");
}

function createHeavyQuestionLocal(payload) {
  const training = getTraining();
  const mode = (payload && payload.mode) || "opening";
  const openerBid = payload && payload.opener_bid;
  const responseBid = payload && payload.response_bid;
  const openerRebidBid = payload && payload.opener_rebid_bid;
  const openerCategory = payload && payload.opener_category;
  const seed = (payload && payload.seed) || randomSeed();
  const settings = settingsFromPayload(payload && payload.settings);

  let question;
  if (mode === "response") {
    question = training.generateResponseQuestion(seed, openerBid, settings, openerCategory);
  } else if (mode === "opener_rebid") {
    question = training.generateOpenerRebidQuestion(
      seed,
      settings,
      openerBid,
      openerCategory,
      responseBid,
    );
  } else if (mode === "responder_rebid") {
    question = training.generateResponderRebidQuestion(
      seed,
      settings,
      openerBid,
      openerCategory,
      responseBid,
      openerRebidBid,
    );
  } else {
    question = training.generateOpeningQuestion(seed, settings);
  }
  return questionToPayload(question, seed);
}

function createQuestionLocal(payload) {
  const mode = (payload && payload.mode) || "opening";
  if (mode === "opening") {
    return createOpeningQuestionLocal(payload);
  }
  return createHeavyQuestionLocal(payload);
}

function checkAnswerLocal(payload) {
  const selectedBid = payload && payload.selected_bid;
  const recommendedBid = payload && payload.recommended_bid;
  const acceptableBids = (payload && payload.acceptable_bids) || [recommendedBid];
  const ruleName = (payload && payload.rule_name) || "";
  const baseExplanation = (payload && payload.explanation) || "";
  const isPrimary = selectedBid === recommendedBid;
  const isAcceptable = acceptableBids.indexOf(selectedBid) >= 0;
  const grade = isPrimary ? "primary" : isAcceptable ? "acceptable" : "incorrect";
  return {
    correct: isAcceptable,
    grade: grade,
    recommended_bid: recommendedBid,
    acceptable_bids: acceptableBids,
    explanation: formatJudgmentExplanation({
      selectedBid: selectedBid,
      recommendedBid: recommendedBid,
      grade: grade,
      baseExplanation: baseExplanation,
      ruleName: ruleName,
      acceptableBids: acceptableBids,
    }),
    rule_name: ruleName,
  };
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
    "开叫训练原则第9条：5-10 HCP 且7张以上长套，按套长作 3/4/5 阶阻击，并遵循有局宕二、无局宕三。",
  "弱二开叫":
    "开叫训练原则第10条：6-10 HCP 且6张以上套，二阶弱二开 2♦/2♥/2♠（不使用弱 2♣），并遵循有局宕二、无局宕三。",
  "6-6 双套弱二": "开叫训练原则第11条：6-10 HCP 且6-6双套，开二阶质量最好的套。",
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

function formatJudgmentExplanation(opts) {
  const selected = (opts && opts.selectedBid) || "?";
  const recommended = (opts && opts.recommendedBid) || "?";
  const grade = (opts && opts.grade) || "incorrect";
  const baseExplanation = ((opts && opts.baseExplanation) || "").trim();
  const ruleName = (opts && opts.ruleName) || "";
  const acceptableBids = (opts && opts.acceptableBids) || [];
  let header;
  if (grade === "primary") {
    header = "判定：正确。你选择了 " + selected + "，与推荐叫品一致。";
  } else if (grade === "acceptable") {
    const alts = acceptableBids.filter(function (bid) {
      return bid !== recommended;
    });
    const altText = alts.length ? "；其他可接受：" + alts.join("、") : "";
    header = "判定：可接受次优。你选择了 " + selected + "，主推仍是 " + recommended + altText + "。";
  } else {
    header = "判定：不太合适。你选择了 " + selected + "，推荐叫品是 " + recommended + "。";
  }
  let text = header + "\n\n" + baseExplanation;
  const principle = lookupOpeningPrinciple(ruleName);
  if (principle && baseExplanation.indexOf("依据原则：") < 0) {
    text += "\n\n依据原则：" + principle;
  }
  return text.trim();
}

function createQuestion(payload) {
  const mode = (payload && payload.mode) || "opening";
  return new Promise(function (resolve, reject) {
    setTimeout(function () {
      try {
        if (mode === "opening") {
          resolve(createOpeningQuestionLocal(payload));
          return;
        }
        setTimeout(function () {
          try {
            resolve(createHeavyQuestionLocal(payload));
          } catch (error) {
            reject(error);
          }
        }, 0);
      } catch (error) {
        reject(error);
      }
    }, 0);
  });
}

function checkAnswer(payload) {
  return new Promise(function (resolve, reject) {
    setTimeout(function () {
      try {
        resolve(checkAnswerLocal(payload));
      } catch (error) {
        reject(error);
      }
    }, 0);
  });
}

module.exports = {
  createQuestion,
  checkAnswer,
  createQuestionLocal,
  checkAnswerLocal,
  APP_VERSION,
};
