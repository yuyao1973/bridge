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
    "4♥",
    "4♠",
    "5♣",
    "5♦",
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
            f"{hcp} HCP，达到当前设置的强 2♣ 下限 {settings.strong_two_club_min} HCP。牌型：{length_text}。",
            "强 2♣",
        )

    if evaluation.balanced and 20 <= hcp <= 21:
        return BidRecommendation(
            "2NT",
            f"{hcp} HCP 且均型，符合 20-21 均型 2NT 开叫。牌型：{length_text}。",
            "20-21 均型 2NT",
        )

    if evaluation.balanced and settings.one_nt_min <= hcp <= settings.one_nt_max:
        return BidRecommendation(
            "1NT",
            f"{hcp} HCP 且均型，符合当前设置的 {settings.one_nt_min}-{settings.one_nt_max} 均型 1NT 开叫。牌型：{length_text}。",
            f"{settings.one_nt_min}-{settings.one_nt_max} 均型 1NT",
        )

    if hcp >= settings.opening_min_hcp and (lengths["S"] >= 5 or lengths["H"] >= 5):
        suit = choose_major_opening(lengths)
        return BidRecommendation(
            f"1{suit_symbol(suit)}",
            f"{hcp} HCP，达到当前一阶开叫下限 {settings.opening_min_hcp} HCP，持有 5 张以上高花，应优先开叫高花。选择 {SUIT_NAMES[suit]}，牌型：{length_text}。",
            "五张高花开叫",
        )

    if hcp >= settings.opening_min_hcp:
        suit = choose_minor_opening(lengths)
        return BidRecommendation(
            f"1{suit_symbol(suit)}",
            f"{hcp} HCP，达到当前一阶开叫下限 {settings.opening_min_hcp} HCP，没有 5 张高花，按较长低花/Better Minor 原则开叫 {SUIT_NAMES[suit]}。牌型：{length_text}。",
            "低花开叫",
        )

    preempt = choose_preempt_opening(lengths, hcp) if settings.weak_two_enabled else None
    if preempt is not None:
        return BidRecommendation(
            preempt,
            f"{hcp} HCP，持有长套，符合当前简化阻击叫条件，开叫 {preempt}。牌型：{length_text}。",
            "阻击开叫",
        )

    weak_two = choose_weak_two(lengths, hcp) if settings.weak_two_enabled else None
    if weak_two is not None:
        return BidRecommendation(
            f"2{suit_symbol(weak_two)}",
            f"{hcp} HCP，持有 6 张 {SUIT_NAMES[weak_two]}，可作二阶弱二开叫。当前训练不使用弱 2♣。牌型：{length_text}。",
            "弱二开叫",
        )

    return BidRecommendation(
        "Pass",
        f"{hcp} HCP，未达到正常开叫条件，也不符合当前弱二规则，建议 Pass。牌型：{length_text}。",
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

    # 一阶开叫后同伴 1NT 应叫，最低限均型通常以止叫为主。
    if opening_level == 1 and response_bid == "1NT" and evaluation.balanced and hcp <= 14:
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

    if response_suit in {"H", "S"} and lengths[response_suit] >= 4:
        level = choose_raise_level(response_level, raise_hcp)
        bid = f"{level}{suit_symbol(response_suit)}"
        return BidRecommendation(
            bid,
            f"同伴应叫 {response_bid}，你有 {hcp} HCP 和 {lengths[response_suit]} 张 {SUIT_NAMES[response_suit]} 支持，优先支持同伴高花，叫 {bid}。牌型：{length_text}。",
            "支持同伴高花",
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

    # 一阶开叫-一阶应叫后，若没有可叫的一阶第二套，通常优先再叫 1NT 描述低限牌力。
    opener_length = lengths[opener_suit] if opener_suit is not None else 0
    has_singleton_or_void = min(lengths.values()) <= 1
    if (
        opening_level == 1
        and response_level == 1
        and 12 <= hcp <= 14
        and opener_length <= 5
        and not has_singleton_or_void
        and is_legal_response_bid(response_bid, "1NT")
    ):
        one_level_second_suit = choose_one_level_second_suit(lengths, opener_suit, response_suit, response_bid)
        if one_level_second_suit is None:
            return BidRecommendation(
                "1NT",
                f"你有 {hcp} HCP，一阶开叫后同伴一阶应叫；牌型无单缺且开叫套不超过 5 张，当前没有可叫的一阶第二套，优先再叫 1NT 表示低限并控制叫牌高度。牌型：{length_text}。",
                "一阶序列低限再叫 1NT",
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

    opener_rebid_contract = parse_contract_bid(opener_rebid_bid)
    response_contract = parse_contract_bid(response_bid)
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

    # 1NT 开叫后的序列：1NT - 2♣(Stayman) / 2♦(红心转移) / 2♥(黑桃转移) - 开叫者应答
    if opening_bid == "1NT":
        game_adjustment_nt = game_threshold_adjustment(vulnerability, settings)
        # 1NT 约 15-17 HCP，应叫者进局门槛：合计 25 HCP，即应叫者约需 8-10 HCP；邀局约 8-9 HCP
        nt_resp_game_hcp = max(8, 10 + game_adjustment_nt)
        nt_resp_invite_low = max(6, 8 + game_adjustment_nt)
        nt_resp_invite_high = nt_resp_game_hcp - 1

        # Stayman 否定序列：1NT - 2♣ - 2♦（未找到 4 张高花），应叫者转入无将分档。
        if response_bid == "2♣" and opener_rebid_bid == "2♦":
            if hcp >= nt_resp_game_hcp and is_legal_response_bid(opener_rebid_bid, "3NT"):
                return BidRecommendation(
                    "3NT",
                    f"1NT-2♣-2♦ 序列中，开叫者否定 4 张高花；你有 {hcp} HCP，叫 3NT 进无将局。牌型：{length_text}。",
                    "Stayman 否定后无将进局",
                )
            if nt_resp_invite_low <= hcp <= nt_resp_invite_high and is_legal_response_bid(opener_rebid_bid, "2NT"):
                return BidRecommendation(
                    "2NT",
                    f"1NT-2♣-2♦ 序列中，开叫者否定 4 张高花；你有 {hcp} HCP，叫 2NT 邀局。牌型：{length_text}。",
                    "Stayman 否定后无将邀局",
                )
            return BidRecommendation(
                "Pass",
                f"1NT-2♣-2♦ 序列中，开叫者否定 4 张高花；你有 {hcp} HCP，牌力不足以邀局，建议 Pass。牌型：{length_text}。",
                "Stayman 否定后止叫",
            )

        # Stayman 序列：1NT - 2♣ - 2♥/2♠（找到高花配合）
        if response_bid == "2♣" and opener_strain in {"♥", "♠"} and opener_suit is not None:
            if lengths[opener_suit] >= 4:
                # 有 4 张配合，按牌力选择加叫层级
                if hcp >= nt_resp_game_hcp:
                    major_game = f"4{opener_strain}"
                    if is_legal_response_bid(opener_rebid_bid, major_game):
                        return BidRecommendation(
                            major_game,
                            f"1NT-2♣-{opener_rebid_bid} 序列后，你有 {hcp} HCP 和 {lengths[opener_suit]} 张配合，叫 {major_game} 进高花局。牌型：{length_text}。",
                            "Stayman 后高花进局",
                        )
                if hcp >= nt_resp_invite_low:
                    major_invite = f"3{opener_strain}"
                    if is_legal_response_bid(opener_rebid_bid, major_invite):
                        return BidRecommendation(
                            major_invite,
                            f"1NT-2♣-{opener_rebid_bid} 序列后，你有 {hcp} HCP 和 {lengths[opener_suit]} 张配合，叫 {major_invite} 邀请高花局。牌型：{length_text}。",
                            "Stayman 后高花邀局",
                        )
            # 无 4 张配合或牌力不足，按 HCP 选 NT 层级
            if hcp >= nt_resp_game_hcp and is_legal_response_bid(opener_rebid_bid, "3NT"):
                return BidRecommendation(
                    "3NT",
                    f"1NT-2♣-{opener_rebid_bid} 序列后，你有 {hcp} HCP，无高花配合，叫 3NT 进无将局。牌型：{length_text}。",
                    "Stayman 后无将进局",
                )
            if hcp >= nt_resp_invite_low and is_legal_response_bid(opener_rebid_bid, "2NT"):
                return BidRecommendation(
                    "2NT",
                    f"1NT-2♣-{opener_rebid_bid} 序列后，你有 {hcp} HCP，邀请无将局。牌型：{length_text}。",
                    "Stayman 后无将邀局",
                )
            return BidRecommendation(
                "Pass",
                f"1NT-2♣-{opener_rebid_bid} 序列后，你有 {hcp} HCP，牌力不足以邀局，建议 Pass。牌型：{length_text}。",
                "Stayman 后止叫",
            )

        # 转移序列：1NT - 2♦ - 2♥（红心转移完成）
        if response_bid == "2♦" and opener_rebid_bid == "2♥":
            if hcp >= nt_resp_game_hcp:
                if lengths["H"] >= 6 and is_legal_response_bid("2♥", "4♥"):
                    return BidRecommendation(
                        "4♥",
                        f"红心转移完成后，你有 {hcp} HCP 和 {lengths['H']} 张红心，直接进 4♥。牌型：{length_text}。",
                        "转移后高花进局",
                    )
                if is_legal_response_bid("2♥", "3NT"):
                    return BidRecommendation(
                        "3NT",
                        f"红心转移完成后，你有 {hcp} HCP，选择 3NT 进无将局。牌型：{length_text}。",
                        "转移后无将进局",
                    )
            if hcp >= nt_resp_invite_low:
                if is_legal_response_bid("2♥", "2NT"):
                    return BidRecommendation(
                        "2NT",
                        f"红心转移完成后，你有 {hcp} HCP，叫 2NT 邀局。牌型：{length_text}。",
                        "转移后邀局",
                    )
            return BidRecommendation(
                "Pass",
                f"红心转移完成后，你有 {hcp} HCP，牌力不足进局，建议 Pass。牌型：{length_text}。",
                "转移后止叫",
            )

        # 转移序列：1NT - 2♥ - 2♠（黑桃转移完成）
        if response_bid == "2♥" and opener_rebid_bid == "2♠":
            if hcp >= nt_resp_game_hcp:
                if lengths["S"] >= 6 and is_legal_response_bid("2♠", "4♠"):
                    return BidRecommendation(
                        "4♠",
                        f"黑桃转移完成后，你有 {hcp} HCP 和 {lengths['S']} 张黑桃，直接进 4♠。牌型：{length_text}。",
                        "转移后高花进局",
                    )
                if is_legal_response_bid("2♠", "3NT"):
                    return BidRecommendation(
                        "3NT",
                        f"黑桃转移完成后，你有 {hcp} HCP，选择 3NT 进无将局。牌型：{length_text}。",
                        "转移后无将进局",
                    )
            if hcp >= nt_resp_invite_low:
                if is_legal_response_bid("2♠", "2NT"):
                    return BidRecommendation(
                        "2NT",
                        f"黑桃转移完成后，你有 {hcp} HCP，叫 2NT 邀局。牌型：{length_text}。",
                        "转移后邀局",
                    )
            return BidRecommendation(
                "Pass",
                f"黑桃转移完成后，你有 {hcp} HCP，牌力不足进局，建议 Pass。牌型：{length_text}。",
                "转移后止叫",
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

    if opener_suit in {"H", "S"} and lengths[opener_suit] >= 3:
        level = choose_raise_level(opener_rebid_contract[0], raise_hcp)
        bid = f"{level}{suit_symbol(opener_suit)}"
        if is_legal_response_bid(opener_rebid_bid, bid):
            return BidRecommendation(
                bid,
                f"开叫者再叫 {opener_rebid_bid}，你有 {lengths[opener_suit]} 张支持和 {hcp} HCP，继续支持到 {bid}。牌型：{length_text}。",
                "支持开叫者再叫花色",
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

    if hcp >= max(10, 12 + game_adjustment) and is_legal_response_bid(opener_rebid_bid, "3NT"):
        return BidRecommendation(
            "3NT",
            f"你有 {hcp} HCP，虽无明确高花配合，优先转入 3NT 进局。牌型：{length_text}。",
            "默认 3NT 进局",
        )

    return BidRecommendation(
        "Pass",
        f"当前简化规则下无更优再应叫，建议 Pass。你有 {hcp} HCP，牌型：{length_text}。",
        "默认止叫",
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
    if settings.stayman_enabled and hcp >= 8 and (lengths["H"] >= 4 or lengths["S"] >= 4):
        return BidRecommendation(
            "2♣",
            f"同伴开 1NT，你有 {hcp} HCP 且至少一个 4 张高花。用 2♣ Stayman 寻找 4-4 高花配合。牌型：{length_text}。",
            "Stayman",
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


def choose_weak_two(lengths: dict[str, int], hcp: int) -> str | None:
    if not 6 <= hcp <= 10:
        return None
    candidates = [suit for suit in ["S", "H", "D"] if lengths[suit] >= 6]
    if not candidates:
        return None
    return max(candidates, key=lambda suit: (lengths[suit], suit == "S", suit == "H"))


def choose_preempt_opening(lengths: dict[str, int], hcp: int) -> str | None:
    if not 5 <= hcp <= 10:
        return None
    suit = max(["S", "H", "D", "C"], key=lambda candidate: (lengths[candidate], candidate == "S", candidate == "H"))
    length = lengths[suit]
    if length >= 8 and suit in {"C", "D"} and hcp >= 8:
        return f"5{suit_symbol(suit)}"
    if length >= 8:
        return f"4{suit_symbol(suit)}"
    if length >= 7:
        return f"3{suit_symbol(suit)}"
    return None


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
