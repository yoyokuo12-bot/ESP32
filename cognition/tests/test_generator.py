"""L3 生成器測試。可用 pytest 或直接 `python cognition/tests/test_generator.py` 執行。"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from cognition.generator import generate_diary, postprocess, synthetic_packet  # noqa: E402
from cognition.llm_client import StubLLMClient  # noqa: E402
from middleware.state import ALL_STATES  # noqa: E402


def test_stub_nonempty_and_within_limit():
    client = StubLLMClient(seed=1)
    for st in ALL_STATES:
        pkt = synthetic_packet(st)
        d = generate_diary(pkt, client=client, max_chars=120)
        assert d["state"] == st
        assert d["node"] == pkt["node"]
        assert d["ts"] == pkt["ts"]
        assert 0 < len(d["diary"]) <= 120, f"{st}: 長度 {len(d['diary'])}"


def test_stub_fills_real_stats():
    # 乾旱模板含濕度，應把 15% 填進去
    client = StubLLMClient(seed=0)
    pkt = synthetic_packet("CRITICAL_DROUGHT")  # moisture_pct=15
    d = generate_diary(pkt, client=client)
    assert "15%" in d["diary"]


def test_postprocess_strips_banned():
    out = postprocess("我是一個 AI 語言模型，但今天好渴。", 120)
    assert "語言模型" not in out
    assert "我是一個 AI" not in out


def test_postprocess_truncates():
    out = postprocess("渴。" * 200, 120)
    assert len(out) <= 120


class _BannedClient:
    def generate(self, packet, system=None, few_shot=None):
        return "作為一個 AI 語言模型，我覺得今天有點熱。"


def test_generate_diary_cleans_client_output():
    pkt = synthetic_packet("HEAT_STRESS")
    d = generate_diary(pkt, client=_BannedClient(), max_chars=120)
    assert "語言模型" not in d["diary"]
    assert "作為一個 AI" not in d["diary"]
    assert len(d["diary"]) > 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print("PASS", fn.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL", fn.__name__, repr(e))
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
