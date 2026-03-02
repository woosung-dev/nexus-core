import { BotForm } from "@/features/bots/components/bot-form"

export default function NewBotPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">새 봇 만들기</h1>
        <p className="text-muted-foreground">
          새로운 AI 챗봇을 생성하고 시스템 프롬프트를 설정합니다.
        </p>
      </div>
      <BotForm />
    </div>
  )
}
