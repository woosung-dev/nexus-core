"use client"

// 작성 중인 지침을 실제 RAG 파이프라인으로 미리 보는 테스트 패널.
import * as React from "react"
import { Loader2, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { MessageCitations } from "@/features/chats/components/MessageCitations"
import { MessageFollowups } from "@/features/chats/components/MessageFollowups"
import { usePreviewInstruction } from "../hooks"
import type { Citation } from "../types"

type TestMessage = {
  role: "user" | "assistant"
  content: string
  citations?: Citation[]
  followups?: string[]
  error?: boolean
}

type TestPanelProps = {
  systemPrompt: string
  botId: number | null
  llm_model: string
}

export function TestPanel({ systemPrompt, botId, llm_model }: TestPanelProps) {
  const [useRag, setUseRag] = React.useState(true)
  const [messages, setMessages] = React.useState<TestMessage[]>([])
  const [input, setInput] = React.useState("")
  const preview = usePreviewInstruction()

  function send(message: string, appendUser = true) {
    const trimmed = message.trim()
    if (!trimmed || preview.isPending) return
    if (appendUser) setMessages((current) => [...current, { role: "user", content: trimmed }])
    setInput("")
    preview.mutate(
      {
        system_prompt: systemPrompt,
        message: trimmed,
        bot_id: botId,
        use_rag: useRag,
        llm_model,
      },
      {
        onSuccess: (result) => setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: result.answer,
            citations: result.citations,
            followups: result.followups,
          },
        ]),
        onError: () => setMessages((current) => [
          ...current,
          { role: "assistant", content: "응답 생성 실패", error: true },
        ]),
      }
    )
  }

  const lastUserMessage = [...messages].reverse().find((message) => message.role === "user")?.content

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Switch id="use-rag" checked={useRag} onCheckedChange={setUseRag} />
          <Label htmlFor="use-rag">RAG 사용</Label>
        </div>
        {botId === null && <span className="text-xs text-muted-foreground">봇 미선택 시 RAG 없이 지침만으로 테스트합니다.</span>}
      </div>
      <div className="min-h-[360px] space-y-3 rounded-lg border bg-muted/20 p-4">
        {messages.length === 0 && !preview.isPending && (
          <div className="rounded-md border bg-background p-4 text-sm text-muted-foreground">
            왼쪽에서 지침을 작성하고, 여기서 바로 테스트해 보세요.
          </div>
        )}
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={message.role === "user" ? "ml-auto max-w-[85%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground" : "mr-auto max-w-[95%] rounded-lg border bg-background px-3 py-2 text-sm"}>
            <p className={message.error ? "text-destructive" : "whitespace-pre-wrap"}>{message.content}</p>
            {message.error && lastUserMessage && (
              <Button type="button" variant="outline" size="sm" className="mt-2" onClick={() => send(lastUserMessage, false)}>
                다시 시도
              </Button>
            )}
            {message.role === "assistant" && !message.error && (
              <>
                <MessageCitations citations={message.citations} />
                <MessageFollowups items={message.followups} />
              </>
            )}
          </div>
        ))}
        {preview.isPending && (
          <div className="mr-auto max-w-[95%] rounded-lg border bg-background px-3 py-2 text-sm motion-safe:animate-pulse">
            <Loader2 className="mr-2 inline size-4 animate-spin" />
            답변 생성 중… (RAG 검색은 최대 12초 걸릴 수 있어요)
          </div>
        )}
      </div>
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          send(input)
        }}
      >
        <div className="min-w-0 flex-1 space-y-1">
          <Label htmlFor="instruction-test-message" className="text-xs">테스트 질문</Label>
          <Input id="instruction-test-message" value={input} onChange={(event) => setInput(event.target.value)} placeholder="테스트할 질문을 입력하세요" disabled={preview.isPending} />
        </div>
        <Button type="submit" size="icon" disabled={preview.isPending || !input.trim()} aria-label="전송">
          <Send />
        </Button>
      </form>
    </div>
  )
}
