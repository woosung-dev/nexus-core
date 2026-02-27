import Header from "@/components/layout/Header";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background selection:bg-amber-500/30">
      <Header />
      
      <main className="flex-1 flex flex-col items-center justify-center p-4">
        {/* Ambient Dark Background Effect */}
        <div className="absolute inset-0 bg-zinc-950/50 -z-10" />
        
        <LoginForm />
      </main>
    </div>
  );
}
