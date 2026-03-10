"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { chatFilterSchema, ChatFilter } from "../schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { botKeys, fetchBots } from "@/features/bots/api";

interface ChatHistoryFilterProps {
  onFilterChange: (values: ChatFilter) => void;
}

export function ChatHistoryFilter({ onFilterChange }: ChatHistoryFilterProps) {
  const form = useForm<ChatFilter>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(chatFilterSchema as any),
    defaultValues: {
      title: "",
      user_email: "",
      bot_id: "",
      has_feedback: "all",
    },
  });

  const { data: botList } = useQuery({
    queryKey: botKeys.lists(),
    queryFn: fetchBots,
  });

  const onSubmit = (data: ChatFilter) => {
    onFilterChange({ ...data, page: 1 });
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="bg-white p-4 rounded-xl border border-zinc-100 shadow-sm flex flex-col sm:flex-row gap-4 mb-6">
      <div className="flex-1 relative">
        <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <Input 
          placeholder="세션 제목 검색..." 
          className="pl-9 h-10 w-full"
          {...form.register("title")}
        />
      </div>
      <div className="flex-1 relative">
        <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <Input 
          placeholder="사용자 이메일 검색..." 
          className="pl-9 h-10 w-full"
          {...form.register("user_email")}
        />
      </div>
      <div className="w-full sm:w-48 relative">
        <select 
          className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          {...form.register("bot_id")}
        >
          <option value="">모든 봇</option>
          {botList?.bots.map((bot) => (
            <option key={bot.id} value={bot.id.toString()}>
              {bot.name}
            </option>
          ))}
        </select>
      </div>
      <div className="w-full sm:w-40 relative">
        <select 
          className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs focus:outline-none focus:ring-1 focus:ring-ring"
          {...form.register("has_feedback")}
        >
          <option value="all">모든 피드백</option>
          <option value="like">👍 좋아요 포함</option>
          <option value="dislike">👎 싫어요 포함</option>
        </select>
      </div>
      <Button type="submit" variant="default" className="h-10 text-white hover:bg-zinc-800">
        검색
      </Button>
    </form>
  );
}
