"use client"

// 토스트 표시기. 이 레포에는 성공·실패를 알리는 수단이 없어서 저장이 실패해도
// 화면에 아무 일도 일어나지 않았다(훅 20여 개에 onError 가 0건이었다).
// admin 은 라이트 전용이라 next-themes 없이 고정 테마로 쓴다.
import { Toaster as Sonner } from "sonner"

export function Toaster() {
  return (
    <Sonner
      theme="light"
      position="bottom-right"
      richColors
      closeButton
      toastOptions={{
        // 토큰을 그대로 태워 다른 화면과 같은 곡률·글꼴을 쓰게 한다.
        classNames: {
          toast: "rounded-md font-sans",
        },
      }}
    />
  )
}
