from __future__ import annotations

from dataclasses import dataclass

from .cards import SUIT_NAMES
from .evaluator import HandEvaluation, describe_lengths

OPENING_BIDS = [
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
]

RESPONSE_BIDS = [
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
]

REBID_BIDS = [
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
]

RESPONDER_REBID_BIDS = [
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
]

STRAIN_ORDER = {"♣": 1, "♦": 2, "♥": 3, "♠": 4, "NT": 5}


@dataclass(frozen=True)
class BidRecommendation:
    bid: str
    explanation: str
    rule_name: str


@dataclass(frozen=True)
class RuleSettings:
    opening_min_hcp: int = 12
    one_nt_min: int = 15
    one_nt_max: int = 17
    strong_two_club_min: int = 22
    weak_two_enabled: bool = True
    stayman_enabled: bool = True
    transfers_enabled: bool = True
    jacoby_2nt_enabled: bool = True
    two_over_one_min_hcp: int = 12
    forcing_nt_min_hcp: int = 6
    forcing_nt_max_hcp: int = 11
    forcing_nt_label: str = "半逼叫"
    scoring_mode: str = "IMP"
    respect_vulnerability: bool = True
    game_aggressiveness: int = 0
    august_2nt_enabled: bool = True
    responder_simple_raise_max: int = 9
    responder_limit_raise_min: int = 10
    responder_limit_raise_max: int = 11
    bergen_raises_enabled: bool = True
    responder_bergen_weak_max: int = 9
    splinter_enabled: bool = True
    responder_splinter_min_hcp: int = 11
    responder_splinter_max_hcp: int = 15
    negative_double_enabled: bool = True
    negative_double_min_hcp: int = 6
    inverted_minors_enabled: bool = False


def default_rule_settings() -> RuleSettings:
    return RuleSettings()


def ns_is_vulnerable(vulnerability: str | None) -> bool:
    return vulnerability in {"南北有局", "双方有局"}


def game_threshold_adjustment(vulnerability: str | None, settings: RuleSettings) -> int:
    mode = settings.scoring_mode.upper().strip()
    aggressiveness = max(-1, min(1, int(settings.game_aggressiveness)))
    if mode == "MP":
        # MP 更注重稳健，薄局门槛略高。
        return 1 - aggressiveness
    if settings.respect_vulnerability and ns_is_vulnerable(vulnerability):
        # IMP 且有局时，成局收益更高，适度积极。
        return -1 - aggressiveness
    return -aggressiveness


# README「开叫训练」原则摘要，用于判题解释援引。
OPENING_RULE_PRINCIPLES: dict[str, str] = {
    "强 2♣": "开叫训练原则第1条：22+ HCP（或达到设置的强 2♣ 下限）开叫 2♣。",
    "20-21 均型 2NT": (
        "开叫训练原则第2条：20-21 HCP 且均型或准均型门门有止"
        "（可能有5张高花/6张低花套）开叫 2NT。"
    ),
    "均型 1NT": (
        "开叫训练原则第3条：15-17 HCP（可设置）且均型或准均型门门有止"
        "（可能有5张高花/6张低花套）开叫 1NT；如有5张高花，开叫一阶高花为次优。"
    ),
    "五张高花开叫": "开叫训练原则第4条：12+ HCP 且有5张以上高花，开叫较长高花；5-5 高花优先 1♠。",
    "低花开叫": "开叫训练原则第5条：12+ HCP 无5张高花，按较长低花开叫；3-3 低花开 1♣，4-4 低花开 1♦。",
    "11 点轻开叫": (
        "开叫训练原则第6/7条：11 HCP 时，6+ 长套且有单缺开该长套；"
        "或 5-5 以上双套（等长开较高花色；高花短于低花时优先较短高花，较长低花为次优）。"
    ),
    "拼搏式 3NT": (
        "开叫训练原则第8条：7张以上坚固低花（含 AKQ），边张无 A/K/Q，"
        "且未达一阶开叫点力时开拼搏式 3NT（优先于同档阻击）。"
    ),
    "阻击开叫": (
        "开叫训练原则第9条：5-10 HCP 且7张以上长套，按套长作 3/4/5 阶阻击；"
        "无局至少1张顶张大牌，有局至少2张；并遵循有局宕二、无局宕三。"
    ),
    "弱二开叫": (
        "开叫训练原则第10条：6-10 HCP 且6张以上套，二阶弱二开 2♦/2♥/2♠"
        "（不使用弱 2♣）；无局至少1张顶张大牌，有局至少2张；并遵循有局宕二、无局宕三。"
    ),
    "6-6 双套弱二": (
        "开叫训练原则第11条：6-10 HCP 且6-6双套，在满足顶张质量的可开弱二花色中"
        "开质量最好的套。"
    ),
    "不叫": "开叫训练原则第12条：不满足以上开叫条件时 Pass。",
}


def lookup_opening_principle(rule_name: str | None) -> str | None:
    if not rule_name:
        return None
    if rule_name in OPENING_RULE_PRINCIPLES:
        return OPENING_RULE_PRINCIPLES[rule_name]
    for key, text in OPENING_RULE_PRINCIPLES.items():
        if rule_name.endswith(key):
            return text
    return None


def with_opening_principle(explanation: str, rule_name: str) -> str:
    principle = lookup_opening_principle(rule_name)
    if not principle:
        return explanation
    return f"{explanation}\n\n依据原则：{principle}"


def format_judgment_explanation(
    *,
    selected_bid: str | None,
    recommended_bid: str | None,
    grade: str,
    base_explanation: str,
    rule_name: str | None = None,
    acceptable_bids: list[str] | None = None,
) -> str:
    """组装判题反馈：对照选择/推荐，并尽量援引 README 原则。"""
    selected = selected_bid or "?"
    recommended = recommended_bid or "?"
    if grade == "primary":
        header = f"判定：正确。你选择了 {selected}，与推荐叫品一致。"
    elif grade == "acceptable":
        alts = [b for b in (acceptable_bids or []) if b != recommended]
        alt_text = f"；其他可接受：{', '.join(alts)}" if alts else ""
        header = (
            f"判定：可接受次优。你选择了 {selected}，主推仍是 {recommended}{alt_text}。"
        )
    else:
        header = f"判定：不太合适。你选择了 {selected}，推荐叫品是 {recommended}。"

    parts = [header, "", (base_explanation or "").strip()]
    principle = lookup_opening_principle(rule_name)
    # 若推荐解释里尚未写入原则，则在末尾补上。
    if principle and "依据原则：" not in (base_explanation or ""):
        parts.extend(["", f"依据原则：{principle}"])
    return "\n".join(part for part in parts if part is not None).strip()


def recommend_opening(
    evaluation: HandEvaluation,
    settings: RuleSettings | None = None,
    vulnerability: str | None = None,
) -> BidRecommendation:
    settings = settings or default_rule_settings()
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)

    if hcp >= settings.strong_two_club_min:
        return BidRecommendation(
            "2♣",
            with_opening_principle(
                (
                    f"你有 {hcp} HCP，达到强开叫门槛（当前设置下限 "
                    f"{settings.strong_two_club_min} HCP），应开叫 2♣。牌型：{length_text}。"
                ),
                "强 2♣",
            ),
            "强 2♣",
        )

    if qualifies_for_nt_opening_shape(evaluation) and 20 <= hcp <= 21:
        shape_text = "均型" if evaluation.balanced else "准均型且门门有止"
        return BidRecommendation(
            "2NT",
            with_opening_principle(
                f"你有 {hcp} HCP，且为{shape_text}，符合 20-21 无将开叫，应开叫 2NT。牌型：{length_text}。",
                "20-21 均型 2NT",
            ),
            "20-21 均型 2NT",
        )

    if qualifies_for_nt_opening_shape(evaluation) and settings.one_nt_min <= hcp <= settings.one_nt_max:
        shape_text = "均型" if evaluation.balanced else "准均型且门门有止"
        rule_name = f"{settings.one_nt_min}-{settings.one_nt_max} 均型 1NT"
        secondary = one_nt_secondary_major_opening_bid(lengths)
        if secondary is not None:
            return BidRecommendation(
                "1NT",
                with_opening_principle(
                    (
                        f"你有 {hcp} HCP，且为{shape_text}，优先开叫 1NT；"
                        f"因另有 5 张高花，开叫 {secondary} 为可接受次优。牌型：{length_text}。"
                    ),
                    rule_name,
                ),
                rule_name,
            )
        return BidRecommendation(
            "1NT",
            with_opening_principle(
                (
                    f"你有 {hcp} HCP，且为{shape_text}，符合当前 "
                    f"{settings.one_nt_min}-{settings.one_nt_max} 无将开叫，应开叫 1NT。牌型：{length_text}。"
                ),
                rule_name,
            ),
            rule_name,
        )

    if hcp >= settings.opening_min_hcp and (lengths["S"] >= 5 or lengths["H"] >= 5):
        suit = choose_major_opening(lengths)
        five_five_note = (
            "两高花均为 5 张时优先开 1♠。"
            if lengths["S"] >= 5 and lengths["H"] >= 5
            else f"选择较长高花 {SUIT_NAMES[suit]}。"
        )
        return BidRecommendation(
            f"1{suit_symbol(suit)}",
            with_opening_principle(
                (
                    f"你有 {hcp} HCP（≥{settings.opening_min_hcp}），持有 5 张以上高花，"
                    f"应优先开叫高花。{five_five_note}牌型：{length_text}。"
                ),
                "五张高花开叫",
            ),
            "五张高花开叫",
        )

    if hcp >= settings.opening_min_hcp:
        suit = choose_minor_opening(lengths)
        clubs, diamonds = lengths["C"], lengths["D"]
        if clubs == diamonds == 3:
            minor_note = "低花 3-3 等长，应开 1♣。"
        elif clubs == diamonds:
            minor_note = f"低花 {diamonds}-{clubs} 等长（含 4-4），应开 1♦。"
        elif diamonds > clubs:
            minor_note = f"方块更长（♦{diamonds}/♣{clubs}），应开 1♦。"
        else:
            minor_note = f"梅花更长（♣{clubs}/♦{diamonds}），应开 1♣。"
        return BidRecommendation(
            f"1{suit_symbol(suit)}",
            with_opening_principle(
                (
                    f"你有 {hcp} HCP（≥{settings.opening_min_hcp}），没有 5 张高花，"
                    f"应按较长低花开叫。{minor_note}牌型：{length_text}。"
                ),
                "低花开叫",
            ),
            "低花开叫",
        )

    # 11 HCP 轻开叫：6+ 长套且有单缺，或 5-5 以上双套。
    if hcp == 11:
        light_suit = choose_eleven_hcp_opening(lengths)
        if light_suit is not None:
            secondary = eleven_hcp_secondary_opening_bid(lengths, light_suit)
            if secondary is not None:
                return BidRecommendation(
                    f"1{suit_symbol(light_suit)}",
                    with_opening_principle(
                        (
                            f"你有 {hcp} HCP，属 5-5 以上双套轻开叫：优先开较短高花 "
                            f"1{suit_symbol(light_suit)}；开叫较长低花 {secondary} 为可接受次优。"
                            f"牌型：{length_text}。"
                        ),
                        "11 点轻开叫",
                    ),
                    "11 点轻开叫",
                )
            return BidRecommendation(
                f"1{suit_symbol(light_suit)}",
                with_opening_principle(
                    (
                        f"你有 {hcp} HCP，符合轻开叫（6+ 长套且有单缺，或 5-5 以上双套），"
                        f"应开叫 1{suit_symbol(light_suit)}。牌型：{length_text}。"
                    ),
                    "11 点轻开叫",
                ),
                "11 点轻开叫",
            )

    # 拼搏式 3NT：7+ 坚固低花（含 AKQ），边张无 A/K/Q；优先于同档阻击叫。
    gambling_minor = choose_gambling_3nt_minor(evaluation, settings.opening_min_hcp)
    if gambling_minor is not None:
        return BidRecommendation(
            "3NT",
            with_opening_principle(
                (
                    f"你有 {hcp} HCP（未达一阶开叫点力），持有 {lengths[gambling_minor]} 张坚固 "
                    f"{SUIT_NAMES[gambling_minor]}（含 AKQ），边张无 A/K/Q，"
                    f"应开叫拼搏式 3NT（优先于同档阻击）。牌型：{length_text}。"
                ),
                "拼搏式 3NT",
            ),
            "拼搏式 3NT",
        )

    preempt = (
        choose_preempt_opening(lengths, hcp, vulnerability, evaluation.top_honors_by_suit)
        if settings.weak_two_enabled
        else None
    )
    if preempt is not None:
        overbid = preempt_overbid_allowance(vulnerability)
        min_honors = preempt_min_top_honors(vulnerability)
        return BidRecommendation(
            preempt,
            with_opening_principle(
                (
                    f"你有 {hcp} HCP，持有 7 张以上长套，应按套长作 3/4/5 阶阻击；"
                    f"当前局况要求长套至少 {min_honors} 张顶张大牌，并遵循有局宕二无局宕三"
                    f"（本次可宕 {overbid}），因此开叫 {preempt}。牌型：{length_text}。"
                ),
                "阻击开叫",
            ),
            "阻击开叫",
        )

    weak_two = (
        choose_weak_two(lengths, hcp, evaluation.top_honors_by_suit, vulnerability)
        if settings.weak_two_enabled
        else None
    )
    if weak_two is not None:
        six_card_suits = [suit for suit in ["S", "H", "D", "C"] if lengths[suit] == 6]
        overbid = preempt_overbid_allowance(vulnerability)
        min_honors = preempt_min_top_honors(vulnerability)
        if len(six_card_suits) >= 2:
            return BidRecommendation(
                f"2{suit_symbol(weak_two)}",
                with_opening_principle(
                    (
                        f"你有 {hcp} HCP，6-6 双套，应按套质量选择二阶弱二；"
                        f"当前局况要求长套至少 {min_honors} 张顶张大牌，并遵循有局宕二无局宕三"
                        f"（本次可宕 {overbid}），因此开叫 2{suit_symbol(weak_two)}。"
                        f"当前训练不使用弱 2♣。牌型：{length_text}。"
                    ),
                    "6-6 双套弱二",
                ),
                "6-6 双套弱二",
            )
        return BidRecommendation(
            f"2{suit_symbol(weak_two)}",
            with_opening_principle(
                (
                    f"你有 {hcp} HCP，持有 {lengths[weak_two]} 张 {SUIT_NAMES[weak_two]}，"
                    f"可作二阶弱二；当前局况要求长套至少 {min_honors} 张顶张大牌，"
                    f"并遵循有局宕二无局宕三（本次可宕 {overbid}），"
                    f"因此开叫 2{suit_symbol(weak_two)}。当前训练不使用弱 2♣。牌型：{length_text}。"
                ),
                "弱二开叫",
            ),
            "弱二开叫",
        )

    return BidRecommendation(
        "Pass",
        with_opening_principle(
            (
                f"你有 {hcp} HCP，未达到正常开叫、轻开叫、拼搏式 3NT 或弱二/阻击条件，"
                f"应 Pass。牌型：{length_text}。"
            ),
            "不叫",
        ),
        "不叫",
    )


def recommend_response(
    opener_bid: str,
    evaluation: HandEvaluation,
    settings: RuleSettings | None = None,
    vulnerability: str | None = None,
    overcall_bid: str | None = None,
) -> BidRecommendation:
    settings = settings or default_rule_settings()
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)

    if overcall_bid and should_make_negative_double(opener_bid, overcall_bid, evaluation, settings):
        target_majors = negative_double_target_majors(opener_bid, overcall_bid)
        majors_text = " 或 ".join([suit_symbol(suit) for suit in target_majors]) if target_majors else "未叫高花"
        return BidRecommendation(
            "X",
            (
                f"同伴开 {opener_bid}，右手竞叫 {overcall_bid}。你有 {hcp} HCP，"
                f"并持有 4 张以上 {majors_text}，按简化否定性加倍约定应叫 X。牌型：{length_text}。"
            ),
            "否定性加倍",
        )

    if opener_bid == "1NT":
        return recommend_response_to_1nt(evaluation, settings, vulnerability)

    if opener_bid in {"1♥", "1♠"}:
        major = "H" if opener_bid == "1♥" else "S"
        return recommend_response_to_major(major, evaluation, settings, vulnerability)

    if opener_bid in {"1♣", "1♦"}:
        minor = "C" if opener_bid == "1♣" else "D"
        return recommend_response_to_minor(minor, evaluation, settings, vulnerability)

    if opener_bid == "2♣":
        return recommend_response_to_strong_two_club(evaluation)

    if opener_bid == "2NT":
        return recommend_response_to_2nt(evaluation, settings, vulnerability)

    if opener_bid == "3NT":
        return recommend_response_to_gambling_3nt(evaluation, settings)

    if opener_bid in {"2♦", "2♥", "2♠", "3♣", "3♦", "3♥", "3♠", "4♣", "4♦", "4♥", "4♠", "5♣", "5♦"}:
        return recommend_response_to_preempt(opener_bid, evaluation, settings)

    return BidRecommendation(
        "Pass",
        f"当前应叫训练只覆盖一阶定约、强开叫与简化阻击开叫。你有 {hcp} HCP，牌型：{length_text}。",
        "未覆盖的开叫",
    )


def legal_response_bids(opener_bid: str) -> list[str]:
    return legal_response_bids_with_interference(opener_bid, None)


def legal_response_bids_with_interference(opener_bid: str, overcall_bid: str | None) -> list[str]:
    previous_bid = overcall_bid if overcall_bid else opener_bid
    legal = legal_bids_after(previous_bid, RESPONSE_BIDS)
    if overcall_bid and is_negative_double_available(opener_bid, overcall_bid):
        if "X" not in legal:
            legal.insert(1 if legal and legal[0] == "Pass" else 0, "X")
    return legal


def legal_rebid_bids(response_bid: str) -> list[str]:
    return legal_bids_after(response_bid, REBID_BIDS)


def legal_responder_rebid_bids(opener_rebid_bid: str) -> list[str]:
    return legal_bids_after(opener_rebid_bid, RESPONDER_REBID_BIDS)


def legal_bids_after(previous_bid: str, choices: list[str]) -> list[str]:
    return [bid for bid in choices if is_legal_response_bid(previous_bid, bid)]


def is_legal_response_bid(opener_bid: str, response_bid: str) -> bool:
    if response_bid == "Pass":
        return True

    opener_contract = parse_contract_bid(opener_bid)
    response_contract = parse_contract_bid(response_bid)
    if opener_contract is None or response_contract is None:
        return False

    opener_level, opener_strain = opener_contract
    response_level, response_strain = response_contract
    if response_level > opener_level:
        return True
    if response_level == opener_level:
        return STRAIN_ORDER[response_strain] > STRAIN_ORDER[opener_strain]
    return False


def parse_contract_bid(bid: str) -> tuple[int, str] | None:
    if len(bid) < 2 or not bid[0].isdigit():
        return None
    level = int(bid[0])
    strain = bid[1:]
    if strain not in STRAIN_ORDER:
        return None
    return level, strain


def is_negative_double_available(opener_bid: str, overcall_bid: str) -> bool:
    opener_contract = parse_contract_bid(opener_bid)
    overcall_contract = parse_contract_bid(overcall_bid)
    if opener_contract is None or overcall_contract is None:
        return False

    opener_level, opener_strain = opener_contract
    overcall_level, overcall_strain = overcall_contract

    # 训练第3阶段先覆盖最常见的一阶开叫后一阶争叫的否定性加倍。
    if opener_level != 1 or overcall_level != 1:
        return False
    if opener_strain not in {"♣", "♦", "♥"}:
        return False
    if overcall_strain not in {"♦", "♥", "♠"}:
        return False
    if STRAIN_ORDER[overcall_strain] <= STRAIN_ORDER[opener_strain]:
        return False
    return bool(negative_double_target_majors(opener_bid, overcall_bid))


