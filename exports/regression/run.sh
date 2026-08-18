#!/usr/bin/env bash
# 회귀 1회 실행 — 프롬프트나 RAG 를 바꿨을 때 수동으로 돌린다.
#
#   ./run.sh --bot-id 7 --tag v1            전체 (질의 → L1 → L2 → L3 → 리포트)
#   ./run.sh --bot-id 7 --tag v1 --no-run   이미 받은 응답으로 판정만 다시
#   ./run.sh --bot-id 7 --tag v1 --probe    빈손 원인 분해까지 (API 추가 호출)
#
# 산출물은 전부 이 디렉터리에 _<단계>_<tag>.json 으로 떨어진다.
# DB 적재는 하지 않는다 — 확인 후 별도로 _apply 를 돌린다.
set -euo pipefail

REPO="/Users/woosung/project/agy-project/nexus-core"
PY="$REPO/backend/.venv/bin/python"
HERE="$REPO/exports/regression"

BOT_ID=7
TAG=""
DO_RUN=1
PROBE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bot-id) BOT_ID="$2"; shift 2 ;;
    --tag)    TAG="$2";    shift 2 ;;
    --no-run) DO_RUN=0;    shift ;;
    --probe)  PROBE="--probe"; shift ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$TAG" ]] || { echo "--tag 필요 (실행 구분자)" >&2; exit 2; }

cd "$REPO/backend"   # .env 로딩 기준 디렉터리

echo "═══ 0. 판정기 자가 테스트 (측정 장치 결함 배제) ═══"
"$PY" "$HERE/_l2.py" --selftest

if [[ $DO_RUN -eq 1 ]]; then
  echo; echo "═══ 1. 응답 수집 (봇 $BOT_ID) ═══"
  "$PY" "$HERE/_run.py" --bot-id "$BOT_ID" --tag "$TAG"
else
  echo; echo "═══ 1. 응답 수집 건너뜀 (--no-run) ═══"
fi

echo; echo "═══ 2. L1 시스템 계측 ═══"
"$PY" "$HERE/_l1.py" --tag "$TAG" $PROBE

echo; echo "═══ 3. L2 규칙 판정 ═══"
"$PY" "$HERE/_l2.py" --tag "$TAG"

echo; echo "═══ 4. L3 의미 판정 (codex) ═══"
"$PY" "$HERE/_l3.py" --tag "$TAG" || echo "  L3 실패 — 정답지 미확정이면 정상이다. 리포트는 계속 진행한다."

echo; echo "═══ 5. 게이트 리포트 ═══"
"$PY" "$HERE/_report.py" --tag "$TAG"
