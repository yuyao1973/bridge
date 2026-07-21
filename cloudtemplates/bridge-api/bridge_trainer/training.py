from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from .bidding import (
    OPENING_BIDS,
    REBID_BIDS,
    RESPONSE_BIDS,
    RESPONDER_REBID_BIDS,
    BidRecommendation,
    RuleSettings,
    default_rule_settings,
    legal_response_bids,
    legal_rebid_bids,
    legal_responder_rebid_bids,
    parse_contract_bid,
    recommend_opening,
    recommend_opener_rebid,
    recommend_responder_rebid,
    recommend_response,
)
from .cards import Hand, deal, new_deck, sort_hand
from .evaluator import HandEvaluation, evaluate_hand


ONE_LEVEL_OPENINGS = {"1♣", "1♦", "1♥", "1♠", "1NT"}
STRONG_OPENINGS = {"2♣", "2NT"}
PREEMPT_OPENINGS = {"2♦", "2♥", "2♠", "3♣", "3♦", "3♥", "3♠", "4♣", "4♦", "4♥", "4♠", "5♣", "5♦"}
SUPPORTED_FILTER_OPENINGS = ONE_LEVEL_OPENINGS | STRONG_OPENINGS | PREEMPT_OPENINGS
DEFAULT_SEARCH_ATTEMPTS = 2_000
OPENING_FILTER_SEARCH_ATTEMPTS = 5_000
RESPONSE_FILTER_SEARCH_ATTEMPTS = 15_000
REBID_FILTER_SEARCH_ATTEMPTS = 40_000
DIRECTED_OPENER_REBID_SEARCH_ATTEMPTS = 120_000
DIRECTED_RESPONDER_REBID_SEARCH_ATTEMPTS = 180_000
# Cap "should Pass" opening deals (below opening strength and no weak/preempt).
# Use integer modulo (not Random(seed).random()) so sequential seeds stay unbiased.
OPENING_PASS_MAX_RATE = 0.09
OPENING_PASS_RATE_DENOM = 100
OPENING_PASS_RATE_NUM = 9
OPENING_DEAL_SEARCH_ATTEMPTS = 50

DIRECTED_OPENER_REBID_SEQUENCES: set[tuple[str, str]] = {
    ("1NT", "2♣"),
    ("1NT", "2♦"),
    ("1NT", "2♥"),
    ("2NT", "3♣"),
    ("2NT", "3♦"),
    ("2NT", "3♥"),
    ("1♥", "2NT"),
    ("1♠", "2NT"),
}

DIRECTED_RESPONDER_REBID_SEQUENCES: set[tuple[str, str, str]] = {
    ("1NT", "2♣", "2♦"),
    ("1NT", "2♣", "2♥"),
    ("1NT", "2♣", "2♠"),
    ("1NT", "2♦", "2♥"),
    ("1NT", "2♥", "2♠"),
    ("1♥", "2NT", "4♥"),
    ("1♠", "2NT", "4♠"),
}


@dataclass(frozen=True)
class TrainingQuestion:
    hand: Hand
    evaluation: HandEvaluation
    recommendation: BidRecommendation
    vulnerability: str
    choices: list[str]
    legal_choices: list[str]
    acceptable_bids: list[str]
    mode: str
    position: str = "南"
    auction: str = "第一家开叫"
    opener_bid: str | None = None
    response_bid: str | None = None
    opener_rebid_bid: str | None = None


def _is_balanced_nt_opening(evaluation: HandEvaluation, settings: RuleSettings, nt_level: int) -> bool:
    if nt_level == 1:
        return evaluation.balanced and settings.one_nt_min <= evaluation.hcp <= settings.one_nt_max
    if nt_level == 2:
        return evaluation.balanced and 20 <= evaluation.hcp <= 21
    return False