def negative_double_target_majors(opener_bid: str, overcall_bid: str) -> list[str]:
    opener_contract = parse_contract_bid(opener_bid)
    overcall_contract = parse_contract_bid(overcall_bid)
    if opener_contract is None or overcall_contract is None:
        return []

    _, opener_strain = opener_contract
    _, overcall_strain = overcall_contract

    if opener_strain == "♣":
        if overcall_strain == "♦":
            return ["H", "S"]
        if overcall_strain == "♥":
            return ["S"]
        if overcall_strain == "♠":
            return ["H"]
    if opener_strain == "♦":
        if overcall_strain == "♥":
            return ["S"]
        if overcall_strain == "♠":
            return ["H"]
    if opener_strain == "♥" and overcall_strain == "♠":
        # 1♥-(1♠)-X 常见为4+张低花，简化版以4+♦作为触发。
        return ["D"]

    return []


def should_make_negative_double(
    opener_bid: str,
    overcall_bid: str,
    evaluation: HandEvaluation,
    settings: RuleSettings,
) -> bool:
    if not settings.negative_double_enabled:
        return False
    if evaluation.hcp < settings.negative_double_min_hcp:
        return False
    if not is_negative_double_available(opener_bid, overcall_bid):
        return False

    targets = negative_double_target_majors(opener_bid, overcall_bid)
    if not targets:
        return False

    lengths = evaluation.lengths
    for suit in targets:
        if lengths[suit] >= 4:
            return True
    return False


def recommend_opener_rebid(
    opening_bid: str,
    response_bid: str,
    evaluation: HandEvaluation,
    settings: RuleSettings | None = None,
    vulnerability: str | None = None,
) -> BidRecommendation:
    settings = settings or default_rule_settings()
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)
    opening_contract = parse_contract_bid(opening_bid)
    response_contract = parse_contract_bid(response_bid)

    if response_bid == "Pass" or response_contract is None or opening_contract is None:
        return BidRecommendation(
            "Pass",
            f"同伴未作有效应叫，当前再叫训练建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
            "再叫后不叫",
        )

    opener_suit = symbol_to_suit(opening_contract[1])
    response_suit = symbol_to_suit(response_contract[1])
    response_level = response_contract[0]
    opening_level = opening_contract[0]
    opening_level, opening_strain = opening_contract
    is_weak_two_opening = opening_level == 2 and opening_strain in {"♦", "♥", "♠"}
    is_three_plus_preempt_opening = opening_level >= 3 and opening_strain in {"♣", "♦", "♥", "♠"}
    game_adjustment = game_threshold_adjustment(vulnerability, settings)
    raise_hcp = hcp - game_adjustment

    if is_three_plus_preempt_opening:
        return BidRecommendation(
            "Pass",
            f"同伴已在阻击序列中推进到 {response_bid}，开叫者在当前简化体系中以止叫为主，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
            "阻击后止叫",
        )

    if is_weak_two_opening and response_bid != "2NT":
        return BidRecommendation(
            "Pass",
            f"弱二开叫后，除 Ogust 2NT 问叫外当前简化体系默认不开新一轮描述，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
            "弱二后止叫",
        )

    # 对手无干扰的简化训练中，同伴直接叫到 3NT 通常为落定成局，开叫者应止叫。
    if response_bid == "3NT":
        return BidRecommendation(
            "Pass",
            f"同伴已直接叫到 3NT，开叫者通常不再进叫，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
            "3NT 后止叫",
        )

    if opening_bid == "1NT":
        if response_bid == "2♣" and settings.stayman_enabled:
            if lengths["H"] >= 4 and is_legal_response_bid(response_bid, "2♥"):
                return BidRecommendation("2♥", f"1NT-2♣ 序列中，开叫者有 4 张红心，按 Stayman 规则应答 2♥。牌型：{length_text}。", "Stayman 应答 2♥")
            if lengths["S"] >= 4 and is_legal_response_bid(response_bid, "2♠"):
                return BidRecommendation("2♠", f"1NT-2♣ 序列中，开叫者无 4 张红心但有 4 张黑桃，按 Stayman 规则应答 2♠。牌型：{length_text}。", "Stayman 应答 2♠")
            if is_legal_response_bid(response_bid, "2♦"):
                return BidRecommendation("2♦", f"1NT-2♣ 序列中，开叫者无 4 张高花，按 Stayman 否定应答 2♦。牌型：{length_text}。", "Stayman 否定应答 2♦")

        if response_bid == "2♦" and settings.transfers_enabled and is_legal_response_bid(response_bid, "2♥"):
            return BidRecommendation("2♥", f"1NT-2♦ 序列中，2♦ 为红心转移，开叫者应接受转移叫 2♥。牌型：{length_text}。", "接受红心转移")

        if response_bid == "2♥" and settings.transfers_enabled and is_legal_response_bid(response_bid, "2♠"):
            return BidRecommendation("2♠", f"1NT-2♥ 序列中，2♥ 为黑桃转移，开叫者应接受转移叫 2♠。牌型：{length_text}。", "接受黑桃转移")

        # 低花转移：1NT-2♠ 要求同伴转叫 3♣（草花直接完成；方块后续再叫 3♦）。
        if response_bid == "2♠" and settings.transfers_enabled and is_legal_response_bid(response_bid, "3♣"):
            return BidRecommendation("3♣", f"1NT-2♠ 序列中，2♠ 为低花转移，开叫者应先转叫 3♣。牌型：{length_text}。", "接受低花转移")

        # 德克萨斯转移：1NT-4♦/4♥，开叫者完成转移到 4♥/4♠。
        if response_bid == "4♦" and settings.transfers_enabled and is_legal_response_bid(response_bid, "4♥"):
            return BidRecommendation("4♥", f"1NT-4♦ 序列中，4♦ 为德克萨斯红心转移，开叫者应接受转移叫 4♥。牌型：{length_text}。", "接受德克萨斯红心转移")
        if response_bid == "4♥" and settings.transfers_enabled and is_legal_response_bid(response_bid, "4♠"):
            return BidRecommendation("4♠", f"1NT-4♥ 序列中，4♥ 为德克萨斯黑桃转移，开叫者应接受转移叫 4♠。牌型：{length_text}。", "接受德克萨斯黑桃转移")

        if response_bid == "2NT":
            accept_invite_hcp = max(16, 17 + game_adjustment)
            if hcp >= accept_invite_hcp and is_legal_response_bid(response_bid, "3NT"):
                return BidRecommendation("3NT", f"1NT-2NT 为邀局；你有 {hcp} HCP，达到接受邀局门槛，叫 3NT。牌型：{length_text}。", "接受 2NT 邀局")
            return BidRecommendation("Pass", f"1NT-2NT 为邀局；你有 {hcp} HCP，未达到接受邀局门槛，建议 Pass。牌型：{length_text}。", "拒绝 2NT 邀局")

    # 二阶弱开叫（2♦/2♥/2♠）+ Ogust 2NT 问叫的开叫者回答
    if (
        opening_contract is not None
        and opening_contract[0] == 2
        and opening_contract[1] in {"♦", "♥", "♠"}
        and response_bid == "2NT"
        and settings.august_2nt_enabled
    ):
        opening_suit = opener_suit
        if opening_suit is not None:
            top_honors = evaluation.top_honors_by_suit.get(opening_suit, 0)
            is_max = hcp >= 8
            if is_max and top_honors >= 3 and is_legal_response_bid(response_bid, "3NT"):
                return BidRecommendation(
                    "3NT",
                    f"Ogust 2NT 问叫后，你有 {hcp} HCP（高限）且开叫套具备 AKQ 三大顶张，按标准回答 3NT。牌型：{length_text}。",
                    "Ogust 回答：高限+AKQ",
                )
            if not is_max and top_honors <= 1 and is_legal_response_bid(response_bid, "3♣"):
                return BidRecommendation(
                    "3♣",
                    f"Ogust 2NT 问叫后，你有 {hcp} HCP（低限）且开叫套顶张质量偏弱（顶三张中至多 1 张），按标准回答 3♣。牌型：{length_text}。",
                    "Ogust 回答：低限+差套",
                )
            if not is_max and top_honors >= 2 and is_legal_response_bid(response_bid, "3♦"):
                return BidRecommendation(
                    "3♦",
                    f"Ogust 2NT 问叫后，你有 {hcp} HCP（低限）且开叫套顶张质量较好（顶三张中 2 张），按标准回答 3♦。牌型：{length_text}。",
                    "Ogust 回答：低限+好套",
                )
            if is_max and top_honors <= 1 and is_legal_response_bid(response_bid, "3♥"):
                return BidRecommendation(
                    "3♥",
                    f"Ogust 2NT 问叫后，你有 {hcp} HCP（高限）且开叫套顶张质量偏弱（顶三张中至多 1 张），按标准回答 3♥。牌型：{length_text}。",
                    "Ogust 回答：高限+差套",
                )
            if is_max and top_honors >= 2 and is_legal_response_bid(response_bid, "3♠"):
                return BidRecommendation(
                    "3♠",
                    f"Ogust 2NT 问叫后，你有 {hcp} HCP（高限）且开叫套顶张质量较好（顶三张中 2 张），按标准回答 3♠。牌型：{length_text}。",
                    "Ogust 回答：高限+好套",
                )

    if is_weak_two_opening and response_bid == "2NT":
        return BidRecommendation(
            "Pass",
            f"弱二开叫面对 2NT 问叫时，当前条件下未触发标准 Ogust 回答，简化体系建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
            "弱二后止叫",
        )

    if opening_bid == "2NT":
        if response_bid == "3♣" and settings.stayman_enabled:
            if lengths["H"] >= 4 and is_legal_response_bid(response_bid, "3♥"):
                return BidRecommendation("3♥", f"2NT-3♣ 序列中，开叫者有 4 张红心，按 Stayman 应答 3♥。牌型：{length_text}。", "2NT Stayman 应答 3♥")
            if lengths["S"] >= 4 and is_legal_response_bid(response_bid, "3♠"):
                return BidRecommendation("3♠", f"2NT-3♣ 序列中，开叫者无 4 张红心但有 4 张黑桃，按 Stayman 应答 3♠。牌型：{length_text}。", "2NT Stayman 应答 3♠")
            if is_legal_response_bid(response_bid, "3♦"):
                return BidRecommendation("3♦", f"2NT-3♣ 序列中，开叫者无 4 张高花，按 Stayman 否定应答 3♦。牌型：{length_text}。", "2NT Stayman 否定应答 3♦")

        if response_bid == "3♦" and settings.transfers_enabled and is_legal_response_bid(response_bid, "3♥"):
            return BidRecommendation("3♥", f"2NT-3♦ 序列中，3♦ 为红心转移，开叫者应接受转移叫 3♥。牌型：{length_text}。", "2NT 后接受红心转移")

        if response_bid == "3♥" and settings.transfers_enabled and is_legal_response_bid(response_bid, "3♠"):
            return BidRecommendation("3♠", f"2NT-3♥ 序列中，3♥ 为黑桃转移，开叫者应接受转移叫 3♠。牌型：{length_text}。", "2NT 后接受黑桃转移")

    # 拼搏式 3NT 后再叫：4♣=Pass or correct；4♦=问单缺；4M=止叫。
    if opening_bid == "3NT":
        gambling_minor = choose_gambling_3nt_minor(evaluation, settings.opening_min_hcp) or (
            "C" if lengths["C"] >= lengths["D"] else "D"
        )
        minor_symbol = suit_symbol(gambling_minor)
        if response_bid == "4♣":
            if gambling_minor == "C":
                return BidRecommendation(
                    "Pass",
                    f"拼搏式 3NT 后同伴叫 4♣（Pass or correct），你的真实花色是梅花，接受并止叫 Pass。牌型：{length_text}。",
                    "拼搏式 3NT 后接受梅花",
                )
            if is_legal_response_bid(response_bid, "4♦"):
                return BidRecommendation(
                    "4♦",
                    f"拼搏式 3NT 后同伴叫 4♣（Pass or correct），你的真实花色是方块，改叫 4♦。牌型：{length_text}。",
                    "拼搏式 3NT 后改叫方块",
                )
        if response_bid == "4♦":
            short_majors = [suit for suit in ["H", "S"] if lengths[suit] <= 1]
            for suit in short_majors:
                shortage_bid = f"4{suit_symbol(suit)}"
                if is_legal_response_bid(response_bid, shortage_bid):
                    return BidRecommendation(
                        shortage_bid,
                        f"拼搏式 3NT 后同伴以 4♦ 询问单缺，你在 {SUIT_NAMES[suit]} 单缺，回答 {shortage_bid}。牌型：{length_text}。",
                        "拼搏式 3NT 后报单缺",
                    )
            other_minor = "D" if gambling_minor == "C" else "C"
            if lengths[other_minor] <= 1:
                other_bid = f"5{suit_symbol(other_minor)}"
                if is_legal_response_bid(response_bid, other_bid):
                    return BidRecommendation(
                        other_bid,
                        f"拼搏式 3NT 后同伴以 4♦ 询问单缺，你在 {SUIT_NAMES[other_minor]} 单缺，回答 {other_bid}。牌型：{length_text}。",
                        "拼搏式 3NT 后报单缺",
                    )
            own_five = f"5{minor_symbol}"
            if is_legal_response_bid(response_bid, own_five):
                return BidRecommendation(
                    own_five,
                    f"拼搏式 3NT 后同伴以 4♦ 询问单缺，你无高花单缺，重叫己方坚固低花 {own_five}。牌型：{length_text}。",
                    "拼搏式 3NT 后无单缺重叫低花",
                )
        if response_bid in {"4♥", "4♠"}:
            return BidRecommendation(
                "Pass",
                f"拼搏式 3NT 后同伴叫 {response_bid} 表示自有高花成局，开叫者止叫 Pass。牌型：{length_text}。",
                "拼搏式 3NT 后高花止叫",
            )
        return BidRecommendation(
            "Pass",
            f"拼搏式 3NT 后同伴叫 {response_bid}，当前简化体系以止叫为主，建议 Pass。牌型：{length_text}。",
            "拼搏式 3NT 后止叫",
        )

    # Jacoby 2NT：一阶高花开叫后，2NT 显示 4+ 将牌支持与进局实力。
    if opening_bid in {"1♥", "1♠"} and response_bid == "2NT":
        game_bid = f"4{opening_strain}"
        if is_legal_response_bid(response_bid, game_bid):
            return BidRecommendation(
                game_bid,
                f"同伴以 Jacoby 2NT 显示对 {opening_strain} 的 4+ 张支持与进局实力；你有 {hcp} HCP，优先确立高花进局 {game_bid}。牌型：{length_text}。",
                "Jacoby 2NT 后高花进局",
            )

    # Bergen 加叫：1♥/1♠ 开叫后，3♣/3♦ 视作对开叫高花的支持。
    # 常见简化分档：
    # - 3♣（弱支持，约 6-9）：开叫方 12-15 以 3M 再叫，16+ 进局 4M。
    # - 3♦（中等支持，约 10-11）：开叫方 14+ 倾向进局 4M，否则 3M。
    if opening_bid in {"1♥", "1♠"} and response_bid in {"3♣", "3♦"} and opener_suit in {"H", "S"}:
        if response_bid == "3♣":
            target_level = 4 if hcp >= 16 else 3
        else:
            target_level = 4 if hcp >= 14 else 3

        bid = f"{target_level}{suit_symbol(opener_suit)}"
        if is_legal_response_bid(response_bid, bid):
            return BidRecommendation(
                bid,
                f"同伴以 Bergen 加叫 {response_bid} 显示对 {SUIT_NAMES[opener_suit]} 的支持；你有 {hcp} HCP，按 Bergen 分档选择 {bid}。牌型：{length_text}。",
                "Bergen 后支持开叫高花",
            )

    # 开叫 1M 后同伴 1NT：按牌力/牌型再叫。
    # 2♣/2♦ 保证 3 张；2M 需 6+；2NT=17-18 均型；3NT=19-21 均型。
    if opening_bid in {"1♥", "1♠"} and response_bid == "1NT" and opener_suit in {"H", "S"}:
        if evaluation.balanced and 19 <= hcp <= 21 and is_legal_response_bid(response_bid, "3NT"):
            return BidRecommendation(
                "3NT",
                f"1{opening_strain}-1NT 后，你有 {hcp} HCP 且均型，叫 3NT。牌型：{length_text}。",
                "1M-1NT 后 3NT",
            )
        if evaluation.balanced and 17 <= hcp <= 18 and is_legal_response_bid(response_bid, "2NT"):
            return BidRecommendation(
                "2NT",
                f"1{opening_strain}-1NT 后，你有 {hcp} HCP 且均型，叫 2NT。牌型：{length_text}。",
                "1M-1NT 后 2NT",
            )
        if lengths[opener_suit] >= 6:
            rebid_major = f"2{opening_strain}"
            if is_legal_response_bid(response_bid, rebid_major):
                return BidRecommendation(
                    rebid_major,
                    f"1{opening_strain}-1NT 后，你有 {lengths[opener_suit]} 张开叫高花，再叫 {rebid_major}。牌型：{length_text}。",
                    "1M-1NT 后重复高花",
                )
        # 1♠-1NT：有 4 张♥ 时再叫 2♥。
        if opening_bid == "1♠" and lengths["H"] >= 4 and is_legal_response_bid(response_bid, "2♥"):
            return BidRecommendation(
                "2♥",
                f"1♠-1NT 后，你有 {lengths['H']} 张红心，再叫 2♥。牌型：{length_text}。",
                "1♠-1NT 后再叫红心",
            )
        minor_for_rebid = choose_minor_for_major_one_nt_rebid(lengths)
        if minor_for_rebid is not None:
            minor_bid = f"2{suit_symbol(minor_for_rebid)}"
            if is_legal_response_bid(response_bid, minor_bid):
                return BidRecommendation(
                    minor_bid,
                    f"1{opening_strain}-1NT 后，你有 {lengths[minor_for_rebid]} 张 {SUIT_NAMES[minor_for_rebid]}（保证 3 张），再叫 {minor_bid}。牌型：{length_text}。",
                    "1M-1NT 后再叫低花",
                )
        return BidRecommendation(
            "Pass",
            f"1{opening_strain}-1NT 后，你有 {hcp} HCP，当前没有更合适的描述叫品，建议 Pass。牌型：{length_text}。",
            "1M-1NT 后止叫",
        )

    # 一阶低花开叫后同伴 1NT 应叫，最低限均型通常以止叫为主。
    if opening_bid in {"1♣", "1♦"} and response_bid == "1NT" and evaluation.balanced and hcp <= 14:
        return BidRecommendation(
            "Pass",
            f"同伴 1NT 应叫后，你有 {hcp} HCP 且均型，属于最低限，通常止叫 Pass。牌型：{length_text}。",
            "1NT 应叫后最低限止叫",
        )

    # 一阶高花开叫后同伴简单加叫到 2M：
    # 最低限（约 12-14）通常止叫；中等（15-17）再邀叫；高限（18+）进局。
    if (
        opening_level == 1
        and opening_strain in {"♥", "♠"}
        and response_contract is not None
        and response_contract[0] == 2
        and response_contract[1] == opening_strain
    ):
        if hcp <= 14:
            return BidRecommendation(
                "Pass",
                f"同伴简单加叫到 {response_bid}，你有 {hcp} HCP 属于最低限，优先止叫 Pass。牌型：{length_text}。",
                "简单加叫后最低限止叫",
            )
        if hcp >= 18:
            game_bid = f"4{opening_strain}"
            if is_legal_response_bid(response_bid, game_bid):
                return BidRecommendation(
                    game_bid,
                    f"同伴简单加叫到 {response_bid}，你有 {hcp} HCP 属于高限，直接进局 {game_bid}。牌型：{length_text}。",
                    "简单加叫后高限进局",
                )

        invite_bid = f"3{opening_strain}"
        if is_legal_response_bid(response_bid, invite_bid):
            return BidRecommendation(
                invite_bid,
                f"同伴简单加叫到 {response_bid}，你有 {hcp} HCP 属于中等强度，叫 {invite_bid} 表示继续邀请。牌型：{length_text}。",
                "简单加叫后邀请",
            )

    # 一阶高花开叫后同伴直接跳到 4M：关煞叫（弱牌+长将牌），开叫者通常止叫。
    if (
        opening_level == 1
        and opening_strain in {"♥", "♠"}
        and response_contract is not None
        and response_contract[0] == 4
        and response_contract[1] == opening_strain
    ):
        return BidRecommendation(
            "Pass",
            f"同伴以 {response_bid} 作高花关煞加叫，已成局且示弱；你有 {hcp} HCP，没有额外牌力继续试探满贯，建议止叫 Pass。牌型：{length_text}。",
            "关煞加叫后止叫",
        )

    # 一阶高花开叫后同伴跳加叫到 3M：多为弱支持跳加；最低限止叫，有额外牌力再进局。
    if (
        opening_level == 1
        and opening_strain in {"♥", "♠"}
        and response_contract is not None
        and response_contract[0] == 3
        and response_contract[1] == opening_strain
    ):
        if hcp <= 15:
            return BidRecommendation(
                "Pass",
                f"同伴跳加叫到 {response_bid} 多为弱支持；你有 {hcp} HCP 属于最低限，建议止叫 Pass。牌型：{length_text}。",
                "弱跳加叫后最低限止叫",
            )
        game_bid = f"4{opening_strain}"
        if is_legal_response_bid(response_bid, game_bid):
            return BidRecommendation(
                game_bid,
                f"同伴跳加叫到 {response_bid}；你有 {hcp} HCP 具备额外牌力，进局 {game_bid}。牌型：{length_text}。",
                "弱跳加叫后进局",
            )

    # 低花反加叫未开启时的 1m-2m：按牌力选择 Pass / 2M / 2NT / 3NT / 3m。
    if (
        not settings.inverted_minors_enabled
        and opening_level == 1
        and opening_strain in {"♣", "♦"}
        and response_contract is not None
        and response_contract[0] == 2
        and response_contract[1] == opening_strain
    ):
        if hcp <= 16:
            return BidRecommendation(
                "Pass",
                f"同伴加叫到 {response_bid}（未启用低花反加叫），你有 {hcp} HCP（≤16），建议止叫 Pass。牌型：{length_text}。",
                "普通低花加叫后止叫",
            )
        if hcp >= 20 and evaluation.balanced and is_legal_response_bid(response_bid, "3NT"):
            return BidRecommendation(
                "3NT",
                f"同伴加叫到 {response_bid}（未启用低花反加叫），你有 {hcp} HCP 且均型，叫 3NT。牌型：{length_text}。",
                "普通低花加叫后 3NT",
            )
        five_plus_majors = [suit for suit in ["S", "H"] if lengths[suit] >= 5]
        if hcp >= 18 and five_plus_majors:
            major = max(five_plus_majors, key=lambda suit: (lengths[suit], suit == "S"))
            major_bid = f"2{suit_symbol(major)}"
            if is_legal_response_bid(response_bid, major_bid):
                return BidRecommendation(
                    major_bid,
                    f"同伴加叫到 {response_bid}（未启用低花反加叫），你有 {hcp} HCP 且 {lengths[major]} 张 {SUIT_NAMES[major]}，再叫 {major_bid}。牌型：{length_text}。",
                    "普通低花加叫后再叫高花",
                )
        if evaluation.balanced and 18 <= hcp <= 19 and is_legal_response_bid(response_bid, "2NT"):
            return BidRecommendation(
                "2NT",
                f"同伴加叫到 {response_bid}（未启用低花反加叫），你有 {hcp} HCP 且均型，叫 2NT。牌型：{length_text}。",
                "普通低花加叫后 2NT",
            )
        if 18 <= hcp <= 19:
            invite_minor = f"3{opening_strain}"
            if is_legal_response_bid(response_bid, invite_minor):
                return BidRecommendation(
                    invite_minor,
                    f"同伴加叫到 {response_bid}（未启用低花反加叫），你有 {hcp} HCP，叫 {invite_minor} 邀局。牌型：{length_text}。",
                    "普通低花加叫后邀局",
                )
        return BidRecommendation(
            "Pass",
            f"同伴加叫到 {response_bid}（未启用低花反加叫），你有 {hcp} HCP，当前没有更合适的继续叫品，建议 Pass。牌型：{length_text}。",
            "普通低花加叫后止叫",
        )

    # 低花反加叫后再叫：1♣-2♣ 或 1♦-2♦（启用时，应叫方 10+ HCP 逼叫一轮）
    # 再叫优先级：3NT(18-19均型) > 3M Splinter(18-21短高花) > 2M报单缺(15-17)
    #             > 2NT(15-17两高花有止) > 顺叫另一低花(12-14有止) > 重叫低花(12-14无止)
    if (
        settings.inverted_minors_enabled
        and opening_level == 1
        and opening_strain in {"♣", "♦"}
        and response_contract is not None
        and response_contract[0] == 2
        and response_contract[1] == opening_strain
    ):
        other_minor = "D" if opener_suit == "C" else "C"
        other_minor_sym = suit_symbol(other_minor)
        spade_stop = lengths["S"] >= 1 and evaluation.top_honors_by_suit.get("S", 0) >= 1
        heart_stop = lengths["H"] >= 1 and evaluation.top_honors_by_suit.get("H", 0) >= 1
        both_majors_stopped = spade_stop and heart_stop
        short_major: str | None = next(
            (mj for mj in ["H", "S"] if lengths[mj] <= 1), None
        )

        # 3NT：18-19 均型，两高花均有止
        if evaluation.balanced and 18 <= hcp <= 19 and both_majors_stopped and is_legal_response_bid(response_bid, "3NT"):
            return BidRecommendation(
                "3NT",
                f"同伴低花反加叫 {response_bid} 后，你有 {hcp} HCP 均型且两高花均有止，直接叫 3NT。牌型：{length_text}。",
                "低花反加叫后 3NT",
            )

        # 20+ HCP：按 README 约定进入满贯探索
        # - 非均型：4NT（以开叫低花为将牌的关键张问叫）
        # - 均型：5NT（邀 6NT）
        if hcp >= 20 and not evaluation.balanced and is_legal_response_bid(response_bid, "4NT"):
            return BidRecommendation(
                "4NT",
                f"同伴低花反加叫 {response_bid} 后，你有 {hcp} HCP 且非均型，按约定以开叫低花为将牌进入 4NT 关键张问叫。牌型：{length_text}。",
                "低花反加叫后 4NT 问叫",
            )

        if hcp >= 20 and evaluation.balanced and is_legal_response_bid(response_bid, "5NT"):
            return BidRecommendation(
                "5NT",
                f"同伴低花反加叫 {response_bid} 后，你有 {hcp} HCP 且均型，按约定叫 5NT 邀请 6NT。牌型：{length_text}。",
                "低花反加叫后 5NT 邀请",
            )

        # 3♥/3♠ Splinter（18-21 HCP）：报高花单缺/缺门，强满贯试探
        if short_major is not None and 18 <= hcp <= 21:
            splinter_bid = f"3{suit_symbol(short_major)}"
            if is_legal_response_bid(response_bid, splinter_bid):
                short_desc = "单张" if lengths[short_major] == 1 else "缺门"
                return BidRecommendation(
                    splinter_bid,
                    f"同伴低花反加叫 {response_bid} 后，你有 {hcp} HCP 且 {SUIT_NAMES[short_major]}{short_desc}，叫 {splinter_bid} 作强满贯试探型 Splinter。牌型：{length_text}。",
                    "低花反加叫后高限 Splinter",
                )

        # 2♥/2♠（15-17 HCP）：报高花单缺/缺门，满贯试探
        if short_major is not None and 15 <= hcp <= 17:
            short_bid = f"2{suit_symbol(short_major)}"
            if is_legal_response_bid(response_bid, short_bid):
                short_desc = "单张" if lengths[short_major] == 1 else "缺门"
                return BidRecommendation(
                    short_bid,
                    f"同伴低花反加叫 {response_bid} 后，你有 {hcp} HCP 且 {SUIT_NAMES[short_major]}{short_desc}，叫 {short_bid} 报单缺作满贯试探。牌型：{length_text}。",
                    "低花反加叫后报单缺",
                )

        # 2NT（15-17 HCP）：两高花均有止，倾向 3NT
        if both_majors_stopped and 15 <= hcp <= 17 and is_legal_response_bid(response_bid, "2NT"):
            return BidRecommendation(
                "2NT",
                f"同伴低花反加叫 {response_bid} 后，你有 {hcp} HCP 且两高花均有止，叫 2NT 倾向 3NT。牌型：{length_text}。",
                "低花反加叫后 2NT",
            )

        # 顺叫另一低花（12-14 HCP）：低限，至少一高花有止，不排斥 3NT
        # 1♣-2♣ → 2♦；1♦-2♦ → 3♣
        if hcp <= 14 and (spade_stop or heart_stop):
            other_level = 2 if opener_suit == "C" else 3
            other_bid = f"{other_level}{other_minor_sym}"
            if is_legal_response_bid(response_bid, other_bid):
                return BidRecommendation(
                    other_bid,
                    f"同伴低花反加叫 {response_bid} 后，你有 {hcp} HCP（低限）且至少一高花有止，顺叫 {other_bid}，不排斥最终 3NT。牌型：{length_text}。",
                    "低花反加叫后顺叫低花",
                )

        # 重叫开叫低花（12-14 HCP）：低限，高花无止
        rebid_minor = f"3{opening_strain}"
        if hcp <= 14 and is_legal_response_bid(response_bid, rebid_minor):
            return BidRecommendation(
                rebid_minor,
                f"同伴低花反加叫 {response_bid} 后，你有 {hcp} HCP（低限）且高花无止，叫 {rebid_minor} 低限止叫。牌型：{length_text}。",
                "低花反加叫后低限重叫低花",
            )

        # 高限牌但未命中既有分支（例如无高花短门且不在 2NT/3NT 处理范围）时，
        # 仍可通过再叫低花继续描述，避免误标为“低限”。
        if is_legal_response_bid(response_bid, rebid_minor):
            return BidRecommendation(
                rebid_minor,
                f"同伴低花反加叫 {response_bid} 后，你有 {hcp} HCP（高限），当前不满足 2NT/3NT 或高花短门分支，先以 {rebid_minor} 继续描述牌型。牌型：{length_text}。",
                "低花反加叫后高限继续描述",
            )

    # 一阶低花开叫后，同伴跳加叫到 3m 通常表示限制加叫（约 10-12）。
    # 开叫方均型且有成局实力时优先 3NT，否则以止叫为主，避免误走“再叫第二套”。
    if (
        opening_level == 1
        and opening_strain in {"♣", "♦"}
        and response_contract is not None
        and response_contract[0] == 3
        and response_contract[1] == opening_strain
    ):
        if evaluation.balanced and hcp >= 13 and is_legal_response_bid(response_bid, "3NT"):
            return BidRecommendation(
                "3NT",
                f"同伴跳加叫 {response_bid} 显示低花限制加叫；你有 {hcp} HCP 且均型，优先选择 3NT 成局。牌型：{length_text}。",
                "低花限制加叫后 3NT",
            )
        return BidRecommendation(
            "Pass",
            f"同伴跳加叫 {response_bid} 显示低花限制加叫；你有 {hcp} HCP，当前未到明确 3NT 成局条件，建议止叫 Pass。牌型：{length_text}。",
            "低花限制加叫后止叫",
        )

    # 仅支持同伴新叫出的高花；若同伴已加叫开叫者高花，由上方专用分支处理。
    if response_suit in {"H", "S"} and lengths[response_suit] >= 4 and response_suit != opener_suit:
        level = choose_raise_level(response_level, raise_hcp)
        bid = f"{level}{suit_symbol(response_suit)}"
        return BidRecommendation(
            bid,
            f"同伴应叫 {response_bid}，你有 {hcp} HCP 和 {lengths[response_suit]} 张 {SUIT_NAMES[response_suit]} 支持，优先支持同伴高花，叫 {bid}。牌型：{length_text}。",
            "支持同伴高花",
        )

    # 一阶开叫-一阶应叫后：优先保留可叫的一阶第二套（如 1♣-1♥-1♠）。
    # 特例：同伴应叫 1♥ 且持有 4 张♠ 时，须先于均型 1NT/2NT 再叫 1♠。
    if opening_level == 1 and response_level == 1:
        one_level_second_suit = choose_one_level_second_suit(lengths, opener_suit, response_suit, response_bid)
        if one_level_second_suit is not None:
            one_level_bid = minimum_legal_bid_for_suit(one_level_second_suit, response_bid, minimum_level=1)
            if one_level_bid is not None:
                return BidRecommendation(
                    one_level_bid,
                    f"你开叫 {opening_bid} 后还有 4 张以上第二套 {SUIT_NAMES[one_level_second_suit]}，再叫新花 {one_level_bid} 描述牌型。牌型：{length_text}。",
                    "再叫第二套",
                )

    if evaluation.balanced:
        strong_nt_min = max(17, 18 + game_adjustment)
        weak_nt_max = min(15, 14 + game_adjustment)
        if hcp >= strong_nt_min and is_legal_response_bid(response_bid, "2NT"):
            return BidRecommendation(
                "2NT",
                f"你有 {hcp} HCP 且均型，开叫后再叫 2NT 表示约 18-19 均型强无将牌。牌型：{length_text}。",
                "18-19 均型再叫 2NT",
            )
        if hcp <= weak_nt_max and is_legal_response_bid(response_bid, "1NT"):
            return BidRecommendation(
                "1NT",
                f"你有 {hcp} HCP 且均型，开叫后再叫 1NT 表示最低限均型牌。牌型：{length_text}。",
                "最低限均型再叫 1NT",
            )

    # 一阶开叫-一阶应叫后：均型低限，或非均型且单缺同伴应叫花色，可再叫 1NT。
    opener_length = lengths[opener_suit] if opener_suit is not None else 0
    has_singleton_or_void = min(lengths.values()) <= 1
    shortage_in_response_suit = (
        response_suit in {"H", "S"} and lengths[response_suit] <= 1
    )
    if opening_level == 1 and response_level == 1:
        if (
            12 <= hcp <= 14
            and opener_length <= 5
            and (not has_singleton_or_void or shortage_in_response_suit)
            and is_legal_response_bid(response_bid, "1NT")
        ):
            reason = (
                "牌型单缺同伴应叫花色"
                if shortage_in_response_suit and not evaluation.balanced
                else "牌型无单缺且开叫套不超过 5 张"
            )
            return BidRecommendation(
                "1NT",
                f"你有 {hcp} HCP，一阶开叫后同伴一阶应叫；{reason}，当前没有可叫的一阶第二套，优先再叫 1NT 表示低限并控制叫牌高度。牌型：{length_text}。",
                "一阶序列低限再叫 1NT",
            )

    # 一阶低花开叫后同伴一阶高花应叫：无支持时，非均型恰好 5 张开叫花色可按点力重复 2/3 阶。
    # （6+ 长套仍走后方重复/6-5 第二套逻辑。）
    if (
        opening_level == 1
        and opening_strain in {"♣", "♦"}
        and response_suit in {"H", "S"}
        and response_level == 1
        and opener_suit is not None
        and lengths[opener_suit] == 5
        and not evaluation.balanced
    ):
        rebid_level = 3 if hcp >= 16 else 2
        rebid_opening = f"{rebid_level}{opening_strain}"
        if is_legal_response_bid(response_bid, rebid_opening):
            return BidRecommendation(
                rebid_opening,
                f"你开叫 {opening_bid} 后持有 5 张 {SUIT_NAMES[opener_suit]}（非均型），无同伴高花支持，按点力重复开叫花色 {rebid_opening}。牌型：{length_text}。",
                "重复开叫花色",
            )

    reverse_min_hcp = 16
    second_suit = choose_second_suit(
        lengths,
        opener_suit,
        response_suit,
        opening_bid,
        response_bid,
        hcp,
        reverse_min_hcp,
    )

    # 6-5 两套型时优先展示第二套，避免过早重复开叫花色。
    if (
        opener_suit is not None
        and lengths[opener_suit] >= 6
        and second_suit is not None
        and lengths[second_suit] >= 5
    ):
        bid = minimum_legal_bid_for_suit(second_suit, response_bid, minimum_level=1)
        if bid is not None:
            return BidRecommendation(
                bid,
                f"你开叫 {opening_bid} 后为 6-5 两套型（{SUIT_NAMES[opener_suit]} {lengths[opener_suit]} 张、{SUIT_NAMES[second_suit]} {lengths[second_suit]} 张），优先再叫第二套 {bid} 描述分布。牌型：{length_text}。",
                "再叫第二套",
            )

    if opener_suit is not None and lengths[opener_suit] >= 6:
        bid = minimum_legal_bid_for_suit(opener_suit, response_bid, minimum_level=2)
        if bid is not None:
            return BidRecommendation(
                bid,
                f"你开叫 {opening_bid} 后持有 {lengths[opener_suit]} 张 {SUIT_NAMES[opener_suit]}，无更优支持或无将再叫，重复自己长套 {bid}。牌型：{length_text}。",
                "重复开叫花色",
            )

    if second_suit is not None:
        bid = minimum_legal_bid_for_suit(second_suit, response_bid, minimum_level=1)
        if bid is not None:
            if is_reverse_second_suit(opening_bid, response_bid, bid):
                return BidRecommendation(
                    bid,
                    f"你开叫 {opening_bid} 后再叫新花 {bid}，属于逆叫；你有 {hcp} HCP，达到逆叫常见门槛（约 {reverse_min_hcp}+ HCP），并有 4 张以上第二套 {SUIT_NAMES[second_suit]}。牌型：{length_text}。",
                    "逆叫第二套",
                )
            return BidRecommendation(
                bid,
                f"你开叫 {opening_bid} 后还有 4 张以上第二套 {SUIT_NAMES[second_suit]}，再叫新花 {bid} 描述牌型。牌型：{length_text}。",
                "再叫第二套",
            )

    if opener_suit is not None:
        bid = minimum_legal_bid_for_suit(opener_suit, response_bid, minimum_level=2)
        if bid is not None:
            return BidRecommendation(
                bid,
                f"没有同伴高花支持、均型无将或合适第二套，回到开叫花色 {bid} 作低限再叫。牌型：{length_text}。",
                "回叫开叫花色",
            )

    fallback = next_legal_contract(response_bid, REBID_BIDS)
    return BidRecommendation(
        fallback or "Pass",
        f"当前简化规则没有更精确描述，选择最低合法叫品 {fallback or 'Pass'}。你有 {hcp} HCP，牌型：{length_text}。",
        "最低合法再叫",
    )


