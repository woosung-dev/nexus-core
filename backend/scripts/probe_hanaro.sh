#!/usr/bin/env bash
# 하나로 공직자판별 API v1/v2 를 동일 키·계정으로 호출해 응답을 비교하는 진단 스크립트
#
# 사용법:
#   bash backend/scripts/probe_hanaro.sh                      # backend/.env 의 키 사용
#   OFFICIAL_CHECK_KEY=새키 bash backend/scripts/probe_hanaro.sh   # 새 키로 테스트
#   USERID=someid PASSWORD=somepw bash backend/scripts/probe_hanaro.sh
#
# 규격서: 공직자 판별 API 규격서 v2 (2026-07-16) 2·3·4장

set -uo pipefail

ENV_FILE="${ENV_FILE:-$(dirname "$0")/../.env}"

# 키는 인자 > 환경변수 > backend/.env 순으로 찾는다
if [ -z "${OFFICIAL_CHECK_KEY:-}" ] && [ -f "$ENV_FILE" ]; then
  OFFICIAL_CHECK_KEY="$(sed -n 's/^OFFICIAL_CHECK_KEY=//p' "$ENV_FILE" | head -1)"
fi

if [ -z "${OFFICIAL_CHECK_KEY:-}" ]; then
  echo "OFFICIAL_CHECK_KEY 를 찾지 못했습니다. 환경변수로 넘기거나 $ENV_FILE 에 설정하세요." >&2
  exit 1
fi

USERID="${USERID:-kjl51555}"
PASSWORD="${PASSWORD:-qaz123!!}"

V2="https://hanaro.ffwp.or.kr/API_kim/officialLoginCheck2"
V1="https://hanaro.ffwp.or.kr/API_kim/officialLoginCheck"

echo "보낸 키: ${#OFFICIAL_CHECK_KEY}자 (값은 출력하지 않음)"
echo "보낸 userid: $USERID"
echo

for URL in "$V2" "$V1"; do
  echo "=== $URL"
  curl -sS -i -X POST "$URL" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "keyValue=$OFFICIAL_CHECK_KEY" \
    --data-urlencode "userid=$USERID" \
    --data-urlencode "password=$PASSWORD" \
    | grep -iE '^(HTTP/|date:|content-type:|server:)|^\{'
  echo
done

echo "판정 기준 (규격서 4장)"
echo "  {\"authenticated\":true,...}                → 키·계정 모두 정상"
echo "  {\"error\":\"invalid_key\"}                   → 그 주소에 대해 키가 유효하지 않음"
echo "  {\"error\":\"missing_parameter\"}             → 요청 파라미터 누락 (이 스크립트에선 나올 수 없음)"
echo "  HTTP 429                                   → 아이디당 실패 15회 누적, 5분 후 해제"