def matches_common_opener_rebid_prefilter(
    opener_bid: str | None,
    response_bid: str | None,
    opener_evaluation: HandEvaluation,
    responder_evaluation: HandEvaluation,
    settings: RuleSettings,
) -> bool:
    if opener_bid is None or response_bid is None:
        return True

    responder_lengths = responder_evaluation.lengths
    opener_lengths = opener_evaluation.lengths

    if opener_bid == "1NT" and response_bid == "2♣":
        return _is_balanced_nt_opening(opener_evaluation, settings, 1) and responder_evaluation.hcp >= 8 and (
            responder_lengths["H"] >= 4 or responder_lengths["S"] >= 4
        )
    if opener_bid == "1NT" and response_bid == "2♦":
        return _is_balanced_nt_opening(opener_evaluation, settings, 1) and settings.transfers_enabled and responder_lengths["H"] >= 5
    if opener_bid == "1NT" and response_bid == "2♥":
        return _is_balanced_nt_opening(opener_evaluation, settings, 1) and settings.transfers_enabled and responder_lengths["S"] >= 5
    if opener_bid == "2NT" and response_bid == "3♣":
        return _is_balanced_nt_opening(opener_evaluation, settings, 2) and (
            responder_lengths["H"] >= 4 or responder_lengths["S"] >= 4
        )
    if opener_bid == "2NT" and response_bid == "3♦":
        return _is_balanced_nt_opening(opener_evaluation, settings, 2) and settings.transfers_enabled and responder_lengths["H"] >= 5
    if opener_bid == "2NT" and response_bid == "3♥":
        return _is_balanced_nt_opening(opener_evaluation, settings, 2) and settings.transfers_enabled and responder_lengths["S"] >= 5
    if opener_bid == "1♥" and response_bid == "2NT":
        return settings.jacoby_2nt_enabled and opener_lengths["H"] >= 5 and responder_lengths["H"] >= 4 and responder_evaluation.hcp >= 12
    if opener_bid == "1♠" and response_bid == "2NT":
        return settings.jacoby_2nt_enabled and opener_lengths["S"] >= 5 and responder_lengths["S"] >= 4 and responder_evaluation.hcp >= 12

    return True


def matches_common_responder_rebid_prefilter(
    opener_bid: str | None,
    response_bid: str | None,
    opener_rebid_bid: str | None,
    opener_evaluation: HandEvaluation,
    responder_evaluation: HandEvaluation,
    settings: RuleSettings,
) -> bool:
    if opener_bid is None or response_bid is None:
        return True

    responder_lengths = responder_evaluation.lengths
    opener_lengths = opener_evaluation.lengths

    if opener_bid == "1NT" and response_bid == "2♣":
        if not (_is_balanced_nt_opening(opener_evaluation, settings, 1) and responder_evaluation.hcp >= 8 and (responder_lengths["H"] >= 4 or responder_lengths["S"] >= 4)):
            return False
        if opener_rebid_bid == "2♥":
            return opener_lengths["H"] >= 4
        if opener_rebid_bid == "2♠":
            return opener_lengths["H"] < 4 and opener_lengths["S"] >= 4
        if opener_rebid_bid == "2♦":
            return opener_lengths["H"] < 4 and opener_lengths["S"] < 4
        return True

    if opener_bid == "1NT" and response_bid == "2♦":
        return (
            _is_balanced_nt_opening(opener_evaluation, settings, 1)
            and settings.transfers_enabled
            and responder_lengths["H"] >= 5
            and (opener_rebid_bid is None or opener_rebid_bid == "2♥")
        )

    if opener_bid == "1NT" and response_bid == "2♥":
        return (
            _is_balanced_nt_opening(opener_evaluation, settings, 1)
            and settings.transfers_enabled
            and responder_lengths["S"] >= 5
            and (opener_rebid_bid is None or opener_rebid_bid == "2♠")
        )

    if opener_bid == "1♥" and response_bid == "2NT":
        if not (settings.jacoby_2nt_enabled and opener_lengths["H"] >= 5 and responder_lengths["H"] >= 4 and responder_evaluation.hcp >= 12):
            return False
        return opener_rebid_bid != "4♥" or opener_lengths["H"] >= 5

    if opener_bid == "1♠" and response_bid == "2NT":
        if not (settings.jacoby_2nt_enabled and opener_lengths["S"] >= 5 and responder_lengths["S"] >= 4 and responder_evaluation.hcp >= 12):
            return False
        return opener_rebid_bid != "4♠" or opener_lengths["S"] >= 5

    return True


def search_attempt_budget(
    opener_bid: str | None = None,
    response_bid: str | None = None,
    opener_rebid_bid: str | None = None,
) -> int:
    attempts = DEFAULT_SEARCH_ATTEMPTS
    if opener_bid is not None:
        attempts = max(attempts, OPENING_FILTER_SEARCH_ATTEMPTS)
    if response_bid is not None:
        attempts = max(attempts, RESPONSE_FILTER_SEARCH_ATTEMPTS)
    if opener_rebid_bid is not None:
        attempts = max(attempts, REBID_FILTER_SEARCH_ATTEMPTS)
    return attempts


