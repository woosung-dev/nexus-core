#!/usr/bin/env bash
# 팔이 끝나는 대로 채점을 붙인다 — gemini 실행(4시간)과 codex 채점을 겹쳐 돌리기 위해서다.
#
# 안전장치: 그 태그로 _run.py 가 돌고 있으면 건드리지 않는다.
#   _run.py 는 호출마다 _answers_<tag>.json 을 통째로 다시 쓴다(원자적 쓰기가 아니다).
#   쓰는 중에 읽으면 JSON 파싱이 깨진다.
set -uo pipefail
ROOT=/Users/woosung/project/agy-project/nexus-core
D="$ROOT/exports/prompt4_2026-08-05"
PY="$ROOT/backend/.venv/bin/python"
TAGS=(j03_45 e6_45 svb_45 sva_45)
cd "$ROOT/backend" || exit 1

while :; do
  running=$(pgrep -f "_run.py --bot-id 11" >/dev/null && echo yes || echo no)
  for T in "${TAGS[@]}"; do
    A="$ROOT/exports/regression/_answers_$T.json"
    [ -f "$A" ] || continue
    pgrep -f -- "--tag $T" >/dev/null && continue      # 이 태그는 지금 실행 중
    # 채점 대상이 남았는지 확인 (앵커 판정 수 < 응답 수)
    NEED=$("$PY" - "$A" "$D/_anchor_$T.json" <<'EOF'
import json, sys, pathlib
ans = json.loads(pathlib.Path(sys.argv[1]).read_text())
n = sum(1 for r in ans["results"] if r.get("gid") and not r["answer"].startswith("[ERROR]"))
p = pathlib.Path(sys.argv[2])
g = len(json.loads(p.read_text())["rows"]) if p.exists() else 0
print(1 if n > g else 0)
EOF
) || continue
    if [ "$NEED" = "1" ]; then
      echo "=== 앵커 채점 $T $(date '+%H:%M:%S')"
      "$PY" "$D/_anchor.py" --tag "$T" 2>&1 | tail -3
    fi
    # 실행이 다 끝난 뒤에만 기계 판정을 돌린다 (questions.json 은 고정이라 언제 돌려도 되지만
    # L3 는 codex 를 또 쓰므로 앵커 채점과 겹치지 않게 마지막에 몬다)
    if [ "$running" = "no" ]; then
      [ -f "$ROOT/exports/regression/_l1_$T.json" ] || "$PY" "$ROOT/exports/regression/_l1.py" --tag "$T" >/dev/null 2>&1
      [ -f "$ROOT/exports/regression/_l2_$T.json" ] || "$PY" "$ROOT/exports/regression/_l2.py" --tag "$T" >/dev/null 2>&1
      [ -f "$ROOT/exports/regression/_l3_$T.json" ] || "$PY" "$ROOT/exports/regression/_l3.py" --tag "$T" 2>&1 | tail -2
    fi
  done
  if [ "$running" = "no" ]; then
    ALL=1
    for T in "${TAGS[@]}"; do
      [ -f "$D/_anchor_$T.json" ] && [ -f "$ROOT/exports/regression/_l3_$T.json" ] || ALL=0
    done
    [ "$ALL" = "1" ] && { echo "=== 전체 채점 완료 $(date '+%H:%M:%S')"; break; }
  fi
  sleep 120
done
"$PY" "$D/_report4.py"