def choose_raise_level(response_level: int, hcp: int) -> int:
    if hcp >= 19:
        return 4
    if hcp >= 16:
        return max(3, response_level + 1)
    return max(2, response_level + 1)


def choose_minor_for_major_one_nt_rebid(lengths: dict[str, int]) -> str | None:
    """1M-1NT 后再叫低花：保证至少 3 张；等长时优先较便宜的 ♣。"""
    candidates = [suit for suit in ["C", "D"] if lengths[suit] >= 3]
    if not candidates:
        return None
    return max(candidates, key=lambda suit: (lengths[suit], suit == "C"))


def prefers_minor_suit_transfer(
    hcp: int,
    lengths: dict[str, int],
    minor: str,
    evaluation: HandEvaluation,
) -> bool:
    """1NT 后低花转移：6+ 单套，且弱牌或强牌/极不均型倾向低花定约。

    8-10 HCP 除非非常不平均，否则不走转移（改走 3m 邀 3NT 或直接 3NT）。
    """
    very_unbalanced = min(lengths.values()) <= 1 or lengths[minor] >= 7
    if hcp < 7:
        return True
    if hcp == 7:
        return True
    if 8 <= hcp <= 10:
        return very_unbalanced
    # >10：仅强牌且倾向低花定约时转移；较均型优先无将。
    if evaluation.balanced and not very_unbalanced:
        return False
    return very_unbalanced or not evaluation.balanced


def choose_second_suit(
    lengths: dict[str, int],
    opener_suit: str | None,
    response_suit: str | None,
    opening_bid: str,
    response_bid: str,
    hcp: int,
    reverse_min_hcp: int,
) -> str | None:
    candidates: list[str] = []
    for suit in ["S", "H", "D", "C"]:
        if suit in {opener_suit, response_suit}:
            continue
        if lengths[suit] < 4:
            continue
        bid = minimum_legal_bid_for_suit(suit, response_bid, minimum_level=1)
        if bid is None:
            continue
        if is_reverse_second_suit(opening_bid, response_bid, bid) and hcp < reverse_min_hcp:
            continue
        if bid is not None:
            candidates.append(suit)
    if not candidates:
        return None
    return max(candidates, key=lambda suit: (lengths[suit], ["C", "D", "H", "S"].index(suit)))


