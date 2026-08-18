#!/bin/bash
set -u
DIR="/Users/woosung/project/agy-project/nexus-core/exports/blessing_v3_2026-06-12"; cd "$DIR"
run_one(){ local user="$1"
  local p="당신은 가정연합 축복·가정관리 도메인의 엄격한 독립 평가자다.
- domain_facts.md 를 먼저 읽어라. eval_rubric.md 규칙을 따르라.
- 평가 데이터: dataset_가_${user}_v5.json (blessing_answer 는 블레싱 가 v5 답변).
blessing_answer 가 '[ERROR]'로 시작하는 항목은 쿼터 결측이니 채점하지 말고 results 에서 제외하라. 나머지 모든 질문 평가. eval_schema.json 스키마 JSON 하나만 출력. evaluator='codex', user='${user}'."
  echo "[codex 가/$user]"; codex exec -C "$DIR" -s read-only --skip-git-repo-check \
    --output-schema "$DIR/eval_schema.json" -o "$DIR/codex_가_${user}_v5.json" "$p" > "$DIR/codex_가_${user}_v5.log" 2>&1; }
run_one "미야자키시호" & run_one "김소영" & run_one "조화연" & wait
echo "codex 가 v3 완료"; ls -la "$DIR"/codex_가_*_v3.json
