import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Star, MessageCircle, MoreVertical } from "lucide-react";
import Image from "next/image";

export interface BotData {
  id: string;
  name: string;
  creator: string;
  description: string;
  category: string;
  tags: string[];
  rating: number;
  users: number;
  imageUrl?: string;
  isOfficial?: boolean;
}

export function BotCard({ bot }: { bot: BotData }) {
  return (
    <Card className="group relative overflow-hidden bg-zinc-950 border-zinc-800 hover:border-amber-500/50 transition-all duration-300 flex flex-col h-full cursor-pointer">
      
      {/* Background Glow Effect on Hover */}
      <div className="absolute inset-0 bg-gradient-to-b from-amber-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

      {/* Image Section */}
      <div className="relative w-full aspect-video bg-zinc-900 overflow-hidden">
        {bot.imageUrl ? (
          <Image 
            src={bot.imageUrl} 
            alt={bot.name}
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-zinc-800/50 text-zinc-500">
            <span className="font-semibold">{bot.name.charAt(0)}</span>
          </div>
        )}
        
        {/* Top Badges */}
        <div className="absolute top-3 left-3 flex gap-2">
          {bot.isOfficial && (
            <Badge className="bg-amber-500 text-black hover:bg-amber-600 font-bold border-none">
              Official
            </Badge>
          )}
          <Badge variant="secondary" className="bg-black/50 backdrop-blur-md text-zinc-300 border-zinc-700">
            {bot.category}
          </Badge>
        </div>
      </div>

      <CardHeader className="p-4 pb-2 space-y-1">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="font-bold text-lg text-foreground line-clamp-1 group-hover:text-amber-500 transition-colors">
              {bot.name}
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">by {bot.creator}</p>
          </div>
          <button className="text-muted-foreground hover:text-foreground transition-colors p-1 -mr-2 -mt-1 rounded-md">
            <MoreVertical className="h-4 w-4" />
          </button>
        </div>
      </CardHeader>

      <CardContent className="p-4 pt-0 flex-grow">
        <p className="text-sm text-zinc-400 line-clamp-2 mt-2">
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

      <CardFooter className="p-4 pt-0 flex items-center justify-between text-xs text-muted-foreground border-t border-border/40 mt-auto">
        <div className="flex items-center space-x-1 mt-3">
          <Star className="h-3.5 w-3.5 fill-amber-500 text-amber-500" />
          <span className="font-medium text-zinc-300">{bot.rating.toFixed(1)}</span>
        </div>
        <div className="flex items-center space-x-1 mt-3">
          <MessageCircle className="h-3.5 w-3.5" />
          <span>{bot.users.toLocaleString()} users</span>
        </div>
      </CardFooter>
    </Card>
  );
}