def choose_one_level_second_suit(
    lengths: dict[str, int], opener_suit: str | None, response_suit: str | None, response_bid: str
) -> str | None:
    candidates: list[str] = []
    for suit in ["S", "H", "D", "C"]:
        if suit in {opener_suit, response_suit}:
            continue
        if lengths[suit] < 4:
            continue
        bid = minimum_legal_bid_for_suit(suit, response_bid, minimum_level=1)
        if bid is None:
            continue
        contract = parse_contract_bid(bid)
        if contract is not None and contract[0] == 1:
            candidates.append(suit)

    if not candidates:
        return None
    return max(candidates, key=lambda suit: (lengths[suit], ["C", "D", "H", "S"].index(suit)))


def is_reverse_second_suit(opening_bid: str, response_bid: str, rebid_bid: str) -> bool:
    opening_contract = parse_contract_bid(opening_bid)
    response_contract = parse_contract_bid(response_bid)
    rebid_contract = parse_contract_bid(rebid_bid)
    if opening_contract is None or response_contract is None or rebid_contract is None:
        return False

    opening_level, opening_strain = opening_contract
    response_level, _ = response_contract
    rebid_level, rebid_strain = rebid_contract
    if opening_level != 1 or response_level != 1:
        return False
    if rebid_level != 2:
        return False
    if opening_strain == "NT" or rebid_strain == "NT":
        return False
    return STRAIN_ORDER[rebid_strain] > STRAIN_ORDER[opening_strain]


def minimum_legal_bid_for_suit(suit: str, previous_bid: str, minimum_level: int = 1) -> str | None:
    symbol = suit_symbol(suit)
    for level in range(minimum_level, 5):
        bid = f"{level}{symbol}"
        if bid in REBID_BIDS and is_legal_response_bid(previous_bid, bid):
            return bid
    return None


def next_legal_contract(previous_bid: str, choices: list[str]) -> str | None:
    for bid in choices:
        if bid != "Pass" and is_legal_response_bid(previous_bid, bid):
            return bid
    return None


def symbol_to_suit(strain: str) -> str | None:
    return {"♣": "C", "♦": "D", "♥": "H", "♠": "S"}.get(strain)


def choose_major_transfer_side_suit_bid(
    lengths: dict[str, int],
    major_suit: str,
    previous_bid: str,
    min_length: int,
) -> tuple[str, str] | None:
    """Pick a natural side-suit follow-up after major transfer; return (suit, bid)."""
    candidates: list[tuple[str, str, int]] = []
    for suit in ["S", "H", "D", "C"]:
        if suit == major_suit or lengths[suit] < min_length:
            continue
        bid = minimum_legal_bid_for_suit(suit, previous_bid, minimum_level=2)
        if bid is None:
            continue
        candidates.append((suit, bid, lengths[suit]))
    if not candidates:
        return None
    suit_rank = {"S": 4, "H": 3, "D": 2, "C": 1}
    suit, bid, _ = max(candidates, key=lambda item: (item[2], suit_rank[item[0]]))
    return suit, bid


def recommend_after_major_transfer_completion(
    major_suit: str,
    opener_rebid_bid: str,
    evaluation: HandEvaluation,
    nt_resp_invite_low: int,
    nt_resp_invite_high: int,
    nt_resp_game_hcp: int,
    slam_try_hcp: int,
) -> BidRecommendation:
    """1NT 高花转移完成后的应叫者再叫（README 应叫者第二次应叫第6条）。"""
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)
    major_symbol = suit_symbol(major_suit)
    major_name = SUIT_NAMES[major_suit]
    major_label = "红心" if major_suit == "H" else "黑桃"

    # 满贯试探（>=15）：叫新花（保证 3 张）
    if hcp >= slam_try_hcp:
        side = choose_major_transfer_side_suit_bid(lengths, major_suit, opener_rebid_bid, min_length=3)
        if side is not None:
            side_suit, side_bid = side
            return BidRecommendation(
                side_bid,
                (
                    f"{major_label}转移完成后，你有 {hcp} HCP，满贯试探再叫新花 {side_bid}"
                    f"（保证至少 3 张 {SUIT_NAMES[side_suit]}）。牌型：{length_text}。"
                ),
                "转移后满贯试探新花",
            )
        game_bid = f"4{major_symbol}"
        if lengths[major_suit] >= 6 and is_legal_response_bid(opener_rebid_bid, game_bid):
            return BidRecommendation(
                game_bid,
                f"{major_label}转移完成后，你有 {hcp} HCP 和 {lengths[major_suit]} 张{major_name}，无合适新花时先确立成局 {game_bid}。牌型：{length_text}。",
                "转移后高花进局",
            )
        if is_legal_response_bid(opener_rebid_bid, "4NT"):
            return BidRecommendation(
                "4NT",
                f"{major_label}转移完成后，你有 {hcp} HCP，无合适新花时以 4NT 试探满贯。牌型：{length_text}。",
                "转移后满贯试探",
            )

    # 进局牌力（10-14）：4M（6+）/ 3NT（均型，其余默认 3NT）
    if hcp >= nt_resp_game_hcp:
        game_bid = f"4{major_symbol}"
        if lengths[major_suit] >= 6 and is_legal_response_bid(opener_rebid_bid, game_bid):
            return BidRecommendation(
                game_bid,
                f"{major_label}转移完成后，你有 {hcp} HCP 和 {lengths[major_suit]} 张{major_name}，直接进 {game_bid} 封局。牌型：{length_text}。",
                "转移后高花进局",
            )
        if is_legal_response_bid(opener_rebid_bid, "3NT"):
            shape_note = "均型牌，" if evaluation.balanced else ""
            return BidRecommendation(
                "3NT",
                f"{major_label}转移完成后，你有 {hcp} HCP，{shape_note}选择 3NT 进无将局。牌型：{length_text}。",
                "转移后无将进局",
            )

    # 邀叫牌力（8-9）：3M（6+）/ 2NT（均型）/ 第二套（非均型）
    if nt_resp_invite_low <= hcp <= nt_resp_invite_high:
        invite_raise = f"3{major_symbol}"
        if lengths[major_suit] >= 6 and is_legal_response_bid(opener_rebid_bid, invite_raise):
            return BidRecommendation(
                invite_raise,
                f"{major_label}转移完成后，你有 {hcp} HCP 和 {lengths[major_suit]} 张{major_name}，加叫至 {invite_raise} 邀局。牌型：{length_text}。",
                "转移后高花邀局",
            )
        if evaluation.balanced and is_legal_response_bid(opener_rebid_bid, "2NT"):
            return BidRecommendation(
                "2NT",
                f"{major_label}转移完成后，你有 {hcp} HCP 均型牌，叫 2NT 邀局。牌型：{length_text}。",
                "转移后无将邀局",
            )
        side = choose_major_transfer_side_suit_bid(lengths, major_suit, opener_rebid_bid, min_length=4)
        if side is not None:
            side_suit, side_bid = side
            return BidRecommendation(
                side_bid,
                (
                    f"{major_label}转移完成后，你有 {hcp} HCP 非均型牌，再叫第二套 {side_bid}"
                    f"（{SUIT_NAMES[side_suit]} {lengths[side_suit]} 张）邀局。牌型：{length_text}。"
                ),
                "转移后第二套邀局",
            )
        if is_legal_response_bid(opener_rebid_bid, "2NT"):
            return BidRecommendation(
                "2NT",
                f"{major_label}转移完成后，你有 {hcp} HCP，无清晰第二套时叫 2NT 邀局。牌型：{length_text}。",
                "转移后无将邀局",
            )

    return BidRecommendation(
        "Pass",
        f"{major_label}转移完成后，你有 {hcp} HCP（弱牌），建议 Pass。牌型：{length_text}。",
        "转移后止叫",
    )


def choose_stayman_minor_probe_bid(
    lengths: dict[str, int],
    previous_bid: str,
) -> tuple[str, str] | None:
    """Stayman 后无高花配合：5+ 低花且有单缺时，试探 3 阶低花。"""
    if min(lengths.values()) > 1:
        return None
    candidates: list[tuple[str, str, int]] = []
    for suit in ["D", "C"]:
        if lengths[suit] < 5:
            continue
        bid = f"3{suit_symbol(suit)}"
        if not is_legal_response_bid(previous_bid, bid):
            continue
        candidates.append((suit, bid, lengths[suit]))
    if not candidates:
        return None
    suit, bid, _ = max(candidates, key=lambda item: (item[2], item[0] == "D"))
    return suit, bid


def recommend_after_stayman_rebid(
    opener_rebid_bid: str,
    evaluation: HandEvaluation,
    fit_suit: str | None,
    fit_strain: str | None,
    nt_resp_invite_low: int,
    nt_resp_invite_high: int,
    nt_resp_game_hcp: int,
    slam_try_hcp: int,
) -> BidRecommendation:
    """1NT-2♣ Stayman 后应叫者再叫（README 应叫者第二次应叫第7条）。"""
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)
    sequence = f"1NT-2♣-{opener_rebid_bid}"
    has_fit = fit_suit is not None and lengths[fit_suit] >= 4

    # 高花配合：邀局 3M / 进局 4M / 满贯试探 4NT
    if has_fit and fit_suit is not None and fit_strain is not None:
        if hcp >= slam_try_hcp and is_legal_response_bid(opener_rebid_bid, "4NT"):
            return BidRecommendation(
                "4NT",
                f"{sequence} 后，你有 {hcp} HCP 和 {lengths[fit_suit]} 张 {SUIT_NAMES[fit_suit]} 配合，叫 4NT 作关键张问叫试探满贯。牌型：{length_text}。",
                "Stayman 后满贯试探 4NT",
            )
        if hcp >= nt_resp_game_hcp:
            major_game = f"4{fit_strain}"
            if is_legal_response_bid(opener_rebid_bid, major_game):
                return BidRecommendation(
                    major_game,
                    f"{sequence} 后，你有 {hcp} HCP 和 {lengths[fit_suit]} 张 {SUIT_NAMES[fit_suit]} 配合，叫 {major_game} 进高花局。牌型：{length_text}。",
                    "Stayman 后高花进局",
                )
        if nt_resp_invite_low <= hcp <= nt_resp_invite_high:
            major_invite = f"3{fit_strain}"
            if is_legal_response_bid(opener_rebid_bid, major_invite):
                return BidRecommendation(
                    major_invite,
                    f"{sequence} 后，你有 {hcp} HCP 和 {lengths[fit_suit]} 张 {SUIT_NAMES[fit_suit]} 配合，叫 {major_invite} 邀局。牌型：{length_text}。",
                    "Stayman 后高花邀局",
                )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后虽有高花配合，但你仅有 {hcp} HCP，牌力不足以邀局，建议 Pass。牌型：{length_text}。",
            "Stayman 后止叫",
        )

    # 高花不配合：2NT 邀局 / 3NT 进局 / 3 阶低花试探
    deny = opener_rebid_bid == "2♦"
    unsuitable_for_nt = not evaluation.balanced and min(lengths.values()) <= 1
    if hcp >= nt_resp_invite_low and unsuitable_for_nt:
        minor_probe = choose_stayman_minor_probe_bid(lengths, opener_rebid_bid)
        if minor_probe is not None:
            minor_suit, minor_bid = minor_probe
            return BidRecommendation(
                minor_bid,
                (
                    f"{sequence} 后无高花配合；你有 {hcp} HCP、{lengths[minor_suit]} 张 "
                    f"{SUIT_NAMES[minor_suit]} 且有单缺，不适合打无将，叫 {minor_bid} 试探低花进局或满贯。牌型：{length_text}。"
                ),
                "Stayman 后低花试探",
            )

    if (
        hcp >= nt_resp_game_hcp
        and evaluation.balanced
        and is_legal_response_bid(opener_rebid_bid, "3NT")
    ):
        return BidRecommendation(
            "3NT",
            f"{sequence} 后无高花配合；你有 {hcp} HCP 均型牌，叫 3NT 进无将局。牌型：{length_text}。",
            "Stayman 否定后无将进局" if deny else "Stayman 后无将进局",
        )
    if nt_resp_invite_low <= hcp <= nt_resp_invite_high and is_legal_response_bid(opener_rebid_bid, "2NT"):
        return BidRecommendation(
            "2NT",
            f"{sequence} 后无高花配合；你有 {hcp} HCP，叫 2NT 邀局。牌型：{length_text}。",
            "Stayman 否定后无将邀局" if deny else "Stayman 后无将邀局",
        )
    return BidRecommendation(
        "Pass",
        f"{sequence} 后无高花配合；你有 {hcp} HCP，牌力不足以邀局，建议 Pass。牌型：{length_text}。",
        "Stayman 否定后止叫" if deny else "Stayman 后止叫",
    )


def has_inverted_major_stop(evaluation: HandEvaluation, suit: str) -> bool:
    """低花反加叫序列中的高花止张：至少 1 张且含 A/K/Q（与开叫者再叫一致）。"""
    return evaluation.lengths[suit] >= 1 and evaluation.top_honors_by_suit.get(suit, 0) >= 1


def is_major_support_first_response(
    opening_bid: str,
    response_bid: str,
    settings: RuleSettings,
) -> bool:
    """1M 开叫后，第一次应叫是否表示支持开叫高花（README 第3条）。"""
    if opening_bid not in {"1♥", "1♠"}:
        return False
    opening_strain = opening_bid[1:]
    opening_suit = symbol_to_suit(opening_strain)
    assert opening_suit is not None

    # 直接加叫 2M/3M/4M
    if response_bid in {f"2{opening_strain}", f"3{opening_strain}", f"4{opening_strain}"}:
        return True

    # Jacoby 2NT
    if settings.jacoby_2nt_enabled and response_bid == "2NT":
        return True

    # Bergen 3♣/3♦
    if settings.bergen_raises_enabled and response_bid in {"3♣", "3♦"}:
        return True

    # Splinter：跳叫另一高花（3OM）；低花 splinter 与 Bergen 冲突时仅在未启用 Bergen 时识别
    other_major_strain = "♠" if opening_suit == "H" else "♥"
    if response_bid == f"3{other_major_strain}":
        return True
    if not settings.bergen_raises_enabled and response_bid in {"3♣", "3♦"}:
        return True

    return False


def major_support_response_is_maximum(
    opening_bid: str,
    response_bid: str,
    evaluation: HandEvaluation,
    settings: RuleSettings,
) -> bool:
    """判断支持性应叫是否属于该档高限（用于开叫者 3M 邀叫后接受/拒绝）。"""
    hcp = evaluation.hcp
    opening_strain = opening_bid[1:]

    if response_bid == f"2{opening_strain}":
        # 简单加叫约 6-9：高限取上半档
        return hcp >= max(8, settings.responder_simple_raise_max - 1)
    if response_bid == f"3{opening_strain}":
        if settings.bergen_raises_enabled:
            # Bergen 下 3M 为弱跳加叫（约 0-6）：默认低限，不接受邀叫进局
            return False
        # 限制性加叫约 10-12：高限取上限附近
        return hcp >= settings.responder_limit_raise_max
    if response_bid == "3♣":
        return hcp >= settings.responder_bergen_weak_max
    if response_bid == "3♦":
        # Bergen 中等支持本身偏邀叫，对开叫者 3M 通常接受
        return True
    if response_bid == "2NT":
        return True
    if response_bid == f"4{opening_strain}":
        return False
    # Splinter 等：偏强，接受进局
    return True


def recommend_after_major_support_response(
    opening_bid: str,
    response_bid: str,
    opener_rebid_bid: str,
    evaluation: HandEvaluation,
    settings: RuleSettings,
) -> BidRecommendation:
    """1M 开叫且第一次应叫已示支持后，应叫者第二次应叫（README 第3条）。"""
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)
    opening_strain = opening_bid[1:]
    opening_suit = symbol_to_suit(opening_strain)
    assert opening_suit is not None
    sequence = f"{opening_bid}-{response_bid}-{opener_rebid_bid}"
    major_three = f"3{opening_strain}"
    major_four = f"4{opening_strain}"
    opener_rebid_contract = parse_contract_bid(opener_rebid_bid)

    # 开叫者 4M：进局止叫
    if opener_rebid_bid == major_four:
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者已进局 {major_four}，建议止叫 Pass。你有 {hcp} HCP，牌型：{length_text}。",
            "支持后再叫高花止叫",
        )

    # 开叫者 3M：邀叫；低限 Pass，高限 4M
    if opener_rebid_bid == major_three:
        if major_support_response_is_maximum(opening_bid, response_bid, evaluation, settings):
            if is_legal_response_bid(opener_rebid_bid, major_four):
                return BidRecommendation(
                    major_four,
                    f"{sequence} 后开叫者以 {major_three} 邀局；你第一次应叫属高限（{hcp} HCP），叫 {major_four} 接受。牌型：{length_text}。",
                    "支持后再叫高花进局",
                )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者以 {major_three} 邀局；你第一次应叫属低限（{hcp} HCP），建议止叫 Pass。牌型：{length_text}。",
            "支持后再叫高花止叫",
        )

    # 开叫者出新花：有配合（新花 4+）→ 4M，否则回 3M
    if opener_rebid_contract is not None and opener_rebid_contract[1] != "NT":
        rebid_suit = symbol_to_suit(opener_rebid_contract[1])
        if rebid_suit is not None and rebid_suit != opening_suit:
            has_new_suit_fit = lengths[rebid_suit] >= 4
            if has_new_suit_fit and is_legal_response_bid(opener_rebid_bid, major_four):
                return BidRecommendation(
                    major_four,
                    f"{sequence} 后开叫者再叫新花；你有 {lengths[rebid_suit]} 张配合，叫 {major_four} 进局。牌型：{length_text}。",
                    "支持后新花有配合进局",
                )
            if is_legal_response_bid(opener_rebid_bid, major_three):
                return BidRecommendation(
                    major_three,
                    f"{sequence} 后开叫者再叫新花；你无足够新花配合，回到 {major_three}。牌型：{length_text}。",
                    "支持后新花无配合回加",
                )
            if is_legal_response_bid(opener_rebid_bid, major_four):
                return BidRecommendation(
                    major_four,
                    f"{sequence} 后开叫者再叫新花；无法回到 3 阶，叫 {major_four}。牌型：{length_text}。",
                    "支持后新花进局",
                )

    return BidRecommendation(
        "Pass",
        f"{sequence} 后，当前简化体系对支持后再叫未覆盖该叫品，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
        "支持后再叫止叫",
    )


