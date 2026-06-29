"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { CircleUser, ClipboardList, ExternalLink, Menu, ShieldCheck } from "lucide-react"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet"
import { AdminSidebar } from "./admin-sidebar"

function generateBreadcrumbLabel(pathname: string) {
  if (pathname.includes("/dashboard")) return "Dashboard"
  if (pathname.includes("/bots")) return "Bots"
  if (pathname.includes("/faqs")) return "FAQs"
  if (pathname.includes("/documents")) return "Documents"
  if (pathname.includes("/users")) return "Users"
  if (pathname.includes("/settings")) return "Settings"
  return "Home"
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

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full">
              <CircleUser className="h-5 w-5" />
              <span className="sr-only">Toggle user menu</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Admin Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Settings</DropdownMenuItem>
            <DropdownMenuItem>Logout</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
