#!/bin/bash
# codex(독립 LLM)로 3인 데이터셋을 평가 → codex_eval_{user}.json (병렬)
set -u
DIR="/Users/woosung/project/agy-project/nexus-core/exports/blessing_vs_abc_2026-06-12"
cd "$DIR"

run_one() {
  local user="$1"
  local prompt="당신은 가정연합 축복·가정관리 도메인의 엄격한 평가자다.
- 도메인 정답 기준: domain_facts.md 를 반드시 먼저 읽어라.
- 평가 과제·출력 규칙: eval_rubric.md 를 읽어라.
- 평가 데이터: dataset_${user}.json (items 배열의 각 항목에 q, ansA_통합, ansB_원리, ansC_정밀, tester_choice, tester_win, tester_feedback, blessing_answer 가 있다).
items 의 모든 질문을 평가하라. tester_feedback 는 참고만 하되 너 자신의 판단으로 채점하라.
최종 응답은 eval_schema.json 스키마를 따르는 JSON 객체 하나만 출력하라. evaluator 는 'codex', user 는 '${user}' 로 채워라."
  echo "[codex] $user 시작..."
  codex exec \
    -C "$DIR" \
    -s read-only \
    --skip-git-repo-check \
    --output-schema "$DIR/eval_schema.json" \
    -o "$DIR/codex_eval_${user}.json" \
    "$prompt" > "$DIR/codex_${user}.log" 2>&1
  echo "[codex] $user 완료 (exit=$?)"
}

run_one "조화연" &
run_one "신은비" &
run_one "김소영" &
wait
echo "=== codex 평가 3인 완료 ==="
ls -la "$DIR"/codex_eval_*.json
