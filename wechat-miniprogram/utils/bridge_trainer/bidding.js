"use strict";

const { describe_lengths } = require("./evaluator");

const SUIT_NAMES = { S: "黑桃", H: "红心", D: "方块", C: "梅花" };
const SUITS_ORDER = ["C", "D", "H", "S"];

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

const RESPONSE_BIDS = [
  "Pass",
  "X",
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
  "4NT",
  "5♣",
  "5♦",
  "5NT",
];

const REBID_BIDS = [
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
  "4NT",
  "5♣",
  "5♦",
  "5♥",
  "5♠",
  "5NT",
];

const RESPONDER_REBID_BIDS = [
  "Pass",
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
  "4NT",
  "5♣",
  "5♦",
  "5♥",
  "5♠",
  "5NT",
  "6♣",
  "6♦",
  "6♥",
  "6♠",
  "6NT",
  "7♣",
  "7♦",
  "7♥",
  "7♠",
  "7NT",
];

const STRAIN_ORDER = { "♣": 1, "♦": 2, "♥": 3, "♠": 4, NT: 5 };

function bidRecommendation(bid, explanation, rule_name) {
  return { bid, explanation, rule_name };
}

function defaultRuleSettings() {
  return {
    opening_min_hcp: 12,
    one_nt_min: 15,
    one_nt_max: 17,
    strong_two_club_min: 22,
    weak_two_enabled: true,
    stayman_enabled: true,
    transfers_enabled: true,
    jacoby_2nt_enabled: true,
    two_over_one_min_hcp: 12,
    forcing_nt_min_hcp: 6,
    forcing_nt_max_hcp: 11,
    forcing_nt_label: "半逼叫",
    scoring_mode: "IMP",
    respect_vulnerability: true,
    game_aggressiveness: 0,
    august_2nt_enabled: true,
    responder_simple_raise_max: 9,
    responder_limit_raise_min: 10,
    responder_limit_raise_max: 11,
    bergen_raises_enabled: true,
    responder_bergen_weak_max: 9,
    splinter_enabled: true,
    responder_splinter_min_hcp: 11,
    responder_splinter_max_hcp: 15,
    negative_double_enabled: true,
    negative_double_min_hcp: 6,
    inverted_minors_enabled: false,
  };
}

function ns_is_vulnerable(vulnerability) {
  return ["南北有局", "双方有局"].includes(vulnerability);
}

function game_threshold_adjustment(vulnerability, settings) {
  const mode = settings.scoring_mode.toUpperCase().trim();
  const aggressiveness = Math.max(-1, Math.min(1, parseInt(settings.game_aggressiveness, 10)));
  if (mode === "MP") {
    return 1 - aggressiveness;
  }
  if (settings.respect_vulnerability && ns_is_vulnerable(vulnerability)) {
    return -1 - aggressiveness;
  }
  return -aggressiveness;
}

function maxSuitByLength(candidates, lengths) {
  return candidates.reduce((best, suit) => {
    const score = [lengths[suit], SUITS_ORDER.indexOf(suit)];
    const bestScore = [lengths[best], SUITS_ORDER.indexOf(best)];
    for (let i = 0; i < 2; i++) {
      if (score[i] !== bestScore[i]) {
        return score[i] > bestScore[i] ? suit : best;
      }
    }
    return best;
  });
}

function maxWeakTwoCandidate(candidates, lengths, topHonorsBySuit) {
  const honors = topHonorsBySuit || {};
  return candidates.reduce((best, suit) => {
    const score = [
      honors[suit] || 0,
      lengths[suit],
      suit === "S" ? 1 : 0,
      suit === "H" ? 1 : 0,
    ];
    const bestScore = [
      honors[best] || 0,
      lengths[best],
      best === "S" ? 1 : 0,
      best === "H" ? 1 : 0,
    ];
    for (let i = 0; i < 4; i++) {
      if (score[i] !== bestScore[i]) {
        return score[i] > bestScore[i] ? suit : best;
      }
    }
    return best;
  });
}

function maxPreemptCandidate(lengths) {
  const candidates = ["S", "H", "D", "C"];
  return candidates.reduce((best, candidate) => {
    const score = [lengths[candidate], candidate === "S" ? 1 : 0, candidate === "H" ? 1 : 0];
    const bestScore = [lengths[best], best === "S" ? 1 : 0, best === "H" ? 1 : 0];
    for (let i = 0; i < 3; i++) {
      if (score[i] !== bestScore[i]) {
        return score[i] > bestScore[i] ? candidate : best;
      }
    }
    return best;
  });
}

function maxTwoOverOneCandidate(candidates, lengths) {
  return candidates.reduce((best, suit) => {
    const score = [lengths[suit], suit === "H" ? 1 : 0, suit === "D" ? 1 : 0];
    const bestScore = [lengths[best], best === "H" ? 1 : 0, best === "D" ? 1 : 0];
    for (let i = 0; i < 3; i++) {
      if (score[i] !== bestScore[i]) {
        return score[i] > bestScore[i] ? suit : best;
      }
    }
    return best;
  });
}

function recommend_opening(evaluation, settings, vulnerability) {
  settings = settings || defaultRuleSettings();
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const length_text = describe_lengths(evaluation);

  function finish(rec) {
    rec.explanation = with_opening_principle(rec.explanation, rec.rule_name);
    return rec;
  }

  if (hcp >= settings.strong_two_club_min) {
    return finish(bidRecommendation(
      "2♣",
      `${hcp} HCP，达到当前设置的强 2♣ 下限 ${settings.strong_two_club_min} HCP。牌型：${length_text}。`,
      "强 2♣",
    ));
  }

  if (qualifies_for_nt_opening_shape(evaluation) && hcp >= 20 && hcp <= 21) {
    const shapeText = evaluation.balanced ? "均型" : "准均型且门门有止";
    return finish(bidRecommendation(
      "2NT",
      `${hcp} HCP 且${shapeText}，符合 20-21 无将开叫。牌型：${length_text}。`,
      "20-21 均型 2NT",
    ));
  }

  if (
    qualifies_for_nt_opening_shape(evaluation) &&
    hcp >= settings.one_nt_min &&
    hcp <= settings.one_nt_max
  ) {
    const shapeText = evaluation.balanced ? "均型" : "准均型且门门有止";
    const secondary = one_nt_secondary_major_opening_bid(lengths);
    if (secondary !== null) {
      return finish(bidRecommendation(
        "1NT",
        `${hcp} HCP 且${shapeText}，优先开叫 1NT；持有 5 张高花时，开叫 ${secondary} 为次优。牌型：${length_text}。`,
        `${settings.one_nt_min}-${settings.one_nt_max} 均型 1NT`,
      ));
    }
    return finish(bidRecommendation(
      "1NT",
      `${hcp} HCP 且${shapeText}，符合当前设置的 ${settings.one_nt_min}-${settings.one_nt_max} 无将开叫。牌型：${length_text}。`,
      `${settings.one_nt_min}-${settings.one_nt_max} 均型 1NT`,
    ));
  }

  if (hcp >= settings.opening_min_hcp && (lengths.S >= 5 || lengths.H >= 5)) {
    const suit = choose_major_opening(lengths);
    return finish(bidRecommendation(
      `1${suit_symbol(suit)}`,
      `${hcp} HCP，达到当前一阶开叫下限 ${settings.opening_min_hcp} HCP，持有 5 张以上高花，应优先开叫高花。选择 ${SUIT_NAMES[suit]}，牌型：${length_text}。`,
      "五张高花开叫",
    ));
  }

  if (hcp >= settings.opening_min_hcp) {
    const suit = choose_minor_opening(lengths);
    return finish(bidRecommendation(
      `1${suit_symbol(suit)}`,
      `${hcp} HCP，达到当前一阶开叫下限 ${settings.opening_min_hcp} HCP，没有 5 张高花，按较长低花/Better Minor 原则开叫 ${SUIT_NAMES[suit]}。牌型：${length_text}。`,
      "低花开叫",
    ));
  }

  if (hcp === 11) {
    const lightSuit = choose_eleven_hcp_opening(lengths);
    if (lightSuit !== null) {
      const secondary = eleven_hcp_secondary_opening_bid(lengths, lightSuit);
      if (secondary !== null) {
        return finish(bidRecommendation(
          `1${suit_symbol(lightSuit)}`,
          `${hcp} HCP，双套轻开叫优先开较短高花 1${suit_symbol(lightSuit)}；开叫较长低花 ${secondary} 为次优。牌型：${length_text}。`,
          "11 点轻开叫",
        ));
      }
      return finish(bidRecommendation(
        `1${suit_symbol(lightSuit)}`,
        `${hcp} HCP，符合轻开叫条件，开叫 1${suit_symbol(lightSuit)}。牌型：${length_text}。`,
        "11 点轻开叫",
      ));
    }
  }

  // 拼搏式 3NT：7+ 坚固低花（含 AKQ），边张无 A/K/Q；优先于同档阻击叫。
  const gambling_minor = choose_gambling_3nt_minor(evaluation, settings.opening_min_hcp);
  if (gambling_minor !== null) {
    return finish(bidRecommendation(
      "3NT",
      `${hcp} HCP，持有 ${lengths[gambling_minor]} 张坚固 ${SUIT_NAMES[gambling_minor]}（含 AKQ），边张无大牌，开叫拼搏式 3NT。牌型：${length_text}。`,
      "拼搏式 3NT",
    ));
  }

  const preempt = settings.weak_two_enabled
    ? choose_preempt_opening(lengths, hcp, vulnerability, evaluation.top_honors_by_suit)
    : null;
  if (preempt !== null) {
    const overbid = preempt_overbid_allowance(vulnerability);
    const minHonors = preempt_min_top_honors(vulnerability);
    return finish(bidRecommendation(
      preempt,
      `${hcp} HCP，持有长套，按有局宕二无局宕三（本次可宕 ${overbid}）且长套至少 ${minHonors} 张顶张大牌开叫阻击 ${preempt}。牌型：${length_text}。`,
      "阻击开叫",
    ));
  }

  const weak_two = settings.weak_two_enabled
    ? choose_weak_two(lengths, hcp, evaluation.top_honors_by_suit, vulnerability)
    : null;
  if (weak_two !== null) {
    const sixCardSuits = ["S", "H", "D", "C"].filter((suit) => lengths[suit] === 6);
    const overbid = preempt_overbid_allowance(vulnerability);
    const minHonors = preempt_min_top_honors(vulnerability);
    if (sixCardSuits.length >= 2) {
      return finish(bidRecommendation(
        `2${suit_symbol(weak_two)}`,
        `${hcp} HCP，6-6 双套，按套质量并遵循有局宕二无局宕三（本次可宕 ${overbid}）、长套至少 ${minHonors} 张顶张开叫二阶 ${SUIT_NAMES[weak_two]}。当前训练不使用弱 2♣。牌型：${length_text}。`,
        "6-6 双套弱二",
      ));
    }
    return finish(bidRecommendation(
      `2${suit_symbol(weak_two)}`,
      `${hcp} HCP，持有 ${lengths[weak_two]} 张 ${SUIT_NAMES[weak_two]}，按有局宕二无局宕三（本次可宕 ${overbid}）且长套至少 ${minHonors} 张顶张作二阶弱二开叫。当前训练不使用弱 2♣。牌型：${length_text}。`,
      "弱二开叫",
    ));
  }

  return finish(bidRecommendation(
    "Pass",
    `${hcp} HCP，未达到正常开叫条件，也不符合当前弱二规则，建议 Pass。牌型：${length_text}。`,
    "不叫",
  ));
}

function recommend_response(opener_bid, evaluation, settings, vulnerability, overcall_bid) {
  settings = settings || defaultRuleSettings();
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const length_text = describe_lengths(evaluation);

  if (overcall_bid && should_make_negative_double(opener_bid, overcall_bid, evaluation, settings)) {
    const target_majors = negative_double_target_majors(opener_bid, overcall_bid);
    const majors_text = target_majors.length
      ? target_majors.map((suit) => suit_symbol(suit)).join(" 或 ")
      : "未叫高花";
    return bidRecommendation(
      "X",
      `同伴开 ${opener_bid}，右手竞叫 ${overcall_bid}。你有 ${hcp} HCP，并持有 4 张以上 ${majors_text}，按简化否定性加倍约定应叫 X。牌型：${length_text}。`,
      "否定性加倍",
    );
  }

  if (opener_bid === "1NT") {
    return recommend_response_to_1nt(evaluation, settings, vulnerability);
  }

  if (["1♥", "1♠"].includes(opener_bid)) {
    const major = opener_bid === "1♥" ? "H" : "S";
    return recommend_response_to_major(major, evaluation, settings, vulnerability);
  }

  if (["1♣", "1♦"].includes(opener_bid)) {
    const minor = opener_bid === "1♣" ? "C" : "D";
    return recommend_response_to_minor(minor, evaluation, settings, vulnerability);
  }

  if (opener_bid === "2♣") {
    return recommend_response_to_strong_two_club(evaluation);
  }

  if (opener_bid === "2NT") {
    return recommend_response_to_2nt(evaluation, settings, vulnerability);
  }

  if (opener_bid === "3NT") {
    return recommend_response_to_gambling_3nt(evaluation, settings);
  }

  if (
    [
      "2♦", "2♥", "2♠", "3♣", "3♦", "3♥", "3♠",
      "4♣", "4♦", "4♥", "4♠", "5♣", "5♦",
    ].includes(opener_bid)
  ) {
    return recommend_response_to_preempt(opener_bid, evaluation, settings);
  }

  return bidRecommendation(
    "Pass",
    `当前应叫训练只覆盖一阶定约、强开叫与简化阻击开叫。你有 ${hcp} HCP，牌型：${length_text}。`,
    "未覆盖的开叫",
  );
}

function legal_response_bids(opener_bid) {
  return legal_response_bids_with_interference(opener_bid, null);
}

function legal_response_bids_with_interference(opener_bid, overcall_bid) {
  const previous_bid = overcall_bid ? overcall_bid : opener_bid;
  const legal = legal_bids_after(previous_bid, RESPONSE_BIDS);
  if (overcall_bid && is_negative_double_available(opener_bid, overcall_bid)) {
    if (!legal.includes("X")) {
      legal.splice(legal.length && legal[0] === "Pass" ? 1 : 0, 0, "X");
    }
  }
  return legal;
}

function legal_rebid_bids(response_bid) {
  return legal_bids_after(response_bid, REBID_BIDS);
}

function legal_responder_rebid_bids(opener_rebid_bid) {
  return legal_bids_after(opener_rebid_bid, RESPONDER_REBID_BIDS);
}

function legal_bids_after(previous_bid, choices) {
  return choices.filter((bid) => is_legal_response_bid(previous_bid, bid));
}

function is_legal_response_bid(opener_bid, response_bid) {
  if (response_bid === "Pass") {
    return true;
  }

  const opener_contract = parse_contract_bid(opener_bid);
  const response_contract = parse_contract_bid(response_bid);
  if (opener_contract === null || response_contract === null) {
    return false;
  }

  const [opener_level, opener_strain] = opener_contract;
  const [response_level, response_strain] = response_contract;
  if (response_level > opener_level) {
    return true;
  }
  if (response_level === opener_level) {
    return STRAIN_ORDER[response_strain] > STRAIN_ORDER[opener_strain];
  }
  return false;
}

function parse_contract_bid(bid) {
  if (bid.length < 2 || !/^\d/.test(bid[0])) {
    return null;
  }
  const level = parseInt(bid[0], 10);
  const strain = bid.slice(1);
  if (!(strain in STRAIN_ORDER)) {
    return null;
  }
  return [level, strain];
}

