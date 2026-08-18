"""추적 대상 파일에 크리덴셜이 박혀 있는지 검사한다. 의존성 없음.

**왜 필요한가.** 지금까지 `.gitignore` 의 `/exports` 가 **우연히** 방어막이었다.
그 디렉터리에 키가 평문으로 박힌 스크립트가 넷 있었는데 ignore 덕에 push 가 안 됐다.
측정 도구를 git 에 남기면서 그 방어막을 걷었으므로 대체가 필요하다.

**GitHub push protection 으로는 부족하다 — 실증됐다.**

    OpenAI  sk-proj-…        ✅ 막았다
    Gemini  AIzaSy…          ❌ 못 잡았다 (손으로 전수 검사해서 찾음)
    Neon    postgresql://…   ❌ 못 잡았다 (PR #73 리뷰에서 찾음)

그리고 push protection 은 **push 시점**에 걸린다. 그때는 이미 커밋이 만들어진 뒤라
되돌리려면 이력을 고쳐야 한다. 그래서 pre-commit 훅과 CI 두 군데서 본다.

    python3 scripts/scan_secrets.py                # 추적 파일 전체
    python3 scripts/scan_secrets.py --staged       # staged 만 (pre-commit 훅)
    python3 scripts/scan_secrets.py path/a path/b  # 지정 경로만

**예외를 두는 법.** 문서의 예시처럼 진짜 크리덴셜이 아니면 그 줄에 `secret-scan: ok`
를 적는다. 파일 통째로 빼지 마라 — 그 파일의 다음 줄이 안 보이게 된다.
"""

from __future__ import annotations

import re
import subprocess
import sys

# 값이 실제로 크리덴셜일 때만 걸리도록 길이를 붙였다. `AIzaSy` 같은 접두사만 보면
# 문서·주석의 설명문("AIzaSy… 로 시작하는 키")까지 걸려 자가 무뎌진다.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Google/Gemini API 키", re.compile(r"AIzaSy[A-Za-z0-9_\-]{27,}")),
    ("OpenAI API 키", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{24,}")),
    ("Anthropic API 키", re.compile(r"sk-ant-[A-Za-z0-9_\-]{24,}")),
    ("GitHub 토큰", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}")),
    ("Slack 토큰", re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("AWS 액세스 키", re.compile(r"AKIA[0-9A-Z]{16}")),
    # 비밀번호가 들어간 DB 접속 문자열. 단 **로컬 호스트는 뺀다**(아래 LOCAL_HOST) —
    # `docker-compose.yml` 의 `nexus:nexus@db` 같은 개발 기본값까지 걸면 14건이 오탐으로
    # 뜨고, 그러면 아무도 이 자를 안 본다. 원격 호스트를 가리키는 것만 사고다.
    ("DB 접속 문자열(비밀번호 포함)", re.compile(r"(?:postgres(?:ql)?|mysql|mongodb)(?:\+\w+)?://[^\s:/@\"']+:(?P<pw>[^\s@\"']+)@(?P<host>[^\s:/@\"']+)")),
    ("PEM 개인키", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
]

# 자리표시자는 크리덴셜이 아니다. 이걸 안 빼면 문서마다 걸려 자를 아무도 안 본다.
PLACEHOLDER = re.compile(
    r"REDACTED|EXAMPLE|CHANGEME|YOUR[_-]?|\.{3}|…|\*{3}|<[^>]+>|\$\{|xxx+|여기에|발급받",
    re.I,
)
ALLOW = re.compile(r"secret-scan:\s*ok")

# 개발용 DSN 이 가리키는 호스트. 여기로 가는 접속 문자열은 비밀이 아니다.
LOCAL_HOST = {"localhost", "127.0.0.1", "::1", "db", "postgres", "mysql", "mongo", "host.docker.internal"}

# 문서가 접속 문자열 서식을 보여줄 때 쓰는 말. 비밀번호 자리가 이것이면 예시다.
PLACEHOLDER_PW = {"password", "passwd", "pass", "secret", "changeme", "mypassword", "postgres"}

SKIP_SUFFIX = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".pdf",
    ".xlsx", ".xls", ".zip", ".gz", ".woff", ".woff2", ".ttf", ".otf",
)


def targets(argv: list[str]) -> list[str]:
    if "--staged" in argv:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    elif paths := [a for a in argv if not a.startswith("-")]:
        return paths
    else:
        cmd = ["git", "ls-files"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p]


def main() -> int:
    hits: list[str] = []
    for path in targets(sys.argv[1:]):
        if path.lower().endswith(SKIP_SUFFIX) or path == "scripts/scan_secrets.py":
            continue
        try:
            text = open(path, encoding="utf-8", errors="strict").read()
        except (OSError, UnicodeDecodeError):
            continue  # 바이너리·삭제된 파일
        for lineno, line in enumerate(text.splitlines(), 1):
            if ALLOW.search(line):
                continue
            for label, pat in PATTERNS:
                m = pat.search(line)
                if not m or PLACEHOLDER.search(m.group(0)):
                    continue
                if (m.groupdict().get("host") or "").lower() in LOCAL_HOST:
                    continue
                if (m.groupdict().get("pw") or "").lower() in PLACEHOLDER_PW:
                    continue
                shown = m.group(0)[:12]
                hits.append(f"  {path}:{lineno}  {label}  →  {shown}… (이하 가림)")
                break

    if not hits:
        return 0
    print("⛔ 크리덴셜로 보이는 문자열을 찾았다. 커밋하지 마라.\n")
    print("\n".join(hits))
    print(
        "\n고치는 법: 값을 코드에서 빼고 `backend/.env` 에서 읽어라"
        " (예: `exports/rag_ad_probe_2026-07-02/_fetch_questions.py` 의 `neon_url()`)."
        "\n진짜 크리덴셜이 아니면 그 줄에 `secret-scan: ok` 를 적는다."
        f"\n\n{len(hits)}건."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
