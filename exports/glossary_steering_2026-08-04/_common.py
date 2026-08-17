# _map.py · _run.py 공용 — Gemini 호출 백오프와 일일 한도 처리.
#
# 선행 러너(_run.py)는 429 를 전부 같게 다뤄 5회 백오프했다. 일일 한도(500/모델)에 걸린 뒤엔
# 남은 호출마다 5번씩 헛돌아 시간만 버린다(AGENTS.md §3-4). 분당 한도와 일일 한도를 가른다.
import asyncio
import time

TIMEOUT = 180


class DailyQuotaExhausted(RuntimeError):
    """모델당 일일 한도 소진. 모델을 바꾸면 팔 사이 조건이 달라지므로 중단하고 재개한다."""


def is_daily_quota(msg: str) -> bool:
    m = (msg or "").lower()
    return "perday" in m or "per day" in m


async def agenerate(client, model, contents, config, tries=5, label=""):
    """generate_content 1회. (응답, 경과초) 반환. 실패 시 마지막 예외를 올린다."""
    delay = 20
    last: BaseException = RuntimeError(f"{label} 호출 실패 (tries={tries})")
    for attempt in range(tries):
        t0 = time.perf_counter()
        try:
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(model=model, contents=contents, config=config),
                timeout=TIMEOUT)
            return resp, round(time.perf_counter() - t0, 1)
        except (Exception, asyncio.TimeoutError) as e:
            msg = str(e)
            if is_daily_quota(msg):
                raise DailyQuotaExhausted(
                    f"{label} 일일 한도 소진 — 모델 교체 금지(팔 사이 조건 고정). "
                    f"PT 자정 이후 같은 명령으로 재개하면 성공분은 건너뛴다.\n  {msg[:200]}") from e
            last = e
            if attempt == tries - 1:
                break
            await asyncio.sleep(delay if ("503" in msg or "429" in msg) else 5)
            delay = min(int(delay * 1.5), 90)
    raise last