def recommend_after_major_forcing_one_nt(
    opening_bid: str,
    opener_rebid_bid: str,
    evaluation: HandEvaluation,
) -> BidRecommendation:
    """1M-1NT（逼叫一轮）后应叫者第二次应叫（README 第5条）。"""
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)
    balanced = evaluation.balanced
    opening_contract = parse_contract_bid(opening_bid)
    assert opening_contract is not None
    opening_strain = opening_contract[1]
    opening_suit = symbol_to_suit(opening_strain)
    assert opening_suit is not None
    sequence = f"{opening_bid}-1NT-{opener_rebid_bid}"
    major_two = f"2{opening_strain}"
    major_three = f"3{opening_strain}"
    major_four = f"4{opening_strain}"
    # 1NT 应叫约 5-12：10-11/12 为高限；9HCP 有单缺可视作高限帮助
    max_values = hcp >= 10
    gameish = hcp >= 11
    has_shortage = min(lengths.values()) <= 1
    three_card_major_support = lengths[opening_suit] >= 3
    two_card_major_help = lengths[opening_suit] >= 2
    # 2M 后再叫：高限有帮助=10-11 有 2+，或 9 有单缺且 2+
    two_major_can_invite_major = two_card_major_help and (
        max_values or (hcp == 9 and has_shortage)
    )

    def best_long_minor_bid() -> str | None:
        """非均型且 5+ 低花长套时，选更长的 3m（等长优先 ♣）。"""
        if balanced:
            return None
        club_len = lengths["C"]
        diamond_len = lengths["D"]
        if club_len < 5 and diamond_len < 5:
            return None
        if club_len >= diamond_len and club_len >= 5 and is_legal_response_bid(opener_rebid_bid, "3♣"):
            return "3♣"
        if diamond_len >= 5 and is_legal_response_bid(opener_rebid_bid, "3♦"):
            return "3♦"
        return None

    def best_own_quality_suit_bid(exclude_suit: str) -> str | None:
        """5+ 好套（至少 1 个顶张大牌），排除开叫者再叫低花。"""
        candidates = [
            suit
            for suit in ["S", "H", "D", "C"]
            if suit != exclude_suit
            and lengths[suit] >= 5
            and evaluation.top_honors_by_suit.get(suit, 0) >= 1
        ]
        if not candidates:
            return None
        # 更长优先；等长时优先高花、再优先黑桃
        suit = max(candidates, key=lambda s: (lengths[s], s in {"S", "H"}, s == "S"))
        return minimum_legal_bid_for_suit(suit, opener_rebid_bid)

    # 开叫者 3NT：11-12 → 4NT 邀叫，否则 Pass
    if opener_rebid_bid == "3NT":
        if 11 <= hcp <= 12 and is_legal_response_bid(opener_rebid_bid, "4NT"):
            return BidRecommendation(
                "4NT",
                f"{sequence} 后开叫者已落 3NT，你有 {hcp} HCP（高限），叫 4NT 邀叫。牌型：{length_text}。",
                "1M-1NT 后无将邀局",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者已落 3NT，你有 {hcp} HCP，建议止叫 Pass。牌型：{length_text}。",
            "1M-1NT 后无将止叫",
        )

    # 开叫者 2NT（17-18）
    if opener_rebid_bid == "2NT":
        # 约 8+：有 3 张支持且非均型 → 4M；10+ 低花长套非均型 → 3m；否则 3NT
        if hcp >= 8:
            if (
                three_card_major_support
                and not balanced
                and is_legal_response_bid(opener_rebid_bid, major_four)
            ):
                return BidRecommendation(
                    major_four,
                    f"{sequence} 后开叫者 2NT 约 17-18；你有 {hcp} HCP、{lengths[opening_suit]} 张支持和非均型，叫 {major_four}。牌型：{length_text}。",
                    "1M-1NT 后高花进局",
                )
            if hcp >= 10:
                minor_bid = best_long_minor_bid()
                if minor_bid is not None:
                    return BidRecommendation(
                        minor_bid,
                        f"{sequence} 后开叫者 2NT；你有 {hcp} HCP 与低花长套（非均型），叫 {minor_bid} 试探低花成局/满贯。牌型：{length_text}。",
                        "1M-1NT 后低花试探",
                    )
            if is_legal_response_bid(opener_rebid_bid, "3NT"):
                return BidRecommendation(
                    "3NT",
                    f"{sequence} 后开叫者 2NT 约 17-18，你有 {hcp} HCP，叫 3NT 成局。牌型：{length_text}。",
                    "1M-1NT 后无将进局",
                )
        # 6-7：有 3 张支持且非均型 → 3M，否则 Pass
        if 6 <= hcp <= 7:
            if (
                three_card_major_support
                and not balanced
                and is_legal_response_bid(opener_rebid_bid, major_three)
            ):
                return BidRecommendation(
                    major_three,
                    f"{sequence} 后开叫者 2NT；你有 {hcp} HCP、{lengths[opening_suit]} 张支持和非均型，叫 {major_three}。牌型：{length_text}。",
                    "1M-1NT 后高花邀局",
                )
            return BidRecommendation(
                "Pass",
                f"{sequence} 后开叫者 2NT 约 17-18，你有 {hcp} HCP，建议止叫 Pass。牌型：{length_text}。",
                "1M-1NT 后无将止叫",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者 2NT 约 17-18，你有 {hcp} HCP（偏低），建议止叫 Pass。牌型：{length_text}。",
            "1M-1NT 后无将止叫",
        )

    # 开叫者 2M：重复 6+ 原花色
    # 低限(5-8 / 9均型) Pass；高限有 2+/3 张支持（10-11，或 9 有单缺）→ 3M；高限无帮助 → 2NT
    if opener_rebid_bid == major_two:
        if two_major_can_invite_major and is_legal_response_bid(opener_rebid_bid, major_three):
            return BidRecommendation(
                major_three,
                f"{sequence} 后开叫者重复高花示 6+ 张；你有 {hcp} HCP 和 {lengths[opening_suit]} 张帮助，叫 {major_three} 邀局。牌型：{length_text}。",
                "1M-1NT 后高花邀局",
            )
        if max_values and not two_card_major_help and is_legal_response_bid(opener_rebid_bid, "2NT"):
            return BidRecommendation(
                "2NT",
                f"{sequence} 后开叫者重复高花；你有 {hcp} HCP 但无足够帮助，叫 2NT 邀无将局。牌型：{length_text}。",
                "1M-1NT 后无将邀局",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者重复高花，你有 {hcp} HCP，建议止叫 Pass。牌型：{length_text}。",
            "1M-1NT 后高花止叫",
        )

    # 1♠-1NT-2♥：开叫者示 4 心
    if opening_bid == "1♠" and opener_rebid_bid == "2♥":
        if lengths["H"] >= 4:
            if gameish and is_legal_response_bid(opener_rebid_bid, "4♥"):
                return BidRecommendation(
                    "4♥",
                    f"{sequence} 后开叫者再叫 2♥ 示 4 心；你有 {lengths['H']} 张红心和 {hcp} HCP，叫 4♥ 进局。牌型：{length_text}。",
                    "1M-1NT 后红心进局",
                )
            if max_values and is_legal_response_bid(opener_rebid_bid, "3♥"):
                return BidRecommendation(
                    "3♥",
                    f"{sequence} 后开叫者再叫 2♥ 示 4 心；你有 {lengths['H']} 张红心和 {hcp} HCP，叫 3♥ 邀局。牌型：{length_text}。",
                    "1M-1NT 后红心邀局",
                )
            return BidRecommendation(
                "Pass",
                f"{sequence} 后开叫者再叫 2♥，你有红心配合但牌力有限，建议止叫 Pass。牌型：{length_text}。",
                "1M-1NT 后红心止叫",
            )
        if lengths["S"] >= 2 and is_legal_response_bid(opener_rebid_bid, "2♠"):
            return BidRecommendation(
                "2♠",
                f"{sequence} 后开叫者再叫 2♥；你无 4 心但有 {lengths['S']} 张黑桃，叫 2♠ 偏好开叫花色。牌型：{length_text}。",
                "1M-1NT 后偏好黑桃",
            )
        if max_values and is_legal_response_bid(opener_rebid_bid, "2NT"):
            return BidRecommendation(
                "2NT",
                f"{sequence} 后开叫者再叫 2♥；你无明确配合，有 {hcp} HCP，叫 2NT 邀局。牌型：{length_text}。",
                "1M-1NT 后无将邀局",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者再叫 2♥，你有 {hcp} HCP，建议止叫 Pass。牌型：{length_text}。",
            "1M-1NT 后止叫",
        )

    # 开叫者 2♣/2♦：新低花（保证 3 张）
    # 5+ 低花配合（或 4441 且该低花 4 张）→ Pass/加叫；5+ 好套 → 叫出自己的套；高限 3 张支持 → 3M；高限无支持 → 2NT；否则 2M
    if opener_rebid_bid in {"2♣", "2♦"}:
        minor_suit = symbol_to_suit(opener_rebid_bid[1:])
        assert minor_suit is not None
        minor_three = f"3{opener_rebid_bid[1:]}"
        # 5+ 低花配合，或 4441 且在该低花有 4 张
        is_4441 = sorted(lengths.values(), reverse=True) == [4, 4, 4, 1]
        has_minor_fit = lengths[minor_suit] >= 5 or (is_4441 and lengths[minor_suit] >= 4)
        three_card_opening_support = lengths[opening_suit] >= 3

        if has_minor_fit:
            if max_values and is_legal_response_bid(opener_rebid_bid, minor_three):
                return BidRecommendation(
                    minor_three,
                    f"{sequence} 后开叫者再叫低花；你有 {lengths[minor_suit]} 张配合和 {hcp} HCP，加叫 {minor_three}。牌型：{length_text}。",
                    "1M-1NT 后低花邀局",
                )
            return BidRecommendation(
                "Pass",
                f"{sequence} 后开叫者再叫低花，你有 {lengths[minor_suit]} 张配合，接受低花并止叫 Pass。牌型：{length_text}。",
                "1M-1NT 后低花止叫",
            )

        own_suit_bid = best_own_quality_suit_bid(minor_suit)
        if own_suit_bid is not None:
            return BidRecommendation(
                own_suit_bid,
                f"{sequence} 后开叫者再叫低花；你有 5+ 好套（含顶张），叫出自己的套 {own_suit_bid}。牌型：{length_text}。",
                "1M-1NT 后自报好套",
            )

        if max_values and three_card_opening_support and is_legal_response_bid(opener_rebid_bid, major_three):
            return BidRecommendation(
                major_three,
                f"{sequence} 后开叫者再叫低花；你有 {hcp} HCP 与 3 张开叫花色支持，叫 {major_three} 邀局。牌型：{length_text}。",
                "1M-1NT 后高花邀局",
            )
        if max_values and is_legal_response_bid(opener_rebid_bid, "2NT"):
            return BidRecommendation(
                "2NT",
                f"{sequence} 后开叫者再叫低花；你有 {hcp} HCP 但无 3 张开叫花色支持，叫 2NT 邀局。牌型：{length_text}。",
                "1M-1NT 后无将邀局",
            )
        if is_legal_response_bid(opener_rebid_bid, major_two):
            return BidRecommendation(
                major_two,
                f"{sequence} 后开叫者再叫低花；当前偏好开叫花色，再叫 {major_two}。牌型：{length_text}。",
                "1M-1NT 后偏好高花",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者再叫低花，你有 {hcp} HCP，建议止叫 Pass。牌型：{length_text}。",
            "1M-1NT 后止叫",
        )

    return BidRecommendation(
        "Pass",
        f"{sequence} 后，当前简化体系未覆盖该开叫者再叫，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
        "1M-1NT 后止叫",
    )


def recommend_after_inverted_minor_responder_rebid(
    opening_bid: str,
    response_bid: str,
    opener_rebid_bid: str,
    evaluation: HandEvaluation,
) -> BidRecommendation:
    """低花反加叫开启且 1m-2m 后，应叫者第二次应叫（README 第6条）。"""
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)
    sequence = f"{opening_bid}-{response_bid}-{opener_rebid_bid}"
    opening_contract = parse_contract_bid(opening_bid)
    assert opening_contract is not None
    opening_strain = opening_contract[1]
    opening_suit = symbol_to_suit(opening_strain)
    assert opening_suit is not None
    minor_game = f"5{opening_strain}"
    minor_raise_4 = f"4{opening_strain}"
    minor_signoff_3 = f"3{opening_strain}"
    spade_stop = has_inverted_major_stop(evaluation, "S")
    heart_stop = has_inverted_major_stop(evaluation, "H")
    both_stops = spade_stop and heart_stop

    # 开叫者 3NT：通常 Pass；极强牌试探满贯
    if opener_rebid_bid == "3NT":
        if hcp >= 18 and is_legal_response_bid(opener_rebid_bid, "6NT"):
            return BidRecommendation(
                "6NT",
                f"{sequence} 后开叫者已落 3NT，你有 {hcp} HCP，直接接受进 6NT。牌型：{length_text}。",
                "反加叫后接受大满贯",
            )
        if hcp >= 16 and is_legal_response_bid(opener_rebid_bid, "4NT"):
            return BidRecommendation(
                "4NT",
                f"{sequence} 后开叫者已落 3NT，你有 {hcp} HCP，叫 4NT 试探满贯。牌型：{length_text}。",
                "反加叫后满贯试探",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者已落 3NT，你有 {hcp} HCP，建议止叫 Pass。牌型：{length_text}。",
            "反加叫后无将止叫",
        )

    # 开叫者 5NT：邀 6NT
    if opener_rebid_bid == "5NT":
        if hcp >= 13 and is_legal_response_bid(opener_rebid_bid, "6NT"):
            return BidRecommendation(
                "6NT",
                f"{sequence} 后开叫者以 5NT 邀请 6NT，你有 {hcp} HCP，接受进 6NT。牌型：{length_text}。",
                "反加叫后接受 6NT",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者以 5NT 邀请 6NT，你有 {hcp} HCP（最低限），拒绝并止叫 Pass。牌型：{length_text}。",
            "反加叫后拒绝 6NT",
        )

    # 开叫者 4NT：以开叫低花为将的 A 张问叫（简化：回到 5m）
    if opener_rebid_bid == "4NT":
        if is_legal_response_bid(opener_rebid_bid, minor_game):
            return BidRecommendation(
                minor_game,
                f"{sequence} 后开叫者 4NT 问 A 张，当前简化体系回到开叫低花 {minor_game}。牌型：{length_text}。",
                "反加叫后回答 4NT",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者 4NT 问 A 张，当前无法继续描述，建议 Pass。牌型：{length_text}。",
            "反加叫后止叫",
        )

    # 开叫者 2NT：两高花有止，倾向 3NT
    if opener_rebid_bid == "2NT":
        if hcp >= 16 and is_legal_response_bid(opener_rebid_bid, "4NT"):
            return BidRecommendation(
                "4NT",
                f"{sequence} 后开叫者 2NT 显示两高花有止，你有 {hcp} HCP，叫 4NT 试探满贯。牌型：{length_text}。",
                "反加叫后满贯试探",
            )
        if is_legal_response_bid(opener_rebid_bid, "3NT"):
            return BidRecommendation(
                "3NT",
                f"{sequence} 后开叫者 2NT 显示两高花有止并倾向无将，你有 {hcp} HCP，叫 3NT 成局。牌型：{length_text}。",
                "反加叫后无将进局",
            )

    # 开叫者重叫 3m：低限且高花无止
    if opener_rebid_bid == minor_signoff_3:
        if both_stops and is_legal_response_bid(opener_rebid_bid, "3NT"):
            return BidRecommendation(
                "3NT",
                f"{sequence} 后开叫者重叫低花显示低限且高花无止；你有两高花止张和 {hcp} HCP，叫 3NT。牌型：{length_text}。",
                "反加叫后无将进局",
            )
        if hcp >= 14 and is_legal_response_bid(opener_rebid_bid, minor_game):
            return BidRecommendation(
                minor_game,
                f"{sequence} 后开叫者重叫低花且高花无止；你有 {hcp} HCP，加叫到 {minor_game} 进低花局。牌型：{length_text}。",
                "反加叫后低花进局",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者重叫低花显示低限且高花无止；你无两高花止张，建议止叫 Pass。牌型：{length_text}。",
            "反加叫后低花止叫",
        )

    # 开叫者顺叫另一低花：低限，至少一门高花有止
    other_minor_rebids = {"2♦"} if opening_suit == "C" else {"3♣"}
    if opener_rebid_bid in other_minor_rebids:
        if spade_stop or heart_stop:
            prefer_game = both_stops or hcp >= 13
            if prefer_game and is_legal_response_bid(opener_rebid_bid, "3NT"):
                return BidRecommendation(
                    "3NT",
                    f"{sequence} 后开叫者顺叫另一低花示低限有止；你有高花止张和 {hcp} HCP，叫 3NT。牌型：{length_text}。",
                    "反加叫后无将进局",
                )
            if is_legal_response_bid(opener_rebid_bid, "2NT"):
                return BidRecommendation(
                    "2NT",
                    f"{sequence} 后开叫者顺叫另一低花；你有部分高花止张和 {hcp} HCP，叫 2NT 邀无将局。牌型：{length_text}。",
                    "反加叫后无将邀局",
                )
            if is_legal_response_bid(opener_rebid_bid, "3NT"):
                return BidRecommendation(
                    "3NT",
                    f"{sequence} 后开叫者顺叫另一低花；你有高花止张和 {hcp} HCP，叫 3NT。牌型：{length_text}。",
                    "反加叫后无将进局",
                )
        if hcp >= 14 and is_legal_response_bid(opener_rebid_bid, minor_game):
            return BidRecommendation(
                minor_game,
                f"{sequence} 后开叫者顺叫另一低花；你无足够高花止张，有 {hcp} HCP，进 {minor_game}。牌型：{length_text}。",
                "反加叫后低花进局",
            )
        if is_legal_response_bid(opener_rebid_bid, minor_signoff_3):
            return BidRecommendation(
                minor_signoff_3,
                f"{sequence} 后开叫者顺叫另一低花；你无足够高花止张，回到开叫低花 {minor_signoff_3}。牌型：{length_text}。",
                "反加叫后回到低花",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者顺叫另一低花；当前无更合适叫品，建议 Pass。牌型：{length_text}。",
            "反加叫后止叫",
        )

    # 开叫者 2M 报单缺（15-17 满贯试探）/ 3M Splinter（18-21）
    if opener_rebid_bid in {"2♥", "2♠", "3♥", "3♠"}:
        short_strain = opener_rebid_bid[1:]
        short_suit = symbol_to_suit(short_strain)
        other_major = "S" if short_suit == "H" else "H"
        other_stop = has_inverted_major_stop(evaluation, other_major)
        is_splinter = opener_rebid_bid in {"3♥", "3♠"}
        slam_hcp = 13 if is_splinter else 14

        if hcp >= slam_hcp and is_legal_response_bid(opener_rebid_bid, "4NT"):
            return BidRecommendation(
                "4NT",
                f"{sequence} 后开叫者{'Splinter' if is_splinter else '报单缺'}试探满贯，你有 {hcp} HCP，叫 4NT 问 A 张。牌型：{length_text}。",
                "反加叫后满贯试探",
            )
        if other_stop and is_legal_response_bid(opener_rebid_bid, "3NT"):
            return BidRecommendation(
                "3NT",
                f"{sequence} 后开叫者在 {SUIT_NAMES[short_suit]} 示单缺；你有另一高花止张和 {hcp} HCP，叫 3NT。牌型：{length_text}。",
                "反加叫后无将进局",
            )
        if hcp >= slam_hcp and is_legal_response_bid(opener_rebid_bid, minor_game):
            return BidRecommendation(
                minor_game,
                f"{sequence} 后开叫者试探满贯；你有 {hcp} HCP 但无将不理想，进低花局 {minor_game}。牌型：{length_text}。",
                "反加叫后低花进局",
            )
        if is_legal_response_bid(opener_rebid_bid, minor_raise_4):
            return BidRecommendation(
                minor_raise_4,
                f"{sequence} 后开叫者试探满贯；你牌力有限，先加到 {minor_raise_4}。牌型：{length_text}。",
                "反加叫后低花继续",
            )
        if is_legal_response_bid(opener_rebid_bid, minor_signoff_3):
            return BidRecommendation(
                minor_signoff_3,
                f"{sequence} 后开叫者试探满贯；你牌力有限，回到 {minor_signoff_3}。牌型：{length_text}。",
                "反加叫后回到低花",
            )
        return BidRecommendation(
            "Pass",
            f"{sequence} 后开叫者试探满贯；当前无更合适叫品，建议 Pass。牌型：{length_text}。",
            "反加叫后止叫",
        )

    return BidRecommendation(
        "Pass",
        f"{sequence} 后，当前简化体系未覆盖该开叫者再叫，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
        "反加叫后止叫",
    )


