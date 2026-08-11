import { redirect } from "next/navigation"

/**
 * 문서 관리는 봇 상세 「자료」 탭으로 들어갔다. 봇을 골라야만 쓸 수 있는 화면이
 * 최상위 메뉴에 있어서, 매번 어느 봇인지 다시 지정해야 했다.
 *
 * 북마크가 있을 수 있어 경로는 남겨 두고 봇 목록으로 보낸다.
 */
export default function DocumentsPage() {
  redirect("/bots")
}
