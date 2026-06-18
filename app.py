from __future__ import annotations

import random
import re

import streamlit as st

from bridge_trainer.bidding import RuleSettings, legal_rebid_bids, legal_response_bids
from bridge_trainer.cards import format_hand_lines
from bridge_trainer.training import (
    TrainingQuestion,
    generate_opener_rebid_question,
    generate_opening_question,
    generate_responder_rebid_question,
    generate_response_question,
)

st.set_page_config(page_title="桥牌 2/1 叫牌训练", page_icon="♠", layout="centered")

st.markdown(
    """
    <style>
    .disabled-bid {
        width: 100%;
        min-height: 2.1rem;
        padding: 0.28rem 0.45rem;
        border: 1px solid #d0d5dd;
        border-radius: 0.5rem;
        background: #f2f4f7;
        color: #98a2b3;
        text-align: center;
        font-weight: 600;
        font-size: 0.88rem;
        cursor: not-allowed;
        opacity: 0.55;
        user-select: none;
    }
    [class*="st-key-bid_"] button {
        min-height: 2.1rem;
        padding: 0.28rem 0.45rem;
        font-size: 0.88rem;
        font-weight: 600;
        line-height: 1.15;
        border-width: 1px !important;
        border-radius: 0.5rem !important;
        transition: box-shadow 0.12s ease, transform 0.12s ease, filter 0.12s ease;
    }
    [class*="st-key-bid_"] button:hover:not(:disabled) {
        filter: brightness(0.97);
        box-shadow: 0 0 0 2px rgba(16, 24, 40, 0.18);
        transform: translateY(-1px);
    }
    [class*="st-key-bid_"] button[kind="primary"] {
        box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.95), 0 0 0 5px rgba(245, 158, 11, 0.25);
        font-weight: 700;
        transform: translateY(-1px);
    }
    .disabled-bid::before {
        content: "✕ ";
        color: #b42318;
    }
    .disabled-bid.bid-club {
        border-color: #2e7d32;
        color: #1b5e20;
        background: #e8f5e9;
    }
    .disabled-bid.bid-diamond {
        border-color: #c62828;
        color: #8e1111;
        background: #fdecea;
    }
    .disabled-bid.bid-heart {
        border-color: #e53935;
        color: #b71c1c;
        background: #ffebee;
    }
    .disabled-bid.bid-spade {
        border-color: #455a64;
        color: #263238;
        background: #eceff1;
    }
    .disabled-bid.bid-nt {
        border-color: #00897b;
        color: #005f56;
        background: #e0f2f1;
    }
    .disabled-bid.bid-pass {
        border-color: #78909c;
        color: #455a64;
        background: #eceff1;
    }
    [class*="st-key-bid_club_"] button {
        border-color: #2e7d32 !important;
        color: #1b5e20 !important;
        background: #e8f5e9 !important;
    }
    [class*="st-key-bid_diamond_"] button {
        border-color: #c62828 !important;
        color: #8e1111 !important;
        background: #fdecea !important;
    }
    [class*="st-key-bid_heart_"] button {
        border-color: #e53935 !important;
        color: #b71c1c !important;
        background: #ffebee !important;
    }
    [class*="st-key-bid_spade_"] button {
        border-color: #455a64 !important;
        color: #263238 !important;
        background: #eceff1 !important;
    }
    [class*="st-key-bid_nt_"] button {
        border-color: #00897b !important;
        color: #005f56 !important;
        background: #e0f2f1 !important;
    }
    [class*="st-key-bid_pass_"] button {
        border-color: #78909c !important;
        color: #455a64 !important;
        background: #eceff1 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

OPENER_CATEGORY_OPTIONS = ["一阶定约", "强开叫", "阻击叫"]
OPENER_BIDS_BY_CATEGORY = {
    "一阶定约": ["随机", "1♣", "1♦", "1♥", "1♠", "1NT"],
    "强开叫": ["2♣", "2NT"],
    "阻击叫": ["随机", "2♦", "2♥", "2♠", "3♣", "3♦", "3♥", "3♠", "4♣", "4♦", "4♥", "4♠", "5♣", "5♦"],
}


def opener_bid_options(category: str) -> list[str]:
    return OPENER_BIDS_BY_CATEGORY.get(category, OPENER_BIDS_BY_CATEGORY["一阶定约"])


def payload_opener_bid(selected_bid: str) -> str | None:
    if selected_bid == "随机":
        return None
    return selected_bid


def response_bid_options_for_opener(selected_bid: str) -> list[str]:
    opener_bid = payload_opener_bid(selected_bid)
    if opener_bid is None:
        return ["随机"]
    return ["随机", *legal_response_bids(opener_bid)]


def payload_response_bid(selected_bid: str) -> str | None:
    if selected_bid == "随机":
        return None
    return selected_bid


def opener_rebid_bid_options_for_response(selected_bid: str) -> list[str]:
    response_bid = payload_response_bid(selected_bid)
    if response_bid is None:
        return ["随机"]
    return ["随机", *legal_rebid_bids(response_bid)]


def payload_opener_rebid_bid(selected_bid: str) -> str | None:
    if selected_bid == "随机":
        return None
    return selected_bid


def selected_opener_bid(bid_key: str, category_key: str) -> tuple[str, str]:
    category = st.session_state.get(category_key, "一阶定约")
    options = opener_bid_options(category)
    bid = st.session_state.get(bid_key, options[0])
    if bid not in options:
        bid = options[0]
        st.session_state[bid_key] = bid
    return bid, category


def reset_auction_meaning() -> None:
    st.session_state.auction_clicked_bid = None
    st.session_state.auction_clicked_meaning = ""


def init_state() -> None:
    if "mode" not in st.session_state:
        st.session_state.mode = "开叫训练"
    if "response_opener_bid" not in st.session_state:
        st.session_state.response_opener_bid = "随机"
    if "response_opener_category" not in st.session_state:
        st.session_state.response_opener_category = "一阶定约"
    if "opener_rebid_opener_bid" not in st.session_state:
        st.session_state.opener_rebid_opener_bid = "随机"
    if "opener_rebid_opener_category" not in st.session_state:
        st.session_state.opener_rebid_opener_category = "一阶定约"
    if "opener_rebid_response_bid" not in st.session_state:
        st.session_state.opener_rebid_response_bid = "随机"
    if "responder_rebid_opener_bid" not in st.session_state:
        st.session_state.responder_rebid_opener_bid = "随机"
    if "responder_rebid_opener_category" not in st.session_state:
        st.session_state.responder_rebid_opener_category = "一阶定约"
    if "responder_rebid_response_bid" not in st.session_state:
        st.session_state.responder_rebid_response_bid = "随机"
    if "responder_rebid_opener_rebid_bid" not in st.session_state:
        st.session_state.responder_rebid_opener_rebid_bid = "随机"
    if "setting_opening_min_hcp" not in st.session_state:
        st.session_state.setting_opening_min_hcp = 12
    if "setting_one_nt_range" not in st.session_state:
        st.session_state.setting_one_nt_range = "15-17"
    if "setting_strong_two_club_min" not in st.session_state:
        st.session_state.setting_strong_two_club_min = 22
    if "setting_weak_two_enabled" not in st.session_state:
        st.session_state.setting_weak_two_enabled = True
    if "setting_august_2nt_enabled" not in st.session_state:
        st.session_state.setting_august_2nt_enabled = True
    if "setting_stayman_enabled" not in st.session_state:
        st.session_state.setting_stayman_enabled = True
    if "setting_transfers_enabled" not in st.session_state:
        st.session_state.setting_transfers_enabled = True
    if "setting_jacoby_2nt_enabled" not in st.session_state:
        st.session_state.setting_jacoby_2nt_enabled = True
    if "setting_bergen_raises_enabled" not in st.session_state:
        st.session_state.setting_bergen_raises_enabled = True
    if "setting_two_over_one_min_hcp" not in st.session_state:
        st.session_state.setting_two_over_one_min_hcp = 12
    if "setting_forcing_nt_hcp_range" not in st.session_state:
        st.session_state.setting_forcing_nt_hcp_range = "6-11"
    if "setting_responder_simple_raise_max" not in st.session_state:
        st.session_state.setting_responder_simple_raise_max = 9
    if "setting_responder_limit_raise_range" not in st.session_state:
        st.session_state.setting_responder_limit_raise_range = "10-12"
    if "setting_responder_bergen_weak_max" not in st.session_state:
        st.session_state.setting_responder_bergen_weak_max = 9
    if "setting_splinter_enabled" not in st.session_state:
        st.session_state.setting_splinter_enabled = True
    if "setting_responder_splinter_min_hcp" not in st.session_state:
        st.session_state.setting_responder_splinter_min_hcp = 11
    if "setting_responder_splinter_max_hcp" not in st.session_state:
        st.session_state.setting_responder_splinter_max_hcp = 15
    if "setting_negative_double_enabled" not in st.session_state:
        st.session_state.setting_negative_double_enabled = True
    if "setting_negative_double_min_hcp" not in st.session_state:
        st.session_state.setting_negative_double_min_hcp = 6
    if "setting_forcing_nt_label" not in st.session_state:
        st.session_state.setting_forcing_nt_label = "半逼叫"
    if "setting_scoring_mode" not in st.session_state:
        st.session_state.setting_scoring_mode = "IMP"
    if "setting_respect_vulnerability" not in st.session_state:
        st.session_state.setting_respect_vulnerability = True
    if "setting_game_aggressiveness" not in st.session_state:
        st.session_state.setting_game_aggressiveness = 0
    if "question" not in st.session_state:
        st.session_state.question = new_question(st.session_state.mode)
    ensure_current_question()
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "selected_bid" not in st.session_state:
        st.session_state.selected_bid = "Pass"
    if "total" not in st.session_state:
        st.session_state.total = 0
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "auction_clicked_bid" not in st.session_state:
        st.session_state.auction_clicked_bid = None
    if "auction_clicked_meaning" not in st.session_state:
        st.session_state.auction_clicked_meaning = ""


def ensure_current_question() -> None:
    question = st.session_state.get("question")
    if (
        question is None
        or not hasattr(question, "legal_choices")
        or not hasattr(question, "response_bid")
        or not hasattr(question, "opener_rebid_bid")
    ):
        st.session_state.question = new_question(st.session_state.mode)


def current_rule_settings() -> RuleSettings:
    one_nt_range = st.session_state.get("setting_one_nt_range", "15-17")
    one_nt_min, one_nt_max = [int(value) for value in one_nt_range.split("-")]
    forcing_nt_range = st.session_state.get("setting_forcing_nt_hcp_range", "6-11")
    forcing_nt_min, forcing_nt_max = [int(value) for value in forcing_nt_range.split("-")]
    responder_limit_range = st.session_state.get("setting_responder_limit_raise_range", "10-12")
    responder_limit_min, responder_limit_max = [int(value) for value in responder_limit_range.split("-")]
    rule_kwargs = {
        "opening_min_hcp": st.session_state.get("setting_opening_min_hcp", 12),
        "one_nt_min": one_nt_min,
        "one_nt_max": one_nt_max,
        "strong_two_club_min": st.session_state.get("setting_strong_two_club_min", 22),
        "weak_two_enabled": st.session_state.get("setting_weak_two_enabled", True),
        "august_2nt_enabled": st.session_state.get("setting_august_2nt_enabled", True),
        "stayman_enabled": st.session_state.get("setting_stayman_enabled", True),
        "transfers_enabled": st.session_state.get("setting_transfers_enabled", True),
        "jacoby_2nt_enabled": st.session_state.get("setting_jacoby_2nt_enabled", True),
        "bergen_raises_enabled": st.session_state.get("setting_bergen_raises_enabled", True),
        "two_over_one_min_hcp": st.session_state.get("setting_two_over_one_min_hcp", 12),
        "forcing_nt_min_hcp": forcing_nt_min,
        "forcing_nt_max_hcp": forcing_nt_max,
        "responder_simple_raise_max": st.session_state.get("setting_responder_simple_raise_max", 9),
        "responder_limit_raise_min": responder_limit_min,
        "responder_limit_raise_max": responder_limit_max,
        "responder_bergen_weak_max": st.session_state.get("setting_responder_bergen_weak_max", 9),
        "splinter_enabled": st.session_state.get("setting_splinter_enabled", True),
        "responder_splinter_min_hcp": st.session_state.get("setting_responder_splinter_min_hcp", 11),
        "responder_splinter_max_hcp": st.session_state.get("setting_responder_splinter_max_hcp", 15),
        "negative_double_enabled": st.session_state.get("setting_negative_double_enabled", True),
        "negative_double_min_hcp": st.session_state.get("setting_negative_double_min_hcp", 6),
        "forcing_nt_label": st.session_state.get("setting_forcing_nt_label", "半逼叫"),
        "scoring_mode": st.session_state.get("setting_scoring_mode", "IMP"),
        "respect_vulnerability": st.session_state.get("setting_respect_vulnerability", True),
        "game_aggressiveness": st.session_state.get("setting_game_aggressiveness", 0),
    }
    supported = getattr(RuleSettings, "__dataclass_fields__", {})
    filtered_kwargs = {key: value for key, value in rule_kwargs.items() if key in supported}
    return RuleSettings(**filtered_kwargs)


def new_question(mode: str) -> TrainingQuestion:
    seed = random.randint(1, 1_000_000_000)
    settings = current_rule_settings()
    if mode == "应叫训练":
        opener_bid, opener_category = selected_opener_bid("response_opener_bid", "response_opener_category")
        return generate_response_question(seed, payload_opener_bid(opener_bid), settings, opener_category)
    if mode == "开叫者再叫训练":
        opener_bid, opener_category = selected_opener_bid("opener_rebid_opener_bid", "opener_rebid_opener_category")
        response_bid = payload_response_bid(st.session_state.get("opener_rebid_response_bid", "随机"))
        return generate_opener_rebid_question(
            seed,
            settings,
            payload_opener_bid(opener_bid),
            opener_category,
            response_bid=response_bid,
        )
    if mode == "应叫者第二次应叫训练":
        opener_bid, opener_category = selected_opener_bid("responder_rebid_opener_bid", "responder_rebid_opener_category")
        response_bid = payload_response_bid(st.session_state.get("responder_rebid_response_bid", "随机"))
        opener_rebid_bid = payload_opener_rebid_bid(st.session_state.get("responder_rebid_opener_rebid_bid", "随机"))
        return generate_responder_rebid_question(
            seed,
            settings,
            payload_opener_bid(opener_bid),
            opener_category,
            response_bid=response_bid,
            opener_rebid_bid=opener_rebid_bid,
        )
    return generate_opening_question(seed, settings)


def next_question() -> None:
    st.session_state.question = new_question(st.session_state.mode)
    st.session_state.submitted = False
    st.session_state.selected_bid = "Pass"
    st.session_state.auction_clicked_bid = None
    st.session_state.auction_clicked_meaning = ""


def change_mode() -> None:
    st.session_state.mode = st.session_state.mode_choice
    st.session_state.question = new_question(st.session_state.mode)
    st.session_state.submitted = False
    st.session_state.selected_bid = "Pass"
    st.session_state.auction_clicked_bid = None
    st.session_state.auction_clicked_meaning = ""


def change_response_opener() -> None:
    st.session_state.response_opener_bid = st.session_state.response_opener_choice
    if st.session_state.mode == "应叫训练":
        st.session_state.question = new_question(st.session_state.mode)
        st.session_state.submitted = False
        st.session_state.selected_bid = "Pass"
        reset_auction_meaning()


def change_response_opener_category() -> None:
    st.session_state.response_opener_category = st.session_state.response_opener_category_choice
    st.session_state.response_opener_bid = opener_bid_options(st.session_state.response_opener_category)[0]
    if st.session_state.mode == "应叫训练":
        st.session_state.question = new_question(st.session_state.mode)
        st.session_state.submitted = False
        st.session_state.selected_bid = "Pass"
        reset_auction_meaning()


def change_opener_rebid_opener() -> None:
    st.session_state.opener_rebid_opener_bid = st.session_state.opener_rebid_opener_choice
    response_options = response_bid_options_for_opener(st.session_state.opener_rebid_opener_bid)
    if st.session_state.opener_rebid_response_bid not in response_options:
        st.session_state.opener_rebid_response_bid = response_options[0]
    if st.session_state.mode == "开叫者再叫训练":
        st.session_state.question = new_question(st.session_state.mode)
        st.session_state.submitted = False
        st.session_state.selected_bid = "Pass"
        reset_auction_meaning()


def change_opener_rebid_opener_category() -> None:
    st.session_state.opener_rebid_opener_category = st.session_state.opener_rebid_opener_category_choice
    st.session_state.opener_rebid_opener_bid = opener_bid_options(st.session_state.opener_rebid_opener_category)[0]
    st.session_state.opener_rebid_response_bid = response_bid_options_for_opener(st.session_state.opener_rebid_opener_bid)[0]
    if st.session_state.mode == "开叫者再叫训练":
        st.session_state.question = new_question(st.session_state.mode)
        st.session_state.submitted = False
        st.session_state.selected_bid = "Pass"
        reset_auction_meaning()


def change_opener_rebid_response() -> None:
    st.session_state.opener_rebid_response_bid = st.session_state.opener_rebid_response_choice
    if st.session_state.mode == "开叫者再叫训练":
        st.session_state.question = new_question(st.session_state.mode)
        st.session_state.submitted = False
        st.session_state.selected_bid = "Pass"
        reset_auction_meaning()


def change_responder_rebid_opener() -> None:
    st.session_state.responder_rebid_opener_bid = st.session_state.responder_rebid_opener_choice
    response_options = response_bid_options_for_opener(st.session_state.responder_rebid_opener_bid)
    if st.session_state.responder_rebid_response_bid not in response_options:
        st.session_state.responder_rebid_response_bid = response_options[0]
    opener_rebid_options = opener_rebid_bid_options_for_response(st.session_state.responder_rebid_response_bid)
    if st.session_state.responder_rebid_opener_rebid_bid not in opener_rebid_options:
        st.session_state.responder_rebid_opener_rebid_bid = opener_rebid_options[0]
    if st.session_state.mode == "应叫者第二次应叫训练":
        st.session_state.question = new_question(st.session_state.mode)
        st.session_state.submitted = False
        st.session_state.selected_bid = "Pass"
        reset_auction_meaning()


def change_responder_rebid_opener_category() -> None:
    st.session_state.responder_rebid_opener_category = st.session_state.responder_rebid_opener_category_choice
    st.session_state.responder_rebid_opener_bid = opener_bid_options(st.session_state.responder_rebid_opener_category)[0]
    st.session_state.responder_rebid_response_bid = response_bid_options_for_opener(st.session_state.responder_rebid_opener_bid)[0]
    st.session_state.responder_rebid_opener_rebid_bid = opener_rebid_bid_options_for_response(
        st.session_state.responder_rebid_response_bid
    )[0]
    if st.session_state.mode == "应叫者第二次应叫训练":
        st.session_state.question = new_question(st.session_state.mode)
        st.session_state.submitted = False
        st.session_state.selected_bid = "Pass"
        reset_auction_meaning()


def change_responder_rebid_response() -> None:
    st.session_state.responder_rebid_response_bid = st.session_state.responder_rebid_response_choice
    opener_rebid_options = opener_rebid_bid_options_for_response(st.session_state.responder_rebid_response_bid)
    if st.session_state.responder_rebid_opener_rebid_bid not in opener_rebid_options:
        st.session_state.responder_rebid_opener_rebid_bid = opener_rebid_options[0]
    if st.session_state.mode == "应叫者第二次应叫训练":
        st.session_state.question = new_question(st.session_state.mode)
        st.session_state.submitted = False
        st.session_state.selected_bid = "Pass"
        reset_auction_meaning()


def change_responder_rebid_opener_rebid() -> None:
    st.session_state.responder_rebid_opener_rebid_bid = st.session_state.responder_rebid_opener_rebid_choice
    if st.session_state.mode == "应叫者第二次应叫训练":
        st.session_state.question = new_question(st.session_state.mode)
        st.session_state.submitted = False
        st.session_state.selected_bid = "Pass"
        reset_auction_meaning()


def change_rules() -> None:
    st.session_state.question = new_question(st.session_state.mode)
    st.session_state.submitted = False
    st.session_state.selected_bid = "Pass"
    st.session_state.auction_clicked_bid = None
    st.session_state.auction_clicked_meaning = ""


def reset_rules() -> None:
    st.session_state.setting_opening_min_hcp = 12
    st.session_state.setting_one_nt_range = "15-17"
    st.session_state.setting_strong_two_club_min = 22
    st.session_state.setting_weak_two_enabled = True
    st.session_state.setting_august_2nt_enabled = True
    st.session_state.setting_stayman_enabled = True
    st.session_state.setting_transfers_enabled = True
    st.session_state.setting_jacoby_2nt_enabled = True
    st.session_state.setting_bergen_raises_enabled = True
    st.session_state.setting_two_over_one_min_hcp = 12
    st.session_state.setting_forcing_nt_hcp_range = "6-11"
    st.session_state.setting_responder_simple_raise_max = 9
    st.session_state.setting_responder_limit_raise_range = "10-12"
    st.session_state.setting_responder_bergen_weak_max = 9
    st.session_state.setting_splinter_enabled = True
    st.session_state.setting_responder_splinter_min_hcp = 11
    st.session_state.setting_responder_splinter_max_hcp = 15
    st.session_state.setting_negative_double_enabled = True
    st.session_state.setting_negative_double_min_hcp = 6
    st.session_state.setting_forcing_nt_label = "半逼叫"
    st.session_state.setting_scoring_mode = "IMP"
    st.session_state.setting_respect_vulnerability = True
    st.session_state.setting_game_aggressiveness = 0
    change_rules()


def submit_answer() -> None:
    ensure_current_question()
    if st.session_state.submitted:
        return
    if st.session_state.selected_bid not in st.session_state.question.legal_choices:
        return
    st.session_state.submitted = True
    st.session_state.total += 1
    acceptable = getattr(
        st.session_state.question,
        "acceptable_bids",
        [st.session_state.question.recommendation.bid],
    )
    # Award 2 points for recommended bid, 1 for acceptable alternative, 0 for wrong
    if st.session_state.selected_bid == st.session_state.question.recommendation.bid:
        st.session_state.score += 2
    elif st.session_state.selected_bid in acceptable:
        st.session_state.score += 1


def render_hand(question: TrainingQuestion) -> None:
    st.subheader(f"你的手牌（{question.position}家）")
    for line in format_hand_lines(question.hand):
        st.markdown(f"### {line}")


def render_evaluation(question: TrainingQuestion) -> None:
    evaluation = question.evaluation
    cols = st.columns(3)
    cols[0].metric("HCP", evaluation.hcp)
    cols[1].metric("牌型 ♠-♥-♦-♣", evaluation.shape)
    cols[2].metric("均型", "是" if evaluation.balanced else "否")


def render_feedback(question: TrainingQuestion) -> None:
    recommendation = question.recommendation
    selected = st.session_state.selected_bid
    acceptable = getattr(question, "acceptable_bids", [recommendation.bid])
    if selected == recommendation.bid:
        st.success(f"✓ 正确：推荐叫品是 {recommendation.bid} （+2 分）")
    elif selected in acceptable:
        alternatives = [bid for bid in acceptable if bid != recommendation.bid]
        alt_text = f"（可接受：{', '.join(alternatives)}）" if alternatives else ""
        st.warning(f"⚠ 可接受次优：你选择了 {selected}，主推仍是 {recommendation.bid}{alt_text} （+1 分）")
    else:
        st.error(f"✗ 不太合适：你选择了 {selected}，推荐叫品是 {recommendation.bid} （0 分）")
    st.info(recommendation.explanation)
    st.caption(f"规则：{recommendation.rule_name}")


def choose_bid(bid: str) -> None:
    st.session_state.selected_bid = bid


def bid_style_key(bid: str) -> str:
    if bid == "Pass":
        return "pass"
    if "♣" in bid:
        return "club"
    if "♦" in bid:
        return "diamond"
    if "♥" in bid:
        return "heart"
    if "♠" in bid:
        return "spade"
    if "NT" in bid:
        return "nt"
    return "pass"


def bid_style_class(bid: str) -> str:
    return f"bid-{bid_style_key(bid)}"


def render_bid_picker(question: TrainingQuestion) -> None:
    st.write("请选择叫品")
    legal_choices = getattr(question, "legal_choices", question.choices)
    cols_per_row = 6
    for start in range(0, len(question.choices), cols_per_row):
        cols = st.columns(cols_per_row)
        for index, bid in enumerate(question.choices[start : start + cols_per_row]):
            is_legal = bid in legal_choices
            style_key = bid_style_key(bid)
            if not is_legal:
                cols[index].markdown(
                    f'<div class="disabled-bid {bid_style_class(bid)}">{bid}</div>',
                    unsafe_allow_html=True,
                )
                continue

            button_type = "primary" if bid == st.session_state.selected_bid else "secondary"
            cols[index].button(
                bid,
                key=(
                    f"bid_{style_key}_{question.mode}_{question.opener_bid}_"
                    f"{question.response_bid}_{question.opener_rebid_bid}_{bid}"
                ),
                disabled=st.session_state.submitted,
                type=button_type,
                use_container_width=True,
                on_click=choose_bid,
                args=(bid,),
            )

    st.caption(f"当前选择：{st.session_state.selected_bid}")
    if question.mode == "应叫训练":
        st.caption("带 ✕ 的灰色叫品表示在当前同伴开叫后已经不能选择。")


def parse_contract(bid: str) -> tuple[int, str] | None:
    match = re.match(r"^(\d)(♣|♦|♥|♠|NT)$", str(bid).strip())
    if not match:
        return None
    return int(match.group(1)), match.group(2)


def extract_auction_bids(auction: str) -> list[str]:
    bids: list[str] = []
    for part in re.split(r"[-\s]+", auction):
        token = part.strip()
        if not token or token == "?":
            continue
        if re.fullmatch(r"[1-7](?:♣|♦|♥|♠|NT)", token):
            bids.append(token)
    return bids


def contextual_response_meaning(bid: str, auction_bids: list[str]) -> str | None:
    opening = parse_contract(auction_bids[0] if auction_bids else "")
    response = parse_contract(bid)
    if opening is None or response is None or not auction_bids:
        return None

    seq = f"{auction_bids[0]}-{bid}"
    if opening[0] == 2 and opening[1] in {"♦", "♥", "♠"} and bid == "2NT":
        return f"在 {seq} 中，2NT 是 Ogust 2NT 问叫，通常用于询问弱二开叫者的牌力高低与开叫套质量。"

    if opening[1] == "NT":
        if bid == "2♣":
            return f"在 {seq} 中，2♣ 是 Stayman，通常询问开叫方是否有四张高花。"
        if bid == "2♦":
            return f"在 {seq} 中，2♦ 是红心转移，通常要求同伴转叫 2♥。"
        if bid == "2♥":
            return f"在 {seq} 中，2♥ 是黑桃转移，通常要求同伴转叫 2♠。"
        if bid == "2NT":
            return f"在 {seq} 中，2NT 通常是无将邀局，约 8-9 HCP。"
        if bid == "3NT":
            return f"在 {seq} 中，3NT 通常是直接无将进局。"
        return f"在 {seq} 中，这是 1NT 体系下的应叫，用于处理高花配合与定约层级。"

    # Splinter（短套扣叫）识别：一阶高花开叫后跳叫新花，通常表示对开叫高花的 4+ 张支持与该新花单缺/缺门。
    if opening[0] == 1 and opening[1] == "♥" and bid == "3♠":
        return f"在 {seq} 中，3♠ 通常是 Splinter（短套扣叫）：显示对 ♥ 的 4+ 张支持，并表示 ♠ 单缺/缺门，常见为进局导向牌力。"
    if opening[0] == 1 and opening[1] == "♠" and bid in {"4♣", "4♦", "4♥"}:
        return f"在 {seq} 中，{bid} 通常是 Splinter（短套扣叫）：显示对 ♠ 的 4+ 张支持，并表示所叫花色单缺/缺门，常见为进局导向牌力。"

    # Bergen加叫识别：高花开叫后的3C/3D是约定性Bergen加叫
    if opening[1] in {"♥", "♠"}:
        if bid == "2NT":
            return (
                f"在 {seq} 中，2NT 通常是 Jacoby 2NT 强将问叫："
                f"显示对 {opening[1]} 的 4 张以上支持，并通常具有进局实力。"
            )
        if bid == "3♣":
            return f"在 {seq} 中，3♣ 是 Bergen 弱支持，通常表示 4 张{opening[1]}支持且点数较弱（6-9 HCP）。"
        if bid == "3♦":
            return f"在 {seq} 中，3♦ 是 Bergen 中等支持，通常表示 4 张{opening[1]}支持且点数中等（10-11 HCP）。"
        if response[1] == opening[1]:
            if opening[0] == 1 and response[0] == 2:
                return (
                    f"在 {seq} 中，2{opening[1]} 是简单加叫：通常约 6-9 HCP，"
                    f"并至少 3 张（更常见 4 张）{opening[1]}支持。"
                )
            if opening[0] == 1 and response[0] == 3:
                return (
                    f"在 {seq} 中，3{opening[1]} 通常是限制性加叫：约 10-11 HCP，"
                    f"并有至少 4 张{opening[1]}支持。"
                )
            if opening[0] == 1 and response[0] >= 4:
                return (
                    f"在 {seq} 中，直接进局加叫通常表示较强配合与进局意图，"
                    f"一般有 4 张以上{opening[1]}支持。"
                )
            return f"在 {seq} 中，应叫同花通常表示支持同伴高花并按牌力分层。"
        if bid == "1NT":
            return f"在 {seq} 中，1NT 通常是高花开叫后的半逼叫/逼叫一轮应叫。"

    if opening[1] in {"♣", "♦"}:
        if response[0] == 1 and response[1] in {"♥", "♠"}:
            return f"在 {seq} 中，一阶高花应叫通常显示 4 张高花并争取高花定约。"
    return None


def contextual_opener_rebid_meaning(bid: str, auction_bids: list[str]) -> str | None:
    opening = parse_contract(auction_bids[0] if len(auction_bids) > 0 else "")
    response = parse_contract(auction_bids[1] if len(auction_bids) > 1 else "")
    rebid = parse_contract(bid)
    if rebid is None or opening is None or response is None or len(auction_bids) < 2:
        return "再叫：根据前序叫牌继续描述牌力与牌型"

    seq = f"{auction_bids[0]}-{auction_bids[1]}"
    
    # Bergen加叫识别：高花开叫后的3C/3D是约定性Bergen加叫而非新花
    if opening[1] in {"♥", "♠"}:
        response_bid = auction_bids[1]
        if response_bid == "3♣":
            return f"在 {seq} 中，3♣ 是 Bergen 弱支持，通常表示 4 张{opening[1]}支持且点数较弱（6-9 HCP）。"
        if response_bid == "3♦":
            return f"在 {seq} 中，3♦ 是 Bergen 中等支持，通常表示 4 张{opening[1]}支持且点数中等（10-11 HCP）。"
    
    if opening[1] == "NT":
        response_bid = auction_bids[1]
        if response_bid == "2♣":
            if bid == "2♦":
                return f"在 {seq} 后再叫 2♦：Stayman 否定叫，通常表示没有四张高花。"
            if bid == "2♥":
                return f"在 {seq} 后再叫 2♥：Stayman 应答，通常表示有四张红心。"
            if bid == "2♠":
                return f"在 {seq} 后再叫 2♠：Stayman 应答，通常表示有四张黑桃。"
        if response_bid == "2♦" and bid == "2♥":
            return f"在 {seq} 后再叫 2♥：接受红心转移，通常为标准完成转移。"
        if response_bid == "2♥" and bid == "2♠":
            return f"在 {seq} 后再叫 2♠：接受黑桃转移，通常为标准完成转移。"
        if response_bid == "2NT" and bid == "3NT":
            return f"在 {seq} 后再叫 3NT：接受邀局，确认无将进局。"
        if rebid[1] == "NT":
            return f"在 {seq} 后再叫 {bid}：1NT 体系后续中的无将牌力描述或进程推进。"
        return f"在 {seq} 后再叫 {bid}：1NT 开叫后的约定叫进程（如 Stayman/转移后的应答）。"

    if rebid[1] == "NT":
        if rebid[0] == 1:
            return f"在 {seq} 后再叫 1NT：约 12-14 HCP，均型最低限。"
        if rebid[0] == 2:
            return f"在 {seq} 后再叫 2NT：约 18-19 HCP，均型强牌。"
        return f"在 {seq} 后再叫 {bid}：通常显示均型进局或更强牌力。"

    if rebid[1] == opening[1]:
        return f"在 {seq} 后重复开叫花色 {bid}：通常 12-15 HCP，显示 6+ 张原开叫花色。"
    if rebid[1] == response[1]:
        return f"在 {seq} 后再叫 {bid} 支持应叫花色：通常 13+ HCP，约 3-4 张支持。"
    return f"在 {seq} 后再叫新花 {bid}：通常 12+ HCP，约 4+ 张该花色，用于描述第二套。"


def contextual_responder_rebid_meaning(bid: str, auction_bids: list[str]) -> str | None:
    opening = parse_contract(auction_bids[0] if len(auction_bids) > 0 else "")
    response = parse_contract(auction_bids[1] if len(auction_bids) > 1 else "")
    opener_rebid = parse_contract(auction_bids[2] if len(auction_bids) > 2 else "")
    responder2 = parse_contract(bid)
    if responder2 is None or opening is None or response is None or opener_rebid is None or len(auction_bids) < 3:
        return "第二次应叫：根据前序叫牌选择邀局、进局或继续描述牌型"

    seq = f"{auction_bids[0]}-{auction_bids[1]}-{auction_bids[2]}"
    if opening[1] == "NT":
        response_bid = auction_bids[1]
        opener_rebid_bid = auction_bids[2]
        if response_bid == "2♦" and opener_rebid_bid == "2♥":
            if bid == "2NT":
                return f"在 {seq} 后再叫 2NT：转移完成后邀局，通常约 8-9 HCP。"
            if bid == "3NT":
                return f"在 {seq} 后再叫 3NT：转移完成后直接无将进局。"
            if responder2[1] == "♥":
                return f"在 {seq} 后再叫 {bid}：红心转移完成后继续描述红心长度与牌力。"
        if response_bid == "2♥" and opener_rebid_bid == "2♠":
            if bid == "2NT":
                return f"在 {seq} 后再叫 2NT：转移完成后邀局，通常约 8-9 HCP。"
            if bid == "3NT":
                return f"在 {seq} 后再叫 3NT：转移完成后直接无将进局。"
            if responder2[1] == "♠":
                return f"在 {seq} 后再叫 {bid}：黑桃转移完成后继续描述黑桃长度与牌力。"
        if response_bid == "2♣":
            if bid == "2NT":
                return f"在 {seq} 后再叫 2NT：Stayman 后无将邀局。"
            if bid == "3NT":
                return f"在 {seq} 后再叫 3NT：Stayman 后确认无将进局。"
            if responder2[1] in {"♥", "♠"}:
                return f"在 {seq} 后再叫 {bid}：Stayman 后确认高花配合并推进定约层级。"
        if responder2[1] == "NT":
            return f"在 {seq} 后再叫 {bid}：1NT 体系后续中以无将邀局/进局为主线。"
        return f"在 {seq} 后再叫 {bid}：1NT 开叫后续的结构化再叫，用于确认配合与定约层级。"

    if responder2[1] == "NT":
        if opener_rebid[1] == "NT":
            if responder2[0] == 2:
                return f"在 {seq} 后应叫者再叫 2NT：约 10-12 HCP，邀请进局。"
            if responder2[0] == 3:
                return f"在 {seq} 后应叫者再叫 3NT：约 13+ HCP，确认无将进局。"
        return f"在 {seq} 后应叫者再叫 {bid}：通常显示均型并推进到邀局/进局层级。"

    if responder2[1] == opener_rebid[1]:
        return f"在 {seq} 后应叫者再叫 {bid} 支持开叫者再叫花色：通常 10+ HCP，约 3+ 张支持。"
    if responder2[1] == response[1]:
        return f"在 {seq} 后应叫者重复原应叫花色 {bid}：通常 10+ HCP，约 6+ 张该花色。"
    if responder2[1] == opening[1]:
        return f"在 {seq} 后应叫者回到开叫花色 {bid}：通常表示补充支持并竞争/邀局。"
    return f"在 {seq} 后应叫者再叫新花 {bid}：通常 10+ HCP，约 4+ 张该花色，继续描述牌型。"


def auction_bid_meaning(bid: str, position: int, auction_bids: list[str]) -> str:
    opening_meanings = {
        "1♣": "梅花开叫 - 12+ HCP，3张以上梅花",
        "1♦": "方片开叫 - 12+ HCP，3张以上方片",
        "1♥": "红心开叫 - 12+ HCP，5张以上红心",
        "1♠": "黑桃开叫 - 12+ HCP，5张以上黑桃",
        "1NT": "无将开叫 - 15-17 HCP，均型",
        "2♣": "强 2♣ - 22+ HCP",
        "2♦": "弱 2 - 6-11 HCP，6张方片",
        "2♥": "弱 2 - 6-11 HCP，6张红心",
        "2♠": "弱 2 - 6-11 HCP，6张黑桃",
        "2NT": "2NT 开叫 - 20-21 HCP，均型",
        "3♣": "预防性 - 6-10 HCP，7张梅花",
        "3♦": "预防性 - 6-10 HCP，7张方片",
        "3♥": "预防性 - 6-10 HCP，7张红心",
        "3♠": "预防性 - 6-10 HCP，7张黑桃",
        "3NT": "3NT 开叫 - 25-27 HCP，均型",
    }
    response_meanings = {
        "1♦": "新花应叫 - 6+ HCP，4张以上方片",
        "1♥": "新花应叫 - 6+ HCP，4张以上红心",
        "1♠": "新花应叫 - 6+ HCP，4张以上黑桃",
        "1NT": "1NT 应叫 - 6-9 HCP，均型",
        "2♣": "2/1 应叫 - 11+ HCP，4张梅花",
        "2♦": "2/1 应叫 - 11+ HCP，4张方片",
        "2♥": "2/1 应叫 - 11+ HCP，4张红心",
        "2♠": "2/1 应叫 - 11+ HCP，4张黑桃",
        "2NT": "2NT 应叫 - 11+ HCP，均型（弱二开叫后常作 Ogust 2NT 问叫）",
        "3♣": "支持邀局 - 11-12 HCP，4张梅花支持",
        "3♦": "支持邀局 - 11-12 HCP，4张方片支持",
        "3♥": "支持邀局 - 11-12 HCP，4张红心支持",
        "3♠": "支持邀局 - 11-12 HCP，4张黑桃支持",
        "3NT": "3NT 应叫 - 12+ HCP，均型",
        "4♥": "支持进局 - 13+ HCP，4张红心支持",
        "4♠": "支持进局 - 13+ HCP，4张黑桃支持",
    }
    rebid_meanings = {
        "1NT": "再叫 1NT - 12-14 HCP，均型最低",
        "2♣": "再叫梅花 - 12-14 HCP，3张梅花",
        "2♦": "再叫方片 - 12-14 HCP，3张方片",
        "2♥": "支持高花 - 3-4张支持",
        "2♠": "支持高花 - 3-4张支持",
        "2NT": "再叫 2NT - 18-19 HCP，均型",
        "3♣": "支持邀局 - 15-17 HCP，5张梅花",
        "3♦": "支持邀局 - 15-17 HCP，5张方片",
        "3♥": "支持进局 - 13+ HCP，5张红心支持",
        "3♠": "支持进局 - 13+ HCP，5张黑桃支持",
        "3NT": "再叫 3NT - 16-18 HCP，均型",
        "4♥": "支持进局 - 13+ HCP，5张红心支持",
        "4♠": "支持进局 - 13+ HCP，5张黑桃支持",
        "4NT": "关键张问叫",
        "5♣": "长套进局 - 13+ HCP，6张梅花",
        "5♦": "长套进局 - 13+ HCP，6张方片",
    }
    responder2_meanings = {
        "2NT": "邀局 - 10-12 HCP，邀请无将",
        "3NT": "进局 - 13+ HCP，无将进局",
        "3♣": "支持邀 - 10-12 HCP，4张梅花支持",
        "3♦": "支持邀 - 10-12 HCP，4张方片支持",
        "3♥": "支持进 - 13+ HCP，4张红心支持",
        "3♠": "支持进 - 13+ HCP，4张黑桃支持",
        "4♥": "支持进 - 13+ HCP，4张红心支持",
        "4♠": "支持进 - 13+ HCP，4张黑桃支持",
        "4NT": "关键张问叫",
        "5♣": "长套 - 13+ HCP，6张梅花",
        "5♦": "长套 - 13+ HCP，6张方片",
        "5♥": "竞争 - 高花长套",
        "5♠": "竞争 - 高花长套",
        "5NT": "小满贯邀 - 14+ HCP",
        "6NT": "小满贯 - 15+ HCP",
        "7NT": "大满贯 - 16+ HCP",
    }

    if position == 0:
        return opening_meanings.get(bid, "开叫叫品")
    if position == 1:
        return contextual_response_meaning(bid, auction_bids) or response_meanings.get(bid, "应叫叫品")
    if position == 2:
        return contextual_opener_rebid_meaning(bid, auction_bids) or rebid_meanings.get(bid, "再叫叫品")
    if position == 3:
        return contextual_responder_rebid_meaning(bid, auction_bids) or responder2_meanings.get(bid, "第二次应叫")
    if position % 2 == 0:
        return contextual_opener_rebid_meaning(bid, auction_bids) or rebid_meanings.get(bid, "再叫叫品")
    return contextual_responder_rebid_meaning(bid, auction_bids) or responder2_meanings.get(bid, "应叫叫品")


def click_auction_bid(bid: str, position: int, auction_bids: list[str]) -> None:
    st.session_state.auction_clicked_bid = bid
    st.session_state.auction_clicked_meaning = auction_bid_meaning(bid, position, auction_bids)


def render_auction_with_meaning(question: TrainingQuestion) -> None:
    auction_bids = extract_auction_bids(question.auction)
    st.write("**叫牌过程：**")
    if not auction_bids:
        st.write(f"{question.auction}，轮到你叫牌。")
        return

    cols = st.columns(len(auction_bids) * 2 + 1)
    col_index = 0
    for index, bid in enumerate(auction_bids):
        cols[col_index].button(
            bid,
            key=f"auction_bid_{question.mode}_{question.auction}_{index}_{bid}",
            use_container_width=True,
            on_click=click_auction_bid,
            args=(bid, index, auction_bids),
        )
        col_index += 1
        if index < len(auction_bids) - 1:
            cols[col_index].markdown("<div style='text-align:center;padding-top:0.55rem;'>-</div>", unsafe_allow_html=True)
            col_index += 1
    cols[col_index].markdown("<div style='text-align:center;padding-top:0.55rem;'>- ?</div>", unsafe_allow_html=True)
    st.caption("点击上方任一叫品可查看含义。")
    if st.session_state.auction_clicked_bid:
        st.info(f"{st.session_state.auction_clicked_bid}：{st.session_state.auction_clicked_meaning}")


def render_stats() -> None:
    total = st.session_state.total
    score = st.session_state.score
    # Calculate percentage based on total points (max 2 points per question)
    rate = score / (total * 2) * 100 if total else 0
    st.sidebar.header("训练统计")
    st.sidebar.radio(
        "训练模式",
        ["开叫训练", "应叫训练", "开叫者再叫训练", "应叫者第二次应叫训练"],
        key="mode_choice",
        index=["开叫训练", "应叫训练", "开叫者再叫训练", "应叫者第二次应叫训练"].index(st.session_state.mode),
        on_change=change_mode,
    )
    if st.session_state.mode == "应叫训练":
        response_category = st.session_state.response_opener_category
        response_options = opener_bid_options(response_category)
        st.sidebar.selectbox(
            "开叫类别",
            OPENER_CATEGORY_OPTIONS,
            key="response_opener_category_choice",
            index=OPENER_CATEGORY_OPTIONS.index(response_category),
            on_change=change_response_opener_category,
            help="先选择开叫类型，再选择具体叫品。",
        )
        st.sidebar.selectbox(
            "同伴开叫叫品",
            response_options,
            key="response_opener_choice",
            index=response_options.index(st.session_state.response_opener_bid)
            if st.session_state.response_opener_bid in response_options
            else 0,
            on_change=change_response_opener,
            help="用于按开叫叫品分别练习应叫。",
        )
    if st.session_state.mode == "开叫者再叫训练":
        opener_rebid_category = st.session_state.opener_rebid_opener_category
        opener_rebid_options = opener_bid_options(opener_rebid_category)
        opener_rebid_response_options = response_bid_options_for_opener(st.session_state.opener_rebid_opener_bid)
        st.sidebar.selectbox(
            "开叫叫品",
            OPENER_CATEGORY_OPTIONS,
            key="opener_rebid_opener_category_choice",
            index=OPENER_CATEGORY_OPTIONS.index(opener_rebid_category),
            on_change=change_opener_rebid_opener_category,
            help="先选择开叫类型，再选择具体叫品。",
        )
        st.sidebar.selectbox(
            "具体开叫叫品",
            opener_rebid_options,
            key="opener_rebid_opener_choice",
            index=opener_rebid_options.index(st.session_state.opener_rebid_opener_bid)
            if st.session_state.opener_rebid_opener_bid in opener_rebid_options
            else 0,
            on_change=change_opener_rebid_opener,
            help="用于按开叫叫品分别练习开叫者再叫。",
        )
        st.sidebar.selectbox(
            "同伴应叫叫品",
            opener_rebid_response_options,
            key="opener_rebid_response_choice",
            index=opener_rebid_response_options.index(st.session_state.opener_rebid_response_bid)
            if st.session_state.opener_rebid_response_bid in opener_rebid_response_options
            else 0,
            on_change=change_opener_rebid_response,
            disabled=payload_opener_bid(st.session_state.opener_rebid_opener_bid) is None,
            help="指定前两拍序列，例如选择 1♥ 和 2NT 来生成 1♥-2NT-? 的牌例。",
        )
    if st.session_state.mode == "应叫者第二次应叫训练":
        responder_rebid_category = st.session_state.responder_rebid_opener_category
        responder_rebid_options = opener_bid_options(responder_rebid_category)
        responder_rebid_response_options = response_bid_options_for_opener(st.session_state.responder_rebid_opener_bid)
        responder_rebid_opener_rebid_options = opener_rebid_bid_options_for_response(
            st.session_state.responder_rebid_response_bid
        )
        st.sidebar.selectbox(
            "开叫叫品",
            OPENER_CATEGORY_OPTIONS,
            key="responder_rebid_opener_category_choice",
            index=OPENER_CATEGORY_OPTIONS.index(responder_rebid_category),
            on_change=change_responder_rebid_opener_category,
            help="先选择开叫类型，再选择具体叫品。",
        )
        st.sidebar.selectbox(
            "具体开叫叫品",
            responder_rebid_options,
            key="responder_rebid_opener_choice",
            index=responder_rebid_options.index(st.session_state.responder_rebid_opener_bid)
            if st.session_state.responder_rebid_opener_bid in responder_rebid_options
            else 0,
            on_change=change_responder_rebid_opener,
            help="用于按开叫叫品分别练习应叫者第二次应叫。",
        )
        st.sidebar.selectbox(
            "应叫叫品",
            responder_rebid_response_options,
            key="responder_rebid_response_choice",
            index=responder_rebid_response_options.index(st.session_state.responder_rebid_response_bid)
            if st.session_state.responder_rebid_response_bid in responder_rebid_response_options
            else 0,
            on_change=change_responder_rebid_response,
            disabled=payload_opener_bid(st.session_state.responder_rebid_opener_bid) is None,
            help="指定第二拍应叫。",
        )
        st.sidebar.selectbox(
            "开叫者再叫",
            responder_rebid_opener_rebid_options,
            key="responder_rebid_opener_rebid_choice",
            index=responder_rebid_opener_rebid_options.index(st.session_state.responder_rebid_opener_rebid_bid)
            if st.session_state.responder_rebid_opener_rebid_bid in responder_rebid_opener_rebid_options
            else 0,
            on_change=change_responder_rebid_opener_rebid,
            disabled=payload_response_bid(st.session_state.responder_rebid_response_bid) is None,
            help="指定前三拍序列，例如 1♥-2NT-4♥ 后练习第四拍。",
        )
    st.sidebar.divider()
    with st.sidebar.expander("叫牌规则设置"):
        st.selectbox(
            "1NT 开叫范围",
            ["14-16", "15-17", "16-18"],
            key="setting_one_nt_range",
            on_change=change_rules,
        )
        st.selectbox(
            "一阶开叫最低 HCP",
            [11, 12, 13],
            key="setting_opening_min_hcp",
            on_change=change_rules,
        )
        st.selectbox(
            "强 2♣ 最低 HCP",
            [21, 22, 23],
            key="setting_strong_two_club_min",
            on_change=change_rules,
        )
        st.checkbox("启用弱二开叫", key="setting_weak_two_enabled", on_change=change_rules)
        st.checkbox("二阶弱开叫后启用 Ogust 2NT 问叫", key="setting_august_2nt_enabled", on_change=change_rules)
        st.checkbox("1NT 后启用 Stayman", key="setting_stayman_enabled", on_change=change_rules)
        st.checkbox("1NT 后启用 Jacoby Transfer", key="setting_transfers_enabled", on_change=change_rules)
        st.checkbox("高花后启用 Jacoby 2NT", key="setting_jacoby_2nt_enabled", on_change=change_rules)
        st.checkbox("高花应叫启用 Bergen Raises（4张支持）", key="setting_bergen_raises_enabled", on_change=change_rules)
        st.selectbox(
            "2/1 进局逼叫最低 HCP",
            [11, 12, 13],
            key="setting_two_over_one_min_hcp",
            on_change=change_rules,
        )
        st.selectbox(
            "Bergen 弱支持上限 HCP（4张支持）",
            [8, 9, 10],
            key="setting_responder_bergen_weak_max",
            on_change=change_rules,
        )
        st.selectbox(
            "高花简单加叫上限 HCP（3张支持）",
            [8, 9, 10],
            key="setting_responder_simple_raise_max",
            on_change=change_rules,
        )
        st.selectbox(
            "高花邀局加叫 HCP 范围（3张支持）",
            ["10-12", "11-12"],
            key="setting_responder_limit_raise_range",
            on_change=change_rules,
        )
        st.selectbox(
            "高花开叫后 1NT 应叫 HCP 范围",
            ["5-11", "6-10", "6-11", "7-11", "6-12"],
            key="setting_forcing_nt_hcp_range",
            on_change=change_rules,
        )
        st.checkbox(
            "高花应叫启用 Splinter（游牌加叫）",
            key="setting_splinter_enabled",
            on_change=change_rules,
        )
        st.selectbox(
            "Splinter 最小 HCP",
            [10, 11, 12],
            key="setting_responder_splinter_min_hcp",
            on_change=change_rules,
        )
        st.selectbox(
            "Splinter 最大 HCP",
            [14, 15, 16],
            key="setting_responder_splinter_max_hcp",
            on_change=change_rules,
        )
        st.checkbox(
            "竞叫后启用否定性加倍（Negative Double）",
            key="setting_negative_double_enabled",
            on_change=change_rules,
        )
        st.selectbox(
            "否定性加倍最低 HCP",
            [6, 7, 8],
            key="setting_negative_double_min_hcp",
            on_change=change_rules,
        )
        st.radio(
            "高花开叫后 1NT 应叫",
            ["半逼叫", "逼叫一轮"],
            key="setting_forcing_nt_label",
            on_change=change_rules,
        )
        st.radio(
            "计分倾向",
            ["IMP", "MP"],
            key="setting_scoring_mode",
            on_change=change_rules,
            help="IMP 倾向更积极争取成局，MP 倾向更稳健。",
        )
        st.checkbox(
            "按局况调整成局阈值（有局/无局）",
            key="setting_respect_vulnerability",
            on_change=change_rules,
        )
        st.selectbox(
            "薄局/薄满贯激进度",
            [-1, 0, 1],
            key="setting_game_aggressiveness",
            on_change=change_rules,
            help="-1 保守，0 标准，1 激进。",
        )
        st.button("恢复默认规则", on_click=reset_rules)
    st.sidebar.metric("已答题", total)
    st.sidebar.metric("总分", score)
    st.sidebar.metric("得分率", f"{rate:.1f}%")
    if st.sidebar.button("重置统计"):
        st.session_state.total = 0
        st.session_state.score = 0
        st.session_state.submitted = False


def practical_profile_text(settings: RuleSettings) -> str:
    vuln_text = "考虑局况" if settings.respect_vulnerability else "不按局况调整"
    agg = settings.game_aggressiveness
    agg_text = f"激进度 {agg:+d}"
    return f"{settings.scoring_mode} | {vuln_text} | {agg_text}"


def main() -> None:
    init_state()
    ensure_current_question()
    render_stats()

    st.title("♠ 桥牌 2/1 Game Force 叫牌训练")
    st.write("选择开叫、应叫、开叫者再叫或应叫者第二次应叫训练，根据手牌和叫牌过程选择最合适的叫品。")
    st.caption(f"实战参数：{practical_profile_text(current_rule_settings())}")
    question: TrainingQuestion = st.session_state.question

    with st.container(border=True):
        st.write(f"**训练模式：** {question.mode}")
        st.write(f"**局况：** {question.vulnerability}")
        st.write(f"**位置：** {question.position}")
        if question.mode == "应叫训练" and question.opener_bid is not None:
            st.write(f"**同伴开叫：** 北家 {question.opener_bid}")
        if question.mode == "开叫者再叫训练" and question.opener_bid is not None:
            st.write(f"**你的开叫：** {question.opener_bid}")
        if question.mode == "应叫者第二次应叫训练" and question.opener_bid is not None:
            st.write(f"**开叫者开叫：** 北家 {question.opener_bid}")
        if question.response_bid is not None:
            label = "同伴应叫" if question.mode != "应叫者第二次应叫训练" else "你的第一次应叫"
            st.write(f"**{label}：** 南家 {question.response_bid}" if question.mode == "应叫者第二次应叫训练" else f"**{label}：** 北家 {question.response_bid}")
        if question.opener_rebid_bid is not None:
            st.write(f"**开叫者再叫：** 北家 {question.opener_rebid_bid}")
        render_auction_with_meaning(question)

    render_hand(question)
    render_evaluation(question)

    render_bid_picker(question)

    col1, col2 = st.columns(2)
    with col1:
        st.button(
            "提交答案",
            type="primary",
            on_click=submit_answer,
            disabled=st.session_state.submitted
            or st.session_state.selected_bid not in getattr(question, "legal_choices", question.choices),
        )
    with col2:
        st.button("下一题", on_click=next_question)

    if st.session_state.submitted:
        render_feedback(question)

    with st.expander("当前训练规则说明"):
        st.markdown(
            """
            **开叫训练**

            - 22+ HCP：2♣ 强开叫
            - 20-21 HCP 且均型：2NT
            - 15-17 HCP 且均型：1NT
            - 12+ HCP 且 5 张以上高花：1♥ / 1♠
            - 12+ HCP 无 5 张高花：较长低花，3-3 开 1♣，4-4 开 1♦
            - 6-10 HCP 且 6 张以上 ♦/♥/♠：弱二开叫
            - 其他：Pass

            **应叫训练**

            - 对 1NT：Stayman、Jacoby Transfer、2NT 邀局、3NT 进局
            - 对 1♥/1♠：简单加叫、限制性加叫、Jacoby 2NT、2/1 进局逼叫、1NT 半逼叫
            - 对 1♣/1♦：优先叫 4 张高花；无高花时按牌力选择 1NT/2NT/3NT 或低花加叫

            **开叫者再叫训练**

                        - 对一阶花色开叫序列：同伴叫出高花后，优先判断是否有 4 张支持并按牌力加叫
                        - 对一阶花色开叫序列：均型低限可再叫 1NT，18-19 均型可再叫 2NT
                        - 1NT 开叫后的专属续叫：
                            - 1NT-2♣：按 Stayman 应答 2♦/2♥/2♠
                            - 1NT-2♦：接受红心转移，叫 2♥
                            - 1NT-2♥：接受黑桃转移，叫 2♠
                            - 1NT-2NT：按牌力接受邀局叫 3NT，否则 Pass
                            - 1NT-3NT：通常 Pass 止叫
                        - 一阶花色序列下有 6 张以上开叫套时可重复开叫花色；无支持、无将或长套时尝试再叫第二套

            **应叫者第二次应叫训练**

                        - 在 1m/1M 开叫序列下，训练应叫者面对开叫者再叫后的第二次决策
                        - 在 1NT 开叫后续序列下，按 Stayman/转移后的结果进行邀局或进局判断
                        - 对无将再叫：默认 8-9 HCP 倾向邀局，10+ HCP 倾向进局，低于邀局门槛可 Pass
                        - 有明确高花配合时继续支持；有 6 张原应叫套时可重复应叫套
                        - 无明显配合时按简化规则止叫或转入 3NT
            """
        )


if __name__ == "__main__":
    main()
