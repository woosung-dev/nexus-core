"""라이브(Neon) 접속 문자열을 `backend/.env` 에서 읽는다. **코드에 박지 마라.**

측정 스크립트 넷이 이 값을 평문으로 갖고 있었다(2026-08-18, PR #73 리뷰에서 발견).
`/exports` 가 gitignore 라 push 는 안 됐지만, 측정 도구를 git 에 남기기로 하면서
그 우연한 방어막이 사라졌다. 여기로 모은다.

**왜 `os.getenv` 가 아닌가.** `exports/` 스크립트는 앱 밖에서 도는 standalone 이라
`.env` 가 프로세스 환경에 안 올라온다. 그리고 라이브 DSN 은 `.env` 에 **주석 줄**로
들어 있다 — 활성 줄은 로컬 docker 다. 그래서 `neon.tech` 로 골라야 한다.

    from _neon import neon_url          # exports/ 바로 아래 스크립트
    conn = await asyncpg.connect(neon_url())

한 단계 깊은 디렉터리에서는 경로를 먼저 넣는다:

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

⚠ **라이브는 읽기 전용으로만 써라.** 쓰기는 관리자 화면·ORM 을 거쳐야 한다 —
`psql`·`asyncpg` 로 `bots` 를 고치면 `updated_at` 이 안 움직여 이력이 안 남는다.
"""

from __future__ import annotations

from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"


def neon_url(*, asyncpg: bool = False) -> str:
    """라이브 DSN. `asyncpg=True` 면 SQLAlchemy 용 `+asyncpg` 형식으로 준다."""
    env_path = BACKEND / ".env"
    try:
        env = env_path.read_text(encoding="utf-8")
    except OSError as e:
        raise SystemExit(f"{env_path} 를 못 읽는다: {e}")

    for line in env.splitlines():
        if "neon.tech" not in line or "DATABASE_URL" not in line:
            continue
        # `split` 이 주석 줄 앞의 `# ` 를 같이 떨군다.
        url = line.split("DATABASE_URL=", 1)[1].strip()
        if asyncpg:
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return (
            url.replace("postgresql+asyncpg://", "postgresql://")
            .replace("?ssl=require", "?sslmode=require")
        )
    raise SystemExit(f"라이브 DATABASE_URL 미발견: {env_path}")
