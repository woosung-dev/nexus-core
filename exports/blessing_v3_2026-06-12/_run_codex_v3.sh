#!/bin/bash
# codex 로 나 v3·가 v3 데이터셋 평가 → codex_{bot}_{user}_v3.json (병렬)
set -u
DIR="/Users/woosung/project/agy-project/nexus-core/exports/blessing_v3_2026-06-12"
cd "$DIR"
run_one() {
  local bot="$1"; local user="$2"
  local prompt="당신은 가정연합 축복·가정관리 도메인의 엄격한 독립 평가자다.
- 도메인 정답 기준: domain_facts.md 를 먼저 읽어라.
- 평가 과제·출력 규칙: eval_rubric.md 를 읽어라.
- 평가 데이터: dataset_${bot}_${user}_v3.json (items 각 항목에 q, ansA_통합, ansB_원리, ansC_정밀, tester_choice, tester_win, tester_feedback, blessing_answer). blessing_answer 는 신규 프롬프트 v3 의 답변이다.
모든 질문을 평가하라. 최종 응답은 eval_schema.json 스키마를 따르는 JSON 객체 하나만 출력하라. evaluator='codex', user='${user}'."
  echo "[codex] $bot/$user 시작..."
  codex exec -C "$DIR" -s read-only --skip-git-repo-check \
    --output-schema "$DIR/eval_schema.json" -o "$DIR/codex_${bot}_${user}_v3.json" \
    "$prompt" > "$DIR/codex_${bot}_${user}_v3.log" 2>&1
  echo "[codex] $bot/$user 완료"
}
run_one "나" "조화연" & run_one "나" "신은비" & run_one "나" "김소영" &
run_one "가" "미야자키시호" & run_one "가" "김소영" & run_one "가" "조화연" &
wait
echo "=== codex v3 6잡 완료 ==="
ls -la "$DIR"/codex_*_v3.json
