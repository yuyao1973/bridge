from __future__ import annotations

import os
import random
from datetime import datetime
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from bridge_trainer.bidding import RuleSettings
from bridge_trainer.cards import Card, format_hand_lines
from bridge_trainer.training import (
    TrainingQuestion,
    generate_opener_rebid_question,
    generate_opening_question,
    generate_responder_rebid_question,
    generate_response_question,
)


DEFAULT_SETTINGS = {
    "opening_min_hcp": 12,
    "one_nt_min": 15,
    "one_nt_max": 17,
    "strong_two_club_min": 22,
    "weak_two_enabled": True,
    "stayman_enabled": True,
    "transfers_enabled": True,
    "jacoby_2nt_enabled": True,
    "bergen_raises_enabled": True,
    "two_over_one_min_hcp": 12,
    "forcing_nt_min_hcp": 6,
    "forcing_nt_max_hcp": 11,
    "responder_simple_raise_max": 9,
    "responder_limit_raise_min": 10,
    "responder_limit_raise_max": 12,
    "responder_bergen_weak_max": 9,
    "splinter_enabled": True,
    "responder_splinter_min_hcp": 11,
    "responder_splinter_max_hcp": 15,
    "forcing_nt_label": "半逼叫",
    "scoring_mode": "IMP",
    "respect_vulnerability": True,
    "game_aggressiveness": 0,
    "august_2nt_enabled": True,
}

APP_VERSION = os.getenv("BRIDGE_TRAINER_VERSION", "v0.1.0")


def get_build_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "app_version": APP_VERSION, "build_time": get_build_time()})


async def create_question(request: Request) -> JSONResponse:
    payload = await request.json()
    mode = payload.get("mode", "opening")
    opener_bid = payload.get("opener_bid")
    opener_category = payload.get("opener_category")
    seed = payload.get("seed") or random.randint(1, 1_000_000_000)
    settings = settings_from_payload(payload.get("settings") or {})

    if mode == "response":
        question = generate_response_question(seed, opener_bid, settings, opener_category)
    elif mode == "opener_rebid":
        question = generate_opener_rebid_question(seed, settings, opener_bid, opener_category)
    elif mode == "responder_rebid":
        question = generate_responder_rebid_question(seed, settings, opener_bid, opener_category)
    else:
        question = generate_opening_question(seed, settings)
    return JSONResponse(question_to_payload(question, seed))


async def check_answer(request: Request) -> JSONResponse:
    payload = await request.json()
    selected_bid = payload.get("selected_bid")
    recommended_bid = payload.get("recommended_bid")
    acceptable_bids = payload.get("acceptable_bids") or [recommended_bid]
    is_primary = selected_bid == recommended_bid
    is_acceptable = selected_bid in acceptable_bids
    grade = "primary" if is_primary else ("acceptable" if is_acceptable else "incorrect")
    return JSONResponse(
        {
            "correct": is_acceptable,
            "grade": grade,
            "recommended_bid": recommended_bid,
            "acceptable_bids": acceptable_bids,
            "explanation": payload.get("explanation", ""),
            "rule_name": payload.get("rule_name", ""),
        }
    )


def settings_from_payload(payload: dict[str, Any]) -> RuleSettings:
    values = {**DEFAULT_SETTINGS, **payload}
    rule_kwargs = {
        "opening_min_hcp": int(values["opening_min_hcp"]),
        "one_nt_min": int(values["one_nt_min"]),
        "one_nt_max": int(values["one_nt_max"]),
        "strong_two_club_min": int(values["strong_two_club_min"]),
        "weak_two_enabled": bool(values["weak_two_enabled"]),
        "stayman_enabled": bool(values["stayman_enabled"]),
        "transfers_enabled": bool(values["transfers_enabled"]),
        "jacoby_2nt_enabled": bool(values["jacoby_2nt_enabled"]),
        "bergen_raises_enabled": bool(values["bergen_raises_enabled"]),
        "two_over_one_min_hcp": int(values["two_over_one_min_hcp"]),
        "forcing_nt_min_hcp": int(values["forcing_nt_min_hcp"]),
        "forcing_nt_max_hcp": int(values["forcing_nt_max_hcp"]),
        "responder_simple_raise_max": int(values["responder_simple_raise_max"]),
        "responder_limit_raise_min": int(values["responder_limit_raise_min"]),
        "responder_limit_raise_max": int(values["responder_limit_raise_max"]),
        "responder_bergen_weak_max": int(values["responder_bergen_weak_max"]),
        "splinter_enabled": bool(values.get("splinter_enabled", True)),
        "responder_splinter_min_hcp": int(values.get("responder_splinter_min_hcp", 11)),
        "responder_splinter_max_hcp": int(values.get("responder_splinter_max_hcp", 15)),
        "forcing_nt_label": str(values["forcing_nt_label"]),
        "scoring_mode": str(values["scoring_mode"]),
        "respect_vulnerability": bool(values["respect_vulnerability"]),
        "game_aggressiveness": max(-1, min(1, int(values["game_aggressiveness"]))),
        "august_2nt_enabled": bool(values["august_2nt_enabled"]),
    }
    supported = getattr(RuleSettings, "__dataclass_fields__", {})
    filtered_kwargs = {key: value for key, value in rule_kwargs.items() if key in supported}
    return RuleSettings(**filtered_kwargs)


def question_to_payload(question: TrainingQuestion, seed: int) -> dict[str, object]:
    recommendation = question.recommendation
    return {
        "app_version": APP_VERSION,
        "build_time": get_build_time(),
        "seed": seed,
        "mode": question.mode,
        "position": question.position,
        "vulnerability": question.vulnerability,
        "auction": question.auction,
        "opener_bid": question.opener_bid,
        "response_bid": question.response_bid,
        "opener_rebid_bid": question.opener_rebid_bid,
        "hand": [card_to_payload(card) for card in question.hand],
        "hand_lines": format_hand_lines(question.hand),
        "evaluation": {
            "hcp": question.evaluation.hcp,
            "shape": question.evaluation.shape,
            "balanced": question.evaluation.balanced,
            "lengths": question.evaluation.lengths,
        },
        "choices": question.choices,
        "legal_choices": question.legal_choices,
        "acceptable_bids": question.acceptable_bids,
        "recommendation": {
            "bid": recommendation.bid,
            "explanation": recommendation.explanation,
            "rule_name": recommendation.rule_name,
        },
    }


def card_to_payload(card: Card) -> dict[str, str]:
    return {"suit": card.suit, "rank": card.rank, "label": card.label()}


routes = [
    Route("/health", health, methods=["GET"]),
    Route("/api/question", create_question, methods=["POST"]),
    Route("/api/answer", check_answer, methods=["POST"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(debug=False, routes=routes, middleware=middleware)
