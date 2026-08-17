# 레드팀 v2 자유서술 피드백을 OpenAI 로 (전체 + 테스터별) 봇별 장단점/개선주제 요약
import json
import os
import re

from openai import OpenAI

BASE = "/Users/woosung/project/agy-project/nexus-core/exports"
OPENAI_KEY = os.environ["OPENAI_API_KEY"]

data = json.load(open(f"{BASE}/_redteam_v2_data.json"))
recs = data["records"]
BOT_KEYS = ["통합", "원리", "정밀"]
EMPTY = {b: {"pros": [], "cons": []} for b in BOT_KEYS}

client = OpenAI(api_key=OPENAI_KEY)


def lines_for(records):
    out = []
    for i, r in enumerate(records):
        parts = []
        if r["feedback"]:
            parts.append(f"피드백: {r['feedback']}")
        if r["etc"]:
            parts.append(f"기타: {r['etc']}")
        if not parts:
            continue
        win = r["win"] or r["choice"]
        out.append(f"[{i}] (유형:{r['qtype']}, 선택:{win}) " + " | ".join(parts))
    return out


def call(prompt):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},  # 유효 JSON 보장
    )
    txt = resp.choices[0].message.content.strip()
    txt = re.sub(r"^```(json)?|```$", "", txt, flags=re.MULTILINE).strip()
    return json.loads(txt)


# 1) 전체 요약 (overall + bots + themes)
corpus = "\n".join(lines_for(recs))
print(f"전체 피드백 라인 {len(corpus.splitlines())}건")
overall_prompt = f"""다음은 '가정연합 축복 상담 AI 챗봇' 레드팀 2주차 테스트의 피드백 모음이다.
이번 테스트는 같은 질문에 대해 봇 3종(통합=A, 원리=B, 정밀=C)의 응답을 비교하고 가장 좋은 응답 하나를 고르는 방식이었다.
'선택:'은 그 행에서 테스터가 고른 봇이다(통합/원리/정밀, 또는 복수/무효).

이 피드백들을 분석하여 관리자/클라이언트 보고용으로 정리하라.

요구사항:
1. 봇 3종(통합·원리·정밀) 각각에 대해 테스터들이 언급한 장점(pros)과 아쉬운점(cons)을 각 2~4개 bullet 로 정리. 근거 없는 추측 금지, 피드백에 실제 언급된 내용 위주.
2. 봇 종류와 무관하게 반복적으로 제기된 공통 개선 주제를 5~6개로 그룹핑(themes): 각 주제마다 짧은 제목(title), 한두 문장 설명(desc), 대략 언급 빈도(count, 정수 추정), 대표 의견 인용 1~2개(quotes, 원문 일부).
3. 어떤 봇이 왜 선호/비선호되었는지를 포함한 총평(overall) 3~4문장.

출력은 JSON 하나만. 형식:
{{"overall":"...","bots":{{"통합":{{"pros":["..."],"cons":["..."]}},"원리":{{"pros":[],"cons":[]}},"정밀":{{"pros":[],"cons":[]}}}},"themes":[{{"title":"...","desc":"...","count":N,"quotes":["..."]}}]}}
마크다운/설명 없이 JSON 만.

[피드백 모음]
{corpus}"""
result = call(overall_prompt)
print("전체 요약 완료. 총평:", result.get("overall", "")[:120])

# 2) 테스터별 봇 장단점 요약
by_tester = {}
for t in data["agg"]["testers"]:
    trecs = [r for r in recs if r["user"] == t]
    tlines = lines_for(trecs)
    if not tlines:
        by_tester[t] = json.loads(json.dumps(EMPTY))
        print(f"  [{t}] 피드백 없음")
        continue
    tblock = "\n".join(tlines)
    tprompt = f"""다음은 레드팀 테스터 '{t}'이(가) '가정연합 축복 상담 AI' 봇 비교 테스트에서 남긴 피드백이다.
봇 3종(통합=A, 원리=B, 정밀=C)에 대해, 이 테스터가 실제로 언급한 장점(pros)과 아쉬운점(cons)을 각 1~3개 bullet 로 정리하라.
이 테스터가 언급하지 않은 봇/항목은 빈 배열([])로 둔다. 다른 테스터의 의견이나 일반론을 지어내지 말 것.

출력은 JSON 하나만:
{{"통합":{{"pros":[],"cons":[]}},"원리":{{"pros":[],"cons":[]}},"정밀":{{"pros":[],"cons":[]}}}}
마크다운/설명 없이 JSON 만.

[{t}의 피드백]
{tblock}"""
    try:
        by_tester[t] = call(tprompt)
        print(f"  [{t}] 완료 ({len(tlines)}건)")
    except Exception as e:
        by_tester[t] = json.loads(json.dumps(EMPTY))
        print(f"  [{t}] 실패: {type(e).__name__} {str(e)[:60]}")

result["byTester"] = by_tester
json.dump(result, open(f"{BASE}/_redteam_v2_summary.json", "w"), ensure_ascii=False, indent=1)
print("저장:", f"{BASE}/_redteam_v2_summary.json", "| 테스터별", len(by_tester), "명")
