import { ScrollArea } from "@/components/ui/scroll-area"
import { Card } from "@/components/ui/card"
import { GitPullRequest, GitMerge, AlertCircle, CheckCircle2 } from "lucide-react"

const activities = [
  {
    type: "pr",
    title: "Review: Add authentication middleware",
    repo: "auth-service",
    author: "sarah-chen",
    time: "2 hours ago",
    icon: GitPullRequest,
    iconColor: "text-blue-600",
  },
  {
    type: "agent",
    title: "Agent completed: Generate API docs",
    repo: "api-gateway",
    author: "codex-agent",
    time: "4 hours ago",
    icon: CheckCircle2,
    iconColor: "text-green-600",
  },
  {
    type: "issue",
    title: "New issue: Memory leak in worker process",
    repo: "agent-platform",
    author: "mike-torres",
    time: "6 hours ago",
    icon: AlertCircle,
    iconColor: "text-orange-600",
  },
  {
    type: "merge",
    title: "Merged: Update dependencies",
    repo: "frontend-app",
    author: "emma-wilson",
    time: "8 hours ago",
    icon: GitMerge,
    iconColor: "text-purple-600",
  },
  {
    type: "pr",
    title: "Review: Refactor database queries",
    repo: "api-gateway",
    author: "alex-kim",
    time: "1 day ago",
    icon: GitPullRequest,
    iconColor: "text-blue-600",
  },
]

export default function ActivitySidebar() {
  return (
    <aside className="w-80 border-l border-border bg-background">
      <div className="flex h-full flex-col">
        <div className="border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold text-foreground">Recent Activity</h2>
        </div>
        <ScrollArea className="flex-1">
          <div className="space-y-1 p-3">
            {activities.map((activity, index) => (
              <Card key={index} className="cursor-pointer border-0 bg-transparent p-3 transition-colors hover:bg-muted">
                <div className="flex gap-3">
                  <activity.icon className={`h-5 w-5 flex-shrink-0 ${activity.iconColor}`} />
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="text-sm font-medium leading-tight text-foreground">{activity.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {activity.repo} • {activity.author}
                    </p>
                    <p className="text-xs text-muted-foreground">{activity.time}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </ScrollArea>
      </div>
    </aside>
  )
}
