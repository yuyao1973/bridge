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
  "4♥",
  "4♠",
  "5♣",
  "5♦",
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

  if (hcp >= settings.strong_two_club_min) {
    return bidRecommendation(
      "2♣",
      `${hcp} HCP，达到当前设置的强 2♣ 下限 ${settings.strong_two_club_min} HCP。牌型：${length_text}。`,
      "强 2♣",
    );
  }

  if (evaluation.balanced && hcp >= 20 && hcp <= 21) {
    return bidRecommendation(
      "2NT",
      `${hcp} HCP 且均型，符合 20-21 均型 2NT 开叫。牌型：${length_text}。`,
      "20-21 均型 2NT",
    );
  }

  if (evaluation.balanced && hcp >= settings.one_nt_min && hcp <= settings.one_nt_max) {
    const secondary = one_nt_secondary_major_opening_bid(lengths);
    if (secondary !== null) {
      return bidRecommendation(
        "1NT",
        `${hcp} HCP 且均型，优先开叫 1NT；持有 5 张高花时，开叫 ${secondary} 为次优。牌型：${length_text}。`,
        `${settings.one_nt_min}-${settings.one_nt_max} 均型 1NT`,
      );
    }
    return bidRecommendation(
      "1NT",
      `${hcp} HCP 且均型，符合当前设置的 ${settings.one_nt_min}-${settings.one_nt_max} 均型 1NT 开叫。牌型：${length_text}。`,
      `${settings.one_nt_min}-${settings.one_nt_max} 均型 1NT`,
    );
  }

  if (hcp >= settings.opening_min_hcp && (lengths.S >= 5 || lengths.H >= 5)) {
    const suit = choose_major_opening(lengths);
    return bidRecommendation(
      `1${suit_symbol(suit)}`,
      `${hcp} HCP，达到当前一阶开叫下限 ${settings.opening_min_hcp} HCP，持有 5 张以上高花，应优先开叫高花。选择 ${SUIT_NAMES[suit]}，牌型：${length_text}。`,
      "五张高花开叫",
    );
  }

  if (hcp >= settings.opening_min_hcp) {
    const suit = choose_minor_opening(lengths);
    return bidRecommendation(
      `1${suit_symbol(suit)}`,
      `${hcp} HCP，达到当前一阶开叫下限 ${settings.opening_min_hcp} HCP，没有 5 张高花，按较长低花/Better Minor 原则开叫 ${SUIT_NAMES[suit]}。牌型：${length_text}。`,
      "低花开叫",
    );
  }

  if (hcp === 11) {
    const lightSuit = choose_eleven_hcp_opening(lengths);
    if (lightSuit !== null) {
      const secondary = eleven_hcp_secondary_opening_bid(lengths, lightSuit);
      if (secondary !== null) {
        return bidRecommendation(
          `1${suit_symbol(lightSuit)}`,
          `${hcp} HCP，双套轻开叫优先开较短高花 1${suit_symbol(lightSuit)}；开叫较长低花 ${secondary} 为次优。牌型：${length_text}。`,
          "11 点轻开叫",
        );
      }
      return bidRecommendation(
        `1${suit_symbol(lightSuit)}`,
        `${hcp} HCP，符合轻开叫条件，开叫 1${suit_symbol(lightSuit)}。牌型：${length_text}。`,
        "11 点轻开叫",
      );
    }
  }

  const preempt = settings.weak_two_enabled ? choose_preempt_opening(lengths, hcp) : null;
  if (preempt !== null) {
    return bidRecommendation(
      preempt,
      `${hcp} HCP，持有长套，符合当前简化阻击叫条件，开叫 ${preempt}。牌型：${length_text}。`,
      "阻击开叫",
    );
  }

  const weak_two = settings.weak_two_enabled
    ? choose_weak_two(lengths, hcp, evaluation.top_honors_by_suit)
    : null;
  if (weak_two !== null) {
    const sixCardSuits = ["S", "H", "D", "C"].filter((suit) => lengths[suit] === 6);
    if (sixCardSuits.length >= 2) {
      return bidRecommendation(
        `2${suit_symbol(weak_two)}`,
        `${hcp} HCP，6-6 双套，按套质量开叫二阶 ${SUIT_NAMES[weak_two]}。当前训练不使用弱 2♣。牌型：${length_text}。`,
        "6-6 双套弱二",
      );
    }
    return bidRecommendation(
      `2${suit_symbol(weak_two)}`,
      `${hcp} HCP，持有 6 张 ${SUIT_NAMES[weak_two]}，可作二阶弱二开叫。当前训练不使用弱 2♣。牌型：${length_text}。`,
      "弱二开叫",
    );
  }

  return bidRecommendation(
    "Pass",
    `${hcp} HCP，未达到正常开叫条件，也不符合当前弱二规则，建议 Pass。牌型：${length_text}。`,
    "不叫",
  );
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

  if (opening_level === 1 && response_bid === "1NT" && evaluation.balanced && hcp <= 14) {
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

  if (["H", "S"].includes(response_suit) && lengths[response_suit] >= 4) {
    const level = choose_raise_level(response_level, raise_hcp);
    const bid = `${level}${suit_symbol(response_suit)}`;
    return bidRecommendation(
      bid,
      `同伴应叫 ${response_bid}，你有 ${hcp} HCP 和 ${lengths[response_suit]} 张 ${SUIT_NAMES[response_suit]} 支持，优先支持同伴高花，叫 ${bid}。牌型：${length_text}。`,
      "支持同伴高花",
    );
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

  const opener_length = opener_suit !== null ? lengths[opener_suit] : 0;
  const has_singleton_or_void = Math.min(lengths.S, lengths.H, lengths.D, lengths.C) <= 1;
  if (
    opening_level === 1 &&
    response_level === 1 &&
    hcp >= 12 &&
    hcp <= 14 &&
    opener_length <= 5 &&
    !has_singleton_or_void &&
    is_legal_response_bid(response_bid, "1NT")
  ) {
    const one_level_second_suit = choose_one_level_second_suit(lengths, opener_suit, response_suit, response_bid);
    if (one_level_second_suit === null) {
      return bidRecommendation(
        "1NT",
        `你有 ${hcp} HCP，一阶开叫后同伴一阶应叫；牌型无单缺且开叫套不超过 5 张，当前没有可叫的一阶第二套，优先再叫 1NT 表示低限并控制叫牌高度。牌型：${length_text}。`,
        "一阶序列低限再叫 1NT",
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
  if (settings.stayman_enabled && hcp >= 8 && (lengths.H >= 4 || lengths.S >= 4)) {
    return bidRecommendation(
      "2♣",
      `同伴开 1NT，你有 ${hcp} HCP 且至少一个 4 张高花。用 2♣ Stayman 寻找 4-4 高花配合。牌型：${length_text}。`,
      "Stayman",
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

function choose_weak_two(lengths, hcp, topHonorsBySuit) {
  if (!(hcp >= 6 && hcp <= 10)) {
    return null;
  }
  const candidates = ["S", "H", "D"].filter((suit) => lengths[suit] >= 6);
  if (!candidates.length) {
    return null;
  }
  return maxWeakTwoCandidate(candidates, lengths, topHonorsBySuit);
}

function choose_preempt_opening(lengths, hcp) {
  if (!(hcp >= 5 && hcp <= 10)) {
    return null;
  }
  const suit = maxPreemptCandidate(lengths);
  const length = lengths[suit];
  if (length >= 8 && ["C", "D"].includes(suit) && hcp >= 8) {
    return `5${suit_symbol(suit)}`;
  }
  if (length >= 8) {
    return `4${suit_symbol(suit)}`;
  }
  if (length >= 7) {
    return `3${suit_symbol(suit)}`;
  }
  return null;
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
  choose_second_suit,
  choose_one_level_second_suit,
  is_reverse_second_suit,
  minimum_legal_bid_for_suit,
  next_legal_contract,
  symbol_to_suit,
  recommend_responder_rebid,
  recommend_response_to_1nt,
  recommend_response_to_2nt,
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
  choose_two_over_one_suit,
  choose_one_level_major_response,
  eleven_hcp_secondary_opening_bid,
  one_nt_secondary_major_opening_bid,
  suit_symbol,
};

