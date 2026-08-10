"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ClipboardList, ExternalLink, Menu, ShieldCheck } from "lucide-react"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet"
import { AdminSidebar, NAV_ITEMS } from "./admin-sidebar"

// 사이드바 배열이 이름의 출처다 — 메뉴에 항목을 더하면 브레드크럼도 같이 따라온다.
function generateBreadcrumbLabel(pathname: string) {
  const item = NAV_ITEMS.find((entry) => pathname.startsWith(entry.url))
  return item?.title ?? "Home"
}

export function AdminHeader() {
  const pathname = usePathname()
  const title = generateBreadcrumbLabel(pathname)

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b px-4 bg-background">
      <div className="flex items-center gap-4">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="outline" size="icon" className="md:hidden">
              <Menu className="size-5" />
              <span className="sr-only">Toggle navigation menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-72">
            <SheetTitle className="sr-only">Navigation Menu</SheetTitle>
            <AdminSidebar />
          </SheetContent>
        </Sheet>
        <Breadcrumb className="hidden md:flex">
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/dashboard">Admin</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{title}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>
      <div className="flex items-center gap-2">
        {/* TEMP: 레드팀 심의 진입 (검토 기간 한정 · 종료 후 이 블록 제거) */}
        <Button asChild variant="outline" size="sm" className="h-9 gap-1.5">
          <Link href="/redteam/overview" target="_blank" rel="noopener noreferrer">
            <ShieldCheck className="size-4" />
            <span className="hidden sm:inline">레드팀 심의</span>
            <ExternalLink className="size-3 opacity-60" />
          </Link>
        </Button>

        {/* TEMP: 중간보고 입력관리 진입 (검토 기간 한정 · 종료 후 이 블록 제거) */}
        <Button asChild variant="outline" size="sm" className="h-9 gap-1.5">
          <Link href="/redteam-manage" target="_blank" rel="noopener noreferrer">
            <ClipboardList className="size-4" />
            <span className="hidden sm:inline">입력관리</span>
            <ExternalLink className="size-3 opacity-60" />
          </Link>
        </Button>

      </div>
    </header>
  )
}