function is_negative_double_available(opener_bid, overcall_bid) {
  const opener_contract = parse_contract_bid(opener_bid);
  const overcall_contract = parse_contract_bid(overcall_bid);
  if (opener_contract === null || overcall_contract === null) {
    return false;
  }

  const [opener_level, opener_strain] = opener_contract;
  const [overcall_level, overcall_strain] = overcall_contract;

  if (opener_level !== 1 || overcall_level !== 1) {
    return false;
  }
  if (!["♣", "♦", "♥"].includes(opener_strain)) {
    return false;
  }
  if (!["♦", "♥", "♠"].includes(overcall_strain)) {
    return false;
  }
  if (STRAIN_ORDER[overcall_strain] <= STRAIN_ORDER[opener_strain]) {
    return false;
  }
  return Boolean(negative_double_target_majors(opener_bid, overcall_bid).length);
}

function negative_double_target_majors(opener_bid, overcall_bid) {
  const opener_contract = parse_contract_bid(opener_bid);
  const overcall_contract = parse_contract_bid(overcall_bid);
  if (opener_contract === null || overcall_contract === null) {
    return [];
  }

  const [, opener_strain] = opener_contract;
  const [, overcall_strain] = overcall_contract;

  if (opener_strain === "♣") {
    if (overcall_strain === "♦") {
      return ["H", "S"];
    }
    if (overcall_strain === "♥") {
      return ["S"];
    }
    if (overcall_strain === "♠") {
      return ["H"];
    }
  }
  if (opener_strain === "♦") {
    if (overcall_strain === "♥") {
      return ["S"];
    }
    if (overcall_strain === "♠") {
      return ["H"];
    }
  }
  if (opener_strain === "♥" && overcall_strain === "♠") {
    return ["D"];
  }

  return [];
}

function should_make_negative_double(opener_bid, overcall_bid, evaluation, settings) {
  if (!settings.negative_double_enabled) {
    return false;
  }
  if (evaluation.hcp < settings.negative_double_min_hcp) {
    return false;
  }
  if (!is_negative_double_available(opener_bid, overcall_bid)) {
    return false;
  }

  const targets = negative_double_target_majors(opener_bid, overcall_bid);
  if (!targets.length) {
    return false;
  }

  const lengths = evaluation.lengths;
  for (const suit of targets) {
    if (lengths[suit] >= 4) {
      return true;
    }
  }
  return false;
}

