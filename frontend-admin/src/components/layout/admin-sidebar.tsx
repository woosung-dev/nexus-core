"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Bot,
  Box,
  Inbox,
  LayoutDashboard,
  MessageSquare,
  Network,
  ShieldAlert,
  Sparkles,
  Users,
} from "lucide-react"

/**
 * 메뉴 이름의 단일 출처 — 헤더 브레드크럼이 이 배열을 그대로 읽는다.
 *
 * 묶는 축은 **일하는 순서**다. 「운영」 세 화면이 하루치 루프고(무슨 일이 있었나 →
 * 뭘 못 했나 → 뭘 채웠나), 「봇」은 그 결과를 반영하는 설정, 「계정」은 나머지다.
 *
 * 봇을 골라야만 쓸 수 있던 문서·지정 답변은 최상위에서 빠지고 봇 상세 탭으로 들어간다.
 */
export const NAV_GROUPS = [
  {
    group: null,
    items: [
      { title: "대시보드", url: "/dashboard", icon: LayoutDashboard, exact: true },
    ],
  },
  {
    group: "운영",
    items: [
      { title: "대화 기록", url: "/chats", icon: MessageSquare },
      { title: "못 답한 질문", url: "/unanswered", icon: Inbox },
      { title: "운영 사실", url: "/ops-facts", icon: ShieldAlert },
    ],
  },
  {
    group: "봇",
    items: [
      { title: "봇 목록", url: "/bots", icon: Bot },
      { title: "프롬프트 작성", url: "/instructions", icon: Sparkles },
      { title: "지식 위키", url: "/wiki", icon: Network },
    ],
  },
  {
    group: "계정",
    items: [{ title: "사용자", url: "/users", icon: Users }],
  },
] as const

export const NAV_ITEMS = NAV_GROUPS.flatMap((g) =>
  g.items.map((item) => ({ ...item, group: g.group }))
)

/** `/bots` 는 `/bots/new` 에서까지 활성으로 잡히면 안 되지만, 상세는 봇 목록에 속한다. */
export function isNavActive(pathname: string, url: string) {
  return pathname === url || pathname.startsWith(`${url}/`)
}

export function AdminSidebar({ className }: { className?: string }) {
  const pathname = usePathname()

  return (
    <div
      className={`flex h-full flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground ${className ?? ""}`}
    >
      <div className="flex h-16 shrink-0 items-center border-b border-sidebar-border bg-sidebar px-6 font-semibold">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
            <Box className="size-4" />
          </div>
          <span>Nexus</span>
        </Link>
      </div>

      <nav className="flex-1 overflow-auto bg-sidebar px-3 py-4">
        {NAV_GROUPS.map((group, index) => (
          <div key={group.group ?? "top"} className={index > 0 ? "mt-5" : undefined}>
            {group.group ? (
              <p className="mb-1.5 px-2 text-2xs font-semibold tracking-wide text-muted-foreground">
                {group.group}
              </p>
            ) : null}
            <div className="grid gap-0.5">
              {group.items.map((item) => {
                const active = isNavActive(pathname, item.url)
                return (
                  <Link
                    key={item.url}
                    href={item.url}
                    aria-current={active ? "page" : undefined}
                    className={`flex h-8 items-center gap-2.5 rounded-md px-2 text-sm font-medium transition-colors ${
                      active
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
                    }`}
                  >
                    <item.icon className="size-4 shrink-0" aria-hidden />
                    {item.title}
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>
    </div>
  )
}
