"use client"

/**
 * 봇 선택 콤보박스 컴포넌트.
 * 봇 목록을 가져와 사용자가 문서를 관리할 봇을 선택할 수 있게 한다.
 */
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useBots } from "@/features/bots/hooks"

interface BotSelectorProps {
  selectedBotId: number | null
  onSelect: (botId: number) => void
}

export function BotSelector({ selectedBotId, onSelect }: BotSelectorProps) {
  const { data, isLoading } = useBots()
  const bots = data?.bots ?? []

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium">봇 선택</label>
      <Select
        value={selectedBotId ? String(selectedBotId) : ""}
        onValueChange={(val) => onSelect(Number(val))}
        disabled={isLoading}
      >
        <SelectTrigger className="w-72">
          <SelectValue placeholder={isLoading ? "봇 목록 불러오는 중..." : "관리할 봇을 선택하세요"} />
        </SelectTrigger>
        <SelectContent>
          {bots.map((bot) => (
            <SelectItem key={bot.id} value={String(bot.id)}>
              {bot.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