function recommend_opener_rebid(opening_bid, response_bid, evaluation, settings, vulnerability) {
  settings = settings || defaultRuleSettings();
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const length_text = describe_lengths(evaluation);
  const opening_contract = parse_contract_bid(opening_bid);
  const response_contract = parse_contract_bid(response_bid);

  if (response_bid === "Pass" || response_contract === null || opening_contract === null) {
    return bidRecommendation(
      "Pass",
      `同伴未作有效应叫，当前再叫训练建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
      "再叫后不叫",
    );
  }

  const opener_suit = symbol_to_suit(opening_contract[1]);
  const response_suit = symbol_to_suit(response_contract[1]);
  const response_level = response_contract[0];
  const opening_level = opening_contract[0];
  const opening_strain = opening_contract[1];
  const is_weak_two_opening = opening_level === 2 && ["♦", "♥", "♠"].includes(opening_strain);
  const is_three_plus_preempt_opening =
    opening_level >= 3 && ["♣", "♦", "♥", "♠"].includes(opening_strain);
  const game_adjustment = game_threshold_adjustment(vulnerability, settings);
  const raise_hcp = hcp - game_adjustment;

  if (is_three_plus_preempt_opening) {
    return bidRecommendation(
      "Pass",
      `同伴已在阻击序列中推进到 ${response_bid}，开叫者在当前简化体系中以止叫为主，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
      "阻击后止叫",
    );
  }

  if (is_weak_two_opening && response_bid !== "2NT") {
    return bidRecommendation(
      "Pass",
      `弱二开叫后，除 Ogust 2NT 问叫外当前简化体系默认不开新一轮描述，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
      "弱二后止叫",
    );
  }

  if (response_bid === "3NT") {
    return bidRecommendation(
      "Pass",
      `同伴已直接叫到 3NT，开叫者通常不再进叫，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
      "3NT 后止叫",
    );
  }

  if (opening_bid === "1NT") {
    if (response_bid === "2♣" && settings.stayman_enabled) {
      if (lengths.H >= 4 && is_legal_response_bid(response_bid, "2♥")) {
        return bidRecommendation(
          "2♥",
          `1NT-2♣ 序列中，开叫者有 4 张红心，按 Stayman 规则应答 2♥。牌型：${length_text}。`,
          "Stayman 应答 2♥",
        );
      }
      if (lengths.S >= 4 && is_legal_response_bid(response_bid, "2♠")) {
        return bidRecommendation(
          "2♠",
          `1NT-2♣ 序列中，开叫者无 4 张红心但有 4 张黑桃，按 Stayman 规则应答 2♠。牌型：${length_text}。`,
          "Stayman 应答 2♠",
        );
      }
      if (is_legal_response_bid(response_bid, "2♦")) {
        return bidRecommendation(
          "2♦",
          `1NT-2♣ 序列中，开叫者无 4 张高花，按 Stayman 否定应答 2♦。牌型：${length_text}。`,
          "Stayman 否定应答 2♦",
        );
      }
    }

    if (response_bid === "2♦" && settings.transfers_enabled && is_legal_response_bid(response_bid, "2♥")) {
      return bidRecommendation(
        "2♥",
        `1NT-2♦ 序列中，2♦ 为红心转移，开叫者应接受转移叫 2♥。牌型：${length_text}。`,
        "接受红心转移",
      );
    }

    if (response_bid === "2♥" && settings.transfers_enabled && is_legal_response_bid(response_bid, "2♠")) {
      return bidRecommendation(
        "2♠",
        `1NT-2♥ 序列中，2♥ 为黑桃转移，开叫者应接受转移叫 2♠。牌型：${length_text}。`,
        "接受黑桃转移",
      );
    }

    // 低花转移：1NT-2♠ 要求同伴转叫 3♣（草花直接完成；方块后续再叫 3♦）。
    if (response_bid === "2♠" && settings.transfers_enabled && is_legal_response_bid(response_bid, "3♣")) {
      return bidRecommendation(
        "3♣",
        `1NT-2♠ 序列中，2♠ 为低花转移，开叫者应先转叫 3♣。牌型：${length_text}。`,
        "接受低花转移",
      );
    }

    // 德克萨斯转移：1NT-4♦/4♥，开叫者完成转移到 4♥/4♠。
    if (response_bid === "4♦" && settings.transfers_enabled && is_legal_response_bid(response_bid, "4♥")) {
      return bidRecommendation(
        "4♥",
        `1NT-4♦ 序列中，4♦ 为德克萨斯红心转移，开叫者应接受转移叫 4♥。牌型：${length_text}。`,
        "接受德克萨斯红心转移",
      );
    }
    if (response_bid === "4♥" && settings.transfers_enabled && is_legal_response_bid(response_bid, "4♠")) {
      return bidRecommendation(
        "4♠",
        `1NT-4♥ 序列中，4♥ 为德克萨斯黑桃转移，开叫者应接受转移叫 4♠。牌型：${length_text}。`,
        "接受德克萨斯黑桃转移",
      );
    }

    if (response_bid === "2NT") {
      const accept_invite_hcp = Math.max(16, 17 + game_adjustment);
      if (hcp >= accept_invite_hcp && is_legal_response_bid(response_bid, "3NT")) {
        return bidRecommendation(
          "3NT",
          `1NT-2NT 为邀局；你有 ${hcp} HCP，达到接受邀局门槛，叫 3NT。牌型：${length_text}。`,
          "接受 2NT 邀局",
        );
      }
      return bidRecommendation(
        "Pass",
        `1NT-2NT 为邀局；你有 ${hcp} HCP，未达到接受邀局门槛，建议 Pass。牌型：${length_text}。`,
        "拒绝 2NT 邀局",
      );
    }
  }

  if (
    opening_contract !== null &&
    opening_contract[0] === 2 &&
    ["♦", "♥", "♠"].includes(opening_contract[1]) &&
    response_bid === "2NT" &&
    settings.august_2nt_enabled
  ) {
    const opening_suit = opener_suit;
    if (opening_suit !== null) {
      const top_honors = evaluation.top_honors_by_suit[opening_suit] || 0;
      const is_max = hcp >= 8;
      if (is_max && top_honors >= 3 && is_legal_response_bid(response_bid, "3NT")) {
        return bidRecommendation(
          "3NT",
          `Ogust 2NT 问叫后，你有 ${hcp} HCP（高限）且开叫套具备 AKQ 三大顶张，按标准回答 3NT。牌型：${length_text}。`,
          "Ogust 回答：高限+AKQ",
        );
      }
      if (!is_max && top_honors <= 1 && is_legal_response_bid(response_bid, "3♣")) {
        return bidRecommendation(
          "3♣",
          `Ogust 2NT 问叫后，你有 ${hcp} HCP（低限）且开叫套顶张质量偏弱（顶三张中至多 1 张），按标准回答 3♣。牌型：${length_text}。`,
          "Ogust 回答：低限+差套",
        );
      }
      if (!is_max && top_honors >= 2 && is_legal_response_bid(response_bid, "3♦")) {
        return bidRecommendation(
          "3♦",
          `Ogust 2NT 问叫后，你有 ${hcp} HCP（低限）且开叫套顶张质量较好（顶三张中 2 张），按标准回答 3♦。牌型：${length_text}。`,
          "Ogust 回答：低限+好套",
        );
      }
      if (is_max && top_honors <= 1 && is_legal_response_bid(response_bid, "3♥")) {
        return bidRecommendation(
          "3♥",
          `Ogust 2NT 问叫后，你有 ${hcp} HCP（高限）且开叫套顶张质量偏弱（顶三张中至多 1 张），按标准回答 3♥。牌型：${length_text}。`,
          "Ogust 回答：高限+差套",
        );
      }
      if (is_max && top_honors >= 2 && is_legal_response_bid(response_bid, "3♠")) {
        return bidRecommendation(
          "3♠",
          `Ogust 2NT 问叫后，你有 ${hcp} HCP（高限）且开叫套顶张质量较好（顶三张中 2 张），按标准回答 3♠。牌型：${length_text}。`,
          "Ogust 回答：高限+好套",
        );
      }
    }
  }

  if (is_weak_two_opening && response_bid === "2NT") {
    return bidRecommendation(
      "Pass",
      `弱二开叫面对 2NT 问叫时，当前条件下未触发标准 Ogust 回答，简化体系建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
      "弱二后止叫",
    );
  }

  if (opening_bid === "2NT") {
    if (response_bid === "3♣" && settings.stayman_enabled) {
      if (lengths.H >= 4 && is_legal_response_bid(response_bid, "3♥")) {
        return bidRecommendation(
          "3♥",
          `2NT-3♣ 序列中，开叫者有 4 张红心，按 Stayman 应答 3♥。牌型：${length_text}。`,
          "2NT Stayman 应答 3♥",
        );
      }
      if (lengths.S >= 4 && is_legal_response_bid(response_bid, "3♠")) {
        return bidRecommendation(
          "3♠",
          `2NT-3♣ 序列中，开叫者无 4 张红心但有 4 张黑桃，按 Stayman 应答 3♠。牌型：${length_text}。`,
          "2NT Stayman 应答 3♠",
        );
      }
      if (is_legal_response_bid(response_bid, "3♦")) {
        return bidRecommendation(
          "3♦",
          `2NT-3♣ 序列中，开叫者无 4 张高花，按 Stayman 否定应答 3♦。牌型：${length_text}。`,
          "2NT Stayman 否定应答 3♦",
        );
      }
    }

    if (response_bid === "3♦" && settings.transfers_enabled && is_legal_response_bid(response_bid, "3♥")) {
      return bidRecommendation(
        "3♥",
        `2NT-3♦ 序列中，3♦ 为红心转移，开叫者应接受转移叫 3♥。牌型：${length_text}。`,
        "2NT 后接受红心转移",
      );
    }

    if (response_bid === "3♥" && settings.transfers_enabled && is_legal_response_bid(response_bid, "3♠")) {
      return bidRecommendation(
        "3♠",
        `2NT-3♥ 序列中，3♥ 为黑桃转移，开叫者应接受转移叫 3♠。牌型：${length_text}。`,
        "2NT 后接受黑桃转移",
      );
    }
  }

  // 拼搏式 3NT 后再叫：4♣=Pass or correct；4♦=问单缺；4M=止叫。
  if (opening_bid === "3NT") {
    let gambling_minor = choose_gambling_3nt_minor(evaluation, settings.opening_min_hcp);
    if (gambling_minor === null) {
      gambling_minor = lengths.C >= lengths.D ? "C" : "D";
    }
    const minor_symbol = suit_symbol(gambling_minor);
    if (response_bid === "4♣") {
      if (gambling_minor === "C") {
        return bidRecommendation(
          "Pass",
          `拼搏式 3NT 后同伴叫 4♣（Pass or correct），你的真实花色是梅花，接受并止叫 Pass。牌型：${length_text}。`,
          "拼搏式 3NT 后接受梅花",
        );
      }
      if (is_legal_response_bid(response_bid, "4♦")) {
        return bidRecommendation(
          "4♦",
          `拼搏式 3NT 后同伴叫 4♣（Pass or correct），你的真实花色是方块，改叫 4♦。牌型：${length_text}。`,
          "拼搏式 3NT 后改叫方块",
        );
      }
    }
    if (response_bid === "4♦") {
      const short_majors = ["H", "S"].filter((suit) => lengths[suit] <= 1);
      for (const suit of short_majors) {
        const shortage_bid = `4${suit_symbol(suit)}`;
        if (is_legal_response_bid(response_bid, shortage_bid)) {
          return bidRecommendation(
            shortage_bid,
            `拼搏式 3NT 后同伴以 4♦ 询问单缺，你在 ${SUIT_NAMES[suit]} 单缺，回答 ${shortage_bid}。牌型：${length_text}。`,
            "拼搏式 3NT 后报单缺",
          );
        }
      }
      const other_minor = gambling_minor === "C" ? "D" : "C";
      if (lengths[other_minor] <= 1) {
        const other_bid = `5${suit_symbol(other_minor)}`;
        if (is_legal_response_bid(response_bid, other_bid)) {
          return bidRecommendation(
            other_bid,
            `拼搏式 3NT 后同伴以 4♦ 询问单缺，你在 ${SUIT_NAMES[other_minor]} 单缺，回答 ${other_bid}。牌型：${length_text}。`,
            "拼搏式 3NT 后报单缺",
          );
        }
      }
      const own_five = `5${minor_symbol}`;
      if (is_legal_response_bid(response_bid, own_five)) {
        return bidRecommendation(
          own_five,
          `拼搏式 3NT 后同伴以 4♦ 询问单缺，你无高花单缺，重叫己方坚固低花 ${own_five}。牌型：${length_text}。`,
          "拼搏式 3NT 后无单缺重叫低花",
        );
      }
    }
    if (["4♥", "4♠"].includes(response_bid)) {
      return bidRecommendation(
        "Pass",
        `拼搏式 3NT 后同伴叫 ${response_bid} 表示自有高花成局，开叫者止叫 Pass。牌型：${length_text}。`,
        "拼搏式 3NT 后高花止叫",
      );
    }
    return bidRecommendation(
      "Pass",
      `拼搏式 3NT 后同伴叫 ${response_bid}，当前简化体系以止叫为主，建议 Pass。牌型：${length_text}。`,
      "拼搏式 3NT 后止叫",
    );
  }

  if (["1♥", "1♠"].includes(opening_bid) && response_bid === "2NT") {
    const game_bid = `4${opening_strain}`;
    if (is_legal_response_bid(response_bid, game_bid)) {
      return bidRecommendation(
        game_bid,
        `同伴以 Jacoby 2NT 显示对 ${opening_strain} 的 4+ 张支持与进局实力；你有 ${hcp} HCP，优先确立高花进局 ${game_bid}。牌型：${length_text}。`,
        "Jacoby 2NT 后高花进局",
      );
    }
  }

  if (["1♥", "1♠"].includes(opening_bid) && ["3♣", "3♦"].includes(response_bid) && ["H", "S"].includes(opener_suit)) {
    let target_level;
    if (response_bid === "3♣") {
      target_level = hcp >= 16 ? 4 : 3;
    } else {
      target_level = hcp >= 14 ? 4 : 3;
    }

    const bid = `${target_level}${suit_symbol(opener_suit)}`;
    if (is_legal_response_bid(response_bid, bid)) {
      return bidRecommendation(
        bid,
        `同伴以 Bergen 加叫 ${response_bid} 显示对 ${SUIT_NAMES[opener_suit]} 的支持；你有 ${hcp} HCP，按 Bergen 分档选择 ${bid}。牌型：${length_text}。`,
        "Bergen 后支持开叫高花",
      );
    }
  }

  // 开叫 1M 后同伴 1NT：按牌力/牌型再叫。
  // 2♣/2♦ 保证 3 张；2M 需 6+；2NT=17-18 均型；3NT=19-21 均型。
  if (["1♥", "1♠"].includes(opening_bid) && response_bid === "1NT" && ["H", "S"].includes(opener_suit)) {
    if (evaluation.balanced && hcp >= 19 && hcp <= 21 && is_legal_response_bid(response_bid, "3NT")) {
      return bidRecommendation(
        "3NT",
        `1${opening_strain}-1NT 后，你有 ${hcp} HCP 且均型，叫 3NT。牌型：${length_text}。`,
        "1M-1NT 后 3NT",
      );
    }
    if (evaluation.balanced && hcp >= 17 && hcp <= 18 && is_legal_response_bid(response_bid, "2NT")) {
      return bidRecommendation(
        "2NT",
        `1${opening_strain}-1NT 后，你有 ${hcp} HCP 且均型，叫 2NT。牌型：${length_text}。`,
        "1M-1NT 后 2NT",
      );
    }
    if (lengths[opener_suit] >= 6) {
      const rebid_major = `2${opening_strain}`;
      if (is_legal_response_bid(response_bid, rebid_major)) {
        return bidRecommendation(
          rebid_major,
          `1${opening_strain}-1NT 后，你有 ${lengths[opener_suit]} 张开叫高花，再叫 ${rebid_major}。牌型：${length_text}。`,
          "1M-1NT 后重复高花",
        );
      }
    }
    // 1♠-1NT：有 4 张♥ 时再叫 2♥。
    if (opening_bid === "1♠" && lengths.H >= 4 && is_legal_response_bid(response_bid, "2♥")) {
      return bidRecommendation(
        "2♥",
        `1♠-1NT 后，你有 ${lengths.H} 张红心，再叫 2♥。牌型：${length_text}。`,
        "1♠-1NT 后再叫红心",
      );
    }
    const minor_for_rebid = choose_minor_for_major_one_nt_rebid(lengths);
    if (minor_for_rebid !== null) {
      const minor_bid = `2${suit_symbol(minor_for_rebid)}`;
      if (is_legal_response_bid(response_bid, minor_bid)) {
        return bidRecommendation(
          minor_bid,
          `1${opening_strain}-1NT 后，你有 ${lengths[minor_for_rebid]} 张 ${SUIT_NAMES[minor_for_rebid]}（保证 3 张），再叫 ${minor_bid}。牌型：${length_text}。`,
          "1M-1NT 后再叫低花",
        );
      }
    }
    return bidRecommendation(
      "Pass",
      `1${opening_strain}-1NT 后，你有 ${hcp} HCP，当前没有更合适的描述叫品，建议 Pass。牌型：${length_text}。`,
      "1M-1NT 后止叫",
    );
  }

  // 一阶低花开叫后同伴 1NT 应叫，最低限均型通常以止叫为主。
  if (["1♣", "1♦"].includes(opening_bid) && response_bid === "1NT" && evaluation.balanced && hcp <= 14) {
    return bidRecommendation(
      "Pass",
      `同伴 1NT 应叫后，你有 ${hcp} HCP 且均型，属于最低限，通常止叫 Pass。牌型：${length_text}。`,
      "1NT 应叫后最低限止叫",
    );
  }

  if (
    opening_level === 1 &&
    ["♥", "♠"].includes(opening_strain) &&
    response_contract !== null &&
    response_contract[0] === 2 &&
    response_contract[1] === opening_strain
  ) {
    if (hcp <= 14) {
      return bidRecommendation(
        "Pass",
        `同伴简单加叫到 ${response_bid}，你有 ${hcp} HCP 属于最低限，优先止叫 Pass。牌型：${length_text}。`,
        "简单加叫后最低限止叫",
      );
    }
    if (hcp >= 18) {
      const game_bid = `4${opening_strain}`;
      if (is_legal_response_bid(response_bid, game_bid)) {
        return bidRecommendation(
          game_bid,
          `同伴简单加叫到 ${response_bid}，你有 ${hcp} HCP 属于高限，直接进局 ${game_bid}。牌型：${length_text}。`,
          "简单加叫后高限进局",
        );
      }
    }

    const invite_bid = `3${opening_strain}`;
    if (is_legal_response_bid(response_bid, invite_bid)) {
      return bidRecommendation(
        invite_bid,
        `同伴简单加叫到 ${response_bid}，你有 ${hcp} HCP 属于中等强度，叫 ${invite_bid} 表示继续邀请。牌型：${length_text}。`,
        "简单加叫后邀请",
      );
    }
  }

  // 一阶高花开叫后同伴直接跳到 4M：关煞叫（弱牌+长将牌），开叫者通常止叫。
  if (
    opening_level === 1 &&
    ["♥", "♠"].includes(opening_strain) &&
    response_contract !== null &&
    response_contract[0] === 4 &&
    response_contract[1] === opening_strain
  ) {
    return bidRecommendation(
      "Pass",
      `同伴以 ${response_bid} 作高花关煞加叫，已成局且示弱；你有 ${hcp} HCP，没有额外牌力继续试探满贯，建议止叫 Pass。牌型：${length_text}。`,
      "关煞加叫后止叫",
    );
  }

  // 一阶高花开叫后同伴跳加叫到 3M：多为弱支持跳加；最低限止叫，有额外牌力再进局。
  if (
    opening_level === 1 &&
    ["♥", "♠"].includes(opening_strain) &&
    response_contract !== null &&
    response_contract[0] === 3 &&
    response_contract[1] === opening_strain
  ) {
    if (hcp <= 15) {
      return bidRecommendation(
        "Pass",
        `同伴跳加叫到 ${response_bid} 多为弱支持；你有 ${hcp} HCP 属于最低限，建议止叫 Pass。牌型：${length_text}。`,
        "弱跳加叫后最低限止叫",
      );
    }
    const game_bid = `4${opening_strain}`;
    if (is_legal_response_bid(response_bid, game_bid)) {
      return bidRecommendation(
        game_bid,
        `同伴跳加叫到 ${response_bid}；你有 ${hcp} HCP 具备额外牌力，进局 ${game_bid}。牌型：${length_text}。`,
        "弱跳加叫后进局",
      );
    }
  }

  // 低花反加叫未开启时的 1m-2m：按牌力选择 Pass / 2M / 2NT / 3NT / 3m。
  if (
    !settings.inverted_minors_enabled &&
    opening_level === 1 &&
    ["♣", "♦"].includes(opening_strain) &&
    response_contract !== null &&
    response_contract[0] === 2 &&
    response_contract[1] === opening_strain
  ) {
    if (hcp <= 16) {
      return bidRecommendation(
        "Pass",
        `同伴加叫到 ${response_bid}（未启用低花反加叫），你有 ${hcp} HCP（≤16），建议止叫 Pass。牌型：${length_text}。`,
        "普通低花加叫后止叫",
      );
    }
    if (hcp >= 20 && evaluation.balanced && is_legal_response_bid(response_bid, "3NT")) {
      return bidRecommendation(
        "3NT",
        `同伴加叫到 ${response_bid}（未启用低花反加叫），你有 ${hcp} HCP 且均型，叫 3NT。牌型：${length_text}。`,
        "普通低花加叫后 3NT",
      );
    }
    const five_plus_majors = ["S", "H"].filter((suit) => lengths[suit] >= 5);
    if (hcp >= 18 && five_plus_majors.length) {
      const major = five_plus_majors.reduce((best, suit) => {
        const bestLen = lengths[best];
        const suitLen = lengths[suit];
        if (suitLen !== bestLen) {
          return suitLen > bestLen ? suit : best;
        }
        return suit === "S" ? suit : best;
      });
      const major_bid = `2${suit_symbol(major)}`;
      if (is_legal_response_bid(response_bid, major_bid)) {
        return bidRecommendation(
          major_bid,
          `同伴加叫到 ${response_bid}（未启用低花反加叫），你有 ${hcp} HCP 且 ${lengths[major]} 张 ${SUIT_NAMES[major]}，再叫 ${major_bid}。牌型：${length_text}。`,
          "普通低花加叫后再叫高花",
        );
      }
    }
    if (evaluation.balanced && hcp >= 18 && hcp <= 19 && is_legal_response_bid(response_bid, "2NT")) {
      return bidRecommendation(
        "2NT",
        `同伴加叫到 ${response_bid}（未启用低花反加叫），你有 ${hcp} HCP 且均型，叫 2NT。牌型：${length_text}。`,
        "普通低花加叫后 2NT",
      );
    }
    if (hcp >= 18 && hcp <= 19) {
      const invite_minor = `3${opening_strain}`;
      if (is_legal_response_bid(response_bid, invite_minor)) {
        return bidRecommendation(
          invite_minor,
          `同伴加叫到 ${response_bid}（未启用低花反加叫），你有 ${hcp} HCP，叫 ${invite_minor} 邀局。牌型：${length_text}。`,
          "普通低花加叫后邀局",
        );
      }
    }
    return bidRecommendation(
      "Pass",
      `同伴加叫到 ${response_bid}（未启用低花反加叫），你有 ${hcp} HCP，当前没有更合适的继续叫品，建议 Pass。牌型：${length_text}。`,
      "普通低花加叫后止叫",
    );
  }

  if (
    settings.inverted_minors_enabled &&
    opening_level === 1 &&
    ["♣", "♦"].includes(opening_strain) &&
    response_contract !== null &&
    response_contract[0] === 2 &&
    response_contract[1] === opening_strain
  ) {
    const other_minor = opener_suit === "C" ? "D" : "C";
    const other_minor_sym = suit_symbol(other_minor);
    const spade_stop = lengths.S >= 1 && (evaluation.top_honors_by_suit.S || 0) >= 1;
    const heart_stop = lengths.H >= 1 && (evaluation.top_honors_by_suit.H || 0) >= 1;
    const both_majors_stopped = spade_stop && heart_stop;
    const short_major = ["H", "S"].find((mj) => lengths[mj] <= 1) || null;

    if (evaluation.balanced && hcp >= 18 && hcp <= 19 && both_majors_stopped && is_legal_response_bid(response_bid, "3NT")) {
      return bidRecommendation(
        "3NT",
        `同伴低花反加叫 ${response_bid} 后，你有 ${hcp} HCP 均型且两高花均有止，直接叫 3NT。牌型：${length_text}。`,
        "低花反加叫后 3NT",
      );
    }

    if (hcp >= 20 && !evaluation.balanced && is_legal_response_bid(response_bid, "4NT")) {
      return bidRecommendation(
        "4NT",
        `同伴低花反加叫 ${response_bid} 后，你有 ${hcp} HCP 且非均型，按约定以开叫低花为将牌进入 4NT 关键张问叫。牌型：${length_text}。`,
        "低花反加叫后 4NT 问叫",
      );
    }

    if (hcp >= 20 && evaluation.balanced && is_legal_response_bid(response_bid, "5NT")) {
      return bidRecommendation(
        "5NT",
        `同伴低花反加叫 ${response_bid} 后，你有 ${hcp} HCP 且均型，按约定叫 5NT 邀请 6NT。牌型：${length_text}。`,
        "低花反加叫后 5NT 邀请",
      );
    }

    if (short_major !== null && hcp >= 18 && hcp <= 21) {
      const splinter_bid = `3${suit_symbol(short_major)}`;
      if (is_legal_response_bid(response_bid, splinter_bid)) {
        const short_desc = lengths[short_major] === 1 ? "单张" : "缺门";
        return bidRecommendation(
          splinter_bid,
          `同伴低花反加叫 ${response_bid} 后，你有 ${hcp} HCP 且 ${SUIT_NAMES[short_major]}${short_desc}，叫 ${splinter_bid} 作强满贯试探型 Splinter。牌型：${length_text}。`,
          "低花反加叫后高限 Splinter",
        );
      }
    }

    if (short_major !== null && hcp >= 15 && hcp <= 17) {
      const short_bid = `2${suit_symbol(short_major)}`;
      if (is_legal_response_bid(response_bid, short_bid)) {
        const short_desc = lengths[short_major] === 1 ? "单张" : "缺门";
        return bidRecommendation(
          short_bid,
          `同伴低花反加叫 ${response_bid} 后，你有 ${hcp} HCP 且 ${SUIT_NAMES[short_major]}${short_desc}，叫 ${short_bid} 报单缺作满贯试探。牌型：${length_text}。`,
          "低花反加叫后报单缺",
        );
      }
    }

    if (both_majors_stopped && hcp >= 15 && hcp <= 17 && is_legal_response_bid(response_bid, "2NT")) {
      return bidRecommendation(
        "2NT",
        `同伴低花反加叫 ${response_bid} 后，你有 ${hcp} HCP 且两高花均有止，叫 2NT 倾向 3NT。牌型：${length_text}。`,
        "低花反加叫后 2NT",
      );
    }

    if (hcp <= 14 && (spade_stop || heart_stop)) {
      const other_level = opener_suit === "C" ? 2 : 3;
      const other_bid = `${other_level}${other_minor_sym}`;
      if (is_legal_response_bid(response_bid, other_bid)) {
        return bidRecommendation(
          other_bid,
          `同伴低花反加叫 ${response_bid} 后，你有 ${hcp} HCP（低限）且至少一高花有止，顺叫 ${other_bid}，不排斥最终 3NT。牌型：${length_text}。`,
          "低花反加叫后顺叫低花",
        );
      }
    }

    const rebid_minor = `3${opening_strain}`;
    if (hcp <= 14 && is_legal_response_bid(response_bid, rebid_minor)) {
      return bidRecommendation(
        rebid_minor,
        `同伴低花反加叫 ${response_bid} 后，你有 ${hcp} HCP（低限）且高花无止，叫 ${rebid_minor} 低限止叫。牌型：${length_text}。`,
        "低花反加叫后低限重叫低花",
      );
    }

    if (is_legal_response_bid(response_bid, rebid_minor)) {
      return bidRecommendation(
        rebid_minor,
        `同伴低花反加叫 ${response_bid} 后，你有 ${hcp} HCP（高限），当前不满足 2NT/3NT 或高花短门分支，先以 ${rebid_minor} 继续描述牌型。牌型：${length_text}。`,
        "低花反加叫后高限继续描述",
      );
    }
  }

  if (
    opening_level === 1 &&
    ["♣", "♦"].includes(opening_strain) &&
    response_contract !== null &&
    response_contract[0] === 3 &&
    response_contract[1] === opening_strain
  ) {
    if (evaluation.balanced && hcp >= 13 && is_legal_response_bid(response_bid, "3NT")) {
      return bidRecommendation(
        "3NT",
        `同伴跳加叫 ${response_bid} 显示低花限制加叫；你有 ${hcp} HCP 且均型，优先选择 3NT 成局。牌型：${length_text}。`,
        "低花限制加叫后 3NT",
      );
    }
    return bidRecommendation(
      "Pass",
      `同伴跳加叫 ${response_bid} 显示低花限制加叫；你有 ${hcp} HCP，当前未到明确 3NT 成局条件，建议止叫 Pass。牌型：${length_text}。`,
      "低花限制加叫后止叫",
    );
  }

  // 仅支持同伴新叫出的高花；若同伴已加叫开叫者高花，由上方专用分支处理。
  if (["H", "S"].includes(response_suit) && lengths[response_suit] >= 4 && response_suit !== opener_suit) {
    const level = choose_raise_level(response_level, raise_hcp);
    const bid = `${level}${suit_symbol(response_suit)}`;
    return bidRecommendation(
      bid,
      `同伴应叫 ${response_bid}，你有 ${hcp} HCP 和 ${lengths[response_suit]} 张 ${SUIT_NAMES[response_suit]} 支持，优先支持同伴高花，叫 ${bid}。牌型：${length_text}。`,
      "支持同伴高花",
    );
  }

  // 一阶开叫-一阶应叫后：优先保留可叫的一阶第二套（如 1♣-1♥-1♠）。
  // 特例：同伴应叫 1♥ 且持有 4 张♠ 时，须先于均型 1NT/2NT 再叫 1♠。
  if (opening_level === 1 && response_level === 1) {
    const one_level_second_suit = choose_one_level_second_suit(
      lengths,
      opener_suit,
      response_suit,
      response_bid,
    );
    if (one_level_second_suit !== null) {
      const one_level_bid = minimum_legal_bid_for_suit(one_level_second_suit, response_bid, 1);
      if (one_level_bid !== null) {
        return bidRecommendation(
          one_level_bid,
          `你开叫 ${opening_bid} 后还有 4 张以上第二套 ${SUIT_NAMES[one_level_second_suit]}，再叫新花 ${one_level_bid} 描述牌型。牌型：${length_text}。`,
          "再叫第二套",
        );
      }
    }
  }

  if (evaluation.balanced) {
    const strong_nt_min = Math.max(17, 18 + game_adjustment);
    const weak_nt_max = Math.min(15, 14 + game_adjustment);
    if (hcp >= strong_nt_min && is_legal_response_bid(response_bid, "2NT")) {
      return bidRecommendation(
        "2NT",
        `你有 ${hcp} HCP 且均型，开叫后再叫 2NT 表示约 18-19 均型强无将牌。牌型：${length_text}。`,
        "18-19 均型再叫 2NT",
      );
    }
    if (hcp <= weak_nt_max && is_legal_response_bid(response_bid, "1NT")) {
      return bidRecommendation(
        "1NT",
        `你有 ${hcp} HCP 且均型，开叫后再叫 1NT 表示最低限均型牌。牌型：${length_text}。`,
        "最低限均型再叫 1NT",
      );
    }
  }

  // 一阶开叫-一阶应叫后：均型低限，或非均型且单缺同伴应叫花色，可再叫 1NT。
  const opener_length = opener_suit !== null ? lengths[opener_suit] : 0;
  const has_singleton_or_void = Math.min(lengths.S, lengths.H, lengths.D, lengths.C) <= 1;
  const shortage_in_response_suit =
    ["H", "S"].includes(response_suit) && lengths[response_suit] <= 1;
  if (opening_level === 1 && response_level === 1) {
    if (
      hcp >= 12 &&
      hcp <= 14 &&
      opener_length <= 5 &&
      (!has_singleton_or_void || shortage_in_response_suit) &&
      is_legal_response_bid(response_bid, "1NT")
    ) {
      const reason =
        shortage_in_response_suit && !evaluation.balanced
          ? "牌型单缺同伴应叫花色"
          : "牌型无单缺且开叫套不超过 5 张";
      return bidRecommendation(
        "1NT",
        `你有 ${hcp} HCP，一阶开叫后同伴一阶应叫；${reason}，当前没有可叫的一阶第二套，优先再叫 1NT 表示低限并控制叫牌高度。牌型：${length_text}。`,
        "一阶序列低限再叫 1NT",
      );
    }
  }

  // 一阶低花开叫后同伴一阶高花应叫：无支持时，非均型恰好 5 张开叫花色可按点力重复 2/3 阶。
  // （6+ 长套仍走后方重复/6-5 第二套逻辑。）
  if (
    opening_level === 1 &&
    ["♣", "♦"].includes(opening_strain) &&
    ["H", "S"].includes(response_suit) &&
    response_level === 1 &&
    opener_suit !== null &&
    lengths[opener_suit] === 5 &&
    !evaluation.balanced
  ) {
    const rebid_level = hcp >= 16 ? 3 : 2;
    const rebid_opening = `${rebid_level}${opening_strain}`;
    if (is_legal_response_bid(response_bid, rebid_opening)) {
      return bidRecommendation(
        rebid_opening,
        `你开叫 ${opening_bid} 后持有 5 张 ${SUIT_NAMES[opener_suit]}（非均型），无同伴高花支持，按点力重复开叫花色 ${rebid_opening}。牌型：${length_text}。`,
        "重复开叫花色",
      );
    }
  }

  const reverse_min_hcp = 16;
  const second_suit = choose_second_suit(
    lengths,
    opener_suit,
    response_suit,
    opening_bid,
    response_bid,
    hcp,
    reverse_min_hcp,
  );

  if (
    opener_suit !== null &&
    lengths[opener_suit] >= 6 &&
    second_suit !== null &&
    lengths[second_suit] >= 5
  ) {
    const bid = minimum_legal_bid_for_suit(second_suit, response_bid, 1);
    if (bid !== null) {
      return bidRecommendation(
        bid,
        `你开叫 ${opening_bid} 后为 6-5 两套型（${SUIT_NAMES[opener_suit]} ${lengths[opener_suit]} 张、${SUIT_NAMES[second_suit]} ${lengths[second_suit]} 张），优先再叫第二套 ${bid} 描述分布。牌型：${length_text}。`,
        "再叫第二套",
      );
    }
  }

  if (opener_suit !== null && lengths[opener_suit] >= 6) {
    const bid = minimum_legal_bid_for_suit(opener_suit, response_bid, 2);
    if (bid !== null) {
      return bidRecommendation(
        bid,
        `你开叫 ${opening_bid} 后持有 ${lengths[opener_suit]} 张 ${SUIT_NAMES[opener_suit]}，无更优支持或无将再叫，重复自己长套 ${bid}。牌型：${length_text}。`,
        "重复开叫花色",
      );
    }
  }

  if (second_suit !== null) {
    const bid = minimum_legal_bid_for_suit(second_suit, response_bid, 1);
    if (bid !== null) {
      if (is_reverse_second_suit(opening_bid, response_bid, bid)) {
        return bidRecommendation(
          bid,
          `你开叫 ${opening_bid} 后再叫新花 ${bid}，属于逆叫；你有 ${hcp} HCP，达到逆叫常见门槛（约 ${reverse_min_hcp}+ HCP），并有 4 张以上第二套 ${SUIT_NAMES[second_suit]}。牌型：${length_text}。`,
          "逆叫第二套",
        );
      }
      return bidRecommendation(
        bid,
        `你开叫 ${opening_bid} 后还有 4 张以上第二套 ${SUIT_NAMES[second_suit]}，再叫新花 ${bid} 描述牌型。牌型：${length_text}。`,
        "再叫第二套",
      );
    }
  }

  if (opener_suit !== null) {
    const bid = minimum_legal_bid_for_suit(opener_suit, response_bid, 2);
    if (bid !== null) {
      return bidRecommendation(
        bid,
        `没有同伴高花支持、均型无将或合适第二套，回到开叫花色 ${bid} 作低限再叫。牌型：${length_text}。`,
        "回叫开叫花色",
      );
    }
  }

  const fallback = next_legal_contract(response_bid, REBID_BIDS);
  return bidRecommendation(
    fallback || "Pass",
    `当前简化规则没有更精确描述，选择最低合法叫品 ${fallback || "Pass"}。你有 ${hcp} HCP，牌型：${length_text}。`,
    "最低合法再叫",
  );
}

function choose_raise_level(response_level, hcp) {
  if (hcp >= 19) {
    return 4;
  }
  if (hcp >= 16) {
    return Math.max(3, response_level + 1);
  }
  return Math.max(2, response_level + 1);
}

function choose_minor_for_major_one_nt_rebid(lengths) {
  // 1M-1NT 后再叫低花：保证至少 3 张；等长时优先较便宜的 ♣。
  const candidates = ["C", "D"].filter((suit) => lengths[suit] >= 3);
  if (!candidates.length) {
    return null;
  }
  return candidates.reduce((best, suit) => {
    const bestLen = lengths[best];
    const suitLen = lengths[suit];
    if (suitLen !== bestLen) {
      return suitLen > bestLen ? suit : best;
    }
    return suit === "C" ? suit : best;
  });
}

function prefers_minor_suit_transfer(hcp, lengths, minor, evaluation) {
  // 1NT 后低花转移：6+ 单套，且弱牌或强牌/极不均型倾向低花定约。
  // 8-10 HCP 除非非常不平均，否则不走转移（改走 3m 邀 3NT 或直接 3NT）。
  const very_unbalanced =
    Math.min(lengths.S, lengths.H, lengths.D, lengths.C) <= 1 || lengths[minor] >= 7;
  if (hcp < 7) {
    return true;
  }
  if (hcp === 7) {
    return true;
  }
  if (hcp >= 8 && hcp <= 10) {
    return very_unbalanced;
  }
  if (evaluation.balanced && !very_unbalanced) {
    return false;
  }
  return very_unbalanced || !evaluation.balanced;
}

function choose_second_suit(lengths, opener_suit, response_suit, opening_bid, response_bid, hcp, reverse_min_hcp) {
  const candidates = [];
  for (const suit of ["S", "H", "D", "C"]) {
    if ([opener_suit, response_suit].includes(suit)) {
      continue;
    }
    if (lengths[suit] < 4) {
      continue;
    }
    const bid = minimum_legal_bid_for_suit(suit, response_bid, 1);
    if (bid === null) {
      continue;
    }
    if (is_reverse_second_suit(opening_bid, response_bid, bid) && hcp < reverse_min_hcp) {
      continue;
    }
    candidates.push(suit);
  }
  if (!candidates.length) {
    return null;
  }
  return maxSuitByLength(candidates, lengths);
}

function choose_one_level_second_suit(lengths, opener_suit, response_suit, response_bid) {
  const candidates = [];
  for (const suit of ["S", "H", "D", "C"]) {
    if ([opener_suit, response_suit].includes(suit)) {
      continue;
    }
    if (lengths[suit] < 4) {
      continue;
    }
    const bid = minimum_legal_bid_for_suit(suit, response_bid, 1);
    if (bid === null) {
      continue;
    }
    const contract = parse_contract_bid(bid);
    if (contract !== null && contract[0] === 1) {
      candidates.push(suit);
    }
  }

  if (!candidates.length) {
    return null;
  }
  return maxSuitByLength(candidates, lengths);
}

function is_reverse_second_suit(opening_bid, response_bid, rebid_bid) {
  const opening_contract = parse_contract_bid(opening_bid);
  const response_contract = parse_contract_bid(response_bid);
  const rebid_contract = parse_contract_bid(rebid_bid);
  if (opening_contract === null || response_contract === null || rebid_contract === null) {
    return false;
  }

  const [opening_level, opening_strain] = opening_contract;
  const [response_level] = response_contract;
  const [rebid_level, rebid_strain] = rebid_contract;
  if (opening_level !== 1 || response_level !== 1) {
    return false;
  }
  if (rebid_level !== 2) {
    return false;
  }
  if (opening_strain === "NT" || rebid_strain === "NT") {
    return false;
  }
  return STRAIN_ORDER[rebid_strain] > STRAIN_ORDER[opening_strain];
}

function minimum_legal_bid_for_suit(suit, previous_bid, minimum_level = 1) {
  const symbol = suit_symbol(suit);
  for (let level = minimum_level; level < 5; level++) {
    const bid = `${level}${symbol}`;
    if (REBID_BIDS.includes(bid) && is_legal_response_bid(previous_bid, bid)) {
      return bid;
    }
  }
  return null;
}

function next_legal_contract(previous_bid, choices) {
  for (const bid of choices) {
    if (bid !== "Pass" && is_legal_response_bid(previous_bid, bid)) {
      return bid;
    }
  }
  return null;
}

function symbol_to_suit(strain) {
  const map = { "♣": "C", "♦": "D", "♥": "H", "♠": "S" };
  return map[strain] !== undefined ? map[strain] : null;
}

function recommend_responder_rebid(opening_bid, response_bid, opener_rebid_bid, evaluation, settings, vulnerability) {
  settings = settings || defaultRuleSettings();
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const length_text = describe_lengths(evaluation);

  // 拼搏式 3NT 后应叫者第二次应叫（含开叫者 Pass；须先于合约解析兜底）。
  if (opening_bid === "3NT") {
    // Pass 后再叫时，以应叫花色作为合法性参照（Pass 本身无法抬级）。
    const legality_prev = opener_rebid_bid === "Pass" ? response_bid : opener_rebid_bid;
    if (response_bid === "4♣" && opener_rebid_bid === "Pass") {
      if (hcp >= 16 && is_legal_response_bid(legality_prev, "5♣")) {
        return bidRecommendation(
          "5♣",
          `拼搏式 3NT-4♣ 后开叫者 Pass 确认梅花，你有 ${hcp} HCP，加叫到 5♣。牌型：${length_text}。`,
          "拼搏式 3NT 后进低花局",
        );
      }
      return bidRecommendation(
        "Pass",
        `拼搏式 3NT-4♣ 后开叫者 Pass 确认梅花，当前牌力以止叫为主，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
        "拼搏式 3NT 后止叫",
      );
    }
    if (response_bid === "4♣" && opener_rebid_bid === "4♦") {
      if (hcp >= 16 && is_legal_response_bid(opener_rebid_bid, "5♦")) {
        return bidRecommendation(
          "5♦",
          `拼搏式 3NT-4♣-4♦ 后确认方块，你有 ${hcp} HCP，加叫到 5♦。牌型：${length_text}。`,
          "拼搏式 3NT 后进低花局",
        );
      }
      return bidRecommendation(
        "Pass",
        `拼搏式 3NT-4♣-4♦ 后确认方块，当前牌力以止叫为主，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
        "拼搏式 3NT 后止叫",
      );
    }
    if (response_bid === "4♦") {
      if (["4♥", "4♠", "5♣", "5♦"].includes(opener_rebid_bid)) {
        if (hcp >= 18 && ["5♣", "5♦"].includes(opener_rebid_bid)) {
          const slam = `6${opener_rebid_bid[1]}`;
          if (is_legal_response_bid(opener_rebid_bid, slam)) {
            return bidRecommendation(
              slam,
              `拼搏式 3NT-4♦-${opener_rebid_bid} 后，你有 ${hcp} HCP，尝试低花小满贯 ${slam}。牌型：${length_text}。`,
              "拼搏式 3NT 后试探满贯",
            );
          }
        }
        if (hcp >= 16 && ["4♥", "4♠"].includes(opener_rebid_bid)) {
          return bidRecommendation(
            "Pass",
            `拼搏式 3NT-4♦-${opener_rebid_bid} 后，开叫者已报单缺；当前简化体系建议先止叫，由开叫者牌型决定定约。你有 ${hcp} HCP，牌型：${length_text}。`,
            "拼搏式 3NT 后止叫",
          );
        }
        return bidRecommendation(
          "Pass",
          `拼搏式 3NT-4♦-${opener_rebid_bid} 后，当前简化体系以止叫为主，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
          "拼搏式 3NT 后止叫",
        );
      }
    }
    if (["4♥", "4♠"].includes(response_bid)) {
      return bidRecommendation(
        "Pass",
        `拼搏式 3NT 后你已叫出高花成局 ${response_bid}，开叫者再叫 ${opener_rebid_bid} 后通常止叫。你有 ${hcp} HCP，牌型：${length_text}。`,
        "拼搏式 3NT 后止叫",
      );
    }
    return bidRecommendation(
      "Pass",
      `拼搏式 3NT 序列中同伴再叫 ${opener_rebid_bid}，当前简化体系建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
      "拼搏式 3NT 后止叫",
    );
  }

  const opener_rebid_contract = parse_contract_bid(opener_rebid_bid);
  const response_contract = parse_contract_bid(response_bid);
  if (opener_rebid_contract === null || response_contract === null) {
    return bidRecommendation(
      "Pass",
      `当前序列无法识别为标准合约叫品，默认 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
      "无有效序列默认 Pass",
    );
  }

  const opener_strain = opener_rebid_contract[1];
  const opener_suit = symbol_to_suit(opener_strain);
  const opening_contract = parse_contract_bid(opening_bid);
  if (opening_contract !== null) {
    const [opening_level, opening_strain] = opening_contract;
    const is_weak_two_opening = opening_level === 2 && ["♦", "♥", "♠"].includes(opening_strain);
    const is_three_plus_preempt_opening =
      opening_level >= 3 && ["♣", "♦", "♥", "♠"].includes(opening_strain);
    if (is_three_plus_preempt_opening) {
      return bidRecommendation(
        "Pass",
        `阻击开叫序列中同伴已再叫 ${opener_rebid_bid}，当前简化体系以止叫为主，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
        "阻击后止叫",
      );
    }
    if (is_weak_two_opening && response_bid === "2NT" && settings.august_2nt_enabled) {
      const opening_suit = symbol_to_suit(opening_strain);
      const ogust_minimum_answers = ["3♣", "3♦"];
      const ogust_maximum_answers = ["3♥", "3♠", "3NT"];
      if (opener_rebid_bid === "3NT") {
        return bidRecommendation(
          "Pass",
          `弱二开叫经 Ogust 2NT 问叫后，开叫者已用 3NT 显示高限强套并落在成局，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
          "Ogust 后止叫",
        );
      }

      if (ogust_minimum_answers.indexOf(opener_rebid_bid) >= 0 || ogust_maximum_answers.indexOf(opener_rebid_bid) >= 0) {
        if (opening_suit !== null) {
          const has_major_support = ["H", "S"].includes(opening_suit) && lengths[opening_suit] >= 3;
          const is_maximum_answer = ogust_maximum_answers.includes(opener_rebid_bid);

          const major_game_hcp = is_maximum_answer ? 12 : 15;
          const major_invite_low = is_maximum_answer ? 10 : 12;
          const major_invite_high = major_game_hcp - 1;
          const nt_game_hcp = is_maximum_answer ? 11 : 13;

          if (has_major_support) {
            const major_game_bid = `4${suit_symbol(opening_suit)}`;
            const major_invite_bid = `3${suit_symbol(opening_suit)}`;
            if (hcp >= major_game_hcp && is_legal_response_bid(opener_rebid_bid, major_game_bid)) {
              return bidRecommendation(
                major_game_bid,
                `弱二开叫经 Ogust 2NT 后，开叫者再叫 ${opener_rebid_bid}（${is_maximum_answer ? "高限" : "低限"}）；你有 ${hcp} HCP 且有 3+ 张将牌支持，按分档直接进局 ${major_game_bid}。牌型：${length_text}。`,
                "Ogust 后高花进局",
              );
            }
            if (
              hcp >= major_invite_low &&
              hcp <= major_invite_high &&
              is_legal_response_bid(opener_rebid_bid, major_invite_bid)
            ) {
              return bidRecommendation(
                major_invite_bid,
                `弱二开叫经 Ogust 2NT 后，开叫者再叫 ${opener_rebid_bid}（${is_maximum_answer ? "高限" : "低限"}）；你有 ${hcp} HCP 且有 3+ 张将牌支持，按分档先邀局 ${major_invite_bid}。牌型：${length_text}。`,
                "Ogust 后高花邀局",
              );
            }
          }

          if (evaluation.balanced && hcp >= nt_game_hcp && is_legal_response_bid(opener_rebid_bid, "3NT")) {
            return bidRecommendation(
              "3NT",
              `弱二开叫经 Ogust 2NT 后，开叫者再叫 ${opener_rebid_bid}（${is_maximum_answer ? "高限" : "低限"}）；你有 ${hcp} HCP 且均型，按分档转入 3NT。牌型：${length_text}。`,
              "Ogust 后无将进局",
            );
          }
        }

        return bidRecommendation(
          "Pass",
          `弱二开叫经 Ogust 2NT 问叫后，开叫者再叫 ${opener_rebid_bid}；当前牌力与配合不足继续推进，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
          "Ogust 后止叫",
        );
      }
    }

    if (is_weak_two_opening) {
      return bidRecommendation(
        "Pass",
        `弱二开叫序列中同伴已再叫 ${opener_rebid_bid}，当前简化体系默认止叫，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
        "弱二后止叫",
      );
    }
  }

  const game_adjustment = game_threshold_adjustment(vulnerability, settings);
  const nt_game_hcp = Math.max(11, 13 + game_adjustment);
  const nt_invite_low = Math.max(7, 10 + game_adjustment);
  const nt_invite_high = nt_game_hcp - 1;
  const raise_hcp = hcp - game_adjustment;

  if (opening_bid === "1NT") {
    const game_adjustment_nt = game_threshold_adjustment(vulnerability, settings);
    const nt_resp_game_hcp = Math.max(8, 10 + game_adjustment_nt);
    const nt_resp_invite_low = Math.max(6, 8 + game_adjustment_nt);
    const nt_resp_invite_high = nt_resp_game_hcp - 1;

    if (response_bid === "2♣" && opener_rebid_bid === "2♦") {
      if (hcp >= nt_resp_game_hcp && is_legal_response_bid(opener_rebid_bid, "3NT")) {
        return bidRecommendation(
          "3NT",
          `1NT-2♣-2♦ 序列中，开叫者否定 4 张高花；你有 ${hcp} HCP，叫 3NT 进无将局。牌型：${length_text}。`,
          "Stayman 否定后无将进局",
        );
      }
      if (
        hcp >= nt_resp_invite_low &&
        hcp <= nt_resp_invite_high &&
        is_legal_response_bid(opener_rebid_bid, "2NT")
      ) {
        return bidRecommendation(
          "2NT",
          `1NT-2♣-2♦ 序列中，开叫者否定 4 张高花；你有 ${hcp} HCP，叫 2NT 邀局。牌型：${length_text}。`,
          "Stayman 否定后无将邀局",
        );
      }
      return bidRecommendation(
        "Pass",
        `1NT-2♣-2♦ 序列中，开叫者否定 4 张高花；你有 ${hcp} HCP，牌力不足以邀局，建议 Pass。牌型：${length_text}。`,
        "Stayman 否定后止叫",
      );
    }

    if (response_bid === "2♣" && ["♥", "♠"].includes(opener_strain) && opener_suit !== null) {
      if (lengths[opener_suit] >= 4) {
        if (hcp >= nt_resp_game_hcp) {
          const major_game = `4${opener_strain}`;
          if (is_legal_response_bid(opener_rebid_bid, major_game)) {
            return bidRecommendation(
              major_game,
              `1NT-2♣-${opener_rebid_bid} 序列后，你有 ${hcp} HCP 和 ${lengths[opener_suit]} 张配合，叫 ${major_game} 进高花局。牌型：${length_text}。`,
              "Stayman 后高花进局",
            );
          }
        }
        if (hcp >= nt_resp_invite_low) {
          const major_invite = `3${opener_strain}`;
          if (is_legal_response_bid(opener_rebid_bid, major_invite)) {
            return bidRecommendation(
              major_invite,
              `1NT-2♣-${opener_rebid_bid} 序列后，你有 ${hcp} HCP 和 ${lengths[opener_suit]} 张配合，叫 ${major_invite} 邀请高花局。牌型：${length_text}。`,
              "Stayman 后高花邀局",
            );
          }
        }
      }
      if (hcp >= nt_resp_game_hcp && is_legal_response_bid(opener_rebid_bid, "3NT")) {
        return bidRecommendation(
          "3NT",
          `1NT-2♣-${opener_rebid_bid} 序列后，你有 ${hcp} HCP，无高花配合，叫 3NT 进无将局。牌型：${length_text}。`,
          "Stayman 后无将进局",
        );
      }
      if (hcp >= nt_resp_invite_low && is_legal_response_bid(opener_rebid_bid, "2NT")) {
        return bidRecommendation(
          "2NT",
          `1NT-2♣-${opener_rebid_bid} 序列后，你有 ${hcp} HCP，邀请无将局。牌型：${length_text}。`,
          "Stayman 后无将邀局",
        );
      }
      return bidRecommendation(
        "Pass",
        `1NT-2♣-${opener_rebid_bid} 序列后，你有 ${hcp} HCP，牌力不足以邀局，建议 Pass。牌型：${length_text}。`,
        "Stayman 后止叫",
      );
    }

    if (response_bid === "2♦" && opener_rebid_bid === "2♥") {
      if (hcp >= nt_resp_game_hcp) {
        if (lengths.H >= 6 && is_legal_response_bid("2♥", "4♥")) {
          return bidRecommendation(
            "4♥",
            `红心转移完成后，你有 ${hcp} HCP 和 ${lengths.H} 张红心，直接进 4♥。牌型：${length_text}。`,
            "转移后高花进局",
          );
        }
        if (is_legal_response_bid("2♥", "3NT")) {
          return bidRecommendation(
            "3NT",
            `红心转移完成后，你有 ${hcp} HCP，选择 3NT 进无将局。牌型：${length_text}。`,
            "转移后无将进局",
          );
        }
      }
      if (hcp >= nt_resp_invite_low) {
        if (is_legal_response_bid("2♥", "2NT")) {
          return bidRecommendation(
            "2NT",
            `红心转移完成后，你有 ${hcp} HCP，叫 2NT 邀局。牌型：${length_text}。`,
            "转移后邀局",
          );
        }
      }
      return bidRecommendation(
        "Pass",
        `红心转移完成后，你有 ${hcp} HCP，牌力不足进局，建议 Pass。牌型：${length_text}。`,
        "转移后止叫",
      );
    }

    if (response_bid === "2♥" && opener_rebid_bid === "2♠") {
      if (hcp >= nt_resp_game_hcp) {
        if (lengths.S >= 6 && is_legal_response_bid("2♠", "4♠")) {
          return bidRecommendation(
            "4♠",
            `黑桃转移完成后，你有 ${hcp} HCP 和 ${lengths.S} 张黑桃，直接进 4♠。牌型：${length_text}。`,
            "转移后高花进局",
          );
        }
        if (is_legal_response_bid("2♠", "3NT")) {
          return bidRecommendation(
            "3NT",
            `黑桃转移完成后，你有 ${hcp} HCP，选择 3NT 进无将局。牌型：${length_text}。`,
            "转移后无将进局",
          );
        }
      }
      if (hcp >= nt_resp_invite_low) {
        if (is_legal_response_bid("2♠", "2NT")) {
          return bidRecommendation(
            "2NT",
            `黑桃转移完成后，你有 ${hcp} HCP，叫 2NT 邀局。牌型：${length_text}。`,
            "转移后邀局",
          );
        }
      }
      return bidRecommendation(
        "Pass",
        `黑桃转移完成后，你有 ${hcp} HCP，牌力不足进局，建议 Pass。牌型：${length_text}。`,
        "转移后止叫",
      );
    }

    // 低花转移后续：1NT - 2♠ - 3♣
    // 弱牌(<7)及中等(7-10)：方块单套 → 3♦，草花单套 → Pass
    // >10 HCP：11-12 邀局 4m；13-15 进局 3NT/5m；16+ 扣叫或 4NT 试探满贯
    if (settings.transfers_enabled && response_bid === "2♠" && opener_rebid_bid === "3♣") {
      const diamond_single = lengths.D >= 6 && lengths.C < 6;
      const club_single = lengths.C >= 6 && lengths.D < 6;
      const true_minor = diamond_single ? "D" : "C";
      const minor_symbol = suit_symbol(true_minor);

      // README：弱牌(<7) 方块→3♦、草花→Pass；7-10 同样先定位花色；>10 才邀局/进局/满贯。
      if (hcp <= 10) {
        const strength_label = hcp < 7 ? "弱牌(<7 HCP)" : "中等牌力(7-10 HCP)";
        if (diamond_single && is_legal_response_bid(opener_rebid_bid, "3♦")) {
          return bidRecommendation(
            "3♦",
            `1NT-2♠-3♣ 后，你有 ${hcp} HCP（${strength_label}）和 ${lengths.D} 张方块单套，再叫 3♦ 表明真实花色并止叫。牌型：${length_text}。`,
            "低花转移后改叫方块",
          );
        }
        return bidRecommendation(
          "Pass",
          `1NT-2♠-3♣ 后，你有 ${hcp} HCP（${strength_label}）和 ${lengths.C} 张草花单套，接受同伴完成转移，建议 Pass。牌型：${length_text}。`,
          "低花转移后止叫",
        );
      }

      if (hcp >= 16) {
        const short_majors = ["H", "S"].filter((suit) => lengths[suit] <= 1);
        for (const suit of short_majors) {
          const cue_bid = `3${suit_symbol(suit)}`;
          if (is_legal_response_bid(opener_rebid_bid, cue_bid)) {
            return bidRecommendation(
              cue_bid,
              `1NT-2♠-3♣ 后，你有 ${hcp} HCP 且 ${SUIT_NAMES[suit]} 单缺，扣叫 ${cue_bid} 试探满贯。牌型：${length_text}。`,
              "低花转移后扣叫试探满贯",
            );
          }
        }
        if (is_legal_response_bid(opener_rebid_bid, "4NT")) {
          return bidRecommendation(
            "4NT",
            `1NT-2♠-3♣ 后，你有 ${hcp} HCP 和 ${lengths[true_minor]} 张 ${SUIT_NAMES[true_minor]}，叫 4NT 问A张试探满贯。牌型：${length_text}。`,
            "低花转移后 4NT 问叫",
          );
        }
      }

      if (hcp >= 13) {
        if (evaluation.balanced && is_legal_response_bid(opener_rebid_bid, "3NT")) {
          return bidRecommendation(
            "3NT",
            `1NT-2♠-3♣ 后，你有 ${hcp} HCP 且均型，直接进局 3NT。牌型：${length_text}。`,
            "低花转移后进局",
          );
        }
        const game_bid = `5${minor_symbol}`;
        if (is_legal_response_bid(opener_rebid_bid, game_bid)) {
          return bidRecommendation(
            game_bid,
            `1NT-2♠-3♣ 后，你有 ${hcp} HCP 和 ${lengths[true_minor]} 张 ${SUIT_NAMES[true_minor]}，直接进局 ${game_bid}。牌型：${length_text}。`,
            "低花转移后进局",
          );
        }
      }

      const invite_bid = `4${minor_symbol}`;
      if (is_legal_response_bid(opener_rebid_bid, invite_bid)) {
        return bidRecommendation(
          invite_bid,
          `1NT-2♠-3♣ 后，你有 ${hcp} HCP 和 ${lengths[true_minor]} 张 ${SUIT_NAMES[true_minor]}，叫 ${invite_bid} 邀局。牌型：${length_text}。`,
          "低花转移后邀局",
        );
      }

      if (diamond_single && is_legal_response_bid(opener_rebid_bid, "3♦")) {
        return bidRecommendation(
          "3♦",
          `1NT-2♠-3♣ 后，你有 ${lengths.D} 张方块单套，再叫 3♦ 表明真实花色。牌型：${length_text}。`,
          "低花转移后改叫方块",
        );
      }
      return bidRecommendation(
        "Pass",
        `1NT-2♠-3♣ 后，你有 ${hcp} HCP，当前没有更合适的继续叫品，建议 Pass。牌型：${length_text}。`,
        "低花转移后止叫",
      );
    }
  }

  if (["1NT", "2NT", "3NT"].includes(opener_rebid_bid)) {
    if (hcp >= nt_game_hcp && is_legal_response_bid(opener_rebid_bid, "3NT")) {
      return bidRecommendation(
        "3NT",
        `开叫者再叫 ${opener_rebid_bid} 显示无将牌力，你有 ${hcp} HCP，合力足够进局，叫 3NT。牌型：${length_text}。`,
        "对无将再叫进局",
      );
    }
    if (hcp >= nt_invite_low && hcp <= nt_invite_high && is_legal_response_bid(opener_rebid_bid, "2NT")) {
      return bidRecommendation(
        "2NT",
        `开叫者再叫 ${opener_rebid_bid} 后，你有 ${hcp} HCP，先做无将邀局。牌型：${length_text}。`,
        "对无将再叫邀局",
      );
    }
    return bidRecommendation(
      "Pass",
      `开叫者再叫 ${opener_rebid_bid} 后，你有 ${hcp} HCP，不足以继续进局动作，建议 Pass。牌型：${length_text}。`,
      "对无将再叫止叫",
    );
  }

  if (["H", "S"].includes(opener_suit) && lengths[opener_suit] >= 3) {
    const level = choose_raise_level(opener_rebid_contract[0], raise_hcp);
    const bid = `${level}${suit_symbol(opener_suit)}`;
    if (is_legal_response_bid(opener_rebid_bid, bid)) {
      return bidRecommendation(
        bid,
        `开叫者再叫 ${opener_rebid_bid}，你有 ${lengths[opener_suit]} 张支持和 ${hcp} HCP，继续支持到 ${bid}。牌型：${length_text}。`,
        "支持开叫者再叫花色",
      );
    }
  }

  const response_suit = symbol_to_suit(response_contract[1]);
  if (response_suit !== null && lengths[response_suit] >= 6) {
    const rebid = minimum_legal_bid_for_suit(
      response_suit,
      opener_rebid_bid,
      response_contract[0] + 1,
    );
    if (rebid !== null) {
      return bidRecommendation(
        rebid,
        `你原应叫花色有 ${lengths[response_suit]} 张，且开叫者再叫 ${opener_rebid_bid} 后未形成更好配合，重复自己长套 ${rebid}。牌型：${length_text}。`,
        "应叫者重复原花色",
      );
    }
  }

  if (hcp >= Math.max(10, 12 + game_adjustment) && is_legal_response_bid(opener_rebid_bid, "3NT")) {
    return bidRecommendation(
      "3NT",
      `你有 ${hcp} HCP，虽无明确高花配合，优先转入 3NT 进局。牌型：${length_text}。`,
      "默认 3NT 进局",
    );
  }

  return bidRecommendation(
    "Pass",
    `当前简化规则下无更优再应叫，建议 Pass。你有 ${hcp} HCP，牌型：${length_text}。`,
    "默认止叫",
  );
}

