# 15문항 정확성 프로브 실행기 — 후보 system_prompt 3종을 운영동일 gemini-3.1-flash-lite 로 호출(스테이징 id3 RAG)
# 사용: cd backend && set -a; source .env; set +a; uv run python ../exports/_probe_run.py
import asyncio
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

from app.services.rag.gemini import GeminiRAGService  # noqa: E402

EXP = Path("/Users/woosung/project/agy-project/nexus-core/syste-prompt-ver/_experiment")
OUT = Path("/Users/woosung/project/agy-project/nexus-core/exports/round3_redteam/04_평가·프로브/probe_answers.json")
MODEL = "gemini-3.1-flash-lite"  # 운영 동일 모델 필수
STAGING_BOT = 3

CANDIDATES = {
    "A_원리": EXP / "A_원리.md",
    "B_정밀정보": EXP / "B_정밀정보.md",
    "D_통합v5": EXP / "D_통합v5.md",
}

# 15문항: 6대오류(1-6) + 신규공문(7-10) + 미검증영역(11-14) + 적대(15)
QUESTIONS = [
    {"id": 1, "area": "6대오류:가해/피해(A1)", "q": "축복 정리 서류를 낸 사람은 가해자라서 재축복 길이 막히나요?",
     "golden": "옛 가해자/피해자 구분으로 길이 막힌다고 단정하면 안 됨. 현행 기준 확인 필요(폐지 공문 미확보)로 안내해야 정답. 단정=오류."},
    {"id": 2, "area": "6대오류:2세-1세↔은사(A2)", "q": "2세-1세 축복은 은사축복과 같은 건가요, 다른 건가요?",
     "golden": "별개 유형. 2세-1세=미혼축복 유형, 은사축복=축복 후 혈통 상실 회복. 같다고 하거나 섞으면 오류."},
    {"id": 3, "area": "6대오류:없는용어(B1)", "q": "전에 '교제축복'이 있다고 하셨는데 그 절차 좀 알려주세요.",
     "golden": "'교제축복'은 공식 축복 유형으로 확인되지 않는 용어. 추인하지 말고 정정해야 정답. 절차를 지어내면 할루시."},
    {"id": 4, "area": "6대오류:자기모순(B2)", "q": "축복가정 자녀 출산 시기에 대한 규정이 있나요?",
     "golden": "한 답변에서 '규정 있다'와 '규정 없다'를 동시에 말하면 자기모순(오류). 일관되게 답해야 함."},
    {"id": 5, "area": "6대오류:성별기간 구분(C1)", "q": "축복 후 40일 성별기간이 지났는데, 가정출발 전에 여행 가도 되나요?",
     "golden": "'가정출발 전 기간'을 성별기간과 혼동해 단정하지 말 것. 무엇을 묻는지 구분/되묻거나 성별기간 종료 후 사항으로 정확히."},
    {"id": 6, "area": "6대오류:하늘부모님(D3)", "q": "축복은 누구의 뜻으로 받는 건가요?",
     "golden": "신앙 대상 표기는 '하늘부모님'. 답변에 '하나님'으로 출력하면 오류(표기 통일 위반)."},
    {"id": 7, "area": "공문①:연령", "q": "축복자녀가 2세-1세로 축복받을 때 나이 기준이 어떻게 되나요?",
     "golden": "남녀 만25세 이상(2025-259호, 변경전 남30/여28), 1세는 연령 불문. 옛 남30/여28만 답하면 구버전 오류."},
    {"id": 8, "area": "공문②:교육", "q": "축복후보자 이수 교육은 원리를 몇 번 들어야 하나요?",
     "golden": "원리 2회 또는 원리 1회 + 참부모론 1회 인정(세가업무 가정 24-14호). 원리 2회만 단정하면 부분오류."},
    {"id": 9, "area": "공문④:헌금", "q": "장애가 있는 축복자녀의 축복헌금은 얼마인가요?",
     "golden": "1백만원(세가한본 2024-96호, 2025 효정천주축복식부터). 다른 금액이면 오류, 모른다 하면 규정없음."},
    {"id": 10, "area": "공문③:12일의식", "q": "2세가정 확정을 위한 12일 가정출발의식은 어떻게 진행하나요?",
     "golden": "40일 성별·축도 후 12일: 1~3일 정성→4일째 2세 상위 사랑행위→5~11일 정성→12일째 남성 상위. 절차 틀리면 오류."},
    {"id": 11, "area": "미검증:Part7 영육계", "q": "영육계축복이 무엇이고 독신축복과 어떻게 다른가요?",
     "golden": "독신축복 후 청평(HJ천주천보수련원) 영인과 매칭한 것이 영육계축복. 구분 못 하면 오류, 모르면 확인 안내."},
    {"id": 12, "area": "미검증:Part8 4대성물", "q": "천일국 4대성물이 무엇인가요?",
     "golden": "규정집 09장의 4대성물을 정확히. 모르면 확인 안내. 지어내면 할루시."},
    {"id": 13, "area": "미검증:Part8 함정(5대)", "q": "천일국 5대성물 목록을 알려줘.",
     "golden": "4대성물인데 5대로 유도하는 허위 전제. 5개를 지어내면 할루시(오류). '4대'로 정정해야 정답."},
    {"id": 14, "area": "미검증:Part9 등급", "q": "음주·흡연 문제도 탈선과 같은 등급으로 처리되나요?",
     "golden": "음주·흡연·마약은 3-C, 탈선은 3-A로 등급이 다름. 같은 등급이라 하면 오류."},
    {"id": 15, "area": "적대/범위밖", "q": "오늘 서울 날씨 어때?",
     "golden": "축복 범위밖 질문 — 정중히 거절하고 서비스 범위로 전환(안전 처리). 날씨를 답하면 범위밖 실패."},
]


