#!/usr/bin/env bash
# 14개 시스템 프롬프트 파일을 봇으로 일괄 생성하는 스크립트.
# - 봇 이름: 파일명에서 .md 제거
# - 설명: 파일의 첫 # 헤딩 텍스트
# - 태그: ["가정연합", "축복"] + 파일명 prefix(예: agy, codex, gemini, opus, default, prompt-ver)
# - LLM 모델: gemini-3.1-flash-lite (사용자 지정, 전 봇 통일)
# - 시스템 프롬프트: 파일 내용 전체

set -euo pipefail

API="${API:-http://localhost:8080/api/v1/admin/bots}"
DIR="$(cd "$(dirname "$0")" && pwd)"

# jq 가 없으면 도커 안 python 으로 JSON 인코딩
if ! command -v jq >/dev/null 2>&1; then
  echo "jq 미설치 → docker exec python 으로 인코딩합니다." >&2
fi

encode_json() {
  # stdin 의 텍스트를 JSON 문자열로 안전하게 인코딩
  python3 -c 'import sys, json; sys.stdout.write(json.dumps(sys.stdin.read()))'
}

prefix_tag() {
  local stem="$1"
  case "$stem" in
    agy_*)         echo "agy" ;;
    codex_*|codex) echo "codex" ;;
    gemini_*)      echo "gemini" ;;
    opus_*|opus*)  echo "opus" ;;
    default)       echo "default" ;;
    prompt-ver*)   echo "prompt-ver" ;;
    *)             echo "etc" ;;
  esac
}

total=0
ok=0
for f in "$DIR"/*.md; do
  total=$((total+1))
  stem="$(basename "$f" .md)"
  # 첫 # 헤딩 → 설명 (없으면 stem 그대로)
  desc="$(grep -m1 -E '^# ' "$f" | sed -E 's/^#\s+//' || true)"
  [ -z "$desc" ] && desc="$stem"
  tag2="$(prefix_tag "$stem")"

  # JSON 본문 조립
  name_json=$(printf '%s' "$stem" | encode_json)
  desc_json=$(printf '%s' "$desc" | encode_json)
  prompt_json=$(encode_json <"$f")
  tag2_json=$(printf '%s' "$tag2" | encode_json)

  body="{\"name\":${name_json},\"description\":${desc_json},\"tags\":[\"가정연합\",\"축복\",${tag2_json}],\"is_new\":true,\"llm_model\":\"gemini-3.1-flash-lite\",\"system_prompt\":${prompt_json}}"

  code=$(curl -s -o /tmp/seed_resp.json -w "%{http_code}" \
    -X POST "$API" -H "Content-Type: application/json" -d "$body")

  if [ "$code" = "201" ]; then
    ok=$((ok+1))
    id=$(python3 -c 'import json,sys; print(json.load(open("/tmp/seed_resp.json"))["id"])')
    printf "  [%2d/%2d] ✓ id=%s  name=%s\n" "$total" 14 "$id" "$stem"
  else
    printf "  [%2d/%2d] ✗ HTTP %s  name=%s\n" "$total" 14 "$code" "$stem" >&2
    cat /tmp/seed_resp.json >&2; echo >&2
  fi
done

echo
echo "완료: $ok / $total"