def directed_sequence_attempt_budget(
    opener_bid: str | None = None,
    response_bid: str | None = None,
    opener_rebid_bid: str | None = None,
) -> int:
    attempts = search_attempt_budget(opener_bid=opener_bid, response_bid=response_bid, opener_rebid_bid=opener_rebid_bid)
    if opener_bid is not None and response_bid is not None:
        if opener_rebid_bid is None and (opener_bid, response_bid) in DIRECTED_OPENER_REBID_SEQUENCES:
            attempts = max(attempts, DIRECTED_OPENER_REBID_SEARCH_ATTEMPTS)
        if opener_rebid_bid is not None and (opener_bid, response_bid, opener_rebid_bid) in DIRECTED_RESPONDER_REBID_SEQUENCES:
            attempts = max(attempts, DIRECTED_RESPONDER_REBID_SEARCH_ATTEMPTS)
    return attempts


def iter_role_pairs(hands: dict[str, Hand], prioritize_sequence: bool, default_opener: str, default_responder: str) -> list[tuple[Hand, Hand]]:
    pairs: list[tuple[Hand, Hand]] = [(hands[default_opener], hands[default_responder])]
    if not prioritize_sequence:
        return pairs

    positions = list(hands.keys())
    for opener_pos in positions:
        for responder_pos in positions:
            if opener_pos == responder_pos:
                continue
            opener_hand = hands[opener_pos]
            responder_hand = hands[responder_pos]
            if any(existing_opener is opener_hand and existing_responder is responder_hand for existing_opener, existing_responder in pairs):
                continue
            pairs.append((opener_hand, responder_hand))
    return pairs


HandConstraint = Callable[[Hand], bool]


def deal_targeted(
    opener_constraint: HandConstraint,
    responder_constraint: HandConstraint,
    seed: int,
    max_opener_attempts: int = 3_000,
    max_responder_attempts: int = 500,
) -> tuple[Hand, Hand] | None:
    """Fast path: build (opener_hand, responder_hand) both satisfying shape/HCP constraints."""
    rng = random.Random(seed)
    deck = new_deck()
    for _ in range(max_opener_attempts):
        rng.shuffle(deck)
        opener_hand = sort_hand(deck[:13])
        if not opener_constraint(opener_hand):
            continue
        remaining = list(deck[13:])
        for _ in range(max_responder_attempts):
            rng.shuffle(remaining)
            responder_hand = sort_hand(remaining[:13])
            if responder_constraint(responder_hand):
                return opener_hand, responder_hand
    return None


def get_sequence_constraints(
    opener_bid: str | None,
    response_bid: str | None,
    opener_rebid_bid: str | None,
    settings: RuleSettings,
) -> tuple[HandConstraint, HandConstraint] | None:
    """Return (opener_constraint, responder_constraint) for a known directed sequence, or None."""
    if opener_bid is None or response_bid is None:
        return None

    def nt1(hand: Hand) -> bool:
        ev = evaluate_hand(hand)
        return ev.balanced and settings.one_nt_min <= ev.hcp <= settings.one_nt_max

    def nt1_no_major(hand: Hand) -> bool:
        ev = evaluate_hand(hand)
        return ev.balanced and settings.one_nt_min <= ev.hcp <= settings.one_nt_max and ev.lengths["H"] < 4 and ev.lengths["S"] < 4

    def nt1_four_hearts(hand: Hand) -> bool:
        ev = evaluate_hand(hand)
        return ev.balanced and settings.one_nt_min <= ev.hcp <= settings.one_nt_max and ev.lengths["H"] >= 4

    def nt1_four_spades_no_hearts(hand: Hand) -> bool:
        ev = evaluate_hand(hand)
        return ev.balanced and settings.one_nt_min <= ev.hcp <= settings.one_nt_max and ev.lengths["S"] >= 4 and ev.lengths["H"] < 4

    def nt2(hand: Hand) -> bool:
        ev = evaluate_hand(hand)
        return ev.balanced and 20 <= ev.hcp <= 21

    def stayman_responder(hand: Hand) -> bool:
        ev = evaluate_hand(hand)
        return ev.hcp >= 8 and (ev.lengths["H"] >= 4 or ev.lengths["S"] >= 4)

    def transfer_hearts_responder(hand: Hand) -> bool:
        return evaluate_hand(hand).lengths["H"] >= 5

    def transfer_spades_responder(hand: Hand) -> bool:
        return evaluate_hand(hand).lengths["S"] >= 5

    def hearts5_opener(hand: Hand) -> bool:
        ev = evaluate_hand(hand)
        return ev.lengths["H"] >= 5 and 12 <= ev.hcp <= 21

    def spades5_opener(hand: Hand) -> bool:
        ev = evaluate_hand(hand)
        return ev.lengths["S"] >= 5 and 12 <= ev.hcp <= 21

    def jacoby_hearts_responder(hand: Hand) -> bool:
        ev = evaluate_hand(hand)
        return ev.hcp >= 12 and ev.lengths["H"] >= 4

    def jacoby_spades_responder(hand: Hand) -> bool:
        ev = evaluate_hand(hand)
        return ev.hcp >= 12 and ev.lengths["S"] >= 4

    if opener_rebid_bid is None:
        # 2-bid sequences: opener rebid training
        if opener_bid == "1NT" and response_bid == "2\u2663":
            return nt1, stayman_responder
        if opener_bid == "1NT" and response_bid == "2\u2666" and settings.transfers_enabled:
            return nt1, transfer_hearts_responder
        if opener_bid == "1NT" and response_bid == "2\u2665" and settings.transfers_enabled:
            return nt1, transfer_spades_responder
        if opener_bid == "2NT" and response_bid == "3\u2663":
            return nt2, stayman_responder
        if opener_bid == "2NT" and response_bid == "3\u2666" and settings.transfers_enabled:
            return nt2, transfer_hearts_responder
        if opener_bid == "2NT" and response_bid == "3\u2665" and settings.transfers_enabled:
            return nt2, transfer_spades_responder
        if opener_bid == "1\u2665" and response_bid == "2NT" and settings.jacoby_2nt_enabled:
            return hearts5_opener, jacoby_hearts_responder
        if opener_bid == "1\u2660" and response_bid == "2NT" and settings.jacoby_2nt_enabled:
            return spades5_opener, jacoby_spades_responder
    else:
        # 3-bid sequences: responder rebid training
        if opener_bid == "1NT" and response_bid == "2\u2663":
            if opener_rebid_bid == "2\u2666":
                return nt1_no_major, stayman_responder
            if opener_rebid_bid == "2\u2665":
                return nt1_four_hearts, stayman_responder
            if opener_rebid_bid == "2\u2660":
                return nt1_four_spades_no_hearts, stayman_responder
        if opener_bid == "1NT" and response_bid == "2\u2666" and settings.transfers_enabled:
            return nt1, transfer_hearts_responder
        if opener_bid == "1NT" and response_bid == "2\u2665" and settings.transfers_enabled:
            return nt1, transfer_spades_responder
        if opener_bid == "1\u2665" and response_bid == "2NT" and settings.jacoby_2nt_enabled:
            return hearts5_opener, jacoby_hearts_responder
        if opener_bid == "1\u2660" and response_bid == "2NT" and settings.jacoby_2nt_enabled:
            return spades5_opener, jacoby_spades_responder

    return None