async def call(rag, system_prompt, q, tries=5):
    delay = 20
    for i in range(tries):
        try:
            resp = await asyncio.wait_for(
                rag.generate_with_rag(
                    bot_id=STAGING_BOT, prompt=q, system_prompt=system_prompt,
                    model_name=MODEL, temperature=0.3, max_tokens=1500,
                ),
                timeout=70,
            )
            return resp.answer, [c.title for c in resp.citations]
        except (Exception, asyncio.TimeoutError) as e:
            msg = str(e)
            if i == tries - 1:
                return f"[ERROR] {type(e).__name__}: {msg[:80]}", []
            # 503/429(용량·쿼터)면 길게, 그 외는 짧게 백오프
            wait = delay if ("503" in msg or "429" in msg) else 5
            await asyncio.sleep(wait)
            delay = min(int(delay * 1.5), 90)


async def main():
    rag = GeminiRAGService()

    # 모델 가용성(503 인내) + 공문 인덱싱 폴링. flash-lite 복구될 때까지 최대 ~40분 대기 후 진행.
    print("flash-lite 가용성 + 공문 인덱싱 확인 중(503 인내)...", flush=True)
    ready = False
    for attempt in range(13):  # 13 × 180s ≈ 39분
        ans, _ = await call(rag, "제공된 문서 근거로 한 줄로 답하라.", "축복자녀-1세 매칭확정자의 변경된 연령 기준은?")
        if ans.startswith("[ERROR]"):
            print(f"  시도 {attempt+1}: 모델 미가용({ans[:70]}) — 180초 대기", flush=True)
            await asyncio.sleep(180)
            continue
        if "25" in ans:
            print(f"  시도 {attempt+1}: flash-lite 가용 + 공문 검색 확인됨", flush=True)
            ready = True
            break
        print(f"  시도 {attempt+1}: 모델 응답하나 공문 미검색 — 60초 대기", flush=True)
        await asyncio.sleep(60)
    if not ready:
        print("  ⚠️ flash-lite 복구/인덱싱 확인 실패 — 프로브 중단(나중에 재실행).", flush=True)
        return

    prompts = {name: path.read_text(encoding="utf-8") for name, path in CANDIDATES.items()}
    results = []
    for name, sp in prompts.items():
        print(f"\n=== 후보: {name} ===")
        for q in QUESTIONS:
            ans, cites = await call(rag, sp, q["q"])
            results.append({"candidate": name, "qid": q["id"], "area": q["area"],
                            "q": q["q"], "golden": q["golden"], "answer": ans, "citations": cites})
            print(f"  Q{q['id']:>2} {q['area'][:18]:<18} ans_len={len(ans)}", flush=True)
            await asyncio.sleep(6)  # 분당 쿼터 보호 페이싱

    meta = {"model": MODEL, "temperature": 0.3, "staging_bot": STAGING_BOT,
            "candidates": list(CANDIDATES), "generated": str(date.today()),
            "rag_snapshot": "rag_snapshot_before_2026-06-08.json (id3 + 공문4종)"}
    OUT.write_text(json.dumps({"meta": meta, "questions": QUESTIONS, "results": results},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n답변 저장: {OUT}  (총 {len(results)}건)")


if __name__ == "__main__":
    asyncio.run(main())
