import { AdminSidebar } from "@/components/layout/admin-sidebar"
import { AdminHeader } from "@/components/layout/admin-header"
import { Toaster } from "@/components/ui/sonner"

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <>
      <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr] bg-muted/20">
        <div className="hidden md:block">
          <AdminSidebar />
        </div>
        <div className="flex flex-col min-w-0">
          <AdminHeader />
          <main className="flex-1 overflow-auto p-4 lg:p-6">
            {children}
          </main>
        </div>
      </div>
      {/* 그리드 자식으로 두면 토스트가 사이드바 칸(280px)에 갇혀 화면 밖에 그려진다 —
          실측 box=0,1094,280,0. 성공·실패 알림이 아무에게도 안 보이고 있었다. */}
      <Toaster />
    </>
  )
}
