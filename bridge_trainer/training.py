from __future__ import annotations

from dataclasses import dataclass

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
from .cards import Hand, deal
from .evaluator import HandEvaluation, evaluate_hand


ONE_LEVEL_OPENINGS = {"1♣", "1♦", "1♥", "1♠", "1NT"}
STRONG_OPENINGS = {"2♣", "2NT"}
PREEMPT_OPENINGS = {"2♦", "2♥", "2♠", "3♣", "3♦", "3♥", "3♠", "4♣", "4♦", "4♥", "4♠", "5♣", "5♦"}
SUPPORTED_FILTER_OPENINGS = ONE_LEVEL_OPENINGS | STRONG_OPENINGS | PREEMPT_OPENINGS
DEFAULT_SEARCH_ATTEMPTS = 2_000
OPENING_FILTER_SEARCH_ATTEMPTS = 5_000
RESPONSE_FILTER_SEARCH_ATTEMPTS = 15_000
REBID_FILTER_SEARCH_ATTEMPTS = 40_000


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


def generate_opening_question(seed: int | None = None, settings: RuleSettings | None = None) -> TrainingQuestion:
    settings = settings or default_rule_settings()
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
    attempts = search_attempt_budget(opener_bid=opener_bid, response_bid=response_bid)

    for offset in range(attempts):
        hands = deal(base_seed + offset)
        vulnerability = choose_vulnerability(base_seed + offset)
        opener_hand = hands["S"]
        opener_evaluation = evaluate_hand(opener_hand)
        opening_recommendation = recommend_opening(opener_evaluation, settings, vulnerability)
        if opening_recommendation.bid not in supported_openings:
            continue
        if opener_bid is not None and opening_recommendation.bid != opener_bid:
            continue

        responder_evaluation = evaluate_hand(hands["N"])
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
    attempts = search_attempt_budget(
        opener_bid=opener_bid,
        response_bid=response_bid,
        opener_rebid_bid=opener_rebid_bid,
    )

    for offset in range(attempts):
        hands = deal(base_seed + offset)
        vulnerability = choose_vulnerability(base_seed + offset)
        opener_hand = hands["N"]
        responder_hand = hands["S"]
        opener_evaluation = evaluate_hand(opener_hand)
        responder_evaluation = evaluate_hand(responder_hand)

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