def _build_opening_question(seed: int, settings: RuleSettings) -> TrainingQuestion:
    hands = deal(seed)
    hand = hands["S"]
    evaluation = evaluate_hand(hand)
    vulnerability = choose_vulnerability(seed)
    recommendation = recommend_opening(evaluation, settings, vulnerability)
    return TrainingQuestion(
        hand=hand,
        evaluation=evaluation,
        recommendation=recommendation,
        vulnerability=vulnerability,
        choices=OPENING_BIDS,
        legal_choices=OPENING_BIDS,
        acceptable_bids=build_acceptable_bids(
            recommendation.bid,
            OPENING_BIDS,
            mode="opening",
        ),
        mode="开叫训练",
    )


def generate_opening_question(seed: int | None = None, settings: RuleSettings | None = None) -> TrainingQuestion:
    settings = settings or default_rule_settings()
    base_seed = seed if seed is not None else random.randint(1, 1_000_000_000)
    prefer_pass = (abs(base_seed) % OPENING_PASS_RATE_DENOM) < OPENING_PASS_RATE_NUM

    fallback: TrainingQuestion | None = None
    if prefer_pass:
        for offset in range(OPENING_DEAL_SEARCH_ATTEMPTS):
            question = _build_opening_question(base_seed + offset, settings)
            if fallback is None:
                fallback = question
            if question.recommendation.bid == "Pass":
                return question
        return fallback  # type: ignore[return-value]

    for offset in range(OPENING_DEAL_SEARCH_ATTEMPTS):
        question = _build_opening_question(base_seed + offset, settings)
        if fallback is None:
            fallback = question
        if question.recommendation.bid != "Pass":
            return question
    return fallback  # type: ignore[return-value]


