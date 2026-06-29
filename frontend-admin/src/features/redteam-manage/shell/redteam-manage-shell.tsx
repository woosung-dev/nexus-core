"use client"

// 중간보고 입력관리 전용 셸 — 기존 /redteam 셸과 분리. 상단 탭(입력관리·비교·미분류·요약) + 테마 토글.
import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { ClipboardList, Moon, Sun } from "lucide-react"
import { cn } from "@/lib/utils"

const THEME_KEY = "redteam-manage.colorScheme"

const TABS = [
  { href: "/redteam-manage", label: "입력관리" },
  { href: "/redteam-manage/compare", label: "비교" },
  { href: "/redteam-manage/unmatched", label: "미분류 큐" },
  { href: "/redteam-manage/summary", label: "중간보고 요약" },
]

export function RedteamManageShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [dark, setDark] = React.useState(false)
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    const saved = localStorage.getItem(THEME_KEY)
    setDark(saved === "dark")
    setMounted(true)
  }, [])

  const toggle = () => {
    setDark((d) => {
      const next = !d
      localStorage.setItem(THEME_KEY, next ? "dark" : "light")
      return next
    })
  }

  return (
    <div className={cn("rtm-theme min-h-dvh", dark && "dark")}>
      <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur print:hidden">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-6">
          <Link href="/redteam-manage" className="flex items-center gap-2.5">
            <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <ClipboardList className="size-5" />
            </span>
            <span className="flex flex-col leading-none">
              <span className="rtm-display text-[15px] tracking-tight">중간보고 입력관리</span>
              <span className="text-[11px] text-muted-foreground">축복·가정관리 AI 챗봇 · 레드팀 피드백</span>
            </span>
          </Link>

          <nav className="ml-4 flex items-center gap-1">
            {TABS.map((tab) => {
              const active =
                tab.href === "/redteam-manage"
                  ? pathname === "/redteam-manage"
                  : pathname.startsWith(tab.href)
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  className={cn(
                    "rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors",
                    active
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                  )}
                >
                  {tab.label}
                </Link>
              )
            })}
          </nav>

          <button
            onClick={toggle}
            className="ml-auto flex size-9 items-center justify-center rounded-lg border border-border text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            title={dark ? "라이트 모드" : "다크 모드"}
            aria-label="테마 전환"
          >
            {mounted && dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
        </div>
      </header>

      <main>{children}</main>
    </div>
  )
}
