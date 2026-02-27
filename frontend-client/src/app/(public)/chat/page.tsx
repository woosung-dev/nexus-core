"use client";

import { useState } from "react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatInput } from "@/components/chat/ChatInput";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex bg-black h-screen overflow-hidden selection:bg-amber-500/30">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block h-full">
        <ChatSidebar />
      </div>

      {/* Mobile Sidebar (Sheet) */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="p-0 border-r border-zinc-900 w-80 bg-zinc-950">
          <SheetTitle className="sr-only">채팅 메뉴</SheetTitle>
          <ChatSidebar className="w-full border-r-0" />
        </SheetContent>
      </Sheet>

      {/* Main Chat Layout */}
      <main className="flex-1 flex flex-col h-full relative relative z-10 w-full min-w-0">
        <ChatHeader onMenuClick={() => setSidebarOpen(true)} />
        <ChatArea />
        <ChatInput />
      </main>
    </div>
  );
}
