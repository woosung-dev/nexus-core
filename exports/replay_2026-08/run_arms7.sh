#!/usr/bin/env bash
# 답변 경로 7안 비교 — 20문항 × 7안 = 140 생성 호출 (하루 한도 500 안)
#
# 설계 근거와 각 안의 뜻은 `docs/architecture/next-session-gate-overblock-2026-08-15.md` §7.
#
# ── 레이어 셋 ────────────────────────────────────────────────────────────
#   L1 검색 경로   bots.retrieval_mode          file_search · lexical · both
#   L2 근거 구성   context_mode                 raw · raw_budget · wiki
#                  ⚠ 코드 하드코딩. `--context-mode` 로 **측정에서만** 덮는다
#   L5 스토어      FILE_SEARCH_STORE_NAME       knowledge-base(34건) · fs-measure-0818(2건)
#                  ⚠ 봇별이 아니라 전역 하나다
#
# ── 왜 이렇게 도나 ───────────────────────────────────────────────────────
#   · `--policy` 를 주지 않는다 = legacy. 게이트는 생성 뒤 판정이라 `_kpi.py` 가 재현한다.
#     호출이 절반이고 같은 답변에서 갈리니 게이트 효과만 순수하게 남는다.
#   · `--no-backfill` 없으면 턴당 호출이 5.65배가 된다(인용 청크마다 LLM 1회).
#   · `--throttle 10` 미만 금지 — 분당 15회 제한.
#   · 태그를 그대로 다시 돌리면 resume 된다. 429 를 맞으면 KST 16:00 이후 같은 명령.
#
# ── ⚠ 안 3(wiki)은 게이트 지표를 못 쓴다 ────────────────────────────────
#   프롬프트에 원문이 안 들어가는데 trace 는 raw_budget 기준으로 적힌다
#   (`_run_e2e.py` 모듈 docstring 참조). **답변률과 자체 거절만 보고 게이트는 버려라.**
#
# 사용: cd backend && bash ../exports/replay_2026-08/run_arms7.sh [안번호…]
#       인자를 주면 그 안만 돈다. 예) bash ../exports/replay_2026-08/run_arms7.sh 3 5

set -u
Q=../exports/replay_2026-08/_input_20.json
BASE="--bot-id 29 --questions $Q --reps 1 --throttle 10 --no-backfill"
FAIR=nexus-fs-measure-0818          # 규정집v20 + 대사전v4 (lexical 과 같은 자료)
REAL=nexus-core-knowledge-base      # 국제규정집·가이드북·공문 포함 34건

run() {  # run <번호> <설명> <추가인자…>
  local n=$1 desc=$2; shift 2
  if [ $# -ge 0 ] && [ -n "${ONLY:-}" ] && ! grep -qw "$n" <<<"$ONLY"; then return; fi
  echo; echo "════ 안 $n · $desc ════"
  .venv/bin/python -u ../exports/regression/_run_e2e.py $BASE --tag "arm$n" "$@"
}

ONLY="$*"

run 1 "현행 라이브 — lexical · 예산분" \
    --retrieval-mode lexical --context-mode raw_budget

run 2 "원문을 더 많이 — lexical · raw(최대 24건)" \
    --retrieval-mode lexical --context-mode raw

run 3 "위키 요약만 — lexical · wiki  ⚠게이트 지표 못 씀" \
    --retrieval-mode lexical --context-mode wiki

# 안 4(+dense)는 dense150 에서 이미 쟀다. 다시 돌리려면 아래 주석을 풀어라.
# WIKI_DENSE_SCALES=unit run 4 "의미 검색 추가" \
#     --retrieval-mode lexical --context-mode raw_budget

FILE_SEARCH_STORE_NAME=$FAIR \
run 5 "구글 검색 · 공정(자료 2건)" \
    --retrieval-mode file_search

FILE_SEARCH_STORE_NAME=$REAL \
run 6 "구글 검색 · 현실(자료 34건)" \
    --retrieval-mode file_search

FILE_SEARCH_STORE_NAME=$FAIR \
run 7 "둘 다 — both · 자료 2건" \
    --retrieval-mode both --context-mode raw_budget

cat <<'DONE'

════ 비교 ════
  cd backend
  .venv/bin/python ../exports/replay_2026-08/_compare.py --a arm1 --b arm2
  .venv/bin/python ../exports/replay_2026-08/_compare.py --a arm1 --b arm3
  .venv/bin/python ../exports/replay_2026-08/_compare.py --a arm1 --b arm5
  ...

  ⚠ arm3(wiki)은 「답 받음 / 자체 거절」만 읽어라. 「게이트 차단」은 무의미하다.
  ⚠ arm5 vs arm6 을 같이 봐야 「검색이 좋아서」와 「자료가 많아서」를 가른다.
DONE