def generate_response_question(
    seed: int | None = None,
    opener_bid: str | None = None,
    settings: RuleSettings | None = None,
    opener_category: str | None = None,
) -> TrainingQuestion:
    settings = settings or default_rule_settings()
    supported_openings = supported_openings_for_category(opener_category)
    if opener_bid is not None and opener_bid not in supported_openings:
        opener_bid = None
    base_seed = seed if seed is not None else 1
    attempts = search_attempt_budget(opener_bid=opener_bid)

    for offset in range(attempts):
        hands = deal(base_seed + offset)
        vulnerability = choose_vulnerability(base_seed + offset)
        opener_evaluation = evaluate_hand(hands["N"])
        opener_recommendation = recommend_opening(opener_evaluation, settings, vulnerability)
        if opener_recommendation.bid not in supported_openings:
            continue
        if opener_bid is not None and opener_recommendation.bid != opener_bid:
            continue

        hand = hands["S"]
        evaluation = evaluate_hand(hand)
        recommendation = recommend_response(opener_recommendation.bid, evaluation, settings, vulnerability)
        return TrainingQuestion(
            hand=hand,
            evaluation=evaluation,
            recommendation=recommendation,
            vulnerability=vulnerability,
            choices=RESPONSE_BIDS,
            legal_choices=legal_response_bids(opener_recommendation.bid),
            acceptable_bids=build_acceptable_bids(
                recommendation.bid,
                legal_response_bids(opener_recommendation.bid),
                mode="response",
                opener_bid=opener_recommendation.bid,
            ),
            mode="应叫训练",
            auction=f"{opener_recommendation.bid}-?",
            opener_bid=opener_recommendation.bid,
        )

    return generate_opening_question(seed, settings)


def generate_opener_rebid_question(
    seed: int | None = None,
    settings: RuleSettings | None = None,
    opener_bid: str | None = None,
    opener_category: str | None = None,
    response_bid: str | None = None,
) -> TrainingQuestion:
    settings = settings or default_rule_settings()
    supported_openings = supported_openings_for_category(opener_category)
    if opener_bid is not None and opener_bid not in supported_openings:
        opener_bid = None
    if opener_bid is not None and response_bid is not None and response_bid not in legal_response_bids(opener_bid):
        response_bid = None
    base_seed = seed if seed is not None else 1
    attempts = directed_sequence_attempt_budget(opener_bid=opener_bid, response_bid=response_bid)
    prioritize_sequence = opener_bid is not None and response_bid is not None

    # Fast path: construct hand pair directly from shape/HCP constraints for known sequences
    if prioritize_sequence:
        _constraints = get_sequence_constraints(opener_bid, response_bid, None, settings)
        if _constraints is not None:
            _opener_c, _responder_c = _constraints
            _targeted = deal_targeted(_opener_c, _responder_c, base_seed)
            if _targeted is not None:
                _opener_hand, _responder_hand = _targeted
                _vuln = choose_vulnerability(base_seed)
                _opener_eval = evaluate_hand(_opener_hand)
                _open_rec = recommend_opening(_opener_eval, settings, _vuln)
                if _open_rec.bid == opener_bid:
                    _resp_eval = evaluate_hand(_responder_hand)
                    _resp_rec = recommend_response(_open_rec.bid, _resp_eval, settings, _vuln)
                    if _resp_rec.bid == response_bid:
                        _rebid_rec = recommend_opener_rebid(
                            _open_rec.bid, _resp_rec.bid, _opener_eval, settings, _vuln
                        )
                        return TrainingQuestion(
                            hand=_opener_hand,
                            evaluation=_opener_eval,
                            recommendation=_rebid_rec,
                            vulnerability=_vuln,
                            choices=REBID_BIDS,
                            legal_choices=legal_rebid_bids(_resp_rec.bid),
                            acceptable_bids=build_acceptable_bids(
                                _rebid_rec.bid,
                                legal_rebid_bids(_resp_rec.bid),
                                mode="opener_rebid",
                                opener_bid=_open_rec.bid,
                                response_bid=_resp_rec.bid,
                            ),
                            mode="开叫者再叫训练",
                            auction=f"{_open_rec.bid}-{_resp_rec.bid}-? ",
                            opener_bid=_open_rec.bid,
                            response_bid=_resp_rec.bid,
                        )

    for offset in range(attempts):
        hands = deal(base_seed + offset)
        vulnerability = choose_vulnerability(base_seed + offset)
        for opener_hand, responder_hand in iter_role_pairs(hands, prioritize_sequence, default_opener="S", default_responder="N"):
            opener_evaluation = evaluate_hand(opener_hand)
            opening_recommendation = recommend_opening(opener_evaluation, settings, vulnerability)
            if opening_recommendation.bid not in supported_openings:
                continue
            if opener_bid is not None and opening_recommendation.bid != opener_bid:
                continue

            responder_evaluation = evaluate_hand(responder_hand)
            if not matches_common_opener_rebid_prefilter(
                opener_bid,
                response_bid,
                opener_evaluation,
                responder_evaluation,
                settings,
            ):
                continue
            response_recommendation = recommend_response(
                opening_recommendation.bid,
                responder_evaluation,
                settings,
                vulnerability,
            )
            if response_recommendation.bid == "Pass" and opening_recommendation.bid not in PREEMPT_OPENINGS:
                continue
            if response_bid is not None and response_recommendation.bid != response_bid:
                continue

            recommendation = recommend_opener_rebid(
                opening_recommendation.bid,
                response_recommendation.bid,
                opener_evaluation,
                settings,
                vulnerability,
            )
            return TrainingQuestion(
                hand=opener_hand,
                evaluation=opener_evaluation,
                recommendation=recommendation,
                vulnerability=vulnerability,
                choices=REBID_BIDS,
                legal_choices=legal_rebid_bids(response_recommendation.bid),
                acceptable_bids=build_acceptable_bids(
                    recommendation.bid,
                    legal_rebid_bids(response_recommendation.bid),
                    mode="opener_rebid",
                    opener_bid=opening_recommendation.bid,
                    response_bid=response_recommendation.bid,
                ),
                mode="开叫者再叫训练",
                auction=f"{opening_recommendation.bid}-{response_recommendation.bid}-? ",
                opener_bid=opening_recommendation.bid,
                response_bid=response_recommendation.bid,
            )

    if response_bid is not None:
        return generate_opener_rebid_question(
            seed,
            settings,
            opener_bid,
            opener_category,
            response_bid=None,
        )

    return generate_response_question(seed, opener_bid, settings, opener_category)


