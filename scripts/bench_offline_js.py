"""Benchmark offline JS question generation via QuickJS."""

from __future__ import annotations

import json
import time
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
            throw new Error('Cannot find module: ' + request + ' from ' + fromId);
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
        "utils/bridge_trainer/bidding.js": (BT / "bidding.js").read_text(encoding="utf-8"),
        "utils/bridge_trainer/training.js": (BT / "training.js").read_text(encoding="utf-8"),
        "utils/api.js": (UTILS / "api.js").read_text(encoding="utf-8"),
    }
    for module_id, source in modules.items():
        t0 = time.perf_counter()
        ctx.eval(wrap_module(module_id, source))
        print(f"eval {module_id}: {(time.perf_counter() - t0) * 1000:.0f}ms ({len(source)} bytes)")

    t0 = time.perf_counter()
    ctx.eval('var api = requireRoot("./api");')
    print(f"require api: {(time.perf_counter() - t0) * 1000:.0f}ms")

    cases = [
        ("opening", '{"mode":"opening","seed":42}'),
        ("response", '{"mode":"response","seed":42}'),
        ("response_1nt", '{"mode":"response","seed":42,"opener_bid":"1NT"}'),
        ("response_5c", '{"mode":"response","seed":7,"opener_bid":"5\\u2663"}'),
        ("opener_rebid", '{"mode":"opener_rebid","seed":42,"opener_bid":"1NT","response_bid":"2\\u2663"}'),
        (
            "opener_rebid_rare",
            '{"mode":"opener_rebid","seed":1,"opener_bid":"1\\u2665","response_bid":"2NT"}',
        ),
        (
            "responder_rebid",
            '{"mode":"responder_rebid","seed":42,"opener_bid":"1NT","response_bid":"2\\u2663","opener_rebid_bid":"2\\u2666"}',
        ),
        (
            "responder_rebid_directed",
            '{"mode":"responder_rebid","seed":9,"opener_bid":"1NT","response_bid":"2\\u2663","opener_rebid_bid":"2\\u2666"}',
        ),
    ]
    for name, payload in cases:
        t0 = time.perf_counter()
        ctx.eval(f"api.createQuestionLocal({payload})")
        print(f"{name}: {(time.perf_counter() - t0) * 1000:.0f}ms")

    # Force full dealTargeted budget miss by impossible constraint via direct call.
    t0 = time.perf_counter()
    ctx.eval(
        """
        var training = requireRoot("./bridge_trainer/training");
        training.dealTargeted(
          function() { return false; },
          function() { return true; },
          1,
          3000,
          500
        );
        """
    )
    print(f"dealTargeted full miss 3000x500: {(time.perf_counter() - t0) * 1000:.0f}ms")


if __name__ == "__main__":
    main()
