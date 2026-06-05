"use client"

// 봇 상세 — 카카오 채널(오픈빌더 bot.id) 등록/삭제 섹션 (자체 완결)
import * as React from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  useCreateKakaoChannel,
  useDeleteKakaoChannel,
  useKakaoChannels,
} from "../hooks"

export function KakaoChannelSection({ botId }: { botId: number }) {
  const { data } = useKakaoChannels(botId)
  const create = useCreateKakaoChannel(botId)
  const remove = useDeleteKakaoChannel(botId)
  const [value, setValue] = React.useState("")

  const onAdd = async () => {
    const v = value.trim()
    if (!v) return
    await create.mutateAsync(v)
    setValue("")
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
        <div className="flex gap-2">
          <Input
            placeholder="오픈빌더 bot.id (예: 5f1a2b3c...)"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          <Button type="button" onClick={onAdd} disabled={create.isPending}>
            등록
          </Button>
        </div>
        <ul className="space-y-2">
          {data?.items.map((ch) => (
            <li
              key={ch.id}
              className="flex items-center justify-between rounded-md border px-3 py-2"
            >
              <span className="font-mono text-sm">{ch.kakao_bot_id}</span>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={() => remove.mutate(ch.id)}
                disabled={remove.isPending}
              >
                삭제
              </Button>
            </li>
          ))}
          {data && data.items.length === 0 && (
            <li className="text-sm text-muted-foreground">
              등록된 카카오 채널이 없습니다.
            </li>
          )}
        </ul>
      </CardContent>
    </Card>
  )
}