def generate_responder_rebid_question(
    seed: int | None = None,
    settings: RuleSettings | None = None,
    opener_bid: str | None = None,
    opener_category: str | None = None,
    response_bid: str | None = None,
    opener_rebid_bid: str | None = None,
) -> TrainingQuestion:
    settings = settings or default_rule_settings()
    supported_openings = supported_openings_for_category(opener_category)
    if opener_bid is not None and opener_bid not in supported_openings:
        opener_bid = None
    if opener_bid is not None and response_bid is not None and response_bid not in legal_response_bids(opener_bid):
        response_bid = None
    if response_bid is not None and opener_rebid_bid is not None and opener_rebid_bid not in legal_rebid_bids(response_bid):
        opener_rebid_bid = None
    base_seed = seed if seed is not None else 1
    attempts = directed_sequence_attempt_budget(
        opener_bid=opener_bid,
        response_bid=response_bid,
        opener_rebid_bid=opener_rebid_bid,
    )
    prioritize_sequence = opener_bid is not None and response_bid is not None and opener_rebid_bid is not None

    # Fast path: construct hand pair directly from shape/HCP constraints for known sequences
    if prioritize_sequence:
        _constraints = get_sequence_constraints(opener_bid, response_bid, opener_rebid_bid, settings)
        if _constraints is not None:
            _opener_c, _responder_c = _constraints
            _targeted = deal_targeted(_opener_c, _responder_c, base_seed)
            if _targeted is not None:
                _opener_hand, _responder_hand = _targeted
                _vuln = choose_vulnerability(base_seed)
                _opener_eval = evaluate_hand(_opener_hand)
                _resp_eval = evaluate_hand(_responder_hand)
                _open_rec = recommend_opening(_opener_eval, settings, _vuln)
                if _open_rec.bid == opener_bid:
                    _resp_rec = recommend_response(_open_rec.bid, _resp_eval, settings, _vuln)
                    if _resp_rec.bid == response_bid:
                        _rebid_rec = recommend_opener_rebid(
                            _open_rec.bid, _resp_rec.bid, _opener_eval, settings, _vuln
                        )
                        if _rebid_rec.bid == opener_rebid_bid:
                            _final_rec = recommend_responder_rebid(
                                _open_rec.bid, _resp_rec.bid, _rebid_rec.bid,
                                _resp_eval, settings, _vuln,
                            )
                            return TrainingQuestion(
                                hand=_responder_hand,
                                evaluation=_resp_eval,
                                recommendation=_final_rec,
                                vulnerability=_vuln,
                                choices=RESPONDER_REBID_BIDS,
                                legal_choices=legal_responder_rebid_bids(_rebid_rec.bid),
                                acceptable_bids=build_acceptable_bids(
                                    _final_rec.bid,
                                    legal_responder_rebid_bids(_rebid_rec.bid),
                                    mode="responder_rebid",
                                    opener_bid=_open_rec.bid,
                                    response_bid=_resp_rec.bid,
                                    opener_rebid_bid=_rebid_rec.bid,
                                ),
                                mode="应叫者第二次应叫训练",
                                auction=(
                                    f"{_open_rec.bid}-Pass-{_resp_rec.bid}-Pass-{_rebid_rec.bid}-Pass-? "
                                ),
                                opener_bid=_open_rec.bid,
                                response_bid=_resp_rec.bid,
                                opener_rebid_bid=_rebid_rec.bid,
                            )

    for offset in range(attempts):
        hands = deal(base_seed + offset)
        vulnerability = choose_vulnerability(base_seed + offset)
        for opener_hand, responder_hand in iter_role_pairs(hands, prioritize_sequence, default_opener="N", default_responder="S"):
            opener_evaluation = evaluate_hand(opener_hand)
            responder_evaluation = evaluate_hand(responder_hand)

            if not matches_common_responder_rebid_prefilter(
                opener_bid,
                response_bid,
                opener_rebid_bid,
                opener_evaluation,
                responder_evaluation,
                settings,
            ):
                continue

            opening_recommendation = recommend_opening(opener_evaluation, settings, vulnerability)
            if opening_recommendation.bid not in supported_openings:
                continue
            if opener_bid is not None and opening_recommendation.bid != opener_bid:
                continue

            response_recommendation = recommend_response(
                opening_recommendation.bid,
                responder_evaluation,
                settings,
                vulnerability,
            )
            if response_recommendation.bid == "Pass":
                continue
            if response_bid is not None and response_recommendation.bid != response_bid:
                continue

            opener_rebid_recommendation = recommend_opener_rebid(
                opening_recommendation.bid,
                response_recommendation.bid,
                opener_evaluation,
                settings,
                vulnerability,
            )
            if opener_rebid_recommendation.bid == "Pass":
                continue
            if opener_rebid_bid is not None and opener_rebid_recommendation.bid != opener_rebid_bid:
                continue

            recommendation = recommend_responder_rebid(
                opening_recommendation.bid,
                response_recommendation.bid,
                opener_rebid_recommendation.bid,
                responder_evaluation,
                settings,
                vulnerability,
            )
            return TrainingQuestion(
                hand=responder_hand,
                evaluation=responder_evaluation,
                recommendation=recommendation,
                vulnerability=vulnerability,
                choices=RESPONDER_REBID_BIDS,
                legal_choices=legal_responder_rebid_bids(opener_rebid_recommendation.bid),
                acceptable_bids=build_acceptable_bids(
                    recommendation.bid,
                    legal_responder_rebid_bids(opener_rebid_recommendation.bid),
                    mode="responder_rebid",
                    opener_bid=opening_recommendation.bid,
                    response_bid=response_recommendation.bid,
                    opener_rebid_bid=opener_rebid_recommendation.bid,
                ),
                mode="应叫者第二次应叫训练",
                auction=(
                    f"{opening_recommendation.bid}-Pass-{response_recommendation.bid}-Pass-{opener_rebid_recommendation.bid}-Pass-? "
                ),
                opener_bid=opening_recommendation.bid,
                response_bid=response_recommendation.bid,
                opener_rebid_bid=opener_rebid_recommendation.bid,
            )

    if opener_rebid_bid is not None:
        return generate_responder_rebid_question(
            seed,
            settings,
            opener_bid,
            opener_category,
            response_bid=response_bid,
            opener_rebid_bid=None,
        )

    if response_bid is not None:
        return generate_responder_rebid_question(
            seed,
            settings,
            opener_bid,
            opener_category,
            response_bid=None,
            opener_rebid_bid=None,
        )

    return generate_response_question(seed, None, settings, opener_category)


