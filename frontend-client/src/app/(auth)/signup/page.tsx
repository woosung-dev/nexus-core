import Header from "@/components/layout/Header";
import { SignupForm } from "@/components/auth/SignupForm";

export default function SignupPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background selection:bg-amber-500/30 overflow-x-hidden">
      <Header />
      
      <main className="flex-1 flex flex-col items-center justify-center py-10 px-4">
        {/* Ambient Dark Background Effect */}
        <div className="fixed inset-0 bg-zinc-950/50 -z-10" />
        
        <SignupForm />
      </main>
    </div>
  );
}
