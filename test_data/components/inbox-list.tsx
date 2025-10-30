"use client"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { GitPullRequest, Bot, FileText, MessageCircle, Sparkles } from "lucide-react"
import type { InboxItem } from "@/lib/mock-inbox-data"

interface InboxListProps {
  items: InboxItem[]
  selectedItem: InboxItem | null
  onSelectItem: (item: InboxItem) => void
  width?: number
}

export function InboxList({ items, selectedItem, onSelectItem, width = 384 }: InboxListProps) {
  const getIcon = (type: InboxItem["type"]) => {
    switch (type) {
      case "review_requested":
        return <GitPullRequest className="h-4 w-4" />
      case "agent_completed":
        return <Bot className="h-4 w-4" />
      case "assigned":
        return <FileText className="h-4 w-4" />
      case "conversation":
        return <MessageCircle className="h-4 w-4" />
      default:
        return <GitPullRequest className="h-4 w-4" />
    }
  }

  const getStatusBadge = (status: InboxItem["status"]) => {
    const variants: Record<string, { label: string; className: string }> = {
      open: { label: "Open", className: "bg-green-100 text-green-700" },
      merged: { label: "Merged", className: "bg-purple-100 text-purple-700" },
      closed: { label: "Closed", className: "bg-gray-100 text-gray-700" },
      draft: { label: "Draft", className: "bg-gray-100 text-gray-600" },
    }
    const variant = variants[status] || variants.open
    return (
      <Badge variant="secondary" className={cn("text-xs", variant.className)}>
        {variant.label}
      </Badge>
    )
  }

  return (
    <div className="border-r bg-background overflow-y-auto" style={{ width: `${width}px` }}>
      <div className="p-4 border-b">
        <h2 className="font-semibold text-sm text-muted-foreground">
          {items.length} {items.length === 1 ? "item" : "items"}
        </h2>
      </div>

      <div className="divide-y">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => onSelectItem(item)}
            className={cn(
              "w-full p-4 text-left hover:bg-muted/50 transition-colors",
              selectedItem?.id === item.id && "bg-muted",
            )}
          >
            <div className="flex gap-3">
              <Avatar className="h-8 w-8 flex-shrink-0">
                <AvatarImage src={item.author.avatar || "/placeholder.svg"} alt={item.author.name} />
                <AvatarFallback>{item.author.name[0]}</AvatarFallback>
              </Avatar>

              <div className="flex-1 min-w-0">
                <div className="flex items-start gap-2 mb-1">
                  <div className="flex-shrink-0 mt-1">{getIcon(item.type)}</div>
                  <h3 className="font-medium text-sm line-clamp-2 flex-1">{item.title}</h3>
                </div>

                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                  <span className="font-medium">{item.author.name}</span>
                  {item.type === "conversation" && item.issueNumber ? (
                    <>
                      <span>commented on</span>
                      <span className="font-medium">#{item.issueNumber}</span>
                    </>
                  ) : (
                    <>
                      <span>•</span>
                      <span className="truncate">{item.repository}</span>
                    </>
                  )}
                  <span>•</span>
                  <span>{item.timestamp}</span>
                </div>

                {item.type === "conversation" && item.comments && item.commentId && (
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                    {item.comments.find((c) => c.id === item.commentId)?.content}
                  </p>
                )}

                {item.aiInsight && (
                  <div className="flex items-center gap-1.5 mb-2">
                    <Sparkles className="h-3 w-3 text-purple-500 flex-shrink-0" />
                    <p className="text-xs text-muted-foreground/80 line-clamp-1">{item.aiInsight}</p>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  {getStatusBadge(item.status)}
                  {item.metadata.filesChanged && (
                    <span className="text-xs text-muted-foreground">{item.metadata.filesChanged} files</span>
                  )}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
