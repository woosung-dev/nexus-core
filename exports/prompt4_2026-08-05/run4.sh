#!/usr/bin/env bash
# 프롬프트 4종 × 55문항 × 2회 = 440 호출. 봇 11 · gemini-3.5-flash-lite.
#
# 회차를 바깥에 둔다 — rep1 을 4팔 모두 끝낸 뒤 rep2 로 간다.
# 일일 한도(모델당 500회, AGENTS.md §3-4)에 걸려도 4방향 비교가 성립하게 하기 위해서다.
# _run.py 는 (문항, 회차) 키로 resume 하므로 같은 태그로 --reps 2 를 다시 돌리면
# rep1 은 재사용되고 rep2 만 추가된다.
set -uo pipefail

ROOT=/Users/woosung/project/agy-project/nexus-core
P="$ROOT/exports/prompt4_2026-08-05/prompts"
LOG="$ROOT/exports/prompt4_2026-08-05/run4.log"
cd "$ROOT/backend" || exit 1          # .env 로딩 기준 디렉터리

ARMS=(
  "j03_45|$P/1_j03_여정동반자.txt"
  "e6_45|$P/2_e6_부모동행v6.md"
  "svb_45|$P/3_svb_서비스방향B.md"
  "sva_45|$P/4_sva_서비스방향A.md"
)

for REP in 1 2; do
  for A in "${ARMS[@]}"; do
    TAG="${A%%|*}"; FILE="${A#*|}"
    echo "===== rep$REP  $TAG  $(date '+%H:%M:%S') =====" | tee -a "$LOG"
    .venv/bin/python "$ROOT/exports/regression/_run.py" \
      --bot-id 11 --model gemini-3.5-flash-lite \
      --system-prompt-file "$FILE" \
      --tag "$TAG" --reps "$REP" --throttle 8 --max-tokens 2048 2>&1 | tee -a "$LOG"
  done
done
echo "===== 전체 완료 $(date '+%H:%M:%S') =====" | tee -a "$LOG"