function recommend_response_to_1nt(evaluation, settings, vulnerability) {
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const length_text = describe_lengths(evaluation);
  const game_adjustment = game_threshold_adjustment(vulnerability, settings);
  const game_hcp = Math.max(8, 10 + game_adjustment);
  const invite_low = Math.max(6, 8 + game_adjustment);
  const invite_high = game_hcp - 1;
  // 相对 15-17 1NT：约 16-17 邀小满，18+ 邀大满。
  const slam_invite_low = Math.max(14, 16 + game_adjustment);
  const grand_invite_low = Math.max(16, 18 + game_adjustment);

  // 德克萨斯：6+ 高花且够局，直接转移到四阶成局。
  if (settings.transfers_enabled && lengths.H >= 6 && hcp >= game_hcp) {
    return bidRecommendation(
      "4♦",
      `同伴开 1NT，你有 ${hcp} HCP 和 ${lengths.H} 张红心，使用德克萨斯转移叫 4♦，要求同伴转叫 4♥。牌型：${length_text}。`,
      "1NT 后德克萨斯红心转移",
    );
  }
  if (settings.transfers_enabled && lengths.S >= 6 && hcp >= game_hcp) {
    return bidRecommendation(
      "4♥",
      `同伴开 1NT，你有 ${hcp} HCP 和 ${lengths.S} 张黑桃，使用德克萨斯转移叫 4♥，要求同伴转叫 4♠。牌型：${length_text}。`,
      "1NT 后德克萨斯黑桃转移",
    );
  }

  // 3♥/3♠：5+ 高花且 15+ HCP，表示满贯兴趣。
  if (lengths.H >= 5 && hcp >= 15) {
    return bidRecommendation(
      "3♥",
      `同伴开 1NT，你有 ${hcp} HCP 和 ${lengths.H} 张红心，跳叫 3♥ 表示满贯兴趣。牌型：${length_text}。`,
      "1NT 后红心满贯兴趣",
    );
  }
  if (lengths.S >= 5 && hcp >= 15) {
    return bidRecommendation(
      "3♠",
      `同伴开 1NT，你有 ${hcp} HCP 和 ${lengths.S} 张黑桃，跳叫 3♠ 表示满贯兴趣。牌型：${length_text}。`,
      "1NT 后黑桃满贯兴趣",
    );
  }

  if (settings.transfers_enabled && lengths.H >= 5) {
    return bidRecommendation(
      "2♦",
      `同伴开 1NT，你有 ${hcp} HCP 和 5 张以上红心。简化规则使用 Jacoby Transfer：叫 2♦，要求同伴转叫 2♥。牌型：${length_text}。`,
      "1NT 后红心转移",
    );
  }
  if (settings.transfers_enabled && lengths.S >= 5) {
    return bidRecommendation(
      "2♥",
      `同伴开 1NT，你有 ${hcp} HCP 和 5 张以上黑桃。简化规则使用 Jacoby Transfer：叫 2♥，要求同伴转叫 2♠。牌型：${length_text}。`,
      "1NT 后黑桃转移",
    );
  }
  if (settings.stayman_enabled && hcp >= invite_low && (lengths.H >= 4 || lengths.S >= 4)) {
    return bidRecommendation(
      "2♣",
      `同伴开 1NT，你有 ${hcp} HCP 且至少一个 4 张高花。用 2♣ Stayman 寻找 4-4 高花配合。牌型：${length_text}。`,
      "Stayman",
    );
  }

  // 3♣/3♦：5+ 低花、8-9 HCP，邀 3NT（8-10 非极不均型优先此路，不走低花转移）。
  const has_four_card_major = lengths.H >= 4 || lengths.S >= 4;
  if (!has_four_card_major && hcp >= invite_low && hcp <= invite_high) {
    const five_plus_minors = ["D", "C"].filter((suit) => lengths[suit] >= 5);
    if (five_plus_minors.length) {
      const candidates = five_plus_minors.filter((suit) => {
        if (lengths[suit] >= 6 && prefers_minor_suit_transfer(hcp, lengths, suit, evaluation)) {
          return false;
        }
        return true;
      });
      if (candidates.length) {
        const minor = candidates.reduce((best, suit) => {
          const bestLen = lengths[best];
          const suitLen = lengths[suit];
          if (suitLen !== bestLen) {
            return suitLen > bestLen ? suit : best;
          }
          return suit === "D" ? suit : best;
        });
        const minor_bid = `3${suit_symbol(minor)}`;
        return bidRecommendation(
          minor_bid,
          `同伴开 1NT，你有 ${hcp} HCP 和 ${lengths[minor]} 张 ${SUIT_NAMES[minor]}，跳叫 ${minor_bid} 邀请 3NT。牌型：${length_text}。`,
          "1NT 后低花邀局",
        );
      }
    }
  }

  // 低花转移：单套 6+，弱牌或强牌/极不均型倾向低花定约；统一先叫 2♠。
  if (settings.transfers_enabled && !has_four_card_major) {
    const club_single = lengths.C >= 6 && lengths.D < 6;
    const diamond_single = lengths.D >= 6 && lengths.C < 6;
    if (club_single || diamond_single) {
      const minor = club_single ? "C" : "D";
      if (prefers_minor_suit_transfer(hcp, lengths, minor, evaluation)) {
        const follow_up =
          hcp > 10
            ? "同伴转叫 3♣ 后按点力继续"
            : club_single
              ? "同伴转叫 3♣ 后止叫"
              : "同伴转叫 3♣ 后再叫 3♦";
        return bidRecommendation(
          "2♠",
          `同伴开 1NT，你有 ${hcp} HCP 和 ${lengths[minor]} 张 ${SUIT_NAMES[minor]} 单套，弱牌或倾向低花定约，使用低花转移叫 2♠（${follow_up}）。牌型：${length_text}。`,
          "1NT 后低花转移",
        );
      }
    }
  }

  // >10 且未走低花转移：无四张高花时优先直接 3NT（见后方均型/兜底档）。

  // 无四张高花的均型牌：按点力 Pass / 2NT / 3NT / 4NT / 5NT。
  if (evaluation.balanced && !has_four_card_major) {
    if (hcp >= grand_invite_low) {
      return bidRecommendation(
        "5NT",
        `同伴 1NT 后，你有 ${hcp} HCP 且均型无四张高花，叫 5NT 邀请大满贯。牌型：${length_text}。`,
        "1NT 后 5NT 邀大满",
      );
    }
    if (hcp >= slam_invite_low) {
      return bidRecommendation(
        "4NT",
        `同伴 1NT 后，你有 ${hcp} HCP 且均型无四张高花，叫 4NT 邀请小满贯。牌型：${length_text}。`,
        "1NT 后 4NT 邀小满",
      );
    }
    if (hcp >= game_hcp) {
      return bidRecommendation(
        "3NT",
        `同伴 1NT 表示 15-17 均型，你有 ${hcp} HCP 且均型无四张高花，合力够局，直接叫 3NT。牌型：${length_text}。`,
        "1NT 后进局",
      );
    }
    if (hcp >= invite_low && hcp <= invite_high) {
      return bidRecommendation(
        "2NT",
        `同伴 1NT 后，你有 ${hcp} HCP 且均型无四张高花，邀请 3NT。牌型：${length_text}。`,
        "1NT 后邀局",
      );
    }
    return bidRecommendation(
      "Pass",
      `同伴 1NT 后，你有 ${hcp} HCP 且均型无四张高花，通常不足以邀局，建议 Pass。牌型：${length_text}。`,
      "1NT 后止叫",
    );
  }

  // 非均型兜底：仍按点力落无将档。
  if (hcp >= grand_invite_low) {
    return bidRecommendation(
      "5NT",
      `同伴 1NT 后，你有 ${hcp} HCP 且无需要先处理的高花，叫 5NT 邀请大满贯。牌型：${length_text}。`,
      "1NT 后 5NT 邀大满",
    );
  }
  if (hcp >= slam_invite_low) {
    return bidRecommendation(
      "4NT",
      `同伴 1NT 后，你有 ${hcp} HCP 且无需要先处理的高花，叫 4NT 邀请小满贯。牌型：${length_text}。`,
      "1NT 后 4NT 邀小满",
    );
  }
  if (hcp >= game_hcp) {
    return bidRecommendation(
      "3NT",
      `同伴 1NT 表示 15-17 均型，你有 ${hcp} HCP 且无需要先处理的高花，合力够局，直接叫 3NT。牌型：${length_text}。`,
      "1NT 后进局",
    );
  }
  if (hcp >= invite_low && hcp <= invite_high) {
    return bidRecommendation(
      "2NT",
      `同伴 1NT 后，你有 ${hcp} HCP 且无 4/5 张高花优先处理，邀请 3NT。牌型：${length_text}。`,
      "1NT 后邀局",
    );
  }
  return bidRecommendation(
    "Pass",
    `同伴 1NT 后，你有 ${hcp} HCP，通常不足以邀局，建议 Pass。牌型：${length_text}。`,
    "1NT 后止叫",
  );
}

