"use client"

// Gems 관리자 — 빌더 / 프롬프트 생성 / 비교 3탭 셸.
import * as React from "react"
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
          <h1 className="text-2xl font-semibold">Gems</h1>
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
