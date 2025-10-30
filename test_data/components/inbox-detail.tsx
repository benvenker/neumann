"use client"

import { useEffect, useRef } from "react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { ExternalLink, Check, X, GitMerge, FileCode, Bot, ChevronRight } from "lucide-react"
import type { InboxItem } from "@/lib/mock-inbox-data"

interface InboxDetailProps {
  item: InboxItem | null
  highlightedCommentId?: string
}

export function InboxDetail({ item, highlightedCommentId }: InboxDetailProps) {
  const highlightedRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (highlightedCommentId && highlightedRef.current) {
      highlightedRef.current.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }, [highlightedCommentId])

  if (!item) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p>Select an item to view details</p>
      </div>
    )
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

  if (item.type === "conversation" && item.comments) {
    return (
      <div className="flex-1 overflow-y-auto bg-background">
        {/* Header */}
        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-sm text-muted-foreground">#{item.issueNumber}</span>
                <h1 className="text-2xl font-semibold">{item.title}</h1>
                {getStatusBadge(item.status)}
              </div>
              <p className="text-sm text-muted-foreground">{item.repository}</p>
            </div>
            <Button variant="outline" size="sm">
              <ExternalLink className="h-4 w-4 mr-2" />
              View Issue
            </Button>
          </div>
        </div>

        {/* Description */}
        {item.description && (
          <div className="p-6">
            <div className="p-4 bg-muted/30 rounded-lg">
              <p className="text-sm leading-relaxed">{item.description}</p>
            </div>
          </div>
        )}

        {/* Comments */}
        <div className="p-6">
          <h3 className="text-sm font-semibold mb-4">Comments ({item.comments.length})</h3>
          <div className="space-y-4">
            {item.comments.map((comment) => (
              <div
                key={comment.id}
                ref={comment.id === highlightedCommentId ? highlightedRef : null}
                className={cn(
                  "flex gap-3 p-4 rounded-lg transition-colors",
                  comment.id === highlightedCommentId ? "bg-blue-50 border border-blue-200" : "bg-muted/30",
                )}
              >
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarImage src={comment.author.avatar || "/placeholder.svg"} alt={comment.author.name} />
                  <AvatarFallback>{comment.author.name[0]}</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium">{comment.author.name}</span>
                    <span className="text-xs text-muted-foreground">{comment.timestamp}</span>
                  </div>
                  <p className="text-sm leading-relaxed">{comment.content}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Agent Quick Actions */}
        <div className="p-6">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Bot className="h-4 w-4" />
            Agent Quick Actions
          </h3>
          <div className="space-y-2">
            <Button variant="outline" size="sm" className="w-full justify-start bg-transparent">
              <ChevronRight className="h-4 w-4 mr-2" />
              Summarize this discussion
            </Button>
            <Button variant="outline" size="sm" className="w-full justify-start bg-transparent">
              <ChevronRight className="h-4 w-4 mr-2" />
              Suggest next steps
            </Button>
            <Button variant="outline" size="sm" className="w-full justify-start bg-transparent">
              <ChevronRight className="h-4 w-4 mr-2" />
              Find related issues
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto bg-background">
      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-semibold">{item.title}</h1>
              {getStatusBadge(item.status)}
            </div>
            <p className="text-sm text-muted-foreground">
              {item.repository} • {item.metadata.branch || "main"}
            </p>
          </div>
          <Button variant="outline" size="sm">
            <ExternalLink className="h-4 w-4 mr-2" />
            View PR
          </Button>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button size="sm" className="bg-green-600 hover:bg-green-700">
            <Check className="h-4 w-4 mr-2" />
            Approve
          </Button>
          <Button size="sm" variant="outline">
            <X className="h-4 w-4 mr-2" />
            Request Changes
          </Button>
          {item.status === "open" && (
            <Button size="sm" variant="outline">
              <GitMerge className="h-4 w-4 mr-2" />
              Merge
            </Button>
          )}
        </div>
      </div>

      {/* Metadata Section */}
      <div className="p-6">
        <div className="grid grid-cols-3 gap-6">
          <div>
            <p className="text-xs text-muted-foreground mb-2">Author</p>
            <div className="flex items-center gap-2">
              <Avatar className="h-6 w-6">
                <AvatarImage src={item.author.avatar || "/placeholder.svg"} alt={item.author.name} />
                <AvatarFallback>{item.author.name[0]}</AvatarFallback>
              </Avatar>
              <span className="text-sm font-medium">{item.author.name}</span>
            </div>
          </div>

          <div>
            <p className="text-xs text-muted-foreground mb-2">Changes</p>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-green-600">+{item.metadata.additions || 0}</span>
              <span className="text-red-600">-{item.metadata.deletions || 0}</span>
            </div>
          </div>

          <div>
            <p className="text-xs text-muted-foreground mb-2">Reviewers</p>
            <div className="flex -space-x-2">
              {item.metadata.reviewers?.map((reviewer, idx) => (
                <Avatar key={idx} className="h-6 w-6 border-2 border-background">
                  <AvatarImage src={reviewer.avatar || "/placeholder.svg"} alt={reviewer.name} />
                  <AvatarFallback>{reviewer.name[0]}</AvatarFallback>
                </Avatar>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Description */}
      {item.description && (
        <div className="p-6">
          <h3 className="text-sm font-semibold mb-3">Description</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">{item.description}</p>
        </div>
      )}

      {/* Files Changed */}
      {item.files && item.files.length > 0 && (
        <div className="p-6">
          <h3 className="text-sm font-semibold mb-3">Files Changed ({item.files.length})</h3>
          <div className="space-y-1">
            {item.files.map((file, idx) => (
              <div key={idx} className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted/50 text-sm">
                <FileCode className="h-4 w-4 text-muted-foreground" />
                <span className="font-mono text-xs">{file}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agent Quick Actions */}
      <div className="p-6">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Bot className="h-4 w-4" />
          Agent Quick Actions
        </h3>
        <div className="space-y-2">
          <Button variant="outline" size="sm" className="w-full justify-start bg-transparent">
            <ChevronRight className="h-4 w-4 mr-2" />
            Run code review on this PR
          </Button>
          <Button variant="outline" size="sm" className="w-full justify-start bg-transparent">
            <ChevronRight className="h-4 w-4 mr-2" />
            Generate unit tests for changes
          </Button>
          <Button variant="outline" size="sm" className="w-full justify-start bg-transparent">
            <ChevronRight className="h-4 w-4 mr-2" />
            Check test coverage impact
          </Button>
        </div>
      </div>

      {/* Activity Timeline */}
      {item.activity && item.activity.length > 0 && (
        <div className="p-6">
          <h3 className="text-sm font-semibold mb-4">Activity</h3>
          <div className="space-y-4">
            {item.activity.map((event, idx) => (
              <div key={idx} className="flex gap-3">
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarImage src={event.author.avatar || "/placeholder.svg"} alt={event.author.name} />
                  <AvatarFallback>{event.author.name[0]}</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium">{event.author.name}</span>
                    <span className="text-xs text-muted-foreground">{event.timestamp}</span>
                  </div>
                  <div className="p-3 bg-muted/30 rounded-lg">
                    <p className="text-sm">{event.content}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
