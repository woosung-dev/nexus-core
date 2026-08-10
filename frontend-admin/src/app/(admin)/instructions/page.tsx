"use client"

// Gems 관리자 — 빌더 / 프롬프트 생성 / 비교 3탭 셸.
import * as React from "react"
import { AlertTriangle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { GemBuilder } from "@/features/instructions/components/gem-builder"
import { GemGenerate } from "@/features/instructions/components/gem-generate"
import { GemCompare } from "@/features/instructions/components/gem-compare"

const TABS = [
  { key: "builder", label: "빌더" },
  { key: "generate", label: "프롬프트 생성" },
  { key: "compare", label: "비교" },
] as const

type TabKey = (typeof TABS)[number]["key"]

export default function InstructionsPage() {
  const [tab, setTab] = React.useState<TabKey>("builder")

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold">Gems</h1>
            <Badge variant="outline" className="text-[10px] font-normal">작성 도구</Badge>
          </div>
          <p className="mt-1 text-muted-foreground">Gem을 만들고, 그 Gem으로 시스템 프롬프트를 생성하고, 비교로 검증하세요.</p>
        </div>
        <div className="flex w-fit gap-1 self-start rounded-md border p-1">
          {TABS.map((item) => (
            <Button
              key={item.key}
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setTab(item.key)}
              className={cn("whitespace-nowrap px-3", tab === item.key && "bg-muted")}
            >
              {item.label}
            </Button>
          ))}
        </div>
      </div>

      {/* 런타임은 bot_instructions 를 읽지 않는다 — 저장이 곧 적용으로 읽히지 않게 한다. */}
      <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 dark:border-amber-900/40 dark:bg-amber-950/30">
        <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
        <p className="text-[11px] leading-relaxed text-foreground/90">
          여기서 만든 프롬프트는 <b>저장해도 챗봇에 자동으로 적용되지 않습니다.</b>{" "}
          복사해서 <b>봇 → 답변 설정 → 고급 설정 → 시스템 프롬프트</b>에 붙여넣어야 반영됩니다.
        </p>
      </div>

      <div className={cn(tab !== "builder" && "hidden")}>
        <GemBuilder />
      </div>
      <div className={cn(tab !== "generate" && "hidden")}>
        <GemGenerate />
      </div>
      <div className={cn(tab !== "compare" && "hidden")}>
        <GemCompare />
      </div>
    </div>
  )
}
