"use client";

// 하나로 SSO 단독 로그인 폼 — 이메일·소셜 로그인은 제공하지 않는다

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Loader2 } from "lucide-react";

export function LoginForm() {
  const router = useRouter();
  const [userid, setUserid] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userid, password }),
      });

      if (!res.ok) {
        // 자격증명 문제와 서버 문제를 구분한다. 뭉치면 사용자가 원인을 오해한다.
        if (res.status === 401) {
          setError("아이디 또는 비밀번호가 올바르지 않습니다.");
        } else if (res.status === 429) {
          setError("로그인 시도가 너무 많습니다. 약 5분 후 다시 시도해 주세요.");
        } else if (res.status === 403) {
          setError("비활성화된 계정입니다. 관리자에게 문의해 주세요.");
        } else {
          setError("로그인 서버에 문제가 있습니다. 관리자에게 문의해 주세요.");
        }
        return;
      }

      // 미들웨어가 보호 경로에서 붙여준 원래 목적지로 되돌린다.
      const redirect = new URLSearchParams(window.location.search).get("redirect_url");
      router.push(redirect && redirect.startsWith("/") ? redirect : "/");
      router.refresh();
    } catch {
      setError("로그인 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md bg-white/90 backdrop-blur-xl border border-amber-100 shadow-xl shadow-amber-500/5 relative overflow-hidden">
      {/* Subtle Glow Effect */}
      <div className="absolute -top-24 -left-24 w-48 h-48 bg-amber-500/10 rounded-full blur-[80px] pointer-events-none" />
      <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-amber-500/10 rounded-full blur-[80px] pointer-events-none" />

      <CardHeader className="space-y-1 pb-6 z-10 relative">
        <CardTitle className="text-3xl font-bold tracking-tight text-center text-zinc-900">
          Welcome back
        </CardTitle>
        <CardDescription className="text-center text-zinc-500 w-full">
          하나로 SSO 계정으로 로그인하세요.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4 z-10 relative pb-8">
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="userid" className="text-zinc-700 font-medium">
              하나로 아이디
            </Label>
            <Input
              id="userid"
              type="text"
              placeholder="하나로 SSO 아이디"
              value={userid}
              onChange={(e) => setUserid(e.target.value)}
              required
              autoComplete="username"
              disabled={isLoading}
              className="bg-zinc-50 border-zinc-200 text-zinc-900 focus-visible:ring-amber-500/30 focus-visible:border-amber-400 transition-all h-12 shadow-sm"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-zinc-700 font-medium">
              비밀번호
            </Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              disabled={isLoading}
              className="bg-zinc-50 border-zinc-200 text-zinc-900 focus-visible:ring-amber-500/30 focus-visible:border-amber-400 transition-all h-12 shadow-sm"
            />
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full h-12 bg-amber-500 hover:bg-amber-600 text-white font-bold text-md mt-6 transition-all shadow-md shadow-amber-500/20 hover:shadow-lg hover:shadow-amber-500/30"
          >
            {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : "로그인"}
          </Button>
        </form>

        <p className="text-center text-sm text-zinc-500 pt-2">
          하나로 계정 문의는 소속 기관 담당자에게 연락해 주세요.
        </p>
      </CardContent>
    </Card>
  );
}
