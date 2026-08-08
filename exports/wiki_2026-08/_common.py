# raw 소스 로더 + 인용 대조용 정규화. `_ingest.py` 와 `_verify.py` 가 같은 것을 봐야 한다.
import json
import re
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
SOURCES = DIR / "sources"
BOTS = DIR / "bots"

_DIGIT_KO = re.compile(r"(\d)\s+(?=[가-힣])")
_WS = re.compile(r"\s+")


def squash(s: str) -> str:
    """대조 전용 정규화 — NFC + 숫자·한글 사이 공백 제거 + 전체 공백 제거.

    `golden_2026-08/_draft.py:88-94` 와 같은 함수다. pdftotext 가 줄바꿈 자리에 공백을
    끼워 넣어("탕 감봉") 공백을 남기면 멀쩡한 인용이 거짓 불일치로 떨어진다.
    """
    return _WS.sub("", _DIGIT_KO.sub(r"\1", unicodedata.normalize("NFC", s)))


def read_unit(path: Path) -> dict:
    """`sources/<sha8>/NNN.md` 를 {src_id, doc, locator, sha8, text} 로 읽는다.

    text 는 프론트매터를 뺀 본문이다 — 인용 대조 대상도 이 본문뿐이다.
    """
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n+(.*)", raw, re.S)
    if not m:
        raise ValueError(f"프론트매터 없음: {path}")
    head = dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.M))
    return {"src_id": head["src_id"], "doc": head["doc"], "sha8": head["sha8"],
            "locator": head["locator"], "text": m.group(2).rstrip(), "path": path}


def load_sources(bot_id: int) -> dict[str, dict]:
    """봇의 manifest 가 가리키는 소스를 전부 읽어 src_id → unit 으로 돌려준다."""
    manifest = json.loads((BOTS / str(bot_id) / "manifest.json").read_text(encoding="utf-8"))
    units: dict[str, dict] = {}
    for s in manifest["sources"]:
        meta = json.loads((SOURCES / s["sha8"] / "meta.json").read_text(encoding="utf-8"))
        for u in meta["units"]:
            unit = read_unit(SOURCES / s["sha8"] / u["file"])
            units[unit["src_id"]] = unit
    return units


def sort_key(src_id: str) -> tuple[int, int]:
    """reg 를 먼저, 그 안에서 조문 순서로. 규정집이 대사전보다 우선이라 먼저 쌓는다."""
    prefix, num = src_id.split("-")
    return (0 if prefix == "reg" else 1, int(num))
