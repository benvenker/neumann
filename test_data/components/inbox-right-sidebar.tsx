"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { MessageSquare, Plus, Clock, Maximize2, X } from "lucide-react"
import { ChatInputSimple } from "@/components/chat-input-simple"
import { WorkflowPanel } from "@/components/workflow-panel"
import { cn } from "@/lib/utils"
import type { WorkflowStep } from "@/lib/mock-inbox-data"

interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

interface InboxRightSidebarProps {
  isCollapsed: boolean
  onToggle: () => void
  width?: number
  onResizeStart?: () => void
  chatContext?: string | null
  onClearContext?: () => void
  mode?: "chat" | "workflow"
  workflowData?: {
    steps: WorkflowStep[]
    insightTitle: string
  }
  onModeChange?: (mode: "chat" | "workflow") => void
}

const mockMessages: ChatMessage[] = [
  {
    id: "1",
    role: "assistant",
    content:
      "Hi! I'm your AI assistant. I can help you with code reviews, issue analysis, and task management. What would you like to work on?",
    timestamp: new Date(Date.now() - 3600000),
  },
  {
    id: "2",
    role: "user",
    content: "Can you help me review PR #42?",
    timestamp: new Date(Date.now() - 3000000),
  },
  {
    id: "3",
    role: "assistant",
    content:
      "I'd be happy to help review PR #42. Let me analyze the changes and provide feedback on code quality, potential issues, and suggestions for improvement.",
    timestamp: new Date(Date.now() - 2900000),
  },
]

export function InboxRightSidebar({
  isCollapsed,
  onToggle,
  width = 400,
  onResizeStart,
  chatContext,
  onClearContext,
  mode = "chat",
  workflowData,
  onModeChange,
}: InboxRightSidebarProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(mockMessages)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    if (chatContext) {
      const contextMessage: ChatMessage = {
        id: Date.now().toString(),
        role: "assistant",
        content: chatContext,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, contextMessage])
      onClearContext?.()
    }
  }, [chatContext, onClearContext])

  const handleSendMessage = (content: string) => {
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date(),
    }
    setMessages([...messages, newMessage])

    setTimeout(() => {
      const aiResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "I'm processing your request. This is a simulated response for demonstration purposes.",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, aiResponse])
    }, 1000)
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  }

  if (mode === "workflow" && workflowData && !isCollapsed) {
    return (
      <WorkflowPanel
        steps={workflowData.steps}
        insightTitle={workflowData.insightTitle}
        onClose={onToggle}
        onSwitchToChat={() => onModeChange?.("chat")}
        width={width}
      />
    )
  }

  if (isCollapsed) {
    return (
      <div className="flex w-16 flex-col items-center gap-4 border-l border-border bg-background py-4">
        <Avatar className="h-8 w-8">
          <AvatarFallback className="text-xs">AI</AvatarFallback>
        </Avatar>
        <Button variant="ghost" size="sm" className="h-10 w-10 p-0" onClick={onToggle} title="Open AI Chat">
          <MessageSquare className="h-5 w-5" />
        </Button>
        <Button variant="ghost" size="sm" className="h-10 w-10 p-0" title="New Chat">
          <Plus className="h-5 w-5" />
        </Button>
        <Button variant="ghost" size="sm" className="h-10 w-10 p-0" title="History">
          <Clock className="h-5 w-5" />
        </Button>
        <div className="flex-1" />
        <Button variant="ghost" size="sm" className="h-10 w-10 p-0" title="Expand">
          <Maximize2 className="h-5 w-5" />
        </Button>
      </div>
    )
  }

  return (
    <div className="relative flex flex-col border-l border-border bg-background" style={{ width: `${width}px` }}>
      <div
        className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500 transition-colors z-10"
        onMouseDown={onResizeStart}
      />

      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Avatar className="h-6 w-6">
            <AvatarFallback className="text-xs">AI</AvatarFallback>
          </Avatar>
          <h2 className="text-sm font-semibold">AI Assistant</h2>
        </div>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={onToggle}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Chat Messages */}
      <ScrollArea className="flex-1 p-4">
        <div ref={scrollRef} className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn("flex gap-3", message.role === "user" ? "justify-end" : "justify-start")}
            >
              {message.role === "assistant" && (
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarFallback className="text-xs">AI</AvatarFallback>
                </Avatar>
              )}
              <div
                className={cn(
                  "max-w-[80%] rounded-lg px-3 py-2 text-sm",
                  message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
                )}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                <p className="mt-1 text-xs opacity-70">{formatTime(message.timestamp)}</p>
              </div>
              {message.role === "user" && (
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarFallback className="text-xs">U</AvatarFallback>
                </Avatar>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Chat Input */}
      <div className="border-t border-border p-4">
        <ChatInputSimple onSend={handleSendMessage} placeholder="Ask AI about this notification..." />
      </div>
    </div>
  )
}