def recommend_responder_rebid(
    opening_bid: str,
    response_bid: str,
    opener_rebid_bid: str,
    evaluation: HandEvaluation,
    settings: RuleSettings | None = None,
    vulnerability: str | None = None,
) -> BidRecommendation:
    settings = settings or default_rule_settings()
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)

    response_contract = parse_contract_bid(response_bid)
    opener_rebid_contract = parse_contract_bid(opener_rebid_bid)

    # 拼搏式 3NT：开叫者可能再叫 Pass（确认梅花），需在合约解析兜底之前处理。
    if opening_bid == "3NT" and response_contract is not None:
        previous_for_legal = response_bid if opener_rebid_bid == "Pass" else opener_rebid_bid
        if response_bid == "4♣" and opener_rebid_bid == "Pass":
            if hcp >= 16 and is_legal_response_bid(previous_for_legal, "5♣"):
                return BidRecommendation(
                    "5♣",
                    f"拼搏式 3NT-4♣ 后开叫者 Pass 确认梅花，你有 {hcp} HCP，加叫到 5♣。牌型：{length_text}。",
                    "拼搏式 3NT 后进低花局",
                )
            return BidRecommendation(
                "Pass",
                f"拼搏式 3NT-4♣ 后开叫者 Pass 确认梅花，当前牌力以止叫为主，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
                "拼搏式 3NT 后止叫",
            )
        if response_bid == "4♣" and opener_rebid_bid == "4♦":
            if hcp >= 16 and is_legal_response_bid(opener_rebid_bid, "5♦"):
                return BidRecommendation(
                    "5♦",
                    f"拼搏式 3NT-4♣-4♦ 后确认方块，你有 {hcp} HCP，加叫到 5♦。牌型：{length_text}。",
                    "拼搏式 3NT 后进低花局",
                )
            return BidRecommendation(
                "Pass",
                f"拼搏式 3NT-4♣-4♦ 后确认方块，当前牌力以止叫为主，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
                "拼搏式 3NT 后止叫",
            )
        if response_bid == "4♦" and opener_rebid_bid in {"4♥", "4♠", "5♣", "5♦"}:
            if hcp >= 18 and opener_rebid_bid in {"5♣", "5♦"}:
                slam = f"6{opener_rebid_bid[1:]}"
                if is_legal_response_bid(opener_rebid_bid, slam):
                    return BidRecommendation(
                        slam,
                        f"拼搏式 3NT-4♦-{opener_rebid_bid} 后，你有 {hcp} HCP，尝试低花小满贯 {slam}。牌型：{length_text}。",
                        "拼搏式 3NT 后试探满贯",
                    )
            return BidRecommendation(
                "Pass",
                f"拼搏式 3NT-4♦-{opener_rebid_bid} 后，当前简化体系以止叫为主，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
                "拼搏式 3NT 后止叫",
            )
        if response_bid in {"4♥", "4♠"}:
            return BidRecommendation(
                "Pass",
                f"拼搏式 3NT 后你已叫出高花成局 {response_bid}，开叫者再叫 {opener_rebid_bid} 后通常止叫。你有 {hcp} HCP，牌型：{length_text}。",
                "拼搏式 3NT 后止叫",
            )
        return BidRecommendation(
            "Pass",
            f"拼搏式 3NT 序列中同伴再叫 {opener_rebid_bid}，当前简化体系建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
            "拼搏式 3NT 后止叫",
        )

    if opener_rebid_contract is None or response_contract is None:
        return BidRecommendation(
            "Pass",
            f"当前序列无法识别为标准合约叫品，默认 Pass。你有 {hcp} HCP，牌型：{length_text}。",
            "无有效序列默认 Pass",
        )

    opener_strain = opener_rebid_contract[1]
    opener_suit = symbol_to_suit(opener_strain)
    opening_contract = parse_contract_bid(opening_bid)
    if opening_contract is not None:
        opening_level, opening_strain = opening_contract
        is_weak_two_opening = opening_level == 2 and opening_strain in {"♦", "♥", "♠"}
        is_three_plus_preempt_opening = opening_level >= 3 and opening_strain in {"♣", "♦", "♥", "♠"}

        if is_three_plus_preempt_opening:
            return BidRecommendation(
                "Pass",
                f"阻击开叫序列中同伴已再叫 {opener_rebid_bid}，当前简化体系以止叫为主，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
                "阻击后止叫",
            )
        if is_weak_two_opening and response_bid == "2NT" and settings.august_2nt_enabled:
            opening_suit = symbol_to_suit(opening_strain)
            ogust_minimum_answers = {"3♣", "3♦"}
            ogust_maximum_answers = {"3♥", "3♠", "3NT"}
            if opener_rebid_bid == "3NT":
                return BidRecommendation(
                    "Pass",
                    f"弱二开叫经 Ogust 2NT 问叫后，开叫者已用 3NT 显示高限强套并落在成局，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
                    "Ogust 后止叫",
                )

            if opener_rebid_bid in ogust_minimum_answers | ogust_maximum_answers:
                if opening_suit is not None:
                    has_major_support = opening_suit in {"H", "S"} and lengths[opening_suit] >= 3
                    is_maximum_answer = opener_rebid_bid in ogust_maximum_answers

                    # Ogust 分档（常见简化）：
                    # 低限回答（3♣/3♦）：有配合约 12-14 邀局，15+ 进局；无配合均型约 13+ 尝试 3NT。
                    # 高限回答（3♥/3♠/3NT）：有配合约 10-11 邀局，12+ 进局；无配合均型约 11+ 尝试 3NT。
                    major_game_hcp = 12 if is_maximum_answer else 15
                    major_invite_low = 10 if is_maximum_answer else 12
                    major_invite_high = major_game_hcp - 1
                    nt_game_hcp = 11 if is_maximum_answer else 13

                    if has_major_support:
                        major_game_bid = f"4{suit_symbol(opening_suit)}"
                        major_invite_bid = f"3{suit_symbol(opening_suit)}"
                        if hcp >= major_game_hcp and is_legal_response_bid(opener_rebid_bid, major_game_bid):
                            return BidRecommendation(
                                major_game_bid,
                                f"弱二开叫经 Ogust 2NT 后，开叫者再叫 {opener_rebid_bid}（{'高限' if is_maximum_answer else '低限'}）；你有 {hcp} HCP 且有 3+ 张将牌支持，按分档直接进局 {major_game_bid}。牌型：{length_text}。",
                                "Ogust 后高花进局",
                            )
                        if major_invite_low <= hcp <= major_invite_high and is_legal_response_bid(opener_rebid_bid, major_invite_bid):
                            return BidRecommendation(
                                major_invite_bid,
                                f"弱二开叫经 Ogust 2NT 后，开叫者再叫 {opener_rebid_bid}（{'高限' if is_maximum_answer else '低限'}）；你有 {hcp} HCP 且有 3+ 张将牌支持，按分档先邀局 {major_invite_bid}。牌型：{length_text}。",
                                "Ogust 后高花邀局",
                            )

                    if evaluation.balanced and hcp >= nt_game_hcp and is_legal_response_bid(opener_rebid_bid, "3NT"):
                        return BidRecommendation(
                            "3NT",
                            f"弱二开叫经 Ogust 2NT 后，开叫者再叫 {opener_rebid_bid}（{'高限' if is_maximum_answer else '低限'}）；你有 {hcp} HCP 且均型，按分档转入 3NT。牌型：{length_text}。",
                            "Ogust 后无将进局",
                        )

                return BidRecommendation(
                    "Pass",
                    f"弱二开叫经 Ogust 2NT 问叫后，开叫者再叫 {opener_rebid_bid}；当前牌力与配合不足继续推进，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
                    "Ogust 后止叫",
                )

        if is_weak_two_opening:
            return BidRecommendation(
                "Pass",
                f"弱二开叫序列中同伴已再叫 {opener_rebid_bid}，当前简化体系默认止叫，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
                "弱二后止叫",
            )

    game_adjustment = game_threshold_adjustment(vulnerability, settings)
    nt_game_hcp = max(11, 13 + game_adjustment)
    nt_invite_low = max(7, 10 + game_adjustment)
    nt_invite_high = nt_game_hcp - 1
    raise_hcp = hcp - game_adjustment

    # 1M-1NT（逼叫一轮）后：按开叫者再叫继续
    if opening_bid in {"1♥", "1♠"} and response_bid == "1NT":
        return recommend_after_major_forcing_one_nt(
            opening_bid,
            opener_rebid_bid,
            evaluation,
        )

    # 1M 开叫后第一次应叫已示支持：按开叫者再叫继续（README 第3条）
    if is_major_support_first_response(opening_bid, response_bid, settings):
        return recommend_after_major_support_response(
            opening_bid,
            response_bid,
            opener_rebid_bid,
            evaluation,
            settings,
        )

    # 低花反加叫开启且 1m-2m：按开叫者再叫语义继续
    if (
        settings.inverted_minors_enabled
        and opening_contract is not None
        and opening_contract[0] == 1
        and opening_contract[1] in {"♣", "♦"}
        and response_contract[0] == 2
        and response_contract[1] == opening_contract[1]
    ):
        return recommend_after_inverted_minor_responder_rebid(
            opening_bid,
            response_bid,
            opener_rebid_bid,
            evaluation,
        )

    # 1NT 开叫后的序列：1NT - 2♣(Stayman) / 2♦(红心转移) / 2♥(黑桃转移) - 开叫者应答
    if opening_bid == "1NT":
        game_adjustment_nt = game_threshold_adjustment(vulnerability, settings)
        # 1NT 约 15-17 HCP，应叫者进局门槛：合计 25 HCP，即应叫者约需 8-10 HCP；邀局约 8-9 HCP
        nt_resp_game_hcp = max(8, 10 + game_adjustment_nt)
        nt_resp_invite_low = max(6, 8 + game_adjustment_nt)
        nt_resp_invite_high = nt_resp_game_hcp - 1

        nt_resp_slam_hcp = max(15, 15 + game_adjustment_nt)

        # Stayman：1NT - 2♣ - 2♦/2♥/2♠
        # 有配合：3M 邀局 / 4M 进局 / 4NT 满贯；无配合：2NT / 3NT / 3m 低花试探
        if response_bid == "2♣" and opener_rebid_bid in {"2♦", "2♥", "2♠"}:
            fit_suit: str | None = None
            fit_strain: str | None = None
            if opener_rebid_bid in {"2♥", "2♠"} and opener_suit is not None:
                fit_suit = opener_suit
                fit_strain = opener_strain
            return recommend_after_stayman_rebid(
                opener_rebid_bid,
                evaluation,
                fit_suit,
                fit_strain,
                nt_resp_invite_low,
                nt_resp_invite_high,
                nt_resp_game_hcp,
                nt_resp_slam_hcp,
            )

        # 转移序列：1NT - 2♦ - 2♥ / 1NT - 2♥ - 2♠（高花转移完成）
        # 弱牌(<7) Pass；邀叫(8-9) 3M/2NT/第二套；进局(10-14) 4M/3NT；满贯试探(>=15) 新花
        if response_bid == "2♦" and opener_rebid_bid == "2♥":
            return recommend_after_major_transfer_completion(
                "H",
                opener_rebid_bid,
                evaluation,
                nt_resp_invite_low,
                nt_resp_invite_high,
                nt_resp_game_hcp,
                nt_resp_slam_hcp,
            )
        if response_bid == "2♥" and opener_rebid_bid == "2♠":
            return recommend_after_major_transfer_completion(
                "S",
                opener_rebid_bid,
                evaluation,
                nt_resp_invite_low,
                nt_resp_invite_high,
                nt_resp_game_hcp,
                nt_resp_slam_hcp,
            )

        # 低花转移后续：1NT - 2♠ - 3♣
        # 弱牌(<7)及中等(7-10)：方块单套 → 3♦，草花单套 → Pass
        # >10 HCP：11-12 邀局 4m；13-15 进局 3NT/5m；16+ 扣叫或 4NT 试探满贯
        if settings.transfers_enabled and response_bid == "2♠" and opener_rebid_bid == "3♣":
            diamond_single = lengths["D"] >= 6 and lengths["C"] < 6
            club_single = lengths["C"] >= 6 and lengths["D"] < 6
            true_minor = "D" if diamond_single else "C"
            minor_symbol = suit_symbol(true_minor)

            # README：弱牌(<7) 方块→3♦、草花→Pass；7-10 同样先定位花色；>10 才邀局/进局/满贯。
            if hcp <= 10:
                strength_label = "弱牌(<7 HCP)" if hcp < 7 else "中等牌力(7-10 HCP)"
                if diamond_single and is_legal_response_bid(opener_rebid_bid, "3♦"):
                    return BidRecommendation(
                        "3♦",
                        f"1NT-2♠-3♣ 后，你有 {hcp} HCP（{strength_label}）和 {lengths['D']} 张方块单套，再叫 3♦ 表明真实花色并止叫。牌型：{length_text}。",
                        "低花转移后改叫方块",
                    )
                return BidRecommendation(
                    "Pass",
                    f"1NT-2♠-3♣ 后，你有 {hcp} HCP（{strength_label}）和 {lengths['C']} 张草花单套，接受同伴完成转移，建议 Pass。牌型：{length_text}。",
                    "低花转移后止叫",
                )

            if hcp >= 16:
                short_majors = [suit for suit in ["H", "S"] if lengths[suit] <= 1]
                for suit in short_majors:
                    cue_bid = f"3{suit_symbol(suit)}"
                    if is_legal_response_bid(opener_rebid_bid, cue_bid):
                        return BidRecommendation(
                            cue_bid,
                            f"1NT-2♠-3♣ 后，你有 {hcp} HCP 且 {SUIT_NAMES[suit]} 单缺，扣叫 {cue_bid} 试探满贯。牌型：{length_text}。",
                            "低花转移后扣叫试探满贯",
                        )
                if is_legal_response_bid(opener_rebid_bid, "4NT"):
                    return BidRecommendation(
                        "4NT",
                        f"1NT-2♠-3♣ 后，你有 {hcp} HCP 和 {lengths[true_minor]} 张 {SUIT_NAMES[true_minor]}，叫 4NT 问A张试探满贯。牌型：{length_text}。",
                        "低花转移后 4NT 问叫",
                    )

            if hcp >= 13:
                if evaluation.balanced and is_legal_response_bid(opener_rebid_bid, "3NT"):
                    return BidRecommendation(
                        "3NT",
                        f"1NT-2♠-3♣ 后，你有 {hcp} HCP 且均型，直接进局 3NT。牌型：{length_text}。",
                        "低花转移后进局",
                    )
                game_bid = f"5{minor_symbol}"
                if is_legal_response_bid(opener_rebid_bid, game_bid):
                    return BidRecommendation(
                        game_bid,
                        f"1NT-2♠-3♣ 后，你有 {hcp} HCP 和 {lengths[true_minor]} 张 {SUIT_NAMES[true_minor]}，直接进局 {game_bid}。牌型：{length_text}。",
                        "低花转移后进局",
                    )

            invite_bid = f"4{minor_symbol}"
            if is_legal_response_bid(opener_rebid_bid, invite_bid):
                return BidRecommendation(
                    invite_bid,
                    f"1NT-2♠-3♣ 后，你有 {hcp} HCP 和 {lengths[true_minor]} 张 {SUIT_NAMES[true_minor]}，叫 {invite_bid} 邀局。牌型：{length_text}。",
                    "低花转移后邀局",
                )

            if diamond_single and is_legal_response_bid(opener_rebid_bid, "3♦"):
                return BidRecommendation(
                    "3♦",
                    f"1NT-2♠-3♣ 后，你有 {lengths['D']} 张方块单套，再叫 3♦ 表明真实花色。牌型：{length_text}。",
                    "低花转移后改叫方块",
                )
            return BidRecommendation(
                "Pass",
                f"1NT-2♠-3♣ 后，你有 {hcp} HCP，当前没有更合适的继续叫品，建议 Pass。牌型：{length_text}。",
                "低花转移后止叫",
            )

    if opener_rebid_bid in {"1NT", "2NT", "3NT"}:
        if hcp >= nt_game_hcp and is_legal_response_bid(opener_rebid_bid, "3NT"):
            return BidRecommendation(
                "3NT",
                f"开叫者再叫 {opener_rebid_bid} 显示无将牌力，你有 {hcp} HCP，合力足够进局，叫 3NT。牌型：{length_text}。",
                "对无将再叫进局",
            )
        if nt_invite_low <= hcp <= nt_invite_high and is_legal_response_bid(opener_rebid_bid, "2NT"):
            return BidRecommendation(
                "2NT",
                f"开叫者再叫 {opener_rebid_bid} 后，你有 {hcp} HCP，先做无将邀局。牌型：{length_text}。",
                "对无将再叫邀局",
            )
        return BidRecommendation(
            "Pass",
            f"开叫者再叫 {opener_rebid_bid} 后，你有 {hcp} HCP，不足以继续进局动作，建议 Pass。牌型：{length_text}。",
            "对无将再叫止叫",
        )

    # 开叫者再叫新高花且形成 4+ 配合：继续支持（README 第2条）
    opening_suit_for_new = symbol_to_suit(opening_contract[1]) if opening_contract is not None else None
    response_suit_for_new = symbol_to_suit(response_contract[1]) if response_contract[1] != "NT" else None
    if (
        opener_suit in {"H", "S"}
        and lengths[opener_suit] >= 4
        and opener_suit != opening_suit_for_new
        and opener_suit != response_suit_for_new
    ):
        level = choose_raise_level(opener_rebid_contract[0], raise_hcp)
        bid = f"{level}{suit_symbol(opener_suit)}"
        if is_legal_response_bid(opener_rebid_bid, bid):
            return BidRecommendation(
                bid,
                f"开叫者再叫新花 {opener_rebid_bid}，你有 {lengths[opener_suit]} 张高花配合（4+）和 {hcp} HCP，继续支持到 {bid}。牌型：{length_text}。",
                "支持开叫者再叫新花",
            )

    response_suit = symbol_to_suit(response_contract[1])
    if response_suit is not None and lengths[response_suit] >= 6:
        rebid = minimum_legal_bid_for_suit(response_suit, opener_rebid_bid, minimum_level=response_contract[0] + 1)
        if rebid is not None:
            return BidRecommendation(
                rebid,
                f"你原应叫花色有 {lengths[response_suit]} 张，且开叫者再叫 {opener_rebid_bid} 后未形成更好配合，重复自己长套 {rebid}。牌型：{length_text}。",
                "应叫者重复原花色",
            )

    if hcp >= nt_game_hcp and is_legal_response_bid(opener_rebid_bid, "3NT"):
        return BidRecommendation(
            "3NT",
            f"你有 {hcp} HCP，虽无明确高花配合，叫 3NT 进无将局。牌型：{length_text}。",
            "无配合无将进局",
        )
    if nt_invite_low <= hcp <= nt_invite_high and is_legal_response_bid(opener_rebid_bid, "2NT"):
        return BidRecommendation(
            "2NT",
            f"你有 {hcp} HCP，虽无明确高花配合，叫 2NT 邀无将局。牌型：{length_text}。",
            "无配合无将邀局",
        )
    nt_one_min = max(5, 6 + game_adjustment)
    if hcp >= nt_one_min and is_legal_response_bid(opener_rebid_bid, "1NT"):
        return BidRecommendation(
            "1NT",
            f"你有 {hcp} HCP，虽无明确高花配合，再叫 1NT 描述牌力。牌型：{length_text}。",
            "无配合再叫 1NT",
        )

    return BidRecommendation(
        "Pass",
        f"当前无明确配合且牌力不足以继续无将动作，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
        "无配合止叫",
    )


