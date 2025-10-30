"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  Clock,
  MessageSquare,
  Loader2,
  Eye,
  UserPlus,
  CalendarPlus,
  Package,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import type { InsightItem, InsightBundle } from "@/lib/mock-inbox-data"
import { cn } from "@/lib/utils"
import { useEffect, useState } from "react"

interface InboxInsightsDetailProps {
  insight: InsightItem | null
  bundle?: InsightBundle
  onStartWorkflow: (insight: InsightItem) => void
}

export function InboxInsightsDetail({ insight, bundle, onStartWorkflow }: InboxInsightsDetailProps) {
  const [generatedSummary, setGeneratedSummary] = useState<string | null>(null)
  const [generatedDrafts, setGeneratedDrafts] = useState<string | null>(null)
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false)
  const [isGeneratingDrafts, setIsGeneratingDrafts] = useState(false)
  const [isAIActionsExpanded, setIsAIActionsExpanded] = useState(false)

  useEffect(() => {
    setGeneratedSummary(null)
    setGeneratedDrafts(null)
    setIsGeneratingSummary(false)
    setIsGeneratingDrafts(false)
  }, [insight?.id, bundle?.id])

  const handleGenerateSummary = async () => {
    setIsGeneratingSummary(true)
    await new Promise((resolve) => setTimeout(resolve, 1500))

    if (bundle) {
      setGeneratedSummary(
        `**Aggregated Summary for "${bundle.title}":**\n\n` +
          `This bundle combines ${bundle.insights.length} related insights affecting ${bundle.metadata.totalCount} total items:\n\n` +
          bundle.insights
            .map(
              (ins, idx) =>
                `${idx + 1}. **${ins.title}:** ${ins.relatedItems.length} items requiring attention. ${ins.urgency?.reason || ""}`,
            )
            .join("\n\n") +
          `\n\n**Recommended Approach:** Address these items together to maximize efficiency and unblock the team faster.`,
      )
    } else {
      const summaries: Record<string, string> = {
        "insight-1":
          "**Key Questions from Sarah:**\n\n1. **Database Migration (#234):** Suggests phased approach - migrate user tables first, then project data. Asks about using Prisma migrations for built-in rollback support.\n\n2. **API Rate Limiting (#189):** Confirms Redis as storage solution for rate limit counters. Working on middleware implementation.\n\n3. **Dashboard Performance (#156):** No direct questions, but discussion involves virtual scrolling implementation to handle large datasets.",
        "insight-2":
          "**Blocking Issues Summary:**\n\n**Issue #234 (Database Migration):** Waiting for your decision on migration approach. Alex suggested Prisma migrations. Team needs direction to proceed.\n\n**Issue #189 (API Rate Limiting):** Emma is implementing middleware but needs approval on Redis usage. Blocking 2 downstream API features scheduled for this sprint.",
        "insight-3":
          "**PR Review Summary:**\n\n**PR #42:** Automated docstring generation by CodeRabbit. Low risk, quick review.\n\n**PR #38:** Analytics dashboard with 12 files changed. Requires thorough review of metrics implementation.\n\n**PR #35:** Already merged - documentation updates only.",
        "insight-4":
          "**Mentions Summary:**\n\n- **Alex (#234):** Asking your opinion on Prisma migrations\n- **Mike (#156):** Needs your input on performance optimization approach\n- **Emma (#189):** Waiting for approval on Redis implementation\n- **Team (#142):** Mobile auth flow discussion needs your architectural guidance",
        "insight-5":
          "**Common Pattern Analysis:**\n\nAll 3 issues relate to dashboard performance with large datasets:\n- Issue #156: 5+ second load times with 10k+ rows\n- Issue #148: Mobile performance degradation\n- Issue #142: Chart rendering failures\n\n**Root Cause:** Rendering all data at once without pagination or virtualization.",
      }

      setGeneratedSummary(summaries[insight?.id || ""] || "Summary generated successfully.")
    }
    setIsGeneratingSummary(false)
  }

  const handleGenerateDrafts = async () => {
    setIsGeneratingDrafts(true)
    await new Promise((resolve) => setTimeout(resolve, 2000))

    if (bundle) {
      setGeneratedDrafts(
        `**Unified Action Plan for "${bundle.title}":**\n\n` +
          bundle.insights
            .map(
              (ins, idx) =>
                `**${idx + 1}. ${ins.title}**\n` +
                `Action: ${ins.actionLabel}\n` +
                `Items: ${ins.relatedItems.map((item) => `#${item.number}`).join(", ")}`,
            )
            .join("\n\n") +
          `\n\n**Execution Order:** Address in priority order (high → medium → low) to maximize team unblocking.`,
      )
    } else {
      const drafts: Record<string, string> = {
        "insight-1":
          '**Draft Responses:**\n\n**To #234 (Database Migration):**\n"@alex Great suggestion on Prisma migrations. Let\'s go with that approach - the built-in rollback support will be valuable. Can you create a migration plan document outlining the phases Sarah mentioned?"\n\n**To #189 (API Rate Limiting):**\n"@emma Redis is the right choice here. Please proceed with the middleware implementation. Let\'s review the PR tomorrow and aim to merge by end of week."\n\n**To #156 (Dashboard Performance):**\n"@alex Virtual scrolling is the right solution. Let\'s implement react-window for the table component. I can review your implementation this afternoon."',
        "insight-2":
          '**Suggested Actions:**\n\n**Issue #234:**\n"Approving Prisma migration approach. @alex please create implementation plan by EOD. This unblocks the v2.0 release timeline."\n\n**Issue #189:**\n"@emma approved to proceed with Redis implementation. Priority: High. This unblocks rate limiting for new API endpoints launching next week."',
        "insight-3":
          "**Review Plan:**\n\n1. **PR #42** (15 min): Quick approval - automated docstrings look good\n2. **PR #38** (45 min): Thorough review needed - check metrics accuracy and performance\n3. **PR #35**: Already merged ✓",
        "insight-4":
          '**Response Templates:**\n\n**@alex (#234):** "Prisma migrations approved - please proceed"\n**@mike (#156):** "Virtual scrolling is the way to go - let\'s implement react-window"\n**@emma (#189):** "Redis implementation approved - high priority"\n**Team (#142):** "Let\'s schedule 30min sync to discuss mobile auth architecture"',
        "insight-5":
          '**Unified Solution Proposal:**\n\n"I\'ve analyzed issues #156, #148, and #142. They all stem from the same root cause: rendering large datasets without optimization.\n\n**Proposed Solution:**\n- Implement virtual scrolling with react-window\n- Add pagination for datasets >1000 rows\n- Lazy load chart data\n\nThis single fix will resolve all 3 issues. I can create a consolidated PR addressing all of them. Estimated time: 4 hours."',
      }

      setGeneratedDrafts(drafts[insight?.id || ""] || "Draft responses generated successfully.")
    }
    setIsGeneratingDrafts(false)
  }

  if (!insight && !bundle) {
    return (
      <div className="flex flex-1 items-center justify-center bg-background">
        <div className="text-center">
          <Sparkles className="mx-auto h-12 w-12 text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-semibold">No insight selected</h3>
          <p className="mt-2 text-sm text-muted-foreground">Select an insight to view details and take action</p>
        </div>
      </div>
    )
  }

  const displayData = bundle || insight
  const isBundle = !!bundle
  const allRelatedItems = isBundle
    ? Array.from(new Map(bundle.insights.flatMap((ins) => ins.relatedItems).map((item) => [item.id, item])).values())
    : insight?.relatedItems || []

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case "resolved":
        return <CheckCircle2 className="h-4 w-4 text-green-600" />
      case "needs_attention":
        return <XCircle className="h-4 w-4 text-red-600" />
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-600" />
      default:
        return null
    }
  }

  const getPriorityColor = (priority?: string) => {
    switch (priority) {
      case "high":
        return "bg-red-500/10 text-red-700 border-red-200"
      case "medium":
        return "bg-yellow-500/10 text-yellow-700 border-yellow-200"
      case "low":
        return "bg-blue-500/10 text-blue-700 border-blue-200"
      default:
        return "bg-gray-500/10 text-gray-700 border-gray-200"
    }
  }

  const suggestedActionsCount = isBundle ? bundle.insights.length + 2 : 2 // Generate Summary + Draft Responses (+ bundle items if applicable)

  return (
    <div className="flex flex-1 flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-primary/10 p-2">
            {isBundle ? <Package className="h-5 w-5 text-primary" /> : <Sparkles className="h-5 w-5 text-primary" />}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold">{displayData.title}</h1>
              {displayData.metadata.priority && (
                <Badge variant="outline" className={cn("text-xs", getPriorityColor(displayData.metadata.priority))}>
                  {displayData.metadata.priority} priority
                </Badge>
              )}
              {isBundle && (
                <Badge variant="secondary" className="text-xs">
                  {bundle.insights.length} insights
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{displayData.description}</p>
            <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
              <span>Generated {displayData.generatedAt} ago</span>
              <span>•</span>
              <span>{isBundle ? bundle.metadata.totalCount : insight?.relatedItems.length || 0} related items</span>
              {!isBundle && insight?.metadata.users && (
                <>
                  <span>•</span>
                  <span>Involves: {insight.metadata.users.join(", ")}</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isBundle && (
          <Card className="mb-6 border-primary/20 bg-primary/5 p-4">
            <div className="flex items-start gap-3">
              <Package className="h-5 w-5 text-primary flex-shrink-0" />
              <div className="flex-1">
                <h3 className="mb-2 text-sm font-semibold">Bundled Insights</h3>
                <div className="space-y-2">
                  {bundle.insights.map((ins) => (
                    <div key={ins.id} className="flex items-start gap-2 text-sm">
                      <Sparkles className="mt-0.5 h-3.5 w-3.5 text-primary flex-shrink-0" />
                      <div className="flex-1">
                        <span className="font-medium">{ins.title}</span>
                        <span className="ml-2 text-muted-foreground">
                          ({ins.relatedItems.length} items, {ins.metadata.priority} priority)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        )}

        <Card className="mb-6 border-primary/20 bg-primary/5 p-4">
          <div className="flex items-start gap-3">
            <Sparkles className="h-5 w-5 text-primary flex-shrink-0" />
            <div className="flex-1">
              <button
                onClick={() => setIsAIActionsExpanded(!isAIActionsExpanded)}
                className="flex w-full items-center justify-between text-left transition-colors hover:opacity-80"
              >
                <h3 className="text-sm font-semibold">AI Actions</h3>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {suggestedActionsCount} suggested action{suggestedActionsCount !== 1 ? "s" : ""}
                  </span>
                  {isAIActionsExpanded ? (
                    <ChevronUp className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
              </button>

              {isAIActionsExpanded && (
                <div className="mt-3 space-y-3">
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleGenerateSummary}
                      disabled={isGeneratingSummary || isGeneratingDrafts}
                      className="gap-2 bg-transparent"
                    >
                      {isGeneratingSummary ? (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-3 w-3" />
                          Generate Summary
                        </>
                      )}
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleGenerateDrafts}
                      disabled={isGeneratingSummary || isGeneratingDrafts}
                      className="gap-2 bg-transparent"
                    >
                      {isGeneratingDrafts ? (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <MessageSquare className="h-3 w-3" />
                          Draft Responses
                        </>
                      )}
                    </Button>
                  </div>

                  {generatedSummary && (
                    <div className="rounded-md bg-background p-3 text-sm">
                      <div className="whitespace-pre-wrap text-foreground">{generatedSummary}</div>
                    </div>
                  )}

                  {generatedDrafts && (
                    <div className="rounded-md bg-background p-3 text-sm">
                      <div className="whitespace-pre-wrap text-foreground">{generatedDrafts}</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Related Items */}
        <div>
          <h3 className="mb-3 text-sm font-semibold">Related Items</h3>
          <div className="space-y-2">
            {allRelatedItems.map((item) => (
              <Card key={item.id} className="group p-4 transition-colors hover:bg-accent/50">
                <div className="flex items-start gap-3">
                  <div className="flex items-start gap-2 flex-shrink-0">
                    {getStatusIcon(item.status)}
                    <span className="text-sm font-medium">#{item.number}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm leading-relaxed">{item.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{item.repository}</p>
                    {item.relationContext && (
                      <p className="mt-1 text-xs text-foreground/70 italic">{item.relationContext}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 flex-shrink-0">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 gap-1 px-2 text-xs"
                      onClick={() => console.log("[v0] Review now:", item.number)}
                    >
                      <Eye className="h-3 w-3" />
                      Review now
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 gap-1 px-2 text-xs"
                      onClick={() => console.log("[v0] Delegate:", item.number)}
                    >
                      <UserPlus className="h-3 w-3" />
                      Delegate
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 gap-1 px-2 text-xs"
                      onClick={() => console.log("[v0] Add to sprint:", item.number)}
                    >
                      <CalendarPlus className="h-3 w-3" />
                      Add to sprint
                    </Button>
                  </div>
                  {item.status && (
                    <Badge variant="outline" className="text-xs capitalize flex-shrink-0">
                      {item.status.replace("_", " ")}
                    </Badge>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="border-t border-border px-6 py-4">
        <Button className="w-full gap-2" size="lg" onClick={() => onStartWorkflow(insight || bundle.insights[0])}>
          <MessageSquare className="h-4 w-4" />
          Start AI-Assisted Workflow
        </Button>
        <p className="mt-2 text-center text-xs text-muted-foreground">
          Launch a guided conversation to resolve this {isBundle ? "bundle" : "insight"}
        </p>
      </div>
    </div>
  )
}
