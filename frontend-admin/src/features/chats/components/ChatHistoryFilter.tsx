"use client";

import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { chatFilterSchema, ChatFilter } from "../schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { botKeys, fetchBots } from "@/features/bots/api";

interface ChatHistoryFilterProps {
  onFilterChange: (values: ChatFilter) => void;
}

// Radix Select 는 빈 문자열 value 를 못 쓴다. 「전체」를 이 값으로 두고 제출 때 벗긴다.
const ALL = "__all__";

export function ChatHistoryFilter({ onFilterChange }: ChatHistoryFilterProps) {
  const form = useForm<ChatFilter>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(chatFilterSchema as any),
    defaultValues: {
      title: "",
      user_email: "",
      bot_id: ALL,
      has_feedback: "all",
    },
  });

  const { data: botList } = useQuery({
    queryKey: botKeys.lists(),
    queryFn: fetchBots,
  });

  const onSubmit = (data: ChatFilter) => {
    onFilterChange({
      ...data,
      bot_id: data.bot_id === ALL ? "" : data.bot_id,
      page: 1,
    });
  };

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="mb-6 flex flex-col gap-2 rounded-md border bg-card p-3 sm:flex-row sm:items-center"
    >
      <div className="relative flex-1">
        <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          placeholder="세션 제목 검색..."
          className="w-full pl-9"
          {...form.register("title")}
        />
      </div>
      <div className="relative flex-1">
        <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          placeholder="사용자 이메일 검색..."
          className="w-full pl-9"
          {...form.register("user_email")}
        />
      </div>

      <Controller
        control={form.control}
        name="bot_id"
        render={({ field }) => (
          <Select value={field.value ?? ALL} onValueChange={field.onChange}>
            <SelectTrigger className="w-full sm:w-48" aria-label="봇">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>모든 봇</SelectItem>
              {botList?.bots.map((bot) => (
                <SelectItem key={bot.id} value={String(bot.id)}>
                  {bot.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      />

      <Controller
        control={form.control}
        name="has_feedback"
        render={({ field }) => (
          <Select value={field.value ?? "all"} onValueChange={field.onChange}>
            <SelectTrigger className="w-full sm:w-40" aria-label="피드백">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">모든 피드백</SelectItem>
              <SelectItem value="like">좋아요 포함</SelectItem>
              <SelectItem value="dislike">싫어요 포함</SelectItem>
            </SelectContent>
          </Select>
        )}
      />

      <Button type="submit">검색</Button>
    </form>
  );
}
