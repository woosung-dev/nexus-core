"use client"

// 봇 상세 — 카카오 채널(오픈빌더 bot.id) 등록/삭제 섹션 (자체 완결)
import * as React from "react"
import { isAxiosError } from "axios"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  useCreateKakaoChannel,
  useDeleteKakaoChannel,
  useKakaoChannels,
} from "../hooks"

export function KakaoChannelSection({ botId }: { botId: number }) {
  const { data, isLoading, isError } = useKakaoChannels(botId)
  const create = useCreateKakaoChannel(botId)
  const remove = useDeleteKakaoChannel(botId)
  const [value, setValue] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const [pendingId, setPendingId] = React.useState<number | null>(null)

  const onAdd = async () => {
    const v = value.trim()
    if (!v) return
    setError(null)
    try {
      await create.mutateAsync(v)
      setValue("")
    } catch (e) {
      const detail =
        isAxiosError(e) && typeof e.response?.data?.message === "string"
          ? e.response.data.message
          : "카카오 채널 등록에 실패했습니다."
      setError(detail)
    }
  }

  const onRemove = (channelId: number) => {
    setPendingId(channelId)
    remove.mutate(channelId, { onSettled: () => setPendingId(null) })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>카카오톡 채널</CardTitle>
        <CardDescription>
          오픈빌더 콜백 요청 본문의 bot.id 를 등록하면 이 봇으로 카카오 메시지를 라우팅합니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label htmlFor="kakao-bot-id">오픈빌더 bot.id</Label>
          <div className="flex gap-2">
            <Input
              id="kakao-bot-id"
              placeholder="예: 5f1a2b3c..."
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault()
                  void onAdd()
                }
              }}
            />
            <Button type="button" onClick={onAdd} disabled={create.isPending}>
              등록
            </Button>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        {isLoading && (
          <p className="text-sm text-muted-foreground">불러오는 중...</p>
        )}
        {isError && (
          <p className="text-sm text-destructive">
            카카오 채널 목록을 불러오지 못했습니다.
          </p>
        )}
        {data && (
          <ul className="space-y-2">
            {data.items.map((ch) => (
              <li
                key={ch.id}
                className="flex items-center justify-between rounded-md border px-3 py-2"
              >
                <span className="font-mono text-sm">{ch.kakao_bot_id}</span>
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => onRemove(ch.id)}
                  disabled={pendingId === ch.id}
                >
                  삭제
                </Button>
              </li>
            ))}
            {data.items.length === 0 && (
              <li className="text-sm text-muted-foreground">
                등록된 카카오 채널이 없습니다.
              </li>
            )}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
