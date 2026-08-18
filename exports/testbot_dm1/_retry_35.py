# gemini-3.5-flash 가 503(과부하) 풀릴 때까지 주기적으로 확인 → 가용하면 상 20건 체인(run→eval→cite→report) 자동 실행
# 봇 8 저장설정은 그대로, 이번 실행만 모델 교체. resume-safe. 사용자 지시 "3.5-flash 나중에 재시도".
import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")
logging.disable(logging.WARNING)

from app.services.rag.gemini import GeminiRAGService  # noqa: E402

MODEL = "gemini-3.5-flash"
TAG = "gemini-3.5-flash_상"
DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/testbot_dm1")
PY = "/Users/woosung/project/agy-project/nexus-core/backend/.venv/bin/python"
ANSWERS = DIR / f"_answers_{TAG}.json"
INTERVAL = 1200          # 20분 간격 프로브
MAX_HOURS = 5            # 최대 대기
MIN_LEN = 400            # 이 미만 답변은 잘림/오류로 보고 재생성


def clean_partial():
    """잘린·오류 답변 제거 → 재시도 시 깨끗이 재생성되게 한다(완전한 것만 유지)."""
    if not ANSWERS.exists():
        return
    d = json.load(open(ANSWERS))
    keep = [r for r in d["results"]
            if not r["answer"].startswith("[ERROR]") and len(r["answer"]) >= MIN_LEN]
    dropped = d["count"] - len(keep)
    d["results"], d["count"] = keep, len(keep)
    ANSWERS.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"정리: 완전한 답변 {len(keep)}건 유지, 잘림/오류 {dropped}건 제거(재생성 대상)", flush=True)


async def probe(n=2):
    """3.5-flash 로 짧은 질의 n회 — 전부 성공해야 '가용'으로 판단."""
    rag = GeminiRAGService()
    for i in range(n):
        try:
            r = await asyncio.wait_for(rag.generate_with_rag(
                bot_id=8, prompt="축복은 몇 살부터 받나요?", system_prompt="당신은 축복 상담 도우미입니다.",
                model_name=MODEL, max_tokens=128), timeout=45)
            if r.answer.startswith("[ERROR]") or not r.answer.strip():
                return False
        except Exception as e:
            print(f"  프로브 {i} 실패: {type(e).__name__} {str(e)[:70]}", flush=True)
            return False
        await asyncio.sleep(2)
    return True


def sh(script, *args):
    return subprocess.run([PY, str(DIR / script), *args]).returncode == 0


def run_complete():
    """answers 파일이 20건 전부 비오류인지."""
    if not ANSWERS.exists():
        return False
    d = json.load(open(ANSWERS))
    ok = [r for r in d["results"] if not r["answer"].startswith("[ERROR]") and len(r["answer"]) >= MIN_LEN]
    return len(ok) >= 20


async def main():
    clean_partial()
    start = time.time()
    rounds = 0
    while True:
        rounds += 1
        elapsed = (time.time() - start) / 3600
        if elapsed > MAX_HOURS:
            print(f"⏱️ 최대 대기({MAX_HOURS}h) 초과 — 재시도 중단. 나중에 이 스크립트 다시 실행하세요.", flush=True)
            return
        print(f"[라운드 {rounds}, {elapsed:.1f}h] {MODEL} 가용성 프로브…", flush=True)
        if await probe():
            print("✅ 3.5-flash 가용 — 상 20건 체인 실행", flush=True)
            clean_partial()  # 직전 라운드의 부분실패 정리
            sh("_run.py", "--model", MODEL, "--risk", "상", "--tag", TAG)
            if run_complete():
                if sh("_eval.py", "--tag", TAG) and sh("_cite.py", "--tag", TAG) and sh("_report.py", "--tag", TAG):
                    print("🎉 완료: 상 20건 3.5-flash 리포트 생성됨", flush=True)
                    return
                print("체인 후반(eval/cite/report) 실패 — 다음 라운드 재시도", flush=True)
            else:
                print("run 미완(일부 503) — 20분 후 이어서 재시도", flush=True)
        print(f"…{INTERVAL//60}분 대기", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
