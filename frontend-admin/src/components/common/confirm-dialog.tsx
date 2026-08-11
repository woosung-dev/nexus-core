"use client"

// 파괴적 작업 확인. 지금까지 브라우저 confirm() 4곳이 이 역할을 했다 — 생김새도
// 포커스 관리도 전부 브라우저에 맡겨져 다른 화면과 따로 놀았다.
//
// **주의**: DropdownMenu 안에서 쓸 때는 이 컴포넌트를 DropdownMenu 의 *형제*로 두고
// open 을 state 로 제어해야 한다. 자식으로 넣으면 메뉴가 닫히면서 같이 언마운트돼
// 다이얼로그가 뜨지 않는다.
import type { ReactNode } from "react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  /** 확인 버튼 글자. 동사로 쓴다 — 「삭제」 「비활성화」 */
  confirmLabel,
  cancelLabel = "취소",
  destructive = true,
  isPending = false,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: ReactNode
  description?: ReactNode
  confirmLabel: string
  cancelLabel?: string
  destructive?: boolean
  isPending?: boolean
  onConfirm: () => void
}) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          {description ? <AlertDialogDescription>{description}</AlertDialogDescription> : null}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending}>{cancelLabel}</AlertDialogCancel>
          <AlertDialogAction
            disabled={isPending}
            onClick={onConfirm}
            className={cn(destructive && buttonVariants({ variant: "destructive" }))}
          >
            {isPending ? "처리 중…" : confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