function recommend_response_to_2nt(evaluation, settings, vulnerability) {
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const length_text = describe_lengths(evaluation);

  if (settings.transfers_enabled && lengths.H >= 5) {
    return bidRecommendation(
      "3♦",
      `同伴开 2NT，你有 ${hcp} HCP 和 5 张以上红心。简化规则使用 3♦ 转移，要求同伴转叫 3♥。牌型：${length_text}。`,
      "2NT 后红心转移",
    );
  }
  if (settings.transfers_enabled && lengths.S >= 5) {
    return bidRecommendation(
      "3♥",
      `同伴开 2NT，你有 ${hcp} HCP 和 5 张以上黑桃。简化规则使用 3♥ 转移，要求同伴转叫 3♠。牌型：${length_text}。`,
      "2NT 后黑桃转移",
    );
  }
  if (settings.stayman_enabled && (lengths.H >= 4 || lengths.S >= 4)) {
    return bidRecommendation(
      "3♣",
      `同伴开 2NT，你有 ${hcp} HCP 且至少一个 4 张高花。用 3♣ Stayman 寻找 4-4 高花配合。牌型：${length_text}。`,
      "2NT 后 Stayman",
    );
  }
  return bidRecommendation(
    "3NT",
    `同伴 2NT 表示 20-21 均型，你有 ${hcp} HCP 且无高花优先处理，直接叫 3NT 成局。牌型：${length_text}。`,
    "2NT 后进局",
  );
}

