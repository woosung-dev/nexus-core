"use client"

// 입력관리 편집 칸 — 상태/레벨/분류/담당자/태그/모범답변. 셀렉트·태그는 즉시 저장, 텍스트는 blur·버튼 저장.
import * as React from "react"
import { Check, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { DISPOSITION_OPTIONS, LEVEL_OPTIONS, STATUS_OPTIONS } from "../constants"
import { useUpdateGroupManage } from "../hooks"
import type { ManageGroupDetail, ManageStatus, Disposition } from "../types"
import { TagInput } from "./tag-input"

const LEVEL_NONE = "__none__"

export function ManageFields({ detail }: { detail: ManageGroupDetail }) {
  const update = useUpdateGroupManage(detail.id)

  // 텍스트 필드는 로컬 상태로 관리 (그룹 전환 시 부모가 key로 remount)
  const [assignee, setAssignee] = React.useState(detail.assignee ?? "")
  const [modelAnswer, setModelAnswer] = React.useState(detail.model_answer)

  const assigneeDirty = assignee.trim() !== (detail.assignee ?? "")
  const modelDirty = modelAnswer !== detail.model_answer

  const saveAssignee = () => {
    if (!assigneeDirty) return
    update.mutate({ assignee: assignee.trim() || null })
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">입력관리</h3>
        {update.isPending && (
          <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <Loader2 className="size-3 animate-spin" /> 저장 중
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {/* 상태 */}
        <div className="flex flex-col gap-1.5">
          <Label className="text-[11px] text-muted-foreground">검증 상태</Label>
          <Select
            value={detail.status}
            onValueChange={(v) => update.mutate({ status: v as ManageStatus })}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 레벨 */}
        <div className="flex flex-col gap-1.5">
          <Label className="text-[11px] text-muted-foreground">보완 레벨</Label>
          <Select
            value={detail.level == null ? LEVEL_NONE : String(detail.level)}
            onValueChange={(v) =>
              update.mutate({ level: v === LEVEL_NONE ? null : Number(v) })
            }
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={LEVEL_NONE}>미분류</SelectItem>
              {LEVEL_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={String(o.value)}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 분류 */}
        <div className="flex flex-col gap-1.5">
          <Label className="text-[11px] text-muted-foreground">처리 분류</Label>
          <Select
            value={detail.disposition}
            onValueChange={(v) => update.mutate({ disposition: v as Disposition })}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DISPOSITION_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 담당자 */}
      <div className="flex flex-col gap-1.5">
        <Label className="text-[11px] text-muted-foreground">담당자</Label>
        <div className="flex items-center gap-2">
          <Input
            value={assignee}
            onChange={(e) => setAssignee(e.target.value)}
            onBlur={saveAssignee}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault()
                saveAssignee()
              }
            }}
            placeholder="담당자 이름"
            className="h-8 max-w-xs text-xs"
          />
          {assigneeDirty && (
            <Button variant="outline" size="sm" className="h-8 px-2 text-xs" onClick={saveAssignee}>
              저장
            </Button>
          )}
        </div>
      </div>

      {/* 태그 */}
      <div className="flex flex-col gap-1.5">
        <Label className="text-[11px] text-muted-foreground">피드백 유형 태그</Label>
        <TagInput tags={detail.tags} onChange={(next) => update.mutate({ tags: next })} />
      </div>

      {/* 모범답변 */}
      <div className="flex flex-col gap-1.5">
        <Label className="text-[11px] text-muted-foreground">모범답변 (그룹 확정)</Label>
        <Textarea
          value={modelAnswer}
          onChange={(e) => setModelAnswer(e.target.value)}
          placeholder="이 질문에 대한 확정 모범답변을 작성합니다. (리뷰어별 옳은 답변은 아래 참고)"
          className="min-h-28 text-sm"
        />
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            className="h-8"
            disabled={!modelDirty || update.isPending}
            onClick={() => update.mutate({ model_answer: modelAnswer })}
          >
            {update.isPending ? <Loader2 className="size-3 animate-spin" /> : null}
            모범답변 저장
          </Button>
          {!modelDirty && detail.model_answer && (
            <span className="flex items-center gap-1 text-[11px] text-emerald-600">
              <Check className="size-3" /> 저장됨
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