def supported_openings_for_category(opener_category: str | None) -> set[str]:
    if opener_category == "一阶定约":
        return set(ONE_LEVEL_OPENINGS)
    if opener_category == "强开叫":
        return set(STRONG_OPENINGS)
    if opener_category == "阻击叫":
        return set(PREEMPT_OPENINGS)
    return set(SUPPORTED_FILTER_OPENINGS)


def choose_vulnerability(seed: int | None = None) -> str:
    options = ["双方无局", "南北有局", "东西有局", "双方有局"]
    if seed is None:
        import random

        return random.choice(options)
    return options[seed % len(options)]


def build_acceptable_bids(
    recommended_bid: str,
    legal_choices: list[str],
    mode: str,
    opener_bid: str | None = None,
    response_bid: str | None = None,
    opener_rebid_bid: str | None = None,
) -> list[str]:
    accepted: list[str] = []
    if recommended_bid in legal_choices:
        accepted.append(recommended_bid)
    if recommended_bid == "Pass":
        return accepted or ["Pass"]

    recommended_contract = parse_contract_bid(recommended_bid)
    if recommended_contract is None:
        return accepted or [recommended_bid]

    rec_level, rec_strain = recommended_contract
    opener_contract = parse_contract_bid(opener_bid) if opener_bid else None
    response_contract = parse_contract_bid(response_bid) if response_bid else None
    opener_rebid_contract = parse_contract_bid(opener_rebid_bid) if opener_rebid_bid else None

    def add_if_legal(bid: str) -> None:
        if bid in legal_choices and bid not in accepted:
            accepted.append(bid)

    # 规则化“次优可接受”策略：按阶段与序列给出最常见的替代动作。
    if mode == "opening":
        if recommended_bid in {"1♣", "1♦"}:
            add_if_legal("1♣")
            add_if_legal("1♦")
        if recommended_bid in {"1♥", "1♠"}:
            other = "1♠" if recommended_bid == "1♥" else "1♥"
            add_if_legal(other)
        if recommended_bid in {"2NT", "3NT"}:
            add_if_legal("2NT")
            add_if_legal("3NT")

    elif mode == "response":
        if opener_bid == "1NT" and recommended_bid in {"2NT", "3NT"}:
            add_if_legal("2NT")
            add_if_legal("3NT")

        # 兼容常见 Bergen 记号差异：部分体系用 1♥-3♣ 表示弱加叫。
        # 为减少训练误判，主推为弱 Bergen 时同时接受 3♣/3♦ 两种写法。
        if opener_bid == "1♥" and recommended_bid in {"3♦", "3♣"}:
            add_if_legal("3♣")
            add_if_legal("3♦")
            add_if_legal("2♥")

        if opener_contract and opener_contract[1] in {"♥", "♠"} and rec_strain == opener_contract[1]:
            add_if_legal(f"{max(2, rec_level - 1)}{rec_strain}")
            add_if_legal(f"{min(4, rec_level + 1)}{rec_strain}")

    elif mode == "opener_rebid":
        if rec_level == 1 and rec_strain in {"♣", "♦", "♥", "♠"}:
            add_if_legal("1NT")

        if (
            rec_level == 4
            and opener_contract is not None
            and response_bid == "2NT"
            and opener_contract[0] == 1
            and rec_strain == opener_contract[1]
        ):
            add_if_legal("3NT")

        if (
            rec_level == 2
            and rec_strain in {"♣", "♦", "♥", "♠"}
            and opener_contract is not None
            and opener_contract[0] == 1
            and opener_contract[1] in {"♥", "♠"}
        ):
            add_if_legal(f"2{opener_contract[1]}")

        if (
            recommended_bid == "1NT"
            and opener_contract is not None
            and response_contract is not None
            and opener_contract[0] == 1
            and response_contract[0] == 1
        ):
            add_if_legal("2♣")
            add_if_legal("2♦")

        if (
            rec_level == 2
            and rec_strain in {"♣", "♦", "♥", "♠"}
            and opener_contract is not None
            and response_contract is not None
            and opener_contract[0] == 1
            and response_contract[0] == 1
        ):
            add_if_legal("1NT")

        if rec_strain == "NT":
            if recommended_bid == "1NT":
                add_if_legal("2NT")
            elif recommended_bid == "2NT":
                add_if_legal("1NT")
                add_if_legal("3NT")
            elif recommended_bid == "3NT":
                add_if_legal("2NT")

        if response_contract and rec_strain == response_contract[1]:
            add_if_legal(f"{max(2, rec_level - 1)}{rec_strain}")
            add_if_legal(f"{rec_level + 1}{rec_strain}")

        if opener_contract and rec_strain == opener_contract[1]:
            add_if_legal(f"{max(2, rec_level - 1)}{rec_strain}")
            add_if_legal(f"{rec_level + 1}{rec_strain}")

    elif mode == "responder_rebid":
        if opener_rebid_contract and opener_rebid_contract[1] == "NT" and recommended_bid in {"2NT", "3NT"}:
            add_if_legal("2NT")
            add_if_legal("3NT")

        if response_contract and rec_strain == response_contract[1]:
            add_if_legal(f"{max(response_contract[0], rec_level - 1)}{rec_strain}")
            add_if_legal(f"{rec_level + 1}{rec_strain}")

        if opener_rebid_contract and rec_strain == opener_rebid_contract[1]:
            add_if_legal(f"{max(opener_rebid_contract[0], rec_level - 1)}{rec_strain}")
            add_if_legal(f"{rec_level + 1}{rec_strain}")

    # 兜底：若阶段规则没有补充到次优，则使用同花色相邻级别。
    if len(accepted) < 2:
        neighbors: list[str] = []
        for bid in legal_choices:
            if bid in accepted or bid == "Pass":
                continue
            contract = parse_contract_bid(bid)
            if contract is None:
                continue
            level, strain = contract
            if strain == rec_strain and abs(level - rec_level) == 1:
                neighbors.append(bid)

        neighbors = sorted(neighbors, key=lambda b: abs(parse_contract_bid(b)[0] - rec_level))
        accepted.extend([bid for bid in neighbors if bid not in accepted][:2])

    return accepted or [recommended_bid]