function has_suit_stopper(evaluation, suit) {
  // 简化止张：至少 2 张且含 A/K/Q 之一。
  return evaluation.lengths[suit] >= 2 && (evaluation.top_honors_by_suit[suit] || 0) >= 1;
}

const SEMI_BALANCED_SHAPES = new Set(["5-4-2-2", "6-3-2-2"]);

function shapeKeyFromLengths(lengths) {
  return Object.values(lengths)
    .slice()
    .sort((a, b) => b - a)
    .join("-");
}

function is_semi_balanced_shape(lengths) {
  return SEMI_BALANCED_SHAPES.has(shapeKeyFromLengths(lengths));
}

function has_stoppers_in_all_suits(evaluation) {
  return ["S", "H", "D", "C"].every((suit) => has_suit_stopper(evaluation, suit));
}

function qualifies_for_nt_opening_shape(evaluation) {
  if (evaluation.balanced) {
    return true;
  }
  const lengths = evaluation.lengths;
  if (lengths.S >= 6 || lengths.H >= 6) {
    return false;
  }
  return is_semi_balanced_shape(lengths) && has_stoppers_in_all_suits(evaluation);
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

function lookup_opening_principle(rule_name) {
  if (!rule_name) {
    return null;
  }
  if (OPENING_RULE_PRINCIPLES[rule_name]) {
    return OPENING_RULE_PRINCIPLES[rule_name];
  }
  const keys = Object.keys(OPENING_RULE_PRINCIPLES);
  for (let i = 0; i < keys.length; i += 1) {
    const key = keys[i];
    if (rule_name.length >= key.length && rule_name.slice(-key.length) === key) {
      return OPENING_RULE_PRINCIPLES[key];
    }
  }
  return null;
}

function with_opening_principle(explanation, rule_name) {
  const principle = lookup_opening_principle(rule_name);
  if (!principle) {
    return explanation;
  }
  return explanation + "\n\n依据原则：" + principle;
}


function preempt_overbid_allowance(vulnerability) {
  return ns_is_vulnerable(vulnerability) ? 2 : 3;
}

function preempt_min_top_honors(vulnerability) {
  return ns_is_vulnerable(vulnerability) ? 2 : 1;
}

function estimate_long_suit_playing_tricks(length) {
  return Math.max(0, length - 1);
}

function max_preempt_level_for_suit(length, vulnerability, suit) {
  if (length < 6) {
    return null;
  }
  const targetTricks = estimate_long_suit_playing_tricks(length) + preempt_overbid_allowance(vulnerability);
  let level = targetTricks - 6;
  if (level < 2) {
    return null;
  }
  if (suit === "S" || suit === "H") {
    return Math.min(level, 4);
  }
  return Math.min(level, 5);
}

function recommend_response_to_gambling_3nt(evaluation, settings) {
  // 拼搏式 3NT 应叫：Pass 打无将；4♣ Pass or correct；4♦ 问单缺；4M 自有高花成局。
  settings = settings || defaultRuleSettings();
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const length_text = describe_lengths(evaluation);

  const six_plus_majors = ["S", "H"].filter((suit) => lengths[suit] >= 6);
  if (six_plus_majors.length) {
    const major = six_plus_majors.slice().sort((a, b) => {
      if (lengths[b] !== lengths[a]) {
        return lengths[b] - lengths[a];
      }
      return (b === "S" ? 1 : 0) - (a === "S" ? 1 : 0);
    })[0];
    const major_bid = `4${suit_symbol(major)}`;
    return bidRecommendation(
      major_bid,
      `同伴拼搏式 3NT，你有 ${hcp} HCP 和 ${lengths[major]} 张 ${SUIT_NAMES[major]}，直接叫 ${major_bid} 打高花成局。牌型：${length_text}。`,
      "拼搏式 3NT 后高花成局",
    );
  }

  const both_majors_stopped = has_suit_stopper(evaluation, "H") && has_suit_stopper(evaluation, "S");
  if (both_majors_stopped) {
    if (hcp >= 16 && is_legal_response_bid("3NT", "4♦")) {
      return bidRecommendation(
        "4♦",
        `同伴拼搏式 3NT，你有 ${hcp} HCP 且两边高花有止，牌力足够用 4♦ 询问开叫者单缺、试探满贯。牌型：${length_text}。`,
        "拼搏式 3NT 后问单缺",
      );
    }
    return bidRecommendation(
      "Pass",
      `同伴拼搏式 3NT，你有 ${hcp} HCP 且两边高花有止，接受打 3NT。牌型：${length_text}。`,
      "拼搏式 3NT 后止叫",
    );
  }

  return bidRecommendation(
    "4♣",
    `同伴拼搏式 3NT，你有 ${hcp} HCP 但高花止张不足，叫 4♣（Pass or correct）转入开叫者坚固低花。牌型：${length_text}。`,
    "拼搏式 3NT 后 Pass or correct",
  );
}

function get_splinter_bid(major, splinter_suit) {
  return `3${suit_symbol(splinter_suit)}`;
}

function find_splinter_suit(major, lengths) {
  if (lengths[major] < 4) {
    return null;
  }

  for (const suit of ["S", "H", "D", "C"]) {
    if (suit !== major && lengths[suit] <= 1) {
      return suit;
    }
  }

  return null;
}

function recommend_response_to_major(major, evaluation, settings, vulnerability) {
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const length_text = describe_lengths(evaluation);
  const major_name = SUIT_NAMES[major];
  const major_bid = suit_symbol(major);
  const game_adjustment = game_threshold_adjustment(vulnerability, settings);
  const game_hcp = Math.max(11, 13 + game_adjustment);
  const has_four_card_support = lengths[major] >= 4;
  const support_count = lengths[major];

  if (support_count <= 2) {
    if (hcp < 5) {
      return bidRecommendation(
        "Pass",
        `同伴开 1${major_bid}，你只有 ${hcp} HCP 且对开叫花色支持不足，通常 Pass。牌型：${length_text}。`,
        `对 1${major_name} 不叫`,
      );
    }
    if (major === "H" && lengths.S >= 4 && hcp >= 6) {
      return bidRecommendation(
        "1♠",
        `同伴开 1♥，你有 ${hcp} HCP 且 4 张以上黑桃，应在一阶叫出 1♠。牌型：${length_text}。`,
        "一盖一应叫",
      );
    }
    if (hcp >= settings.two_over_one_min_hcp) {
      const suit = choose_two_over_one_suit(lengths, major);
      if (suit !== null) {
        return bidRecommendation(
          `2${suit_symbol(suit)}`,
          `同伴开 1${major_bid}，你有 ${hcp} HCP，达到当前 2/1 下限 ${settings.two_over_one_min_hcp} HCP，二阶新花为进局逼叫，选择较长的 ${SUIT_NAMES[suit]}。牌型：${length_text}。`,
          "2/1 进局逼叫",
        );
      }
    }
    if (hcp >= settings.forcing_nt_min_hcp && hcp <= settings.forcing_nt_max_hcp) {
      return bidRecommendation(
        "1NT",
        `同伴开 1${major_bid}，你有 ${hcp} HCP，落在当前 1NT 应叫范围 ${settings.forcing_nt_min_hcp}-${settings.forcing_nt_max_hcp} HCP 内，当前设置中 1NT 为${settings.forcing_nt_label}。牌型：${length_text}。`,
        `1NT ${settings.forcing_nt_label}`,
      );
    }
    return bidRecommendation(
      "Pass",
      `同伴开 1${major_bid}，你有 ${hcp} HCP，但既无足够支持也无合适一阶/二阶应叫，建议 Pass。牌型：${length_text}。`,
      `对 1${major_name} 不叫`,
    );
  }

  if (settings.bergen_raises_enabled) {
    if (support_count >= 5 && hcp <= 10 && is_legal_response_bid(`1${major_bid}`, `4${major_bid}`)) {
      return bidRecommendation(
        `4${major_bid}`,
        `同伴开 1${major_bid}，你有 ${hcp} HCP 且 5+ 张支持，按弱牌关煞思路直接跳到 4${major_bid}。牌型：${length_text}。`,
        "高花关煞加叫",
      );
    }

    if (settings.splinter_enabled && has_four_card_support) {
      const splinter_suit = find_splinter_suit(major, lengths);
      if (splinter_suit !== null) {
        const short_len = lengths[splinter_suit];
        const splinter_min_hcp =
          short_len === 1 ? settings.responder_splinter_min_hcp : Math.max(0, settings.responder_splinter_min_hcp - 2);
        if (hcp >= splinter_min_hcp && hcp <= settings.responder_splinter_max_hcp) {
          const splinter_bid = get_splinter_bid(major, splinter_suit);
          const splinter_suit_name = SUIT_NAMES[splinter_suit];
          const short_desc = short_len === 1 ? "单张" : "缺门";
          return bidRecommendation(
            splinter_bid,
            `同伴开 1${major_bid}，你有 ${hcp} HCP 和 4 张支持。牌型特殊：${splinter_suit_name}花${short_desc}。使用Splinter叫 ${splinter_bid}。牌型：${length_text}。`,
            "Splinter游牌加叫",
          );
        }
      }
    }

    const otherLengths = [];
    const allSuits = ["S", "H", "D", "C"];
    for (let si = 0; si < allSuits.length; si += 1) {
      if (allSuits[si] !== major) {
        otherLengths.push(lengths[allSuits[si]]);
      }
    }
    const no_shortage = Math.min.apply(null, otherLengths) >= 2;
    if (settings.jacoby_2nt_enabled && has_four_card_support && hcp >= 13 && no_shortage) {
      return bidRecommendation(
        "2NT",
        `同伴开 1${major_bid}，你有 ${hcp} HCP 和 4 张以上支持，且无单缺，按 Jacoby 2NT 表示进局逼叫支持。牌型：${length_text}。`,
        "Jacoby 2NT 支持",
      );
    }

    if (has_four_card_support) {
      if (hcp <= 6 && is_legal_response_bid(`1${major_bid}`, `3${major_bid}`)) {
        return bidRecommendation(
          `3${major_bid}`,
          `同伴开 1${major_bid}，你有 ${hcp} HCP 和 4 张支持，按弱支持跳加叫到 3${major_bid}。牌型：${length_text}。`,
          "Bergen 弱支持 (4张)",
        );
      }
      if (
        hcp >= 7 &&
        hcp <= settings.responder_bergen_weak_max &&
        !evaluation.balanced &&
        is_legal_response_bid(`1${major_bid}`, "3♣")
      ) {
        return bidRecommendation(
          "3♣",
          `同伴开 1${major_bid}，你有 ${hcp} HCP 和 4 张支持，按 Bergen 约定用 3♣ 表示弱支持且偏分布牌。牌型：${length_text}。`,
          "Bergen 弱支持 (4张)",
        );
      }
      if (hcp >= 10 && hcp <= 12 && no_shortage && is_legal_response_bid(`1${major_bid}`, "3♦")) {
        return bidRecommendation(
          "3♦",
          `同伴开 1${major_bid}，你有 ${hcp} HCP 和 4 张支持且无单缺，按 Bergen 约定用 3♦ 表示中等支持。牌型：${length_text}。`,
          "Bergen 中等支持 (4张)",
        );
      }
    }

    if (hcp >= 6 && hcp <= 9 && is_legal_response_bid(`1${major_bid}`, `2${major_bid}`)) {
      return bidRecommendation(
        `2${major_bid}`,
        `同伴开 1${major_bid}，你有 ${hcp} HCP 和 ${support_count} 张支持，简单加叫到 2${major_bid}。牌型：${length_text}。`,
        "高花简单加叫",
      );
    }
    if (hcp >= 10 && hcp <= 12 && support_count === 3 && is_legal_response_bid(`1${major_bid}`, "1NT")) {
      return bidRecommendation(
        "1NT",
        `同伴开 1${major_bid}，你有 ${hcp} HCP 且仅 3 张支持，按 Bergen 体系常用处理先叫 1NT 过渡。牌型：${length_text}。`,
        `1NT ${settings.forcing_nt_label}`,
      );
    }
    if (hcp >= 13) {
      const suit = choose_two_over_one_suit(lengths, major);
      if (suit !== null) {
        return bidRecommendation(
          `2${suit_symbol(suit)}`,
          `同伴开 1${major_bid}，你有 ${hcp} HCP，按高限进程优先新花进局逼叫。牌型：${length_text}。`,
          "2/1 进局逼叫",
        );
      }
    }
  }

  if (support_count >= 3 && hcp >= game_hcp) {
    return bidRecommendation(
      `4${major_bid}`,
      `同伴开 1${major_bid}，你有 ${hcp} HCP 和 3 张支持，合力够局，直接加叫到 4${major_bid}。牌型：${length_text}。`,
      "高花进局加叫",
    );
  }

  if (
    support_count >= 3 &&
    hcp >= settings.responder_limit_raise_min &&
    hcp <= settings.responder_limit_raise_max
  ) {
    return bidRecommendation(
      `3${major_bid}`,
      `同伴开 1${major_bid}，你有 ${hcp} HCP 和 3 张支持，属于邀局加叫，叫 3${major_bid}。牌型：${length_text}。`,
      "高花邀局加叫",
    );
  }

  const simple_low = Math.max(5, 6 + game_adjustment);
  if (support_count >= 3 && hcp >= simple_low && hcp <= settings.responder_simple_raise_max) {
    return bidRecommendation(
      `2${major_bid}`,
      `同伴开 1${major_bid}，你有 ${hcp} HCP 和 3 张支持，简单加叫到 2${major_bid}。牌型：${length_text}。`,
      "高花简单加叫",
    );
  }

  if (major === "H" && lengths.S >= 4 && hcp >= 6) {
    return bidRecommendation(
      "1♠",
      `同伴开 1♥，你有 ${hcp} HCP 且 4 张以上黑桃，应在一阶叫出 1♠。牌型：${length_text}。`,
      "一盖一应叫",
    );
  }

  if (hcp >= settings.two_over_one_min_hcp) {
    const suit = choose_two_over_one_suit(lengths, major);
    if (suit !== null) {
      return bidRecommendation(
        `2${suit_symbol(suit)}`,
        `同伴开 1${major_bid}，你有 ${hcp} HCP，达到当前 2/1 下限 ${settings.two_over_one_min_hcp} HCP，二阶新花为进局逼叫，选择较长的 ${SUIT_NAMES[suit]}。牌型：${length_text}。`,
        "2/1 进局逼叫",
      );
    }
  }

  if (hcp >= settings.forcing_nt_min_hcp && hcp <= settings.forcing_nt_max_hcp) {
    return bidRecommendation(
      "1NT",
      `同伴开 1${major_bid}，你有 ${hcp} HCP，落在当前 1NT 应叫范围 ${settings.forcing_nt_min_hcp}-${settings.forcing_nt_max_hcp} HCP 内，无足够支持，也没有可叫的一阶新高花。当前设置中 1NT 为${settings.forcing_nt_label}。牌型：${length_text}。`,
      `1NT ${settings.forcing_nt_label}`,
    );
  }

  return bidRecommendation(
    "Pass",
    `同伴开 1${major_bid}，你只有 ${hcp} HCP，且没有足够支持，通常 Pass。牌型：${length_text}。`,
    `对 1${major_name} 不叫`,
  );
}

function recommend_response_to_minor(minor, evaluation, settings, vulnerability) {
  const hcp = evaluation.hcp;
  const lengths = evaluation.lengths;
  const length_text = describe_lengths(evaluation);
  const minor_bid = suit_symbol(minor);
  const game_adjustment = game_threshold_adjustment(vulnerability, settings);
  const nt_game_hcp = Math.max(11, 13 + game_adjustment);
  const nt_invite_low = Math.max(9, 11 + game_adjustment);
  const nt_invite_high = nt_game_hcp - 1;

  if (hcp < 6) {
    return bidRecommendation(
      "Pass",
      `同伴开 1${minor_bid}，你只有 ${hcp} HCP，通常不足以应叫。牌型：${length_text}。`,
      "低花开叫后不叫",
    );
  }

  const major = choose_one_level_major_response(lengths);
  if (major !== null) {
    return bidRecommendation(
      `1${suit_symbol(major)}`,
      `同伴开 1${minor_bid}，你有 ${hcp} HCP 和 4 张以上高花，优先一阶叫出高花 ${SUIT_NAMES[major]}。牌型：${length_text}。`,
      "低花后叫高花",
    );
  }

  const minor_honors = evaluation.top_honors_by_suit[minor] || 0;
  // README：无高花时，非均型通常以 5+ 张低花支持加叫。
  const has_minor_support = lengths[minor] >= 5 || (lengths[minor] === 4 && minor_honors >= 2);

  if (!evaluation.balanced && has_minor_support) {
    if (settings.inverted_minors_enabled) {
      if (hcp <= 9) {
        return bidRecommendation(
          `3${minor_bid}`,
          `同伴开 1${minor_bid}，你有 ${hcp} HCP 且低花支持明确，按低花反加叫使用 3${minor_bid} 表示弱牌加叫。牌型：${length_text}。`,
          "低花反加叫（弱）",
        );
      }
      return bidRecommendation(
        `2${minor_bid}`,
        `同伴开 1${minor_bid}，你有 ${hcp} HCP 且低花支持明确，按低花反加叫使用 2${minor_bid} 表示逼叫一轮。牌型：${length_text}。`,
        "低花反加叫（逼叫）",
      );
    }

    // 未启用低花反加叫：按点力选择 2m / 3m / 4m / 5m / 4NT。
    if (hcp >= 6 && hcp <= 9) {
      return bidRecommendation(
        `2${minor_bid}`,
        `同伴开 1${minor_bid}，你有 ${hcp} HCP 和低花支持，作简单加叫 2${minor_bid}。牌型：${length_text}。`,
        "低花简单加叫",
      );
    }
    if (hcp >= 10 && hcp <= 12) {
      return bidRecommendation(
        `3${minor_bid}`,
        `同伴开 1${minor_bid}，你有 ${hcp} HCP 和低花支持，作限制性加叫 3${minor_bid}。牌型：${length_text}。`,
        "低花限制加叫",
      );
    }
    if (hcp >= 13 && hcp <= 15) {
      return bidRecommendation(
        `4${minor_bid}`,
        `同伴开 1${minor_bid}，你有 ${hcp} HCP 和低花支持，作邀局加叫 4${minor_bid}。牌型：${length_text}。`,
        "低花邀局加叫",
      );
    }
    if (hcp >= 16 && hcp <= 18) {
      return bidRecommendation(
        `5${minor_bid}`,
        `同伴开 1${minor_bid}，你有 ${hcp} HCP 和低花支持，直接进局 5${minor_bid}。牌型：${length_text}。`,
        "低花直接进局",
      );
    }
    if (hcp >= 19) {
      return bidRecommendation(
        "4NT",
        `同伴开 1${minor_bid}，你有 ${hcp} HCP 和低花支持，以开叫低花为将牌作 4NT 关键张问叫试探满贯。牌型：${length_text}。`,
        "低花满贯试探 4NT",
      );
    }
  }

  if (evaluation.balanced && hcp >= nt_game_hcp) {
    return bidRecommendation(
      "3NT",
      `同伴开 1${minor_bid}，你有 ${hcp} HCP，均型且无 4 张高花，合力够局，叫 3NT。牌型：${length_text}。`,
      "低花后 3NT",
    );
  }
  if (evaluation.balanced && hcp >= nt_invite_low && hcp <= nt_invite_high) {
    return bidRecommendation(
      "2NT",
      `同伴开 1${minor_bid}，你有 ${hcp} HCP，均型且无 4 张高花，邀请 3NT。牌型：${length_text}。`,
      "低花后 2NT 邀局",
    );
  }
  if (evaluation.balanced) {
    return bidRecommendation(
      "1NT",
      `同伴开 1${minor_bid}，你有 ${hcp} HCP，均型且无 4 张高花，叫 1NT。牌型：${length_text}。`,
      "低花后 1NT",
    );
  }

  return bidRecommendation(
    "1NT",
    `同伴开 1${minor_bid}，你有 ${hcp} HCP，无 4 张高花且没有更清楚的低花支持叫品，暂用 1NT 描述。牌型：${length_text}。`,
    "低花后默认 1NT",
  );
}

function recommend_response_to_strong_two_club(evaluation) {
  const length_text = describe_lengths(evaluation);
  return bidRecommendation(
    "2♦",
    `同伴强开叫 2♣，当前简化体系使用 2♦ 作为等待叫，先保留空间让开叫者描述牌型。你有 ${evaluation.hcp} HCP，牌型：${length_text}。`,
    "强 2♣ 后 2♦ 等待",
  );
}

function recommend_response_to_weak_two(opening_suit, evaluation) {
  const length_text = describe_lengths(evaluation);
  if (evaluation.hcp >= 15 && evaluation.balanced) {
    return bidRecommendation(
      "2NT",
      `同伴弱二开叫，你有 ${evaluation.hcp} HCP 且均型，当前简化体系用 2NT 作为强询问/邀局。牌型：${length_text}。`,
      "弱二后 2NT 询问",
    );
  }
  return bidRecommendation(
    "Pass",
    `同伴弱二开叫 2${suit_symbol(opening_suit)}，当前简化体系多数低限或普通牌选择 Pass。你有 ${evaluation.hcp} HCP，牌型：${length_text}。`,
    "弱二后止叫",
  );
}

function recommend_response_to_preempt(opener_bid, evaluation, settings) {
  settings = settings || defaultRuleSettings();
  const opener_contract = parse_contract_bid(opener_bid);
  const length_text = describe_lengths(evaluation);
  if (opener_contract === null) {
    return bidRecommendation(
      "Pass",
      `同伴阻击开叫后，当前简化规则建议 Pass。你有 ${evaluation.hcp} HCP，牌型：${length_text}。`,
      "阻击后止叫",
    );
  }

  const [opener_level, opener_strain] = opener_contract;
  const opener_suit = symbol_to_suit(opener_strain);
  game_threshold_adjustment(null, settings);

  if (
    settings.august_2nt_enabled &&
    opener_level === 2 &&
    ["♦", "♥", "♠"].includes(opener_strain) &&
    is_legal_response_bid(opener_bid, "2NT")
  ) {
    if (evaluation.hcp >= 11) {
      return bidRecommendation(
        "2NT",
        `同伴二阶弱开叫后，你有 ${evaluation.hcp} HCP，当前使用 Ogust 2NT 问叫，请开叫者按标准表描述低限/高限与开叫套质量。牌型：${length_text}。`,
        "Ogust 2NT 问叫",
      );
    }
  }

  if (
    evaluation.balanced &&
    evaluation.hcp >= 13 &&
    opener_level <= 3 &&
    is_legal_response_bid(opener_bid, "3NT")
  ) {
    return bidRecommendation(
      "3NT",
      `同伴阻击开叫后，你有 ${evaluation.hcp} HCP 且均型，当前简化规则优先尝试 3NT 成局。牌型：${length_text}。`,
      "阻击后 3NT",
    );
  }

  if (opener_suit !== null && evaluation.lengths[opener_suit] >= 3) {
    if (["H", "S"].includes(opener_suit) && opener_level < 4 && evaluation.hcp >= 10) {
      const bid = `4${suit_symbol(opener_suit)}`;
      if (is_legal_response_bid(opener_bid, bid)) {
        return bidRecommendation(
          bid,
          `同伴阻击开叫，你有 ${evaluation.hcp} HCP 和 ${evaluation.lengths[opener_suit]} 张支持，高花有局价值明确，抬到 ${bid}。牌型：${length_text}。`,
          "阻击后高花进局",
        );
      }
    }
    if (["C", "D"].includes(opener_suit) && opener_level < 5 && evaluation.hcp >= 10) {
      const bid = `5${suit_symbol(opener_suit)}`;
      if (is_legal_response_bid(opener_bid, bid)) {
        return bidRecommendation(
          bid,
          `同伴低花阻击开叫，你有 ${evaluation.hcp} HCP 和 ${evaluation.lengths[opener_suit]} 张支持，当前简化规则抬到低花局 ${bid}。牌型：${length_text}。`,
          "阻击后低花进局",
        );
      }
    }
    if (opener_level < 4) {
      const bid = `${opener_level + 1}${suit_symbol(opener_suit)}`;
      if (is_legal_response_bid(opener_bid, bid)) {
        return bidRecommendation(
          bid,
          `同伴阻击开叫，你有 ${evaluation.lengths[opener_suit]} 张支持，当前简化规则可小幅加阻。你有 ${evaluation.hcp} HCP，牌型：${length_text}。`,
          "阻击后加阻",
        );
      }
    }
  }

  return bidRecommendation(
    "Pass",
    `同伴阻击开叫后，当前简化规则没有明确进局或加阻条件，建议 Pass。你有 ${evaluation.hcp} HCP，牌型：${length_text}。`,
    "阻击后止叫",
  );
}

function choose_major_opening(lengths) {
  if (lengths.S >= 5 && lengths.H >= 5) {
    return "S";
  }
  if (lengths.S >= 5 && lengths.S >= lengths.H) {
    return "S";
  }
  return "H";
}

function one_nt_secondary_major_opening_bid(lengths) {
  if (lengths.S < 5 && lengths.H < 5) {
    return null;
  }
  return `1${suit_symbol(choose_major_opening(lengths))}`;
}

function has_singleton_or_void(lengths) {
  return Math.min(lengths.S, lengths.H, lengths.D, lengths.C) <= 1;
}

function choose_eleven_hcp_long_suit_with_shortage(lengths) {
  if (!has_singleton_or_void(lengths)) {
    return null;
  }
  const longSuits = ["S", "H", "D", "C"].filter((suit) => lengths[suit] >= 6);
  if (!longSuits.length) {
    return null;
  }
  return longSuits.slice().sort((a, b) => {
    if (lengths[b] !== lengths[a]) {
      return lengths[b] - lengths[a];
    }
    const rank = { S: 3, H: 2, D: 1, C: 0 };
    return rank[b] - rank[a];
  })[0];
}

function choose_eleven_hcp_two_suiter(lengths) {
  const fivePlus = ["S", "H", "D", "C"].filter((suit) => lengths[suit] >= 5);
  if (fivePlus.length < 2) {
    return null;
  }

  const suitRank = { S: 4, H: 3, D: 2, C: 1 };
  const majors = fivePlus.filter((suit) => suit === "S" || suit === "H");
  const minors = fivePlus.filter((suit) => suit === "D" || suit === "C");

  if (majors.length && minors.length) {
    const maxMinorLen = Math.max.apply(
      null,
      minors.map((suit) => lengths[suit]),
    );
    const shortMajors = majors.filter((suit) => lengths[suit] < maxMinorLen);
    if (shortMajors.length) {
      return shortMajors.slice().sort((a, b) => {
        if (lengths[a] !== lengths[b]) {
          return lengths[a] - lengths[b];
        }
        return suitRank[b] - suitRank[a];
      })[0];
    }
  }

  return fivePlus.slice().sort((a, b) => {
    if (lengths[b] !== lengths[a]) {
      return lengths[b] - lengths[a];
    }
    return suitRank[b] - suitRank[a];
  })[0];
}

function eleven_hcp_secondary_opening_bid(lengths, primarySuit) {
  if (primarySuit !== "S" && primarySuit !== "H") {
    return null;
  }
  const fivePlus = ["S", "H", "D", "C"].filter((suit) => lengths[suit] >= 5);
  if (fivePlus.length < 2) {
    return null;
  }
  const minors = fivePlus.filter((suit) => suit === "D" || suit === "C");
  if (!minors.length) {
    return null;
  }
  const longerMinor = minors.slice().sort((a, b) => {
    if (lengths[b] !== lengths[a]) {
      return lengths[b] - lengths[a];
    }
    const rank = { D: 1, C: 0 };
    return rank[b] - rank[a];
  })[0];
  if (lengths[primarySuit] < lengths[longerMinor]) {
    return `1${suit_symbol(longerMinor)}`;
  }
  return null;
}

function choose_eleven_hcp_opening(lengths) {
  const twoSuiter = choose_eleven_hcp_two_suiter(lengths);
  if (twoSuiter !== null) {
    return twoSuiter;
  }
  return choose_eleven_hcp_long_suit_with_shortage(lengths);
}

function choose_minor_opening(lengths) {
  const clubs = lengths.C;
  const diamonds = lengths.D;
  if (diamonds > clubs) {
    return "D";
  }
  if (clubs > diamonds) {
    return "C";
  }
  if (clubs === 3 && diamonds === 3) {
    return "C";
  }
  return "D";
}

function choose_weak_two(lengths, hcp, topHonorsBySuit, vulnerability) {
  if (!(hcp >= 6 && hcp <= 10)) {
    return null;
  }
  const honors = topHonorsBySuit || {};
  const minHonors = preempt_min_top_honors(vulnerability);
  const candidates = ["S", "H", "D"].filter(
    (suit) =>
      lengths[suit] >= 6 &&
      (honors[suit] || 0) >= minHonors &&
      max_preempt_level_for_suit(lengths[suit], vulnerability, suit) !== null,
  );
  if (!candidates.length) {
    return null;
  }
  return maxWeakTwoCandidate(candidates, lengths, topHonorsBySuit);
}

function choose_preempt_opening(lengths, hcp, vulnerability, topHonorsBySuit) {
  if (!(hcp >= 5 && hcp <= 10)) {
    return null;
  }
  const honors = topHonorsBySuit || {};
  const minHonors = preempt_min_top_honors(vulnerability);
  const candidates = [];
  for (const suit of ["S", "H", "D", "C"]) {
    const length = lengths[suit];
    if (length < 7 || (honors[suit] || 0) < minHonors) {
      continue;
    }
    const level = max_preempt_level_for_suit(length, vulnerability, suit);
    if (level === null || level < 3) {
      continue;
    }
    candidates.push({ suit, level });
  }
  if (!candidates.length) {
    return null;
  }
  candidates.sort((a, b) => {
    if (lengths[b.suit] !== lengths[a.suit]) {
      return lengths[b.suit] - lengths[a.suit];
    }
    const rank = { S: 3, H: 2, D: 1, C: 0 };
    if (rank[b.suit] !== rank[a.suit]) {
      return rank[b.suit] - rank[a.suit];
    }
    return b.level - a.level;
  });
  const best = candidates[0];
  return `${best.level}${suit_symbol(best.suit)}`;
}

function choose_gambling_3nt_minor(evaluation, opening_min_hcp) {
  // 拼搏式 3NT：7+ 坚固低花（含 AKQ），边张无 A/K/Q，且未达一阶开叫点力。
  if (opening_min_hcp == null) {
    opening_min_hcp = 12;
  }
  if (evaluation.hcp >= opening_min_hcp) {
    return null;
  }
  const lengths = evaluation.lengths;
  const honors = evaluation.top_honors_by_suit || {};
  const candidates = [];
  for (const suit of ["C", "D"]) {
    if (lengths[suit] < 7 || (honors[suit] || 0) < 3) {
      continue;
    }
    let outside_top = 0;
    for (const other of ["S", "H", "D", "C"]) {
      if (other !== suit) {
        outside_top += honors[other] || 0;
      }
    }
    if (outside_top === 0) {
      candidates.push(suit);
    }
  }
  if (!candidates.length) {
    return null;
  }
  return candidates.slice().sort((a, b) => {
    if (lengths[b] !== lengths[a]) {
      return lengths[b] - lengths[a];
    }
    return (b === "D" ? 1 : 0) - (a === "D" ? 1 : 0);
  })[0];
}

function choose_two_over_one_suit(lengths, excluded) {
  const candidates = ["C", "D", "H"].filter((suit) => suit !== excluded && lengths[suit] >= 4);
  if (!candidates.length) {
    return null;
  }
  return maxTwoOverOneCandidate(candidates, lengths);
}

function choose_one_level_major_response(lengths) {
  const hearts = lengths.H;
  const spades = lengths.S;
  if (hearts < 4 && spades < 4) {
    return null;
  }
  if (spades > hearts) {
    return "S";
  }
  return "H";
}

function suit_symbol(suit) {
  return { S: "♠", H: "♥", D: "♦", C: "♣" }[suit];
}

module.exports = {
  OPENING_BIDS,
  RESPONSE_BIDS,
  REBID_BIDS,
  RESPONDER_REBID_BIDS,
  STRAIN_ORDER,
  bidRecommendation,
  defaultRuleSettings,
  ns_is_vulnerable,
  game_threshold_adjustment,
  recommend_opening,
  recommend_response,
  legal_response_bids,
  legal_response_bids_with_interference,
  legal_rebid_bids,
  legal_responder_rebid_bids,
  legal_bids_after,
  is_legal_response_bid,
  parse_contract_bid,
  is_negative_double_available,
  negative_double_target_majors,
  should_make_negative_double,
  recommend_opener_rebid,
  choose_raise_level,
  choose_minor_for_major_one_nt_rebid,
  prefers_minor_suit_transfer,
  choose_second_suit,
  choose_one_level_second_suit,
  is_reverse_second_suit,
  minimum_legal_bid_for_suit,
  next_legal_contract,
  symbol_to_suit,
  recommend_responder_rebid,
  recommend_response_to_1nt,
  recommend_response_to_2nt,
  has_suit_stopper,
  qualifies_for_nt_opening_shape,
  preempt_overbid_allowance,
  preempt_min_top_honors,
  recommend_response_to_gambling_3nt,
  get_splinter_bid,
  find_splinter_suit,
  recommend_response_to_major,
  recommend_response_to_minor,
  recommend_response_to_strong_two_club,
  recommend_response_to_weak_two,
  recommend_response_to_preempt,
  choose_major_opening,
  choose_minor_opening,
  choose_weak_two,
  choose_preempt_opening,
  choose_gambling_3nt_minor,
  choose_two_over_one_suit,
  choose_one_level_major_response,
  eleven_hcp_secondary_opening_bid,
  one_nt_secondary_major_opening_bid,
  suit_symbol,
};

