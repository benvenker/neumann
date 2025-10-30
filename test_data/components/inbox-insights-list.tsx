"use client"
import { Badge } from "@/components/ui/badge"
import type React from "react"

import { Button } from "@/components/ui/button"
import { TooltipRoot, TooltipTrigger, TooltipContent, TooltipProvider, TooltipPortal } from "@/components/ui/tooltip"
import { Sparkles, Loader2, ArrowRight, Clock, ChevronDown, Brain, Package, X } from "lucide-react"
import type { InsightItem, InsightBundle } from "@/lib/mock-inbox-data"
import { cn } from "@/lib/utils"
import { useState } from "react"
import { InsightsLoading } from "./insights-loading"

interface InboxInsightsListProps {
  insights: InsightItem[]
  bundles: InsightBundle[]
  selectedInsight: InsightItem | null
  selectedBundle: InsightBundle | null
  onSelectInsight: (insight: InsightItem) => void
  onSelectBundle: (bundle: InsightBundle) => void
  width?: number
  priorityFilter?: string | null
  onPriorityFilterChange?: (priority: string | null) => void
}

export function InboxInsightsList({
  insights,
  bundles,
  selectedInsight,
  selectedBundle,
  onSelectInsight,
  onSelectBundle,
  width = 384,
  priorityFilter,
  onPriorityFilterChange,
}: InboxInsightsListProps) {
  const [expandedReasoning, setExpandedReasoning] = useState<string | null>(null)
  const [expandedBundles, setExpandedBundles] = useState<Set<string>>(new Set())
  const [isLoading] = useState(false)

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

  const toggleBundle = (bundleId: string) => {
    const newExpanded = new Set(expandedBundles)
    if (newExpanded.has(bundleId)) {
      newExpanded.delete(bundleId)
    } else {
      newExpanded.add(bundleId)
    }
    setExpandedBundles(newExpanded)
  }

  const handlePriorityClick = (priority: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (priorityFilter === priority) {
      onPriorityFilterChange?.(null)
    } else {
      onPriorityFilterChange?.(priority)
    }
  }

  const bundledInsightIds = new Set(bundles.flatMap((bundle) => bundle.insights.map((i) => i.id)))
  const standaloneInsights = insights.filter((insight) => !bundledInsightIds.has(insight.id))

  const filteredBundles = priorityFilter
    ? bundles.filter((bundle) => bundle.metadata.priority === priorityFilter)
    : bundles

  const filteredStandaloneInsights = priorityFilter
    ? standaloneInsights.filter((insight) => insight.metadata.priority === priorityFilter)
    : standaloneInsights

  return (
    <TooltipProvider>
      <div className="flex flex-col border-r border-border bg-background" style={{ width: `${width}px` }}>
        {/* Header */}
        <div className="border-b border-border px-4 py-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">AI Insights</h2>
            <Badge variant="secondary" className="text-xs">
              {bundles.length + standaloneInsights.length} insights
            </Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">AI-generated recommendations for your workflow</p>

          {priorityFilter && (
            <div className="mt-2 flex items-center gap-2">
              <Badge variant="outline" className={cn("text-xs", getPriorityColor(priorityFilter))}>
                {priorityFilter} priority
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 px-1 text-xs"
                onClick={() => onPriorityFilterChange?.(null)}
              >
                <X className="h-3 w-3" />
                Clear filter
              </Button>
            </div>
          )}
        </div>

        {isLoading ? (
          <InsightsLoading />
        ) : (
          <div className="flex-1 overflow-y-auto">
            <div className="divide-y divide-border">
              {filteredBundles.map((bundle) => {
                const isExpanded = expandedBundles.has(bundle.id)
                const isSelected = selectedBundle?.id === bundle.id

                return (
                  <div key={bundle.id} className="border-b-2 border-primary/20">
                    <div
                      className={cn(
                        "cursor-pointer px-4 py-3 transition-colors hover:bg-accent/50",
                        isSelected ? "bg-accent" : "",
                      )}
                      onClick={() => onSelectBundle(bundle)}
                    >
                      <div className="flex items-start gap-2">
                        <Package className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold">{bundle.title}</h3>
                            <Badge
                              variant="outline"
                              className={cn(
                                "shrink-0 text-xs cursor-pointer hover:opacity-80 transition-opacity",
                                getPriorityColor(bundle.metadata.priority),
                                priorityFilter === bundle.metadata.priority && "ring-2 ring-primary",
                              )}
                              onClick={(e) => handlePriorityClick(bundle.metadata.priority, e)}
                            >
                              {bundle.metadata.priority}
                            </Badge>
                            <Badge variant="secondary" className="shrink-0 text-xs">
                              {bundle.insights.length} insights
                            </Badge>
                          </div>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            {bundle.metadata.totalCount} total items • {bundle.generatedAt}
                          </p>

                          {bundle.urgency && (
                            <div className="mt-1.5 flex items-center gap-1.5 text-xs">
                              <Clock className="h-3 w-3 text-orange-600" />
                              <span className="font-medium text-orange-600">{bundle.urgency.deadline}</span>
                              <span className="text-muted-foreground">{bundle.urgency.reason}</span>
                            </div>
                          )}

                          {bundle.reasoning && (
                            <div className="mt-2">
                              <button
                                className="flex items-center gap-1.5 text-xs text-primary hover:underline"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setExpandedReasoning(expandedReasoning === bundle.id ? null : bundle.id)
                                }}
                              >
                                <Brain className="h-3 w-3" />
                                <span>Why bundle these together?</span>
                                <ChevronDown
                                  className={cn(
                                    "h-3 w-3 transition-transform",
                                    expandedReasoning === bundle.id && "rotate-180",
                                  )}
                                />
                              </button>

                              {expandedReasoning === bundle.id && (
                                <div className="mt-2 rounded-md border border-primary/20 bg-primary/5 p-2.5">
                                  <div className="mb-1.5 flex items-center justify-between">
                                    <span className="text-xs font-medium text-primary">AI detected:</span>
                                    <span className="text-xs text-muted-foreground">
                                      {bundle.reasoning.confidence}% confidence
                                    </span>
                                  </div>
                                  <ul className="space-y-1">
                                    {bundle.reasoning.factors.map((factor, index) => (
                                      <li key={index} className="text-xs text-muted-foreground">
                                        • {factor}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}

                          <div className="mt-2 flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 text-xs font-medium text-primary hover:text-primary"
                              onClick={(e) => {
                                e.stopPropagation()
                                onSelectBundle(bundle)
                              }}
                            >
                              {bundle.actionLabel}
                              <ArrowRight className="ml-1 h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 text-xs"
                              onClick={(e) => {
                                e.stopPropagation()
                                toggleBundle(bundle.id)
                              }}
                            >
                              {isExpanded ? "Hide" : "Show"} {bundle.insights.length} insights
                              <ChevronDown
                                className={cn("ml-1 h-3 w-3 transition-transform", isExpanded && "rotate-180")}
                              />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="bg-accent/30">
                        {bundle.insights.map((insight) => (
                          <div
                            key={insight.id}
                            className={cn(
                              "cursor-pointer px-4 py-2.5 pl-10 transition-colors hover:bg-accent/50 border-l-2 border-primary/40",
                              selectedInsight?.id === insight.id ? "bg-accent" : "",
                            )}
                            onClick={(e) => {
                              e.stopPropagation()
                              onSelectInsight(insight)
                            }}
                          >
                            <div className="flex items-start gap-2">
                              <Sparkles className="mt-0.5 h-3 w-3 shrink-0 text-primary" />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <h4 className="text-xs font-medium truncate">{insight.title}</h4>
                                  {insight.metadata.priority && (
                                    <Badge
                                      variant="outline"
                                      className={cn(
                                        "shrink-0 text-xs cursor-pointer hover:opacity-80 transition-opacity",
                                        getPriorityColor(insight.metadata.priority),
                                        priorityFilter === insight.metadata.priority && "ring-2 ring-primary",
                                      )}
                                      onClick={(e) => handlePriorityClick(insight.metadata.priority!, e)}
                                    >
                                      {insight.metadata.priority}
                                    </Badge>
                                  )}
                                </div>
                                <p className="mt-0.5 text-xs text-muted-foreground">
                                  {insight.relatedItems.length} items • {insight.generatedAt}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}

              {filteredStandaloneInsights.map((insight) => (
                <div
                  key={insight.id}
                  className={cn(
                    "cursor-pointer px-4 py-3 transition-colors hover:bg-accent/50",
                    selectedInsight?.id === insight.id ? "bg-accent" : "",
                  )}
                  onClick={() => onSelectInsight(insight)}
                >
                  {insight.status === "generating" ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Analyzing patterns...</span>
                      <span className="ml-auto text-xs text-muted-foreground">{insight.generatedAt}</span>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-start gap-2">
                        <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h3 className="text-sm font-medium truncate">{insight.title}</h3>
                            {insight.metadata.priority && (
                              <TooltipRoot delayDuration={300}>
                                <TooltipTrigger asChild>
                                  <Badge
                                    variant="outline"
                                    className={cn(
                                      "shrink-0 text-xs cursor-pointer hover:opacity-80 transition-opacity",
                                      getPriorityColor(insight.metadata.priority),
                                      priorityFilter === insight.metadata.priority && "ring-2 ring-primary",
                                    )}
                                    onClick={(e) => handlePriorityClick(insight.metadata.priority!, e)}
                                  >
                                    {insight.metadata.priority}
                                  </Badge>
                                </TooltipTrigger>
                                <TooltipPortal>
                                  <TooltipContent side="top" className="max-w-xs">
                                    <p className="text-xs">
                                      {insight.metadata.priorityReason || "Priority assigned by AI"}
                                    </p>
                                  </TooltipContent>
                                </TooltipPortal>
                              </TooltipRoot>
                            )}
                          </div>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            {insight.relatedItems.length} related {insight.relatedItems.length === 1 ? "item" : "items"}{" "}
                            • {insight.generatedAt}
                            {insight.metadata.involvedUsers && insight.metadata.involvedUsers.length > 0 && (
                              <> • Involves: {insight.metadata.involvedUsers.join(", ")}</>
                            )}
                          </p>
                          {insight.urgency && (
                            <div className="mt-1.5 flex items-center gap-1.5 text-xs">
                              <Clock className="h-3 w-3 text-orange-600" />
                              <span className="font-medium text-orange-600">{insight.urgency.deadline}</span>
                              <span className="text-muted-foreground">{insight.urgency.reason}</span>
                            </div>
                          )}

                          {insight.reasoning && (
                            <div className="mt-2">
                              <button
                                className="flex items-center gap-1.5 text-xs text-primary hover:underline"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setExpandedReasoning(expandedReasoning === insight.id ? null : insight.id)
                                }}
                              >
                                <Brain className="h-3 w-3" />
                                <span>Why is this {insight.metadata.priority} priority?</span>
                                <ChevronDown
                                  className={cn(
                                    "h-3 w-3 transition-transform",
                                    expandedReasoning === insight.id && "rotate-180",
                                  )}
                                />
                              </button>

                              {expandedReasoning === insight.id && (
                                <div className="mt-2 rounded-md border border-primary/20 bg-primary/5 p-2.5">
                                  <div className="mb-1.5 flex items-center justify-between">
                                    <span className="text-xs font-medium text-primary">AI detected:</span>
                                    <span className="text-xs text-muted-foreground">
                                      {insight.reasoning.confidence}% confidence
                                    </span>
                                  </div>
                                  <ul className="space-y-1">
                                    {insight.reasoning.factors.map((factor, index) => (
                                      <li key={index} className="text-xs text-muted-foreground">
                                        • {factor}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}

                          <Button
                            variant="ghost"
                            size="sm"
                            className="mt-2 h-7 text-xs font-medium text-primary hover:text-primary"
                            onClick={(e) => {
                              e.stopPropagation()
                              onSelectInsight(insight)
                            }}
                          >
                            {insight.actionLabel}
                            <ArrowRight className="ml-1 h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </TooltipProvider>
  )
}
