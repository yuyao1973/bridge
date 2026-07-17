"""Smoke-test WeChat offline bridge_trainer JS modules via QuickJS."""

from __future__ import annotations

import json
from pathlib import Path

from quickjs import Context

ROOT = Path(__file__).resolve().parents[1]
BT = ROOT / "wechat-miniprogram" / "utils" / "bridge_trainer"
UTILS = ROOT / "wechat-miniprogram" / "utils"


def wrap_module(module_id: str, source: str) -> str:
    return (
        f"register({json.dumps(module_id)}, function(require, module, exports) {{\n"
        f"{source}\n"
        f"}});\n"
    )


def main() -> None:
    ctx = Context()
    ctx.eval(
        """
        var __modules = {};
        var __moduleCache = {};
        function dirname(id) {
          var i = id.lastIndexOf('/');
          return i < 0 ? '.' : id.slice(0, i);
        }
        function normalize(path) {
          var parts = path.split('/');
          var out = [];
          for (var i = 0; i < parts.length; i++) {
            var p = parts[i];
            if (!p || p === '.') continue;
            if (p === '..') { out.pop(); continue; }
            out.push(p);
          }
          return out.join('/');
        }
        function resolve(fromId, request) {
          var abs;
          if (request.charAt(0) === '.') {
            abs = normalize(dirname(fromId) + '/' + request);
          } else {
            abs = request;
          }
          if (__modules[abs]) return abs;
          if (__modules[abs + '.js']) return abs + '.js';
          return abs;
        }
        function requireFrom(fromId, request) {
          var id = resolve(fromId, request);
          if (__moduleCache[id]) return __moduleCache[id].exports;
          if (!__modules[id]) {
            throw new Error('Cannot find module: ' + request + ' from ' + fromId + ' resolved=' + id);
          }
          var module = { exports: {} };
          __moduleCache[id] = module;
          __modules[id](function(req) { return requireFrom(id, req); }, module, module.exports);
          return module.exports;
        }
        function register(id, fn) { __modules[id] = fn; }
        function requireRoot(request) { return requireFrom('utils/api.js', request); }
        """
    )

    modules = {
        "utils/bridge_trainer/random.js": (BT / "random.js").read_text(encoding="utf-8"),
        "utils/bridge_trainer/cards.js": (BT / "cards.js").read_text(encoding="utf-8"),
        "utils/bridge_trainer/evaluator.js": (BT / "evaluator.js").read_text(encoding="utf-8"),
        "utils/bridge_trainer/opening_lite.js": (BT / "opening_lite.js").read_text(encoding="utf-8"),
        "utils/bridge_trainer/bidding.js": (BT / "bidding.js").read_text(encoding="utf-8"),
        "utils/bridge_trainer/training.js": (BT / "training.js").read_text(encoding="utf-8"),
        "utils/api.js": (UTILS / "api.js").read_text(encoding="utf-8"),
    }
    for module_id, source in modules.items():
        ctx.eval(wrap_module(module_id, source))

    result = ctx.eval(
        """
        (function() {
          var PythonRandom = requireRoot('./bridge_trainer/random.js').PythonRandom;
          var r = new PythonRandom(42);
          var r1 = r.random();
          var r2 = new PythonRandom(42);
          var deck = [];
          for (var i = 0; i < 52; i++) deck.push(i);
          r2.shuffle(deck);
          var rr = [];
          var r3 = new PythonRandom(42);
          for (var i = 10; i > 0; i--) rr.push(r3.randrange(i + 1));
          return JSON.stringify({ r1: r1, shuffle: deck.slice(0, 10), randrange: rr });
        })()
        """
    )
    data = json.loads(result)
    assert abs(data["r1"] - 0.6394267984578837) < 1e-12, data["r1"]
    assert data["shuffle"] == [9, 23, 25, 3, 21, 38, 16, 39, 19, 11], data["shuffle"]
    assert data["randrange"] == [10, 1, 0, 4, 1, 1, 1, 0, 2, 0], data["randrange"]
    print("random: OK")

    result = ctx.eval(
        """
        (function() {
          var api = requireRoot('./api.js');
          var q = api.createQuestionLocal({ mode: 'opening', seed: 42, settings: {} });
          return JSON.stringify({
            mode: q.mode,
            hcp: q.evaluation.hcp,
            bid: q.recommendation.bid,
            hand_lines: q.hand_lines,
            choices: q.choices.length,
            version: q.app_version
          });
        })()
        """
    )
    opening = json.loads(result)
    assert opening["mode"] == "开叫训练", opening
    assert opening["choices"] == 21, opening
    assert opening["bid"], opening
    assert len(opening["hand_lines"]) == 4, opening
    print("opening question:", opening["bid"], "HCP", opening["hcp"])

    result = ctx.eval(
        """
        (function() {
          var api = requireRoot('./api.js');
          var q = api.createQuestionLocal({ mode: 'opening', seed: 7, settings: {} });
          var ok = api.checkAnswerLocal({
            selected_bid: q.recommendation.bid,
            recommended_bid: q.recommendation.bid,
            acceptable_bids: q.acceptable_bids
          });
          var wrongRecommended = q.recommendation.bid === 'Pass' ? '1NT' : q.recommendation.bid;
          var bad = api.checkAnswerLocal({
            selected_bid: 'Pass',
            recommended_bid: wrongRecommended,
            acceptable_bids: wrongRecommended === 'Pass' ? ['Pass'] : [wrongRecommended]
          });
          if (wrongRecommended === 'Pass') {
            bad = api.checkAnswerLocal({
              selected_bid: '1NT',
              recommended_bid: 'Pass',
              acceptable_bids: ['Pass']
            });
          }
          return JSON.stringify({ ok: ok, bad: bad, bid: q.recommendation.bid });
        })()
        """
    )
    answer = json.loads(result)
    assert answer["ok"]["correct"] is True
    assert answer["ok"]["grade"] == "primary"
    assert answer["bad"]["correct"] is False
    print("answer check: OK")

    result = ctx.eval(
        """
        (function() {
          var api = requireRoot('./api.js');
          var q = api.createQuestionLocal({
            mode: 'response',
            seed: 99,
            opener_bid: '1NT',
            opener_category: '一阶定约',
            settings: {}
          });
          return JSON.stringify({
            mode: q.mode,
            opener: q.opener_bid,
            auction: q.auction,
            bid: q.recommendation.bid,
            legal: q.legal_choices.length
          });
        })()
        """
    )
    response = json.loads(result)
    assert response["opener"] == "1NT", response
    assert response["auction"].startswith("1NT"), response
    print(
        "response question:",
        response["auction"].encode("unicode_escape").decode(),
        "->",
        response["bid"].encode("unicode_escape").decode(),
    )

    result = ctx.eval(
        """
        (function() {
          var api = requireRoot('./api.js');
          var q = api.createQuestionLocal({
            mode: 'opener_rebid',
            seed: 1,
            opener_bid: '1NT',
            opener_category: '一阶定约',
            response_bid: '2♣',
            settings: {}
          });
          return JSON.stringify({
            auction: q.auction,
            bid: q.recommendation.bid,
            opener: q.opener_bid,
            response: q.response_bid
          });
        })()
        """
    )
    rebid = json.loads(result)
    assert rebid["opener"] == "1NT", rebid
    assert rebid["response"] == "2♣", rebid
    print(
        "opener rebid:",
        rebid["auction"].encode("unicode_escape").decode(),
        "->",
        rebid["bid"].encode("unicode_escape").decode(),
    )

    # Compare opening bid with Python for same seed
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from bridge_trainer.training import generate_opening_question

    py_q = generate_opening_question(42)
    assert opening["bid"] == py_q.recommendation.bid, (opening["bid"], py_q.recommendation.bid)
    assert opening["hcp"] == py_q.evaluation.hcp, (opening["hcp"], py_q.evaluation.hcp)
    print("python parity (seed=42): OK")

    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
