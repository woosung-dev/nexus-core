"use client"

// 레드팀·입력관리 셸의 조회 실패 표시.
//
// 이 두 그룹은 화면 전체가 `isLoading || !data` 로 되어 있어, 서버가 죽으면
// 스켈레톤이 영원히 남았다 — 사용자에게는 무한 로딩으로 보인다.
// admin 셸의 ErrorState 와 달리 여기는 자체 테마(.rt-theme/.rtm-theme)라
// 토큰만 쓰고 색은 각 셸이 정한 값을 따른다.
export function LoadFailed({
  title = "불러오지 못했습니다",
  onRetry,
}: {
  title?: string
  onRetry?: () => void
}) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-destructive/40 bg-destructive/5 px-6 py-10 text-center"
    >
      <p className="text-sm font-semibold text-destructive">{title}</p>
      <p className="mt-1 text-xs text-muted-foreground">
        서버 응답이 없습니다. 잠시 후 다시 시도해 주세요.
      </p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-accent"
        >
          다시 시도
        </button>
      ) : null}
    </div>
  )
}
