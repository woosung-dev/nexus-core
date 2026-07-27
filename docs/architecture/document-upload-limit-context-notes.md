# 문서 업로드 한도 결정 기록

- 2026-07-27. API 오류 메시지는 FastAPI의 `MAX_UPLOAD_SIZE_MB` 검증에서 생성됐다. Google File Search 호출 전의 서버 측 제한이다.
- 2026-07-27. Google File Search의 문서당 상한 100MB보다 낮은 운영 한도 50MB로 서버와 관리자 화면을 통일했다.
- 2026-07-27. Vercel 외부 rewrite를 통한 실제 대용량 업로드는 코드 테스트 범위 밖이므로 배포 뒤 확인한다.
- 2026-07-27. 백엔드 `uv run pytest` 76건과 관리자 화면 `pnpm lint`를 통과했다.
