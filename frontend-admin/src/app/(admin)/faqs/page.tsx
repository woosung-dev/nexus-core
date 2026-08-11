import { redirect } from "next/navigation"

/** 지정 답변(FAQ)은 봇 상세 「지정 답변」 탭으로 들어갔다. 북마크용으로만 남긴다. */
export default function FaqsPage() {
  redirect("/bots")
}
