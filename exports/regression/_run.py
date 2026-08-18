# 회귀셋 50문항을 봇에 질의하고 L1 신호까지 함께 기록한다 (resume-safe).
#
# L1 신호 확보 방식: gemini.py 는 chunk_count 를 RAGResponse 에 담지 않고 logger.info 로만
# 내보낸다(gemini.py:472-489). 제품 코드를 건드리지 않기 위해 해당 로거에 핸들러를 붙여
# record.args 튜플에서 값을 그대로 읽는다 — 문자열 파싱이 아니라 구조화 값 수집이다.
import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

# sqlalchemy echo 등 소음만 끄고, RAG 로거는 살려둔다 (L1 신호가 여기로 온다).
for name in ("sqlalchemy.engine", "sqlalchemy.pool", "httpx", "google_genai"):
    logging.getLogger(name).setLevel(logging.WARNING)

from app.services.rag.gemini import GeminiRAGService  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.crud import crud_bot  # noqa: E402
# 운영 사실 오버레이 — 런타임(chat_service)이 쓰는 것과 **같은 함수**를 쓴다.
# 하네스가 chat_service 를 우회하므로 여기서 안 붙이면 재측정이 개입을 못 잰다.
# `_attach_crisis` 는 비공개지만 **운영과 같은 함수를 쓰는 것이 요점**이다.
# 여기서 다시 구현하면 규약이 조용히 갈라진다(거절문 판정·교체 조건).
from app.services.chat_service import _attach_crisis as attach_crisis  # noqa: E402
from app.services.ops_facts_service import (  # noqa: E402
    apply_term_rules,
    build_crisis_suffix,
    build_prompt_overlay,
    load_runtime_facts,
    term_rules,
)

DIR = Path(__file__).parent
RAG_LOGGER = "app.services.rag.gemini"
_MSG = "gemini RAG generate_content elapsed"


class L1Capture(logging.Handler):
    """generate_content 측정 로그의 args 를 구조화 값으로 받는다.

    포맷: elapsed=%.1f model=%s bot_id=%s answer_len=%d grounding_chunks=%d citations=%d followups=%d
    """

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.last = None

    def emit(self, record):
        try:
            a = record.args
            # 이 로그는 위치 인자(tuple)로만 기록된다. dict 스타일이면 우리 포맷이 아니다.
            if not (isinstance(record.msg, str) and record.msg.startswith(_MSG)
                    and isinstance(a, tuple) and len(a) >= 7):
                return
            self.last = {"gen_ms": round(float(a[0]), 1), "model": str(a[1]),
                         "answer_len": int(a[3]), "grounding_chunks": int(a[4]),
                         "citations": int(a[5]), "followups": int(a[6])}
        except Exception:
            pass  # 계측 실패가 실행을 막지 않는다


async def _lexical(bot_id, sp, model, q, max_tokens):
    """어휘 검색(BM25) 팔 — 라이브 봇 11 이 실제로 타는 경로다.

    하네스는 `chat_service` 를 우회하므로 `bots.retrieval_mode` 를 읽지 않는다. 그래서
    file_search 팔만 재고 있었다(8/11 880호출이 그랬다). 여기서 같은 함수를 직접 부른다 —
    `chat_service.py:438` 의 lexical 분기가 부르는 것과 **같은 `answer_with_wiki`** 다.

    dense 는 기본 꺼져 있어(`WIKI_DENSE_SCALES` 빈값) BM25 전용이다 — 임베딩 호출 0회.
    질의당 생성 1회만 든다.
    """
    from app.services.wiki.service import _select_units, answer_with_wiki

    t0 = time.time()
    resp, retrieved = await answer_with_wiki(
        bot_id=bot_id, question=q, system_prompt=sp, model_name=model,
        max_tokens=max_tokens, context_mode="raw_budget")
    units = _select_units(retrieved, "raw_budget")
    # gemini 로거를 안 타므로 L1 신호를 여기서 만든다. 키 이름은 file_search 팔과 맞춘다.
    # gen_ms 는 검색까지 포함한 벽시계다(file_search 팔의 gen_ms 는 생성만) — 그래도
    # 어휘 검색은 BM25 로컬이라 차이가 수 ms 수준이다.
    l1 = {"model": model, "gen_ms": round((time.time() - t0) * 1000, 1),
          "answer_len": len(resp.answer),
          "grounding_chunks": len(units),
          "chars": sum(len(u.text[:2000]) for u in units),
          "pages": [p.slug for p, _ in retrieved.pages],
          "citations": len(resp.citations), "followups": 0}
    return resp, l1