def recommend_response_to_1nt(
    evaluation: HandEvaluation,
    settings: RuleSettings,
    vulnerability: str | None = None,
) -> BidRecommendation:
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)
    game_adjustment = game_threshold_adjustment(vulnerability, settings)
    game_hcp = max(8, 10 + game_adjustment)
    invite_low = max(6, 8 + game_adjustment)
    invite_high = game_hcp - 1
    # 相对 15-17 1NT：约 16-17 邀小满，18+ 邀大满。
    slam_invite_low = max(14, 16 + game_adjustment)
    grand_invite_low = max(16, 18 + game_adjustment)

    # 德克萨斯：6+ 高花且够局，直接转移到四阶成局。
    if settings.transfers_enabled and lengths["H"] >= 6 and hcp >= game_hcp:
        return BidRecommendation(
            "4♦",
            f"同伴开 1NT，你有 {hcp} HCP 和 {lengths['H']} 张红心，使用德克萨斯转移叫 4♦，要求同伴转叫 4♥。牌型：{length_text}。",
            "1NT 后德克萨斯红心转移",
        )
    if settings.transfers_enabled and lengths["S"] >= 6 and hcp >= game_hcp:
        return BidRecommendation(
            "4♥",
            f"同伴开 1NT，你有 {hcp} HCP 和 {lengths['S']} 张黑桃，使用德克萨斯转移叫 4♥，要求同伴转叫 4♠。牌型：{length_text}。",
            "1NT 后德克萨斯黑桃转移",
        )

    # 3♥/3♠：5+ 高花且 15+ HCP，表示满贯兴趣。
    if lengths["H"] >= 5 and hcp >= 15:
        return BidRecommendation(
            "3♥",
            f"同伴开 1NT，你有 {hcp} HCP 和 {lengths['H']} 张红心，跳叫 3♥ 表示满贯兴趣。牌型：{length_text}。",
            "1NT 后红心满贯兴趣",
        )
    if lengths["S"] >= 5 and hcp >= 15:
        return BidRecommendation(
            "3♠",
            f"同伴开 1NT，你有 {hcp} HCP 和 {lengths['S']} 张黑桃，跳叫 3♠ 表示满贯兴趣。牌型：{length_text}。",
            "1NT 后黑桃满贯兴趣",
        )

    if settings.transfers_enabled and lengths["H"] >= 5:
        return BidRecommendation(
            "2♦",
            f"同伴开 1NT，你有 {hcp} HCP 和 5 张以上红心。简化规则使用 Jacoby Transfer：叫 2♦，要求同伴转叫 2♥。牌型：{length_text}。",
            "1NT 后红心转移",
        )
    if settings.transfers_enabled and lengths["S"] >= 5:
        return BidRecommendation(
            "2♥",
            f"同伴开 1NT，你有 {hcp} HCP 和 5 张以上黑桃。简化规则使用 Jacoby Transfer：叫 2♥，要求同伴转叫 2♠。牌型：{length_text}。",
            "1NT 后黑桃转移",
        )
    if settings.stayman_enabled and hcp >= invite_low and (lengths["H"] >= 4 or lengths["S"] >= 4):
        return BidRecommendation(
            "2♣",
            f"同伴开 1NT，你有 {hcp} HCP 且至少一个 4 张高花。用 2♣ Stayman 寻找 4-4 高花配合。牌型：{length_text}。",
            "Stayman",
        )

    # 3♣/3♦：5+ 低花、8-9 HCP，邀 3NT（8-10 非极不均型优先此路，不走低花转移）。
    has_four_card_major = lengths["H"] >= 4 or lengths["S"] >= 4
    if not has_four_card_major and invite_low <= hcp <= invite_high:
        five_plus_minors = [suit for suit in ["D", "C"] if lengths[suit] >= 5]
        if five_plus_minors:
            # 极不均型 6+ 单套留给低花转移；其余 5+/普通 6 套走邀局。
            candidates = []
            for suit in five_plus_minors:
                if lengths[suit] >= 6 and prefers_minor_suit_transfer(hcp, lengths, suit, evaluation):
                    continue
                candidates.append(suit)
            if candidates:
                minor = max(candidates, key=lambda suit: (lengths[suit], suit == "D"))
                minor_bid = f"3{suit_symbol(minor)}"
                return BidRecommendation(
                    minor_bid,
                    f"同伴开 1NT，你有 {hcp} HCP 和 {lengths[minor]} 张 {SUIT_NAMES[minor]}，跳叫 {minor_bid} 邀请 3NT。牌型：{length_text}。",
                    "1NT 后低花邀局",
                )

    # 低花转移：单套 6+，弱牌或强牌/极不均型倾向低花定约；统一先叫 2♠。
    if settings.transfers_enabled and not has_four_card_major:
        club_single = lengths["C"] >= 6 and lengths["D"] < 6
        diamond_single = lengths["D"] >= 6 and lengths["C"] < 6
        if club_single or diamond_single:
            minor = "C" if club_single else "D"
            if prefers_minor_suit_transfer(hcp, lengths, minor, evaluation):
                follow_up = (
                    "同伴转叫 3♣ 后按点力继续"
                    if hcp > 10
                    else ("同伴转叫 3♣ 后止叫" if club_single else "同伴转叫 3♣ 后再叫 3♦")
                )
                return BidRecommendation(
                    "2♠",
                    f"同伴开 1NT，你有 {hcp} HCP 和 {lengths[minor]} 张 {SUIT_NAMES[minor]} 单套，"
                    f"弱牌或倾向低花定约，使用低花转移叫 2♠（{follow_up}）。牌型：{length_text}。",
                    "1NT 后低花转移",
                )

    # >10 且未走低花转移：无四张高花时优先直接 3NT（见后方均型/兜底档）。

    # 无四张高花的均型牌：按点力 Pass / 2NT / 3NT / 4NT / 5NT。
    if evaluation.balanced and not has_four_card_major:
        if hcp >= grand_invite_low:
            return BidRecommendation(
                "5NT",
                f"同伴 1NT 后，你有 {hcp} HCP 且均型无四张高花，叫 5NT 邀请大满贯。牌型：{length_text}。",
                "1NT 后 5NT 邀大满",
            )
        if hcp >= slam_invite_low:
            return BidRecommendation(
                "4NT",
                f"同伴 1NT 后，你有 {hcp} HCP 且均型无四张高花，叫 4NT 邀请小满贯。牌型：{length_text}。",
                "1NT 后 4NT 邀小满",
            )
        if hcp >= game_hcp:
            return BidRecommendation(
                "3NT",
                f"同伴 1NT 表示 15-17 均型，你有 {hcp} HCP 且均型无四张高花，合力够局，直接叫 3NT。牌型：{length_text}。",
                "1NT 后进局",
            )
        if invite_low <= hcp <= invite_high:
            return BidRecommendation(
                "2NT",
                f"同伴 1NT 后，你有 {hcp} HCP 且均型无四张高花，邀请 3NT。牌型：{length_text}。",
                "1NT 后邀局",
            )
        return BidRecommendation(
            "Pass",
            f"同伴 1NT 后，你有 {hcp} HCP 且均型无四张高花，通常不足以邀局，建议 Pass。牌型：{length_text}。",
            "1NT 后止叫",
        )

    # 非均型兜底：仍按点力落无将档。
    if hcp >= grand_invite_low:
        return BidRecommendation(
            "5NT",
            f"同伴 1NT 后，你有 {hcp} HCP 且无需要先处理的高花，叫 5NT 邀请大满贯。牌型：{length_text}。",
            "1NT 后 5NT 邀大满",
        )
    if hcp >= slam_invite_low:
        return BidRecommendation(
            "4NT",
            f"同伴 1NT 后，你有 {hcp} HCP 且无需要先处理的高花，叫 4NT 邀请小满贯。牌型：{length_text}。",
            "1NT 后 4NT 邀小满",
        )
    if hcp >= game_hcp:
        return BidRecommendation(
            "3NT",
            f"同伴 1NT 表示 15-17 均型，你有 {hcp} HCP 且无需要先处理的高花，合力够局，直接叫 3NT。牌型：{length_text}。",
            "1NT 后进局",
        )
    if invite_low <= hcp <= invite_high:
        return BidRecommendation(
            "2NT",
            f"同伴 1NT 后，你有 {hcp} HCP 且无 4/5 张高花优先处理，邀请 3NT。牌型：{length_text}。",
            "1NT 后邀局",
        )
    return BidRecommendation(
        "Pass",
        f"同伴 1NT 后，你有 {hcp} HCP，通常不足以邀局，建议 Pass。牌型：{length_text}。",
        "1NT 后止叫",
    )


def recommend_response_to_2nt(
    evaluation: HandEvaluation,
    settings: RuleSettings,
    vulnerability: str | None = None,
) -> BidRecommendation:
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)

    if settings.transfers_enabled and lengths["H"] >= 5:
        return BidRecommendation(
            "3♦",
            f"同伴开 2NT，你有 {hcp} HCP 和 5 张以上红心。简化规则使用 3♦ 转移，要求同伴转叫 3♥。牌型：{length_text}。",
            "2NT 后红心转移",
        )
    if settings.transfers_enabled and lengths["S"] >= 5:
        return BidRecommendation(
            "3♥",
            f"同伴开 2NT，你有 {hcp} HCP 和 5 张以上黑桃。简化规则使用 3♥ 转移，要求同伴转叫 3♠。牌型：{length_text}。",
            "2NT 后黑桃转移",
        )
    if settings.stayman_enabled and (lengths["H"] >= 4 or lengths["S"] >= 4):
        return BidRecommendation(
            "3♣",
            f"同伴开 2NT，你有 {hcp} HCP 且至少一个 4 张高花。用 3♣ Stayman 寻找 4-4 高花配合。牌型：{length_text}。",
            "2NT 后 Stayman",
        )
    return BidRecommendation(
        "3NT",
        f"同伴 2NT 表示 20-21 均型，你有 {hcp} HCP 且无高花优先处理，直接叫 3NT 成局。牌型：{length_text}。",
        "2NT 后进局",
    )


def has_suit_stopper(evaluation: HandEvaluation, suit: str) -> bool:
    """简化止张：至少 2 张且含 A/K/Q 之一。"""
    return evaluation.lengths[suit] >= 2 and evaluation.top_honors_by_suit.get(suit, 0) >= 1


SEMI_BALANCED_SHAPES = {(5, 4, 2, 2), (6, 3, 2, 2)}


def is_semi_balanced_shape(lengths: dict[str, int]) -> bool:
    sorted_shape = tuple(sorted(lengths.values(), reverse=True))
    return sorted_shape in SEMI_BALANCED_SHAPES


def has_stoppers_in_all_suits(evaluation: HandEvaluation) -> bool:
    return all(has_suit_stopper(evaluation, suit) for suit in ["S", "H", "D", "C"])


def qualifies_for_nt_opening_shape(evaluation: HandEvaluation) -> bool:
    """均型，或准均型（5422/6322）且门门有止；6 张高花不按无将开叫。"""
    if evaluation.balanced:
        return True
    lengths = evaluation.lengths
    if lengths["S"] >= 6 or lengths["H"] >= 6:
        return False
    return is_semi_balanced_shape(lengths) and has_stoppers_in_all_suits(evaluation)


def preempt_overbid_allowance(vulnerability: str | None) -> int:
    """阻击叫：有局宕二，无局宕三。"""
    return 2 if ns_is_vulnerable(vulnerability) else 3


def preempt_min_top_honors(vulnerability: str | None) -> int:
    """阻击/弱二长套顶张要求：无局至少1张，有局至少2张（A/K/Q）。"""
    return 2 if ns_is_vulnerable(vulnerability) else 1


def estimate_long_suit_playing_tricks(length: int) -> int:
    """弱牌长套预期赢墩：约套长减一。"""
    return max(0, length - 1)


def max_preempt_level_for_suit(
    length: int,
    vulnerability: str | None,
    suit: str,
) -> int | None:
    """按有局宕二无局宕三计算该长套最高阻击阶数；不足二阶则返回 None。"""
    if length < 6:
        return None
    target_tricks = estimate_long_suit_playing_tricks(length) + preempt_overbid_allowance(vulnerability)
    level = target_tricks - 6
    if level < 2:
        return None
    if suit in {"S", "H"}:
        return min(level, 4)
    return min(level, 5)


def recommend_response_to_gambling_3nt(
    evaluation: HandEvaluation,
    settings: RuleSettings | None = None,
) -> BidRecommendation:
    """拼搏式 3NT 应叫：Pass 打无将；4♣ Pass or correct；4♦ 问单缺；4M 自有高花成局。"""
    settings = settings or default_rule_settings()
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)

    six_plus_majors = [suit for suit in ["S", "H"] if lengths[suit] >= 6]
    if six_plus_majors:
        major = max(six_plus_majors, key=lambda suit: (lengths[suit], suit == "S"))
        major_bid = f"4{suit_symbol(major)}"
        return BidRecommendation(
            major_bid,
            f"同伴拼搏式 3NT，你有 {hcp} HCP 和 {lengths[major]} 张 {SUIT_NAMES[major]}，直接叫 {major_bid} 打高花成局。牌型：{length_text}。",
            "拼搏式 3NT 后高花成局",
        )

    both_majors_stopped = has_suit_stopper(evaluation, "H") and has_suit_stopper(evaluation, "S")
    if both_majors_stopped:
        if hcp >= 16 and is_legal_response_bid("3NT", "4♦"):
            return BidRecommendation(
                "4♦",
                f"同伴拼搏式 3NT，你有 {hcp} HCP 且两边高花有止，牌力足够用 4♦ 询问开叫者单缺、试探满贯。牌型：{length_text}。",
                "拼搏式 3NT 后问单缺",
            )
        return BidRecommendation(
            "Pass",
            f"同伴拼搏式 3NT，你有 {hcp} HCP 且两边高花有止，接受打 3NT。牌型：{length_text}。",
            "拼搏式 3NT 后止叫",
        )

    return BidRecommendation(
        "4♣",
        f"同伴拼搏式 3NT，你有 {hcp} HCP 但高花止张不足，叫 4♣（Pass or correct）转入开叫者坚固低花。牌型：{length_text}。",
        "拼搏式 3NT 后 Pass or correct",
    )


def get_splinter_bid(major: str, splinter_suit: str) -> str:
    """获取splinter的叫品。
    
    Splinter规则：
    - 1♥开叫后，如果在♠有单张/void，叫3♠
    - 1♥开叫后，如果在♣有单张/void，叫3♣
    - 1♥开叫后，如果在♦有单张/void，叫3♦
    - 1♠开叫后，如果在♥有单张/void，叫3♥
    - 1♠开叫后，如果在♣有单张/void，叫3♣
    - 1♠开叫后，如果在♦有单张/void，叫3♦
    
    Args:
        major: 主花色 ("H" 或 "S")
        splinter_suit: splinter所在花色 ("S", "H", "D", "C")
        
    Returns:
        splinter叫品，如 "3♠", "3♣" 等
    """
    return f"3{suit_symbol(splinter_suit)}"


def find_splinter_suit(
    major: str,
    lengths: dict[str, int],
) -> str | None:
    """检测是否存在splinter（对主花有4+支持，某花色1张或0张）。
    
    Args:
        major: 主花色 ("H" 或 "S")
        lengths: 各花色长度字典
        
    Returns:
        splinter所在花色代码，如果没有则返回None
    """
    if lengths[major] < 4:
        return None
    
    for suit in ["S", "H", "D", "C"]:
        if suit != major and lengths[suit] <= 1:  # 单张或void
            return suit
    
    return None


def recommend_response_to_major(
    major: str,
    evaluation: HandEvaluation,
    settings: RuleSettings,
    vulnerability: str | None = None,
) -> BidRecommendation:
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)
    major_name = SUIT_NAMES[major]
    major_bid = suit_symbol(major)
    game_adjustment = game_threshold_adjustment(vulnerability, settings)
    game_hcp = max(11, 13 + game_adjustment)
    has_four_card_support = lengths[major] >= 4
    support_count = lengths[major]

    if support_count <= 2:
        if hcp < 5:
            return BidRecommendation(
                "Pass",
                f"同伴开 1{major_bid}，你只有 {hcp} HCP 且对开叫花色支持不足，通常 Pass。牌型：{length_text}。",
                f"对 1{major_name} 不叫",
            )
        if major == "H" and lengths["S"] >= 4 and hcp >= 6:
            return BidRecommendation(
                "1♠",
                f"同伴开 1♥，你有 {hcp} HCP 且 4 张以上黑桃，应在一阶叫出 1♠。牌型：{length_text}。",
                "一盖一应叫",
            )
        if hcp >= settings.two_over_one_min_hcp:
            suit = choose_two_over_one_suit(lengths, excluded=major)
            if suit is not None:
                return BidRecommendation(
                    f"2{suit_symbol(suit)}",
                    f"同伴开 1{major_bid}，你有 {hcp} HCP，达到当前 2/1 下限 {settings.two_over_one_min_hcp} HCP，二阶新花为进局逼叫，选择较长的 {SUIT_NAMES[suit]}。牌型：{length_text}。",
                    "2/1 进局逼叫",
                )
        if settings.forcing_nt_min_hcp <= hcp <= settings.forcing_nt_max_hcp:
            return BidRecommendation(
                "1NT",
                f"同伴开 1{major_bid}，你有 {hcp} HCP，落在当前 1NT 应叫范围 {settings.forcing_nt_min_hcp}-{settings.forcing_nt_max_hcp} HCP 内，当前设置中 1NT 为{settings.forcing_nt_label}。牌型：{length_text}。",
                f"1NT {settings.forcing_nt_label}",
            )
        return BidRecommendation(
            "Pass",
            f"同伴开 1{major_bid}，你有 {hcp} HCP，但既无足够支持也无合适一阶/二阶应叫，建议 Pass。牌型：{length_text}。",
            f"对 1{major_name} 不叫",
        )

    if settings.bergen_raises_enabled:
        # 5+ 张支持的弱牌优先关煞叫。
        if support_count >= 5 and hcp <= 10 and is_legal_response_bid(f"1{major_bid}", f"4{major_bid}"):
            return BidRecommendation(
                f"4{major_bid}",
                f"同伴开 1{major_bid}，你有 {hcp} HCP 且 5+ 张支持，按弱牌关煞思路直接跳到 4{major_bid}。牌型：{length_text}。",
                "高花关煞加叫",
            )

        # Splinter优先于Jacoby 2NT，因为牌型更特殊。
        if settings.splinter_enabled and has_four_card_support:
            splinter_suit = find_splinter_suit(major, lengths)
            if splinter_suit is not None:
                short_len = lengths[splinter_suit]
                splinter_min_hcp = settings.responder_splinter_min_hcp if short_len == 1 else max(0, settings.responder_splinter_min_hcp - 2)
                if splinter_min_hcp <= hcp <= settings.responder_splinter_max_hcp:
                    splinter_bid = get_splinter_bid(major, splinter_suit)
                    splinter_suit_name = SUIT_NAMES[splinter_suit]
                    short_desc = "单张" if short_len == 1 else "缺门"
                    return BidRecommendation(
                        splinter_bid,
                        f"同伴开 1{major_bid}，你有 {hcp} HCP 和 4 张支持。牌型特殊：{splinter_suit_name}花{short_desc}。使用Splinter叫 {splinter_bid}。牌型：{length_text}。",
                        "Splinter游牌加叫",
                    )

        no_shortage = min(lengths[suit] for suit in ["S", "H", "D", "C"] if suit != major) >= 2
        if settings.jacoby_2nt_enabled and has_four_card_support and hcp >= 13 and no_shortage:
            return BidRecommendation(
                "2NT",
                f"同伴开 1{major_bid}，你有 {hcp} HCP 和 4 张以上支持，且无单缺，按 Jacoby 2NT 表示进局逼叫支持。牌型：{length_text}。",
                "Jacoby 2NT 支持",
            )

        if has_four_card_support:
            if hcp <= 6 and is_legal_response_bid(f"1{major_bid}", f"3{major_bid}"):
                return BidRecommendation(
                    f"3{major_bid}",
                    f"同伴开 1{major_bid}，你有 {hcp} HCP 和 4 张支持，按弱支持跳加叫到 3{major_bid}。牌型：{length_text}。",
                    "Bergen 弱支持 (4张)",
                )
            if 7 <= hcp <= settings.responder_bergen_weak_max and not evaluation.balanced and is_legal_response_bid(f"1{major_bid}", "3♣"):
                return BidRecommendation(
                    "3♣",
                    f"同伴开 1{major_bid}，你有 {hcp} HCP 和 4 张支持，按 Bergen 约定用 3♣ 表示弱支持且偏分布牌。牌型：{length_text}。",
                    "Bergen 弱支持 (4张)",
                )
            if 10 <= hcp <= 12 and no_shortage and is_legal_response_bid(f"1{major_bid}", "3♦"):
                return BidRecommendation(
                    "3♦",
                    f"同伴开 1{major_bid}，你有 {hcp} HCP 和 4 张支持且无单缺，按 Bergen 约定用 3♦ 表示中等支持。牌型：{length_text}。",
                    "Bergen 中等支持 (4张)",
                )

        if 6 <= hcp <= 9 and is_legal_response_bid(f"1{major_bid}", f"2{major_bid}"):
            return BidRecommendation(
                f"2{major_bid}",
                f"同伴开 1{major_bid}，你有 {hcp} HCP 和 {support_count} 张支持，简单加叫到 2{major_bid}。牌型：{length_text}。",
                "高花简单加叫",
            )
        if 10 <= hcp <= 12 and support_count == 3 and is_legal_response_bid(f"1{major_bid}", "1NT"):
            return BidRecommendation(
                "1NT",
                f"同伴开 1{major_bid}，你有 {hcp} HCP 且仅 3 张支持，按 Bergen 体系常用处理先叫 1NT 过渡。牌型：{length_text}。",
                f"1NT {settings.forcing_nt_label}",
            )
        if hcp >= 13:
            suit = choose_two_over_one_suit(lengths, excluded=major)
            if suit is not None:
                return BidRecommendation(
                    f"2{suit_symbol(suit)}",
                    f"同伴开 1{major_bid}，你有 {hcp} HCP，按高限进程优先新花进局逼叫。牌型：{length_text}。",
                    "2/1 进局逼叫",
                )

    if support_count >= 3 and hcp >= game_hcp:
        return BidRecommendation(
            f"4{major_bid}",
            f"同伴开 1{major_bid}，你有 {hcp} HCP 和 3 张支持，合力够局，直接加叫到 4{major_bid}。牌型：{length_text}。",
            "高花进局加叫",
        )

    if support_count >= 3 and settings.responder_limit_raise_min <= hcp <= settings.responder_limit_raise_max:
        return BidRecommendation(
            f"3{major_bid}",
            f"同伴开 1{major_bid}，你有 {hcp} HCP 和 3 张支持，属于邀局加叫，叫 3{major_bid}。牌型：{length_text}。",
            "高花邀局加叫",
        )

    simple_low = max(5, 6 + game_adjustment)
    if support_count >= 3 and simple_low <= hcp <= settings.responder_simple_raise_max:
        return BidRecommendation(
            f"2{major_bid}",
            f"同伴开 1{major_bid}，你有 {hcp} HCP 和 3 张支持，简单加叫到 2{major_bid}。牌型：{length_text}。",
            "高花简单加叫",
        )

    if major == "H" and lengths["S"] >= 4 and hcp >= 6:
        return BidRecommendation(
            "1♠",
            f"同伴开 1♥，你有 {hcp} HCP 且 4 张以上黑桃，应在一阶叫出 1♠。牌型：{length_text}。",
            "一盖一应叫",
        )

    if hcp >= settings.two_over_one_min_hcp:
        suit = choose_two_over_one_suit(lengths, excluded=major)
        if suit is not None:
            return BidRecommendation(
                f"2{suit_symbol(suit)}",
                f"同伴开 1{major_bid}，你有 {hcp} HCP，达到当前 2/1 下限 {settings.two_over_one_min_hcp} HCP，二阶新花为进局逼叫，选择较长的 {SUIT_NAMES[suit]}。牌型：{length_text}。",
                "2/1 进局逼叫",
            )

    if settings.forcing_nt_min_hcp <= hcp <= settings.forcing_nt_max_hcp:
        return BidRecommendation(
            "1NT",
            f"同伴开 1{major_bid}，你有 {hcp} HCP，落在当前 1NT 应叫范围 {settings.forcing_nt_min_hcp}-{settings.forcing_nt_max_hcp} HCP 内，无足够支持，也没有可叫的一阶新高花。当前设置中 1NT 为{settings.forcing_nt_label}。牌型：{length_text}。",
            f"1NT {settings.forcing_nt_label}",
        )

    return BidRecommendation(
        "Pass",
        f"同伴开 1{major_bid}，你只有 {hcp} HCP，且没有足够支持，通常 Pass。牌型：{length_text}。",
        f"对 1{major_name} 不叫",
    )


