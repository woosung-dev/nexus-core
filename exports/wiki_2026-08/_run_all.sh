#!/bin/zsh
# 250건을 끝까지 처리한다 — 지금 돌고 있는 ingest 가 끝나면 실패분을 자동으로 다시 돌린다.
#
# _ingest.py 는 한 번 실행 안에서 실패한 소스를 건너뛴다(뒤를 살리기 위해서다).
# 그래서 "모두 처리"하려면 재실행이 필요하고, 재실행은 ok 가 아닌 것만 집어 든다.
#
# 병렬 금지가 절대 규칙이라 앞선 프로세스가 끝난 뒤에만 다음 라운드를 시작한다.
#
# 사용: nohup ./_run_all.sh <앞선_PID> > _run_all.log 2>&1 &
set -u
cd "$(dirname "$0")"

PREV_PID="${1:-}"
MAX_ROUNDS=4

count_ok() {
  python3 -c "
import json
s = json.load(open('bots/11/_ingest_state.json'))
print(sum(1 for v in s.values() if v.get('ok')))"
}

if [[ -n "$PREV_PID" ]]; then
  echo "[wait] 앞선 ingest(PID $PREV_PID) 종료 대기…"
  while kill -0 "$PREV_PID" 2>/dev/null; do sleep 30; done
  echo "[wait] 종료 확인. 성공 $(count_ok)/250"
fi

for round in $(seq 1 $MAX_ROUNDS); do
  before=$(count_ok)
  if [[ "$before" -ge 250 ]]; then
    echo "[done] 250/250 — 재시도 불필요"
    break
  fi
  echo "[round $round] 시작 · 현재 성공 $before/250"
  python3 _ingest.py --bot 11 --today 2026-08-08
  after=$(count_ok)
  echo "[round $round] 끝 · 성공 $before → $after"
  # 한 라운드가 아무것도 못 살렸으면 재시도로는 안 되는 실패다. 멈추고 사람이 본다.
  if [[ "$after" -eq "$before" ]]; then
    echo "[stop] 라운드에서 새로 성공한 건이 없다 — 재시도로 풀리지 않는 실패다"
    break
  fi
done

echo "[final] 성공 $(count_ok)/250 · 페이지 $(ls bots/11/wiki/pages/*.md 2>/dev/null | wc -l | tr -d ' ')쪽"
python3 -c "
import json
s = json.load(open('bots/11/_ingest_state.json'))
ng = [k for k, v in s.items() if not v.get('ok')]
print(f'[final] 남은 실패 {len(ng)}건: {ng}')"
