#!/bin/bash
set -u
DIR="/Users/woosung/project/agy-project/nexus-core/exports/blessing_v3_2026-06-12"; cd "$DIR"
run_one(){ local user="$1"
  local p="당신은 가정연합 축복·가정관리 도메인의 엄격한 독립 평가자다.
- domain_facts.md 를 먼저 읽어라. eval_rubric.md 의 규칙을 따르라.
- 평가 데이터: dataset_나_${user}_v3.json (blessing_answer 는 블레싱 나 v3 답변).
모든 질문 평가. eval_schema.json 스키마 JSON 하나만 출력. evaluator='codex', user='${user}'."
  echo "[codex 나/$user]"; codex exec -C "$DIR" -s read-only --skip-git-repo-check \
    --output-schema "$DIR/eval_schema.json" -o "$DIR/codex_나_${user}_v3.json" "$p" > "$DIR/codex_나_${user}_v3.log" 2>&1; }
run_one "조화연" & run_one "신은비" & run_one "김소영" & wait
echo "codex 나 v3 완료"; ls -la "$DIR"/codex_나_*_v3.json
