// 로그인하지 않은 접근을 로그인 페이지로 돌린다 (세션 쿠키 기준)

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE } from "@/lib/session";

export default async function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();

  if (!cookieStore.get(SESSION_COOKIE)?.value) {
    redirect("/login");
  }

  return <>{children}</>;
}
