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
  const isPrimary = selectedBid === recommendedBid;
  const isAcceptable = acceptableBids.indexOf(selectedBid) >= 0;
  const grade = isPrimary ? "primary" : isAcceptable ? "acceptable" : "incorrect";
  return {
    correct: isAcceptable,
    grade: grade,
    recommended_bid: recommendedBid,
    acceptable_bids: acceptableBids,
    explanation: (payload && payload.explanation) || "",
    rule_name: (payload && payload.rule_name) || "",
  };
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