async def call(rag, bot_id, sp, model, q, cap, tries=5, max_tokens=2048, mode="file_search"):
    """운영과 동일하게 generate_with_rag 호출. 429/503 백오프."""
    delay = 20
    for i in range(tries):
        cap.last = None
        try:
            if mode == "lexical":
                resp, l1 = await asyncio.wait_for(
                    _lexical(bot_id, sp, model, q, max_tokens), timeout=180)
                cap.last = l1
                titles, seen = [], set()
                for c in resp.citations:
                    t = (c.title or "").strip()
                    if t and t not in seen:
                        seen.add(t)
                        titles.append(t)
                return resp.answer, titles, len(resp.citations), cap.last
            resp = await asyncio.wait_for(
                rag.generate_with_rag(bot_id=bot_id, prompt=q, system_prompt=sp,
                                      model_name=model, max_tokens=max_tokens),
                timeout=180)
            titles, seen = [], set()
            for c in resp.citations:
                t = (c.title or "").strip()
                if t and t not in seen:
                    seen.add(t)
                    titles.append(t)
            return resp.answer, titles, len(resp.citations), cap.last
        except (Exception, asyncio.TimeoutError) as e:
            msg = str(e)
            if i == tries - 1:
                return f"[ERROR] {type(e).__name__}: {msg[:100]}", [], 0, cap.last
            await asyncio.sleep(delay if ("503" in msg or "429" in msg) else 5)
            delay = min(int(delay * 1.5), 90)
    return "[ERROR] retries exhausted", [], 0, None


