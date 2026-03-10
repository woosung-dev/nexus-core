"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Bot, FileText, HelpCircle, LayoutDashboard, Settings, Users, Box, MessageSquare } from "lucide-react"

const items = [
  { title: "Dashboard", url: "/dashboard", icon: LayoutDashboard },
  { title: "Bots", url: "/bots", icon: Bot },
  { title: "FAQs", url: "/faqs", icon: HelpCircle },
  { title: "Documents", url: "/documents", icon: FileText },
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
          <span>Nexus Core</span>
        </Link>
      </div>
      <div className="flex-1 overflow-auto py-4 bg-sidebar">
        <nav className="grid gap-1 px-4">
          <p className="px-2 text-xs font-semibold uppercase tracking-wider opacity-70 mb-2">Management</p>
          {items.map((item) => {
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
      <div className="p-4 border-t border-sidebar-border bg-sidebar">
        <Link
          href="/settings"
          className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
        >
          <Settings className="size-4" />
          Settings
        </Link>
      </div>
    </div>
  )
}
