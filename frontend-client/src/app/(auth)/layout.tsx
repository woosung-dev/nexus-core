// 이미 로그인한 사용자가 로그인 페이지로 오면 메인으로 돌린다

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE } from "@/lib/session";

export default async function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();

  if (cookieStore.get(SESSION_COOKIE)?.value) {
    redirect("/");
  }

  return <>{children}</>;
}