async def main(bot_id, tag, limit, model_override, max_tokens, throttle, sp_file, reps,
               ops_facts=False, mode=""):
    items = json.loads((DIR / "questions.json").read_text(encoding="utf-8"))["items"]
    if limit:
        items = items[:limit]
    out = DIR / (f"_answers_{tag}.json" if tag else "_answers.json")

    async with async_session() as s:
        row = (await s.execute(text(
            "SELECT id,name,system_prompt,llm_model,retrieval_mode FROM bots WHERE id=:b"),
            {"b": bot_id})).mappings().first()
    if not row:
        raise SystemExit(f"bots.id={bot_id} 없음")
    sp, model, name = row["system_prompt"], row["llm_model"], row["name"]
    if model_override:
        model = model_override  # 봇 저장 설정은 그대로, 이번 실행만 교체
    # 기본은 봇 저장값을 **따른다**. 안 그러면 lexical 봇을 file_search 로 재게 된다
    # (8/11 880호출이 그 상태였다 — 봇 11 은 lexical 인데 하네스가 chat_service 를 우회했다).
    eff_mode = mode or (row["retrieval_mode"] or "file_search")
    if eff_mode not in ("file_search", "lexical"):
        raise SystemExit(f"이 하네스가 지원하지 않는 모드다: {eff_mode} (file_search|lexical)")

    # 프롬프트만 교체하고 RAG(= bot_id 로 걸리는 문서 집합)는 그 봇 것을 그대로 쓴다.
    sp_source = f"bots.id={bot_id}"
    if sp_file:
        p = Path(sp_file)
        if not p.exists():
            raise SystemExit(f"프롬프트 파일 없음: {sp_file}")
        sp = p.read_text(encoding="utf-8")
        sp_source = str(p)
        print(f"프롬프트 교체 → {p.name} ({len(sp)}자). RAG 는 봇 {bot_id} 문서 유지.", flush=True)

    # resume 키에 rep 을 포함한다 — reps>1 이면 같은 문항이 여러 번 나오므로
    # 키가 문항 하나면 2회차부터 1회차 결과를 재사용해 버린다(변동을 못 잰다).
    done = {}
    if out.exists():
        prev = json.loads(out.read_text(encoding="utf-8"))
        done = {((r.get("cid") or r.get("gid")), r.get("rep", 1)): r
                for r in prev.get("results", []) if not r["answer"].startswith("[ERROR]")}
        print(f"이전 결과 {len(done)}건 재사용", flush=True)

    cap = L1Capture()
    logging.getLogger(RAG_LOGGER).addHandler(cap)
    logging.getLogger(RAG_LOGGER).setLevel(logging.INFO)

    # 운영 사실 오버레이 — 기본은 꺼져 있다. 켜야 기존 팔과 A/B 가 성립한다.
    bot_obj = None
    if ops_facts:
        async with async_session() as s:
            bot_obj = await crud_bot.get_bot(s, bot_id)
        if bot_obj is None:
            raise SystemExit(f"ops-facts 오버레이용 봇 조회 실패: id={bot_id}")
        # 프롬프트 교체(--system-prompt-file) 와 겹쳐도 오버레이는 그 뒤에 붙는다.
        bot_obj.system_prompt = sp
        print("운영 사실 오버레이 ON — 승인분만 반영된다(초안은 무시).", flush=True)

    # lexical 은 File Search 스토어를 **한 번도 건드리지 않는다**(BM25 + plain generate_content).
    # 그래서 스토어가 없는 API 키로도 돈다 — 키만 바꾸면 하루 한도를 새로 받는다.
    # 반대로 file_search 팔은 스토어가 그 키의 프로젝트에 있어야 하므로 키를 못 바꾼다.
    rag = None if eff_mode == "lexical" else GeminiRAGService()
    print(f"bot id={bot_id} '{name}' model={model} sp_len={len(sp)} "
          f"retrieval={eff_mode}{' (봇 저장값)' if not mode else ' (실행 지정)'} → {out.name}",
          flush=True)
    print(f"대상 {len(items)}건 (A {sum(i['bucket']=='A' for i in items)} · "
          f"B {sum(i['bucket']=='B' for i in items)} · C {sum(i['bucket']=='C' for i in items)})"
          f" × {reps}회 = {len(items)*reps}호출", flush=True)

    def snapshot(results):
        out.write_text(json.dumps({"bot": {"id": bot_id, "name": name, "model": model,
                                           "prompt_source": sp_source, "prompt_len": len(sp),
                                           "retrieval_mode": eff_mode,
                                           "ops_facts": bool(ops_facts)},
                                   "reps": reps, "count": len(results), "results": results},
                                  ensure_ascii=False, indent=1), encoding="utf-8")

    results, total = [], len(items) * reps
    idx = 0
    # 회차를 바깥 루프에 둔다 — 중간에 끊겨도 완결된 회차가 남아 비교가 성립한다.
    for rep in range(1, reps + 1):
        for it in items:
            idx += 1
            key = it.get("cid") or it.get("gid")
            if (key, rep) in done:
                results.append(done[(key, rep)])
                continue
            t = time.time()
            # 오버레이는 질문마다 다시 만든다 — triggers 가 있는 사실(위기 자원 등)은
            # 질문에 그 표현이 있을 때만 붙기 때문이다. 조회는 서비스가 60초 캐시한다.
            sp_eff, rules, crisis = sp, [], ""
            if ops_facts:
                async with async_session() as s:
                    facts = await load_runtime_facts(s, bot_obj, it["q"])
                sp_eff = sp + build_prompt_overlay(facts)
                rules = term_rules(facts)
                crisis = build_crisis_suffix(facts)
            ans, titles, n_cit, l1 = await call(rag, bot_id, sp_eff, model, it["q"], cap,
                                                max_tokens=max_tokens, mode=eff_mode)
            if rules:
                # 운영과 같은 후처리. 여기서 안 하면 term 위반 수치가 운영과 달라진다.
                ans = apply_term_rules(ans, rules)
            if crisis:
                # ⚠ 이걸 빼면 crisis 승인이 **이 하네스에서만** 역효과를 낸다.
                # 오버레이가 모델에게 「연락처는 시스템이 덧붙이니 네가 쓰지 마라」고
                # 시키는데 하네스가 안 덧붙이면, 109·1577-0199 가 승인 전보다 덜 나온다.
                # 운영과 같은 규약 — 표기 치환 뒤, 거절문이면 통째로 교체.
                ans, _ = attach_crisis(ans, crisis)
            rec = {"gid": it.get("gid"), "cid": it.get("cid"), "rep": rep, "bucket": it["bucket"],
                   "cat": it["cat"], "risk": it.get("risk"), "q": it["q"],
                   "answer": ans, "citations": titles, "n_citations": n_cit, "l1": l1}
            results.append(rec)
            chunks = (l1 or {}).get("grounding_chunks")
            flag = "ERR" if ans.startswith("[ERROR]") else ("검색빈손" if chunks == 0 else "ok")
            print(f"[{idx:>3}/{total}] r{rep} {key} {it['bucket']} {flag} {time.time()-t:.1f}s "
                  f"chunks={chunks} cites={n_cit} len={len(ans)}", flush=True)
            snapshot(results)
            await asyncio.sleep(throttle)

    # 루프 안 저장은 '신규 호출 직후'에만 일어난다. 마지막 신규 호출 이후의 resume 항목이
    # 디스크에 안 써진 채 남으므로 종료 시 한 번 더 써서 전량을 보존한다.
    snapshot(results)
    errs = sum(1 for r in results if r["answer"].startswith("[ERROR]"))
    empty = sum(1 for r in results if (r.get("l1") or {}).get("grounding_chunks") == 0)
    print(f"\n완료 {len(results)}호출 (오류 {errs} · 검색빈손 {empty}) → {out}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot-id", type=int, default=7, help="대상 봇 (7=D 라이브, 11=여정동반자 경량)")
    ap.add_argument("--tag", default="", help="산출물 접미사")
    ap.add_argument("--limit", type=int, default=0, help="앞 N건만 (스모크용)")
    ap.add_argument("--model", default="", help="llm_model 오버라이드")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--throttle", type=int, default=12, help="호출 간 대기(초). RPM 보호")
    ap.add_argument("--system-prompt-file", default="",
                    help="이 파일 내용으로 system_prompt 교체 (RAG 는 --bot-id 문서 그대로 사용)")
    # reps 를 왜 두는가 — 같은 봇·모델·프롬프트·질문인데 세션 간 판정이 뒤집힌 실측이 있다
    # (R-219 편성분기 0/2 ↔ 2/2, 동일조건 10회에서 8/10). 잡음 바닥이 20pp 라 1회로는
    # 개입 효과를 못 잰다. 개선 여부를 판정하려면 5회 이상이 필요하다.
    ap.add_argument("--reps", type=int, default=1,
                    help="문항당 반복 호출 수. 개입 효과 판정에는 5 이상 권장")
    ap.add_argument("--retrieval-mode", default="", choices=["", "file_search", "lexical"],
                    help="비우면 봇 저장값(bots.retrieval_mode)을 따른다. "
                         "lexical = BM25 로 규정 원문만 주입(라이브 봇 11 의 실제 경로)")
    ap.add_argument("--ops-facts", action="store_true",
                    help="운영 사실 오버레이(프롬프트 주입 + 표기 치환)를 켠다. "
                         "끈 팔이 기준선이다. 승인된 행이 없으면 켜도 차이가 없다")
    a = ap.parse_args()
    asyncio.run(main(a.bot_id, a.tag, a.limit, a.model, a.max_tokens, a.throttle,
                     a.system_prompt_file, a.reps, a.ops_facts, a.retrieval_mode))
