import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function BotCardSkeleton() {
  return (
    <div className="block h-full group">
      <Card className="relative overflow-hidden bg-white border-zinc-100 shadow-sm flex flex-col h-full">
        {/* Image Section Skeleton */}
        <div className="relative w-full aspect-video bg-zinc-100 animate-pulse overflow-hidden">
          <div className="absolute top-3 left-3 flex gap-2">
            <div className="h-6 w-16 bg-zinc-200/50 rounded-full animate-pulse backdrop-blur-md" />
          </div>
        </div>

        <CardHeader className="p-4 pb-0 space-y-1">
          <div className="flex justify-between items-start">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 min-w-0">
                <div className="h-6 w-3/4 bg-zinc-100 animate-pulse rounded-md" />
              </div>
            </div>
            {/* More icon placeholder */}
            <div className="h-6 w-6 bg-zinc-100 animate-pulse rounded-md shrink-0 -mr-2 -mt-1" />
          </div>
        </CardHeader>

        <CardContent className="p-4 pt-5 grow flex flex-col">
          {/* Description lines skeleton */}
          <div className="w-full h-4 bg-zinc-100 animate-pulse rounded-md" />
          <div className="w-4/5 h-4 bg-zinc-100 animate-pulse rounded-md mt-2" />
          
          {/* Tags skeleton */}
          <div className="flex flex-wrap gap-1.5 mt-4">
            <div className="h-5 w-12 bg-zinc-100 animate-pulse rounded-full" />
            <div className="h-5 w-16 bg-zinc-100 animate-pulse rounded-full" />
            <div className="h-5 w-14 bg-zinc-100 animate-pulse rounded-full" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
