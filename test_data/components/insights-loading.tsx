"use client"

import { Loader2, Sparkles } from "lucide-react"
import { useEffect, useState } from "react"

export function InsightsLoading() {
  const [elapsedTime, setElapsedTime] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedTime((prev) => prev + 1)
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  return (
    <div className="flex flex-col items-center justify-center p-8 space-y-4">
      <div className="relative">
        <Sparkles className="h-8 w-8 text-primary animate-pulse" />
        <Loader2 className="absolute -top-1 -right-1 h-4 w-4 animate-spin text-primary" />
      </div>
      <div className="text-center space-y-2">
        <p className="text-sm font-medium">Analyzing your notifications...</p>
        <p className="text-xs text-muted-foreground">Thinking time: {formatTime(elapsedTime)}</p>
      </div>
      <div className="flex flex-col items-center gap-1 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          <span>Scanning for patterns</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse delay-150" />
          <span>Identifying blockers</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse delay-300" />
          <span>Generating recommendations</span>
        </div>
      </div>
    </div>
  )
}
