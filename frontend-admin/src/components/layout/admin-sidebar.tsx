"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Bot, FileText, HelpCircle, Inbox, LayoutDashboard, Users, Box, MessageSquare, Sparkles, ShieldAlert, Network } from "lucide-react"

// 메뉴 이름의 단일 출처 — 헤더 브레드크럼이 이 배열을 그대로 읽는다.
export const NAV_ITEMS = [
  { title: "Dashboard", url: "/dashboard", icon: LayoutDashboard },
  { title: "Bots", url: "/bots", icon: Bot },
  { title: "FAQs", url: "/faqs", icon: HelpCircle },
  { title: "LLM 위키", url: "/wiki", icon: Network },
  // 못 답한 질문 → 운영 사실 순서. 앞 화면이 뒤 화면에 무엇을 채울지 알려 준다.
  { title: "못 답한 질문", url: "/unanswered", icon: Inbox },
  { title: "운영 사실", url: "/ops-facts", icon: ShieldAlert },
  { title: "Documents", url: "/documents", icon: FileText },
  { title: "Gems", url: "/instructions", icon: Sparkles },
  { title: "Chats", url: "/chats", icon: MessageSquare },
  { title: "Users", url: "/users", icon: Users },
]

export function AdminSidebar({ className }: { className?: string }) {
  const pathname = usePathname()

  return (
    <div className={`flex flex-col h-full bg-sidebar text-sidebar-foreground border-r border-sidebar-border ${className}`}>
      <div className="flex h-16 shrink-0 items-center px-6 font-semibold border-b border-sidebar-border bg-sidebar">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
            <Box className="size-4" />
          </div>
          <span>Nexus</span>
        </Link>
      </div>
      <div className="flex-1 overflow-auto py-4 bg-sidebar">
        <nav className="grid gap-1 px-4">
          <p className="px-2 text-xs font-semibold uppercase tracking-wider opacity-70 mb-2">Management</p>
          {NAV_ITEMS.map((item) => {
            const isActive = pathname.startsWith(item.url)
            return (
              <Link
                key={item.title}
                href={item.url}
                className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-sidebar-accent text-sidebar-accent-foreground" : "hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
                }`}
              >
                <item.icon className="size-4" />
                {item.title}
              </Link>
            )
          })}
        </nav>
      </div>
    </div>
  )
}
