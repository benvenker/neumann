"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card } from "@/components/ui/card"
import { ArrowUp, Plus } from "lucide-react"

interface ChatInputSimpleProps {
  onSend?: (message: string) => void
  placeholder?: string
}

export function ChatInputSimple({ onSend, placeholder = "Ask AI..." }: ChatInputSimpleProps) {
  const [message, setMessage] = useState("")

  const handleSend = () => {
    if (message.trim() && onSend) {
      onSend(message)
      setMessage("")
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <Card className="overflow-hidden border border-border bg-card shadow-sm p-0">
      <Textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="min-h-[100px] resize-none border-0 bg-transparent p-4 text-sm focus-visible:ring-0"
      />
      <div className="flex items-center justify-between px-4 pb-3">
        <Button variant="ghost" size="sm" className="h-8 gap-2">
          <Plus className="h-4 w-4" />
        </Button>
        <Button size="sm" className="h-8 w-8 rounded-full p-0" onClick={handleSend}>
          <ArrowUp className="h-4 w-4" />
        </Button>
      </div>
    </Card>
  )
}
