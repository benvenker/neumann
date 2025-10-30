import { Folder, Inbox } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import Link from "next/link"

const projects = [
  { name: "agent-platform", path: "benvenker/agent-platform" },
  { name: "code-review-bot", path: "benvenker/code-review-bot" },
  { name: "test-coverage-analyzer", path: "benvenker/test-coverage-analyzer" },
  { name: "docs-generator", path: "benvenker/docs-generator" },
  { name: "api-gateway", path: "benvenker/api-gateway" },
  { name: "auth-service", path: "benvenker/auth-service" },
  { name: "frontend-app", path: "benvenker/frontend-app" },
]

export default function ProjectsSidebar() {
  return (
    <aside className="w-64 border-r border-border bg-background">
      <div className="flex h-full flex-col">
        <div className="border-b border-border p-2">
          <Link
            href="/inbox"
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            <Inbox className="h-5 w-5" />
            <span>Inbox</span>
          </Link>
        </div>
        <div className="border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold text-foreground">Your Projects</h2>
        </div>
        <ScrollArea className="flex-1">
          <div className="space-y-1 p-2">
            {projects.map((project) => (
              <button
                key={project.path}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-foreground transition-colors hover:bg-muted"
              >
                <Folder className="h-4 w-4 text-muted-foreground" />
                <span className="truncate">{project.name}</span>
              </button>
            ))}
          </div>
        </ScrollArea>
      </div>
    </aside>
  )
}
