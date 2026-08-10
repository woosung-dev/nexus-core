"use client"

/**
 * 처리 경로 선택 — 관리자가 「어느 트랙의 일인가」를 찍는다.
 *
 * 색만으로 뜻을 전하지 않는다(WCAG). 아이콘 + 한글 라벨이 항상 함께 간다.
 */
import { Ban, CircleHelp, FileX, SearchX, TriangleAlert } from "lucide-react"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import { TRIAGE_ACTION, TRIAGE_LABEL, TRIAGE_ORDER } from "../constants"
import type { UnansweredTriage } from "../types"

const TRIAGE_ICON: Record<UnansweredTriage, typeof CircleHelp> = {
  미분류: CircleHelp,
  문서없음: FileX,
  검색못함: SearchX,
  문서오류: TriangleAlert,
  해당없음: Ban,
}

export function TriageIcon({
  triage,
  className = "size-3.5",
}: {
  triage: UnansweredTriage
  className?: string
}) {
  const Icon = TRIAGE_ICON[triage]
  return <Icon className={className} aria-hidden />
}

export function TriageSelect({
  value,
  onChange,
  disabled,
}: {
  value: UnansweredTriage
  onChange: (next: UnansweredTriage) => void
  disabled?: boolean
}) {
  return (
    <Select
      value={value}
      onValueChange={(next) => onChange(next as UnansweredTriage)}
      disabled={disabled}
    >
      {/* 트리거에는 라벨만 보인다. `SelectValue` 는 고른 항목의 자식을 그대로 되비추므로
          설명까지 딸려 들어온다("문서가 틀림·낡음— 운영 사실로 덮는다"). 직접 그린다. */}
      <SelectTrigger className="h-8 w-[190px] text-xs" aria-label="처리 경로">
        <SelectValue asChild>
          <span className="flex items-center gap-1.5">
            <TriageIcon triage={value} />
            {TRIAGE_LABEL[value]}
          </span>
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {TRIAGE_ORDER.map((triage) => (
          <SelectItem key={triage} value={triage} className="text-xs">
            <span className="flex items-center gap-2">
              <TriageIcon triage={triage} />
              <span>{TRIAGE_LABEL[triage]}</span>
              <span className="text-muted-foreground">— {TRIAGE_ACTION[triage]}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
