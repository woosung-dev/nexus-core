"""E2E 측정 하네스 — `chat_service.process_chat_request` 를 그대로 태운다.

## 왜 `_run.py` 를 안 쓰나

`_run.py` 는 `answer_with_wiki` 를 직접 부른다. 그래서 **여덟 단계 중 생성 하나만** 잰다.
FAQ 분기·ops_facts 주입·strict 게이트·표기 제거·「답변 못 함」 치환·용어 후처리·기록이
전부 빠진 채였다. 880호출·1,320호출로 잰 것은 「봇」이 아니라 「봇의 한 조각」이다.

**「유보율」은 strict(4단)와 unanswered(6단)가 만드는 값이다.** 생성만 재면 못 잰다.

## 정책은 legacy 로 한 번만 돌린다

strict 게이트는 **생성 뒤 판정**이라 legacy 와 strict 는 같은 생성 결과에서 갈린다.
그래서 legacy 로 한 번 돌리고 `_gate.py` 가 trace 로 strict 판정을 재현한다.
호출이 절반이고, 같은 답변에서 갈리니 게이트 효과만 순수하게 남는다.

## 라이브 금지

이 스크립트는 세션·메시지를 **쓴다**. DSN 에 neon 이 보이면 즉시 중단한다.

## ⚠⚠ `--context-mode wiki` 는 trace 와 게이트가 어긋난다 (2026-08-18 실측)

`wiki` 모드는 프롬프트에 **위키 페이지 본문만** 넣고 원문(`units`)은 안 넣는다. 그런데
`chat_service.py:379` 가 trace 용으로 `_select_units(retrieved, "raw_budget")` 를 **따로**
호출하므로, `trace.unit_refs` 에는 **프롬프트에 들어가지도 않은 원문 4건**이 적힌다.

    프롬프트: 위키 3쪽 (원문 0건)
    trace   : unit_refs 4건  ← 실제로 안 들어간 것

그래서 `wiki` 모드에서는 다음이 **전부 못 믿을 값**이다.

    strict 게이트(`evidence_ok`)  주입 안 한 units 로 판정 → 사실상 항상 차단
    `_kpi.py:replay()` 재현        같은 이유로 무의미
    `_triage.py` 의 「검색못함」    unit_refs 를 근거로 삼는다

**wiki 모드는 「답을 받았나 / 봇이 거절했나」만 보고, 게이트 지표는 버려라.**
고치려면 `chat_service` 가 context_mode 를 알아야 하는데 그건 프로덕션 변경이다.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent
BACKEND = DIR.parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

LOCAL_DEFAULT = "postgresql+asyncpg://nexus_user:nexus_pass@localhost:5432/nexus_core"


def _key(item: dict) -> object:
    """문항 식별자. **`gid` 만 쓰면 안 된다** — C01~C10 열 문항이 전부 `gid=null` 이라
    resume 키가 `(None, rep)` 하나로 뭉개져 C 문항 10개 중 9개가 통째로 건너뛰어진다.
    `_run.py:210` 이 이미 `cid or gid` 로 하고 있다. 같게 맞춘다."""
    return item.get("cid") or item.get("gid")


async def main(bot_id: int, tag: str, limit: int, reps: int, throttle: float, mode: str,
               only_cid: str, policy: str, questions: str, no_backfill: bool,
               context_mode: str) -> None:
    dsn = os.environ.get("DATABASE_URL", LOCAL_DEFAULT)
    if "neon.tech" in dsn:
        sys.exit("⛔ 라이브 DSN 이다. 이 하네스는 세션·메시지를 쓴다. 중단한다.")

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    # `app.models` 패키지만 import 하면 부족하다. `chat_sessions.user_id` 의 FK 가
    # `users` 테이블을 못 찾아 flush 에서 죽는다. 참조되는 모델을 직접 끌어와야 한다.
    from app.models.bot import Bot
    from app.models.chat import ChatSession, Message
    from app.models.user import User  # noqa: F401  — FK 해석용
    from app.schemas.chat import ChatCompletionRequest
    from app.services.chat_service import ChatService

    # **호출 수가 문항 수와 다르다.** 답변 생성 1회 뒤에 배경 태스크가 더 나간다 —
    # `_fill_evidence` 는 **인용 청크마다 LLM 1회**다(`rag/evidence.py:107`). 실측 평균
    # 인용 4.65개라 턴당 5.65회가 된다. replay 600건이 3,400회가 되어 무료 한도(모델당
    # 하루 500회)를 첫날에 넘긴다.
    #
    # 백필 산출물은 `messages.citations` 의 표시용 근거 구절이고, 우리 판정은 전부
    # `trace`(retrieval.unit_refs · strict.cited)로 한다. 결손 수집에는 안 쓰인다.
    # 그래서 replay 처럼 호출이 큰 측정에서만 끈다. **본 답변 경로는 그대로다.**
    if no_backfill:
        import app.services.chat_service as _cs

        _cs._schedule_evidence_fill = lambda **kw: None
        _cs._schedule_citation_backfill = lambda **kw: None
        print("⚠ 배경 인용 백필·근거 구절 추출을 껐다. 턴당 호출 1회.")

    # ── L2(근거 구성)를 측정에서만 덮어쓴다 ──────────────────────────────
    #
    # `chat_service.py:370` 이 `context_mode="raw_budget"` 을 **하드코딩**한다. `bots` 테이블에
    # `context_mode` 컬럼이 없어서 봇 설정으로는 못 바꾼다. 그런데 이 축이 팔 B(raw)·C(wiki)를
    # 가르는 전부라, 안 열면 「LLM 위키 모드가 나은가」를 영영 못 잰다.
    #
    # `chat_service` 가 **함수 안에서** import 하므로(`:361`) 모듈 속성을 갈아끼우면 먹는다.
    # **프로덕션 코드는 한 글자도 안 건드린다.**
    #
    #   raw         상위 페이지가 인용하는 원문 전부 (최대 24건)
    #   raw_budget  RRF 유닛 순위 상위, 예산 안에서만 (≤8건·3,000자·바닥 4건) ← 라이브
    #   wiki        위키 페이지 본문으로 답한다. 원문은 안 넣는다 (카파시 원안)
    if context_mode:
        import app.services.wiki.service as _ws

        _orig_awk = _ws.answer_with_wiki

        async def _awk(*a, **kw):
            kw["context_mode"] = context_mode
            return await _orig_awk(*a, **kw)

        _ws.answer_with_wiki = _awk
        print(f"⚠ context_mode 를 '{context_mode}' 로 덮는다(측정 전용, DB·코드 무변경).")
        if context_mode == "wiki":
            print("⚠⚠ wiki 모드는 trace·게이트가 어긋난다 — 아래 주의를 읽어라.")

    # L5(스토어)는 환경변수로 바꾼다 — `FILE_SEARCH_STORE_NAME=... ` 를 앞에 붙여 실행한다.
    # 코드가 `settings.FILE_SEARCH_STORE_NAME`(기본 `nexus-core-knowledge-base`)을 보고,
    # **봇별이 아니라 전역 하나**다. 자료를 맞춘 공정 비교는 `nexus-fs-measure-0818`(2건).
    if os.environ.get("FILE_SEARCH_STORE_NAME"):
        print(f"⚠ 스토어 = {os.environ['FILE_SEARCH_STORE_NAME']}")

    # 기본은 45/55문항 벤치마크. replay 처럼 다른 입력을 태울 때만 `--questions` 를 준다.
    # 형식은 같다: {"items":[{"q": "...", "cid": "R0001", ...}]}
    # ⚠ `cid` 를 반드시 채워라 — resume 키가 `(cid or gid, rep)` 라서 비면 전부 뭉개진다.
    qpath = Path(questions) if questions else (DIR / "questions.json")
    if not qpath.exists():
        sys.exit(f"문항 파일 없음: {qpath}")
    items = json.loads(qpath.read_text(encoding="utf-8"))["items"]
    if questions:
        blank = sum(1 for it in items if not (it.get("cid") or it.get("gid")))
        if blank:
            sys.exit(f"⛔ 식별자(cid/gid) 없는 문항 {blank}건. resume 이 뭉개진다.")
        print(f"문항 파일: {qpath} · {len(items)}건")
    if only_cid:
        wanted = {c.strip() for c in only_cid.split(",") if c.strip()}
        items = [it for it in items if it.get("cid") in wanted]
        missing = wanted - {it.get("cid") for it in items}
        if missing:
            sys.exit(f"cid 없음: {sorted(missing)}")
    if limit:
        items = items[:limit]
    if not items:
        sys.exit("돌릴 문항이 없다")

    engine = create_async_engine(dsn)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    out = DIR / f"_e2e_{tag}.json"
    results: list[dict] = []
    done: set[tuple[object, int]] = set()
    if out.exists():  # 태그 재사용 = resume. 조건을 바꿨으면 반드시 새 태그를 써라.
        prev = json.loads(out.read_text(encoding="utf-8"))
        results = [r for r in prev.get("results", []) if not r.get("error")]
        # ⚠ 2026-08-14 이전 산출물에는 `cid` 키가 아예 없다. 그걸로 resume 하면 C 문항이
        # 다시 `(None, rep)` 로 뭉개진다. 옛 파일이면 이어가지 말고 새 태그를 요구한다.
        if results and any("cid" not in r for r in results):
            sys.exit(f"⛔ {out.name} 은 cid 가 없는 옛 산출물이다. resume 하면 C 문항이 "
                     f"뭉개진다. 새 태그를 써라.")
        done = {(r.get("cid") or r.get("gid"), r["rep"]) for r in results}
        print(f"resume — 기존 {len(results)}건 이어간다")

    async with Session() as probe:  # 봇 확인 전용. 문항 루프는 자체 세션을 연다.
        bot = await probe.get(Bot, bot_id)
        if bot is None:
            sys.exit(f"봇 {bot_id} 없음")
        if mode:
            bot.retrieval_mode = mode  # 런타임 오버라이드. DB 저장값은 안 건드린다.
        stored_policy = bot.evidence_policy_mode
        if policy:
            bot.evidence_policy_mode = policy
        print(f"✅ 봇 {bot.id} '{bot.name}' · {bot.retrieval_mode} · {bot.evidence_policy_mode}"
              f"{f' (DB 저장값 {stored_policy})' if policy else ''}"
              f" · {bot.llm_model} · 프롬프트 {len(bot.system_prompt or '')}자")
        if stored_policy != "legacy":
            sys.exit("⛔ 봇 **저장값**이 legacy 가 아니다. 앞 측정이 DB 를 오염시켰는지 본다.")
        if policy and policy != "legacy":
            # strict 를 실경로로 태우는 건 기본이 아니다. `_gate.py` 오프라인 재현으로
            # 안 되는 것(= 게이트 예외가 실제로 먹는가)만 여기서 잰다.
            print(f"⚠ 정책을 런타임에서만 {policy} 로 덮는다. DB 는 안 건드린다.")

    total = len(items) * reps
    n = 0
    for rep in range(1, reps + 1):
        for it in items:
            n += 1
            if (_key(it), rep) in done:
                continue
            t0 = time.time()
            row: dict = {"gid": it.get("gid"), "cid": it.get("cid"), "rep": rep,
                         "bucket": it.get("bucket"), "risk": it.get("risk"),
                         "cat": it.get("cat"), "q": it["q"]}
            # 한 문항이 터져도 루프는 계속된다. 첫 실행에서는 세션 생성이 try 밖에 있어
            # 4번째 문항 하나 때문에 110건이 통째로 날아갔다.
            delay = 20.0
            for attempt in range(4):
                # **문항마다 세션을 새로 연다.** 앞 호출이 API 예외로 죽으면 그
                # AsyncSession 은 되살릴 수 없다 — rollback 뒤 재사용하면
                # `MissingGreenlet: greenlet_spawn has not been called` 로 두 번째
                # 결함이 생긴다(실측). 세션을 버리는 것이 유일하게 확실한 격리다.
                try:
                    async with Session() as db:
                        b = await db.get(Bot, bot_id)
                        # **분리하고 나서 바꾼다.** 세션에 붙은 채 바꾸면
                        # `process_chat_request` 안의 commit 에 딸려 들어가 봇의 **저장값**이
                        # 바뀐다. 실제로 봇 29 의 retrieval_mode 가 file_search 로 남았다.
                        # 읽기만 하는 객체라 분리해도 동작에 영향이 없다.
                        db.expunge(b)
                        if mode:
                            b.retrieval_mode = mode
                        if policy:
                            b.evidence_policy_mode = policy
                        cs = ChatSession(user_id=None, bot_id=b.id, title=f"e2e {tag} r{rep}")
                        db.add(cs)
                        await db.flush()
                        resp = await asyncio.wait_for(
                            ChatService(db).process_chat_request(
                                ChatCompletionRequest(bot_id=b.id, message=it["q"],
                                                      use_rag=True, stream=False),
                                b, cs),
                            timeout=180)
                        await db.commit()
                        msg = (await db.execute(
                            Message.__table__.select()
                            .where(Message.session_id == cs.id)
                            .order_by(Message.id.desc()).limit(1))).mappings().first()
                        row["answer"] = resp.content
                        row["source"] = resp.source
                        row["trace"] = msg["trace"] if msg else None
                        row["message_id"] = msg["id"] if msg else None
                        row.pop("error", None)
                    break
                except Exception as e:  # 실패도 남긴다 — 예외 턴은 trace 가 없다
                    detail = f"{type(e).__name__}: {str(e)[:200]}"
                    row["error"] = detail
                    row["answer"] = ""
                    retryable = any(k in str(e) for k in ("429", "503", "500", "RESOURCE_EXHAUSTED",
                                                          "UNAVAILABLE", "Timeout"))
                    print(f"    ⚠ {_key(it)} rep={rep} 시도{attempt + 1}: {detail}", flush=True)
                    if attempt == 3 or not retryable:
                        break
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.6, 120)
            row["wall_ms"] = round((time.time() - t0) * 1000, 1)
            results.append(row)
            mark = "!" if row.get("error") else "."
            print(f"{mark} [{n}/{total}] {_key(it)} rep={rep} {row['wall_ms']:.0f}ms", flush=True)
            out.write_text(json.dumps(
                {"bot": {"id": bot.id, "name": bot.name, "mode": bot.retrieval_mode,
                         "model": bot.llm_model, "policy": bot.evidence_policy_mode},
                 "reps": reps, "count": len(results), "results": results},
                ensure_ascii=False, indent=1), encoding="utf-8")
            if throttle:
                await asyncio.sleep(throttle)

    await engine.dispose()
    errs = sum(1 for r in results if r.get("error"))
    print(f"\n완료 — {len(results)}건 · 오류 {errs}건 → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot-id", type=int, default=29, help="로컬 D-1 ver2 = 29")
    ap.add_argument("--tag", required=True, help="산출물 접미사. 조건을 바꾸면 반드시 새 태그")
    ap.add_argument("--limit", type=int, default=0, help="앞 N건만 (스모크용)")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--throttle", type=float, default=4.0, help="호출 간 대기(초)")
    ap.add_argument("--retrieval-mode", default="", choices=["", "lexical", "file_search", "both"])
    ap.add_argument("--only-cid", default="",
                    help="C07 처럼 cid 로 고른다(쉼표 구분). --limit 은 앞에서 자를 뿐이라 못 고른다")
    ap.add_argument("--policy", default="", choices=["", "legacy", "strict"],
                    help="런타임에서만 정책을 덮는다. 기본은 legacy 강제(strict 는 _gate.py 재현)")
    ap.add_argument("--questions", default="",
                    help="문항 파일 경로. 기본은 questions.json(45/55문항). replay 용 입력을 태울 때만 준다")
    ap.add_argument("--no-backfill", action="store_true",
                    help="배경 인용 백필·근거 구절 추출을 끈다. 턴당 호출 5.65→1회. "
                         "판정은 trace 로 하므로 결손 수집에는 영향이 없다")
    ap.add_argument("--context-mode", default="", choices=["", "raw", "raw_budget", "wiki"],
                    help="L2 근거 구성. 측정에서만 덮는다(코드는 raw_budget 하드코딩). "
                         "wiki = 위키 본문으로만 답함(팔 C)")
    a = ap.parse_args()
    asyncio.run(main(a.bot_id, a.tag, a.limit, a.reps, a.throttle, a.retrieval_mode,
                     a.only_cid, a.policy, a.questions, a.no_backfill, a.context_mode))
