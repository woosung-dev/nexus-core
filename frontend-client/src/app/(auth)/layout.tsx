import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export default async function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  // 이미 로그인된 유저는 메인으로 리다이렉트
  if (user) {
    redirect("/");
  }

  return <>{children}</>;
}
