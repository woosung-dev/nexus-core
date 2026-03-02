import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MoreVertical } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { BotResponse } from "@/types/api";

export function BotCard({ bot }: { bot: BotResponse }) {
  // 백엔드 정적 파일 URL을 풀 경로로 변환하는 헬퍼
  const getFullImageUrl = (path?: string) => {
    if (!path) return undefined;
    if (path.startsWith('http')) return path;
    return path;
  };

  const imageUrl = getFullImageUrl(bot.image_url ?? undefined);

  return (
    <Link href={`/chat/new/${bot.id}`} className="block h-full group">
      <Card className="relative overflow-hidden bg-zinc-950 border-zinc-800 hover:border-amber-500/50 transition-all duration-300 flex flex-col h-full cursor-pointer">
        
        {/* Background Glow Effect on Hover */}
        <div className="absolute inset-0 bg-linear-to-b from-amber-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

      {/* Image Section */}
      <div className="relative w-full aspect-video bg-zinc-900 overflow-hidden">
        {imageUrl ? (
          <Image 
            src={imageUrl} 
            alt={bot.name}
            fill
            unoptimized
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-zinc-800/50 text-zinc-500">
            <span className="font-semibold">{bot.name.charAt(0)}</span>
          </div>
        )}
        
        <div className="absolute top-3 left-3 flex gap-2">
          {bot.is_verified && (
            <Badge className="bg-amber-500 text-black hover:bg-amber-600 font-bold border-none">
              Official
            </Badge>
          )}
          <Badge variant="secondary" className="bg-black/50 backdrop-blur-md text-zinc-300 border-zinc-700">
            {bot.tags?.[0] || 'AI Bot'}
          </Badge>
        </div>
      </div>

      <CardHeader className="p-4 pb-0 space-y-1">
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 min-w-0">
              <h3 className="font-bold text-lg text-foreground truncate group-hover:text-amber-500 transition-colors">
                {bot.name}
              </h3>
              {bot.is_verified && (
                <div className="shrink-0 text-amber-500" title="Official Bot">
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                  </svg>
                </div>
              )}
            </div>

          </div>
          <button className="text-muted-foreground hover:text-foreground transition-colors p-1 -mr-2 -mt-1 rounded-md shrink-0">
            <MoreVertical className="h-4 w-4" />
          </button>
        </div>
      </CardHeader>

      <CardContent className="p-4 pt-5 grow flex flex-col">
        <p className="text-sm text-zinc-400 line-clamp-2 leading-relaxed">
          {bot.description}
        </p>
        
        {/* Tags */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {bot.tags.map(tag => (
            <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800/50 text-zinc-400 border border-zinc-800">
              #{tag}
            </span>
          ))}
        </div>
      </CardContent>

      {/* <CardFooter className="p-4 pt-0 flex items-center justify-between text-xs text-muted-foreground border-t border-border/40 mt-auto">
        <div className="flex items-center space-x-1 mt-3">
          <Star className="h-3.5 w-3.5 fill-amber-500 text-amber-500" />
          <span className="font-medium text-zinc-300">{bot?.rating?.toFixed(1)}</span>
        </div>
        <div className="flex items-center space-x-1 mt-3">
          <MessageCircle className="h-3.5 w-3.5" />
          <span>{bot.users?.toLocaleString()} users</span>
        </div>
      </CardFooter> */}
      </Card>
    </Link>
  );
}
