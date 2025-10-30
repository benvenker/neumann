"use client"

import { Inbox, GitPullRequest, Bot, FileText, Activity, MessageCircle, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

interface InboxNavProps {
  activeFilter: string
  onFilterChange: (filter: string) => void
  counts: {
    inbox: number
    reviews: number
    agentTasks: number
    myIssues: number
    conversations: number
    insights: number
  }
}

export function InboxNav({ activeFilter, onFilterChange, counts }: InboxNavProps) {
  const navItems = [
    { id: "inbox", label: "Inbox", icon: Inbox, count: counts.inbox },
    { id: "insights", label: "Insights", icon: Sparkles, count: counts.insights, isSubItem: true },
    { id: "reviews", label: "Reviews", icon: GitPullRequest, count: counts.reviews },
    { id: "agent-tasks", label: "Agent Tasks", icon: Bot, count: counts.agentTasks },
    { id: "conversations", label: "Conversations", icon: MessageCircle, count: counts.conversations },
    { id: "my-issues", label: "My Issues", icon: FileText, count: counts.myIssues },
    { id: "all-activity", label: "All Activity", icon: Activity, count: 0 },
  ]

  return (
    <div className="min-w-64 max-w-64 flex-shrink-0 border-r bg-background p-4 flex flex-col gap-1 w-[280px]">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Notifications</h1>
      </div>

      <nav className="flex flex-col gap-1">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <button
              key={item.id}
              onClick={() => onFilterChange(item.id)}
              className={cn(
                "flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors overflow-hidden",
                item.isSubItem && "ml-6",
                activeFilter === item.id
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
              )}
            >
              <div className="flex items-center gap-3 min-w-0 overflow-hidden">
                <Icon className="h-4 w-4 flex-shrink-0" />
                <span className="truncate">{item.label}</span>
              </div>
              {item.count > 0 && (
                <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full flex-shrink-0">
                  {item.count}
                </span>
              )}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
