"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export function SignupForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreeTerms, setAgreeTerms] = useState<boolean | 'indeterminate'>(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement signup logic
    console.log("Signup with:", { email, password, confirmPassword, agreeTerms });
  };

  return (
    <Card className="w-full max-w-md bg-zinc-950/80 backdrop-blur-xl border-zinc-800 shadow-2xl relative overflow-hidden">
      {/* Subtle Glow Effect */}
      <div className="absolute -top-32 -right-32 w-64 h-64 bg-amber-500/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute -bottom-32 -left-32 w-64 h-64 bg-blue-500/10 rounded-full blur-[100px] pointer-events-none" />

      <CardHeader className="space-y-1 pb-6 z-10 relative">
        <CardTitle className="text-3xl font-bold tracking-tight text-center text-foreground">
          Create an account
        </CardTitle>
        <CardDescription className="text-center text-muted-foreground w-full">
          AI Chat Hub의 모든 기능을 이용하기 위해<br className="hidden sm:block" />
          간단한 정보를 입력해 주세요.
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4 z-10 relative">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-zinc-300">이메일 계정</Label>
            <Input 
              id="email" 
              type="email" 
              placeholder="name@example.com" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
              className="bg-zinc-900/50 border-zinc-800 focus-visible:ring-amber-500/50 focus-visible:border-amber-500 transition-all h-12"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="password" className="text-zinc-300">비밀번호</Label>
            <Input 
              id="password" 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
              className="bg-zinc-900/50 border-zinc-800 focus-visible:ring-amber-500/50 focus-visible:border-amber-500 transition-all h-12"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-zinc-300">비밀번호 확인</Label>
            <Input 
              id="confirmPassword" 
              type="password" 
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required 
              className="bg-zinc-900/50 border-zinc-800 focus-visible:ring-amber-500/50 focus-visible:border-amber-500 transition-all h-12"
            />
          </div>

          <div className="flex items-start space-x-3 pt-2">
            <Checkbox 
              id="terms" 
              checked={agreeTerms}
              onCheckedChange={setAgreeTerms}
              className="data-[state=checked]:bg-amber-500 data-[state=checked]:border-amber-500 border-zinc-600 mt-1"
            />
            <div className="grid leading-tight max-w-[90%]">
              <label
                htmlFor="terms"
                className="text-sm font-medium text-zinc-300 peer-disabled:cursor-not-allowed peer-disabled:opacity-70 leading-relaxed cursor-pointer select-none"
              >
                서비스 이용약관 및 개인정보 처리방침에 동의합니다.
              </label>
            </div>
          </div>

          <Button type="submit" className="w-full h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold text-md mt-6 transition-all shadow-[0_0_15px_rgba(245,158,11,0.3)] hover:shadow-[0_0_25px_rgba(245,158,11,0.5)]">
            회원가입 완료
          </Button>
        </form>
      </CardContent>
      
      <CardFooter className="flex justify-center z-10 relative border-t border-border/40 pt-6 mt-2 pb-8">
        <p className="text-sm text-muted-foreground text-center">
          이미 계정이 있으신가요?{" "}
          <Link href="/login" className="text-amber-500 font-semibold hover:text-amber-400 hover:underline underline-offset-4 transition-all">
            로그인
          </Link>
        </p>
      </CardFooter>
    </Card>
  );
}
