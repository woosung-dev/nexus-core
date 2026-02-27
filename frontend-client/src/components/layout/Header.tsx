import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { LayoutDashboard, User } from 'lucide-react';

export default function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 max-w-screen-2xl items-center px-4 md:px-8 mx-auto">
        <div className="flex flex-1 items-center justify-between">
          
          {/* Logo & Brand */}
          <Link href="/" className="flex items-center space-x-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <span className="font-bold text-primary">N</span>
            </div>
            <span className="font-bold inline-block text-lg shrink-0">
              AI Chat Hub
            </span>
          </Link>

          {/* Navigation & Actions */}
          <nav className="flex items-center space-x-2 md:space-x-4 shrink-0">
            <Button variant="ghost" size="sm" asChild className="text-muted-foreground hover:text-foreground hidden sm:inline-flex">
              <Link href="/mypage">
                <LayoutDashboard className="h-4 w-4 mr-2" />
                마이페이지
              </Link>
            </Button>
            
            {/* Mobile Mypage Icon */}
            <Button variant="ghost" size="icon" asChild className="text-muted-foreground hover:text-foreground sm:hidden">
              <Link href="/mypage" aria-label="마이페이지">
                <User className="h-5 w-5" />
              </Link>
            </Button>

            <Button size="sm" asChild className="font-semibold bg-primary text-primary-foreground hover:bg-primary/90">
              <Link href="/login">
                로그인
              </Link>
            </Button>
          </nav>
        </div>
      </div>
    </header>
  );
}