def recommend_response_to_minor(
    minor: str,
    evaluation: HandEvaluation,
    settings: RuleSettings,
    vulnerability: str | None = None,
) -> BidRecommendation:
    hcp = evaluation.hcp
    lengths = evaluation.lengths
    length_text = describe_lengths(evaluation)
    minor_bid = suit_symbol(minor)
    game_adjustment = game_threshold_adjustment(vulnerability, settings)
    nt_game_hcp = max(11, 13 + game_adjustment)
    nt_invite_low = max(9, 11 + game_adjustment)
    nt_invite_high = nt_game_hcp - 1

    if hcp < 6:
        return BidRecommendation(
            "Pass",
            f"同伴开 1{minor_bid}，你只有 {hcp} HCP，通常不足以应叫。牌型：{length_text}。",
            "低花开叫后不叫",
        )

    major = choose_one_level_major_response(lengths)
    if major is not None:
        return BidRecommendation(
            f"1{suit_symbol(major)}",
            f"同伴开 1{minor_bid}，你有 {hcp} HCP 和 4 张以上高花，优先一阶叫出高花 {SUIT_NAMES[major]}。牌型：{length_text}。",
            "低花后叫高花",
        )

    minor_honors = evaluation.top_honors_by_suit.get(minor, 0)
    # README：无高花时，非均型通常以 5+ 张低花支持加叫。
    has_minor_support = lengths[minor] >= 5 or (lengths[minor] == 4 and minor_honors >= 2)

    if not evaluation.balanced and has_minor_support:
        if settings.inverted_minors_enabled:
            if hcp <= 9:
                return BidRecommendation(
                    f"3{minor_bid}",
                    f"同伴开 1{minor_bid}，你有 {hcp} HCP 且低花支持明确，按低花反加叫使用 3{minor_bid} 表示弱牌加叫。牌型：{length_text}。",
                    "低花反加叫（弱）",
                )
            return BidRecommendation(
                f"2{minor_bid}",
                f"同伴开 1{minor_bid}，你有 {hcp} HCP 且低花支持明确，按低花反加叫使用 2{minor_bid} 表示逼叫一轮。牌型：{length_text}。",
                "低花反加叫（逼叫）",
            )

        # 未启用低花反加叫：按点力选择 2m / 3m / 4m / 5m / 4NT。
        if 6 <= hcp <= 9:
            return BidRecommendation(
                f"2{minor_bid}",
                f"同伴开 1{minor_bid}，你有 {hcp} HCP 和低花支持，作简单加叫 2{minor_bid}。牌型：{length_text}。",
                "低花简单加叫",
            )
        if 10 <= hcp <= 12:
            return BidRecommendation(
                f"3{minor_bid}",
                f"同伴开 1{minor_bid}，你有 {hcp} HCP 和低花支持，作限制性加叫 3{minor_bid}。牌型：{length_text}。",
                "低花限制加叫",
            )
        if 13 <= hcp <= 15:
            return BidRecommendation(
                f"4{minor_bid}",
                f"同伴开 1{minor_bid}，你有 {hcp} HCP 和低花支持，作邀局加叫 4{minor_bid}。牌型：{length_text}。",
                "低花邀局加叫",
            )
        if 16 <= hcp <= 18:
            return BidRecommendation(
                f"5{minor_bid}",
                f"同伴开 1{minor_bid}，你有 {hcp} HCP 和低花支持，直接进局 5{minor_bid}。牌型：{length_text}。",
                "低花直接进局",
            )
        if hcp >= 19:
            return BidRecommendation(
                "4NT",
                f"同伴开 1{minor_bid}，你有 {hcp} HCP 和低花支持，以开叫低花为将牌作 4NT 关键张问叫试探满贯。牌型：{length_text}。",
                "低花满贯试探 4NT",
            )

    if evaluation.balanced and hcp >= nt_game_hcp:
        return BidRecommendation(
            "3NT",
            f"同伴开 1{minor_bid}，你有 {hcp} HCP，均型且无 4 张高花，合力够局，叫 3NT。牌型：{length_text}。",
            "低花后 3NT",
        )
    if evaluation.balanced and nt_invite_low <= hcp <= nt_invite_high:
        return BidRecommendation(
            "2NT",
            f"同伴开 1{minor_bid}，你有 {hcp} HCP，均型且无 4 张高花，邀请 3NT。牌型：{length_text}。",
            "低花后 2NT 邀局",
        )
    if evaluation.balanced:
        return BidRecommendation(
            "1NT",
            f"同伴开 1{minor_bid}，你有 {hcp} HCP，均型且无 4 张高花，叫 1NT。牌型：{length_text}。",
            "低花后 1NT",
        )

    return BidRecommendation(
        "1NT",
        f"同伴开 1{minor_bid}，你有 {hcp} HCP，无 4 张高花且没有更清楚的低花支持叫品，暂用 1NT 描述。牌型：{length_text}。",
        "低花后默认 1NT",
    )


def recommend_response_to_strong_two_club(evaluation: HandEvaluation) -> BidRecommendation:
    length_text = describe_lengths(evaluation)
    return BidRecommendation(
        "2♦",
        f"同伴强开叫 2♣，当前简化体系使用 2♦ 作为等待叫，先保留空间让开叫者描述牌型。你有 {evaluation.hcp} HCP，牌型：{length_text}。",
        "强 2♣ 后 2♦ 等待",
    )


def recommend_response_to_weak_two(opening_suit: str, evaluation: HandEvaluation) -> BidRecommendation:
    length_text = describe_lengths(evaluation)
    if evaluation.hcp >= 15 and evaluation.balanced:
        return BidRecommendation(
            "2NT",
            f"同伴弱二开叫，你有 {evaluation.hcp} HCP 且均型，当前简化体系用 2NT 作为强询问/邀局。牌型：{length_text}。",
            "弱二后 2NT 询问",
        )
    return BidRecommendation(
        "Pass",
        f"同伴弱二开叫 2{suit_symbol(opening_suit)}，当前简化体系多数低限或普通牌选择 Pass。你有 {evaluation.hcp} HCP，牌型：{length_text}。",
        "弱二后止叫",
    )


def recommend_response_to_preempt(
    opener_bid: str,
    evaluation: HandEvaluation,
    settings: RuleSettings | None = None,
) -> BidRecommendation:
    settings = settings or default_rule_settings()
    opener_contract = parse_contract_bid(opener_bid)
    length_text = describe_lengths(evaluation)
    if opener_contract is None:
        return BidRecommendation("Pass", f"同伴阻击开叫后，当前简化规则建议 Pass。你有 {evaluation.hcp} HCP，牌型：{length_text}。", "阻击后止叫")

    opener_level, opener_strain = opener_contract
    opener_suit = symbol_to_suit(opener_strain)
    game_adjustment = game_threshold_adjustment(None, settings)

    # Ogust 2NT 问叫：仅适用于二阶弱开叫（2♦/2♥/2♠）
    if (
        settings.august_2nt_enabled
        and opener_level == 2
        and opener_strain in {"♦", "♥", "♠"}
        and is_legal_response_bid(opener_bid, "2NT")
    ):
        if evaluation.hcp >= 11:
            return BidRecommendation(
                "2NT",
                f"同伴二阶弱开叫后，你有 {evaluation.hcp} HCP，当前使用 Ogust 2NT 问叫，请开叫者按标准表描述低限/高限与开叫套质量。牌型：{length_text}。",
                "Ogust 2NT 问叫",
            )

    if evaluation.balanced and evaluation.hcp >= 13 and opener_level <= 3 and is_legal_response_bid(opener_bid, "3NT"):
        return BidRecommendation(
            "3NT",
            f"同伴阻击开叫后，你有 {evaluation.hcp} HCP 且均型，当前简化规则优先尝试 3NT 成局。牌型：{length_text}。",
            "阻击后 3NT",
        )

    if opener_suit is not None and evaluation.lengths[opener_suit] >= 3:
        if opener_suit in {"H", "S"} and opener_level < 4 and evaluation.hcp >= 10:
            bid = f"4{suit_symbol(opener_suit)}"
            if is_legal_response_bid(opener_bid, bid):
                return BidRecommendation(
                    bid,
                    f"同伴阻击开叫，你有 {evaluation.hcp} HCP 和 {evaluation.lengths[opener_suit]} 张支持，高花有局价值明确，抬到 {bid}。牌型：{length_text}。",
                    "阻击后高花进局",
                )
        if opener_suit in {"C", "D"} and opener_level < 5 and evaluation.hcp >= 10:
            bid = f"5{suit_symbol(opener_suit)}"
            if is_legal_response_bid(opener_bid, bid):
                return BidRecommendation(
                    bid,
                    f"同伴低花阻击开叫，你有 {evaluation.hcp} HCP 和 {evaluation.lengths[opener_suit]} 张支持，当前简化规则抬到低花局 {bid}。牌型：{length_text}。",
                    "阻击后低花进局",
                )
        if opener_level < 4:
            bid = f"{opener_level + 1}{suit_symbol(opener_suit)}"
            if is_legal_response_bid(opener_bid, bid):
                return BidRecommendation(
                    bid,
                    f"同伴阻击开叫，你有 {evaluation.lengths[opener_suit]} 张支持，当前简化规则可小幅加阻。你有 {evaluation.hcp} HCP，牌型：{length_text}。",
                    "阻击后加阻",
                )

    return BidRecommendation(
        "Pass",
        f"同伴阻击开叫后，当前简化规则没有明确进局或加阻条件，建议 Pass。你有 {evaluation.hcp} HCP，牌型：{length_text}。",
        "阻击后止叫",
    )


def choose_major_opening(lengths: dict[str, int]) -> str:
    if lengths["S"] >= 5 and lengths["H"] >= 5:
        return "S"
    if lengths["S"] >= 5 and lengths["S"] >= lengths["H"]:
        return "S"
    return "H"


def one_nt_secondary_major_opening_bid(lengths: dict[str, int]) -> str | None:
    """均型 1NT 开叫时，若有 5 张高花，一阶高花为次优。"""
    if lengths["S"] < 5 and lengths["H"] < 5:
        return None
    return f"1{suit_symbol(choose_major_opening(lengths))}"


def has_singleton_or_void(lengths: dict[str, int]) -> bool:
    return min(lengths.values()) <= 1


def choose_eleven_hcp_long_suit_with_shortage(lengths: dict[str, int]) -> str | None:
    """11 HCP：6+ 长套且有单缺/缺门时，开叫该长套（一阶）。"""
    if not has_singleton_or_void(lengths):
        return None
    long_suits = [suit for suit in ["S", "H", "D", "C"] if lengths[suit] >= 6]
    if not long_suits:
        return None
    return max(long_suits, key=lambda suit: (lengths[suit], suit == "S", suit == "H", suit == "D"))


def choose_eleven_hcp_two_suiter(lengths: dict[str, int]) -> str | None:
    """11 HCP：5-5 以上双套。

    - 等长：开较高花色（♠>♥>♦>♣）
    - 否则：开较长花色
    - 若高花套短于低花套：次优开较短高花
    """
    five_plus = [suit for suit in ["S", "H", "D", "C"] if lengths[suit] >= 5]
    if len(five_plus) < 2:
        return None

    suit_rank = {"S": 4, "H": 3, "D": 2, "C": 1}
    majors = [suit for suit in five_plus if suit in {"S", "H"}]
    minors = [suit for suit in five_plus if suit in {"D", "C"}]

    if majors and minors:
        max_minor_len = max(lengths[suit] for suit in minors)
        short_majors = [suit for suit in majors if lengths[suit] < max_minor_len]
        if short_majors:
            # 较短高花；同长时取较高花色
            return min(short_majors, key=lambda suit: (lengths[suit], -suit_rank[suit]))

    # 较长优先；等长时较高花色
    return max(five_plus, key=lambda suit: (lengths[suit], suit_rank[suit]))


def eleven_hcp_secondary_opening_bid(lengths: dict[str, int], primary_suit: str) -> str | None:
    """高花短于低花时，较长低花为一阶开叫次优。"""
    if primary_suit not in {"S", "H"}:
        return None
    five_plus = [suit for suit in ["S", "H", "D", "C"] if lengths[suit] >= 5]
    if len(five_plus) < 2:
        return None
    minors = [suit for suit in five_plus if suit in {"D", "C"}]
    if not minors:
        return None
    longer_minor = max(minors, key=lambda suit: (lengths[suit], suit == "D", suit == "C"))
    if lengths[primary_suit] < lengths[longer_minor]:
        return f"1{suit_symbol(longer_minor)}"
    return None


def choose_eleven_hcp_opening(lengths: dict[str, int]) -> str | None:
    # 双套优先走规则 7，否则 6+ 单缺走规则 6。
    two_suiter = choose_eleven_hcp_two_suiter(lengths)
    if two_suiter is not None:
        return two_suiter
    return choose_eleven_hcp_long_suit_with_shortage(lengths)


def choose_minor_opening(lengths: dict[str, int]) -> str:
    clubs = lengths["C"]
    diamonds = lengths["D"]
    if diamonds > clubs:
        return "D"
    if clubs > diamonds:
        return "C"
    if clubs == 3 and diamonds == 3:
        return "C"
    return "D"


def choose_weak_two(
    lengths: dict[str, int],
    hcp: int,
    top_honors_by_suit: dict[str, int] | None = None,
    vulnerability: str | None = None,
) -> str | None:
    if not 6 <= hcp <= 10:
        return None
    # 当前训练不使用弱 2♣；6-6 双套在可开弱二花色中按质量（A/K/Q 张数）选择。
    # 有局宕二无局宕三：仅当该套至少可叫到二阶时才开弱二。
    # 无局至少1张顶张，有局至少2张顶张。
    honors = top_honors_by_suit or {}
    min_honors = preempt_min_top_honors(vulnerability)
    candidates = [
        suit
        for suit in ["S", "H", "D"]
        if lengths[suit] >= 6
        and honors.get(suit, 0) >= min_honors
        and max_preempt_level_for_suit(lengths[suit], vulnerability, suit) is not None
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda suit: (honors.get(suit, 0), lengths[suit], suit == "S", suit == "H"),
    )


def choose_preempt_opening(
    lengths: dict[str, int],
    hcp: int,
    vulnerability: str | None = None,
    top_honors_by_suit: dict[str, int] | None = None,
) -> str | None:
    """7+ 长套阻击：按套长与有局宕二无局宕三定阶；二阶交由弱二处理。

    长套还需满足顶张质量：无局至少1张，有局至少2张。
    """
    if not 5 <= hcp <= 10:
        return None
    honors = top_honors_by_suit or {}
    min_honors = preempt_min_top_honors(vulnerability)
    candidates: list[tuple[str, int]] = []
    for suit in ["S", "H", "D", "C"]:
        length = lengths[suit]
        if length < 7 or honors.get(suit, 0) < min_honors:
            continue
        level = max_preempt_level_for_suit(length, vulnerability, suit)
        if level is None or level < 3:
            continue
        candidates.append((suit, level))
    if not candidates:
        return None
    suit, level = max(
        candidates,
        key=lambda item: (lengths[item[0]], item[0] == "S", item[0] == "H", item[1]),
    )
    return f"{level}{suit_symbol(suit)}"


def choose_gambling_3nt_minor(
    evaluation: HandEvaluation,
    opening_min_hcp: int = 12,
) -> str | None:
    """拼搏式 3NT：7+ 坚固低花（含 AKQ），边张无 A/K/Q，且未达一阶开叫点力。"""
    if evaluation.hcp >= opening_min_hcp:
        return None
    lengths = evaluation.lengths
    honors = evaluation.top_honors_by_suit
    candidates: list[str] = []
    for suit in ["C", "D"]:
        if lengths[suit] < 7 or honors.get(suit, 0) < 3:
            continue
        outside_top = sum(honors.get(other, 0) for other in ["S", "H", "D", "C"] if other != suit)
        if outside_top == 0:
            candidates.append(suit)
    if not candidates:
        return None
    return max(candidates, key=lambda suit: (lengths[suit], suit == "D"))


def choose_two_over_one_suit(lengths: dict[str, int], excluded: str) -> str | None:
    candidates = [suit for suit in ["C", "D", "H"] if suit != excluded and lengths[suit] >= 4]
    if not candidates:
        return None
    return max(candidates, key=lambda suit: (lengths[suit], suit == "H", suit == "D"))


def choose_one_level_major_response(lengths: dict[str, int]) -> str | None:
    hearts = lengths["H"]
    spades = lengths["S"]
    if hearts < 4 and spades < 4:
        return None
    if spades > hearts:
        return "S"
    return "H"


def suit_symbol(suit: str) -> str:
    return {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}[suit]
