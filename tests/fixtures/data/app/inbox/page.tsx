"use client"

import { useState, useEffect } from "react"
import TopNav from "@/components/top-nav"
import { InboxNav } from "@/components/inbox-nav"
import { InboxList } from "@/components/inbox-list"
import { InboxDetail } from "@/components/inbox-detail"
import { InboxInsightsList } from "@/components/inbox-insights-list"
import { InboxInsightsDetail } from "@/components/inbox-insights-detail"
import { InboxRightSidebar } from "@/components/inbox-right-sidebar"
import { mockInboxItems, mockInsights, mockInsightBundles } from "@/lib/mock-inbox-data"
import type { InboxItem, InsightItem, InsightBundle, WorkflowStep } from "@/lib/mock-inbox-data"

const DEFAULT_LIST_WIDTH = 384 // 96 * 4 = 384px (w-96)
const LIST_WIDTH_STORAGE_KEY = "inbox-list-width"
const DEFAULT_RIGHT_SIDEBAR_WIDTH = 400
const RIGHT_SIDEBAR_WIDTH_STORAGE_KEY = "inbox-right-sidebar-width"

export default function InboxPage() {
  const [selectedItem, setSelectedItem] = useState<InboxItem | null>(mockInboxItems[0])
  const [selectedInsight, setSelectedInsight] = useState<InsightItem | null>(null)
  const [selectedBundle, setSelectedBundle] = useState<InsightBundle | null>(null)
  const [activeFilter, setActiveFilter] = useState<string>("inbox")
  const [priorityFilter, setPriorityFilter] = useState<string | null>(null)
  const [highlightedCommentId, setHighlightedCommentId] = useState<string | undefined>(undefined)
  const [isRightSidebarCollapsed, setIsRightSidebarCollapsed] = useState(true)
  const [chatContext, setChatContext] = useState<string | null>(null)
  const [listWidth, setListWidth] = useState(DEFAULT_LIST_WIDTH)
  const [isResizing, setIsResizing] = useState(false)
  const [rightSidebarWidth, setRightSidebarWidth] = useState(DEFAULT_RIGHT_SIDEBAR_WIDTH)
  const [isResizingRightSidebar, setIsResizingRightSidebar] = useState(false)
  const [sidebarMode, setSidebarMode] = useState<"chat" | "workflow">("chat")
  const [workflowData, setWorkflowData] = useState<{ steps: WorkflowStep[]; insightTitle: string } | undefined>()

  useEffect(() => {
    const savedWidth = localStorage.getItem(LIST_WIDTH_STORAGE_KEY)
    if (savedWidth) {
      setListWidth(Number(savedWidth))
    }
    const savedRightWidth = localStorage.getItem(RIGHT_SIDEBAR_WIDTH_STORAGE_KEY)
    if (savedRightWidth) {
      setRightSidebarWidth(Number(savedRightWidth))
    }
  }, [])

  useEffect(() => {
    localStorage.setItem(LIST_WIDTH_STORAGE_KEY, listWidth.toString())
  }, [listWidth])

  useEffect(() => {
    localStorage.setItem(RIGHT_SIDEBAR_WIDTH_STORAGE_KEY, rightSidebarWidth.toString())
  }, [rightSidebarWidth])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing && !isResizingRightSidebar) return

      if (isResizing) {
        const leftNavWidth = 256
        const newWidth = e.clientX - leftNavWidth
        const constrainedWidth = Math.max(300, Math.min(600, newWidth))
        setListWidth(constrainedWidth)
      }

      if (isResizingRightSidebar) {
        const newWidth = window.innerWidth - e.clientX
        const constrainedWidth = Math.max(300, Math.min(700, newWidth))
        setRightSidebarWidth(constrainedWidth)
      }
    }

    const handleMouseUp = () => {
      setIsResizing(false)
      setIsResizingRightSidebar(false)
    }

    if (isResizing || isResizingRightSidebar) {
      document.addEventListener("mousemove", handleMouseMove)
      document.addEventListener("mouseup", handleMouseUp)
      document.body.style.userSelect = "none"
      document.body.style.cursor = "col-resize"
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove)
      document.removeEventListener("mouseup", handleMouseUp)
      document.body.style.userSelect = ""
      document.body.style.cursor = ""
    }
  }, [isResizing, isResizingRightSidebar])

  const handleSelectItem = (item: InboxItem) => {
    setSelectedItem(item)
    setSelectedInsight(null)
    setSelectedBundle(null)
    if (item.type === "conversation" && item.commentId) {
      setHighlightedCommentId(item.commentId)
    } else {
      setHighlightedCommentId(undefined)
    }
  }

  const handleSelectInsight = (insight: InsightItem) => {
    setSelectedInsight(insight)
    setSelectedItem(null)
    setSelectedBundle(null)
  }

  const handleSelectBundle = (bundle: InsightBundle) => {
    setSelectedBundle(bundle)
    setSelectedInsight(null)
    setSelectedItem(null)
  }

  const handleStartWorkflow = (insight: InsightItem) => {
    if (insight.workflow && insight.workflow.length > 0) {
      setWorkflowData({
        steps: insight.workflow,
        insightTitle: insight.title,
      })
      setSidebarMode("workflow")
    } else {
      setChatContext(insight.actionPrompt)
      setSidebarMode("chat")
    }

    if (rightSidebarWidth < 400) {
      setRightSidebarWidth(DEFAULT_RIGHT_SIDEBAR_WIDTH)
    }
    setIsRightSidebarCollapsed(false)
  }

  const handleFilterChange = (filter: string) => {
    setActiveFilter(filter)
    setPriorityFilter(null)
    if (filter === "insights") {
      setSelectedItem(null)
      if (mockInsightBundles.length > 0) {
        setSelectedBundle(mockInsightBundles[0])
        setSelectedInsight(null)
      } else {
        setSelectedInsight(mockInsights[0] || null)
        setSelectedBundle(null)
      }
    } else {
      setSelectedInsight(null)
      setSelectedBundle(null)
      setSelectedItem(mockInboxItems[0] || null)
    }
  }

  const filteredItems = mockInboxItems.filter((item) => {
    if (activeFilter === "inbox") return true
    if (activeFilter === "reviews") return item.type === "review_requested"
    if (activeFilter === "agent-tasks") return item.type === "agent_completed"
    if (activeFilter === "conversations") return item.type === "conversation"
    if (activeFilter === "my-issues") return item.type === "assigned"
    return true
  })

  const filteredInsights = mockInsights.filter((insight) => {
    if (!priorityFilter) return true
    return insight.metadata?.priority === priorityFilter
  })

  return (
    <div className="flex h-screen flex-col bg-background">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        <InboxNav
          activeFilter={activeFilter}
          onFilterChange={handleFilterChange}
          counts={{
            inbox: mockInboxItems.length,
            reviews: mockInboxItems.filter((i) => i.type === "review_requested").length,
            agentTasks: mockInboxItems.filter((i) => i.type === "agent_completed").length,
            conversations: mockInboxItems.filter((i) => i.type === "conversation").length,
            myIssues: mockInboxItems.filter((i) => i.type === "assigned").length,
            insights: mockInsights.length,
          }}
        />

        {activeFilter === "insights" ? (
          <>
            <div className="relative flex">
              <InboxInsightsList
                insights={filteredInsights}
                bundles={mockInsightBundles}
                selectedInsight={selectedInsight}
                selectedBundle={selectedBundle}
                onSelectInsight={handleSelectInsight}
                onSelectBundle={handleSelectBundle}
                width={listWidth}
                priorityFilter={priorityFilter}
                onPriorityFilterChange={setPriorityFilter}
              />

              <div
                className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500 transition-colors z-10"
                onMouseDown={() => setIsResizing(true)}
                style={{
                  backgroundColor: isResizing ? "rgb(59 130 246)" : "transparent",
                }}
              />
            </div>

            {selectedBundle ? (
              <InboxInsightsDetail
                insight={selectedBundle.insights[0]}
                bundle={selectedBundle}
                onStartWorkflow={handleStartWorkflow}
              />
            ) : (
              <InboxInsightsDetail insight={selectedInsight} onStartWorkflow={handleStartWorkflow} />
            )}
          </>
        ) : (
          <>
            <div className="relative flex">
              <InboxList
                items={filteredItems}
                selectedItem={selectedItem}
                onSelectItem={handleSelectItem}
                width={listWidth}
              />

              <div
                className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500 transition-colors z-10"
                onMouseDown={() => setIsResizing(true)}
                style={{
                  backgroundColor: isResizing ? "rgb(59 130 246)" : "transparent",
                }}
              />
            </div>

            <InboxDetail item={selectedItem} highlightedCommentId={highlightedCommentId} />
          </>
        )}

        <InboxRightSidebar
          isCollapsed={isRightSidebarCollapsed}
          onToggle={() => setIsRightSidebarCollapsed(!isRightSidebarCollapsed)}
          width={rightSidebarWidth}
          onResizeStart={() => setIsResizingRightSidebar(true)}
          chatContext={chatContext}
          onClearContext={() => setChatContext(null)}
          mode={sidebarMode}
          workflowData={workflowData}
          onModeChange={setSidebarMode}
        />
      </div>
    </div>
  )
}
