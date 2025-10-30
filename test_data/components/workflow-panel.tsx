"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { CheckCircle2, ChevronDown, ChevronUp, Loader2, MessageSquare, Sparkles, X } from "lucide-react"
import type { WorkflowStep } from "@/lib/mock-inbox-data"

interface WorkflowPanelProps {
  steps: WorkflowStep[]
  insightTitle: string
  onClose: () => void
  onSwitchToChat: () => void
  width?: number
}

export function WorkflowPanel({
  steps: initialSteps,
  insightTitle,
  onClose,
  onSwitchToChat,
  width = 400,
}: WorkflowPanelProps) {
  const [steps, setSteps] = useState(initialSteps)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    summary: true,
    drafts: false,
  })

  const handleStepAction = (stepIndex: number, actionIndex: number) => {
    console.log("[v0] Workflow action:", { stepIndex, actionIndex })

    // Simulate action completion
    setSteps((prev) =>
      prev.map((step, idx) => {
        if (idx === stepIndex) {
          return { ...step, status: "completed" as const }
        }
        if (idx === stepIndex + 1) {
          return { ...step, status: "in_progress" as const }
        }
        return step
      }),
    )

    // Auto-expand next section
    if (stepIndex === 0) {
      setExpandedSections((prev) => ({ ...prev, drafts: true }))
    }
  }

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }))
  }

  useEffect(() => {
    setSteps(initialSteps)
  }, [initialSteps])

  const inProgressStep = steps.find((step) => step.status === "in_progress")
  const currentStep = inProgressStep || steps[0]

  return (
    <div className="relative flex h-full flex-col border-l border-border bg-background" style={{ width: `${width}px` }}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <h2 className="text-sm font-semibold">AI Assistant</h2>
          <span className="text-xs text-muted-foreground">|</span>
          <span className="text-xs text-muted-foreground">Working on this insight...</span>
        </div>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Workflow Title */}
      <div className="border-b border-border bg-muted/30 px-4 py-3">
        <p className="text-sm font-medium">{insightTitle}</p>
      </div>

      {/* Analysis Summary - Always visible at top */}
      <div className="border-b border-border bg-background px-4 py-3 space-y-2">
        {steps.map((step, idx) => {
          if (step.status === "completed") {
            return (
              <div key={idx} className="flex items-start gap-2 text-sm">
                <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-muted-foreground">{step.title}</span>
              </div>
            )
          }
          if (step.status === "in_progress") {
            return (
              <div key={idx} className="flex items-start gap-2 text-sm">
                <Loader2 className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5 animate-spin" />
                <span className="text-blue-600 font-medium">{step.title}</span>
              </div>
            )
          }
          return null
        })}
      </div>

      {/* Work Products - Immediately visible */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-4">
          {currentStep && currentStep.content && (
            <>
              {/* Summary Section */}
              {currentStep.content.some((c) => c.type === "summary" || c.type === "list") && (
                <Card className="overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between p-4 text-left hover:bg-muted/50 transition-colors"
                    onClick={() => toggleSection("summary")}
                  >
                    <h3 className="text-sm font-semibold">Summary ready to review</h3>
                    {expandedSections.summary ? (
                      <ChevronUp className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>

                  {expandedSections.summary && (
                    <div className="px-4 pb-4 space-y-3">
                      {currentStep.content.map((content, idx) => {
                        if (content.type === "summary") {
                          return (
                            <div key={idx} className="rounded-lg bg-muted/50 p-3">
                              <p className="text-sm leading-relaxed">{content.text}</p>
                            </div>
                          )
                        }
                        if (content.type === "list") {
                          return (
                            <div key={idx} className="space-y-2">
                              <p className="text-xs font-medium text-muted-foreground">{content.label}</p>
                              <ul className="space-y-2">
                                {content.items?.map((item, itemIdx) => (
                                  <li key={itemIdx} className="text-sm flex items-start gap-2">
                                    <span className="font-semibold text-muted-foreground">{itemIdx + 1}.</span>
                                    <span>{item}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )
                        }
                        return null
                      })}

                      {/* Actions for current step */}
                      {currentStep.actions && currentStep.actions.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2">
                          {currentStep.actions.map((action, actionIndex) => (
                            <Button
                              key={actionIndex}
                              variant={action.variant || "default"}
                              size="sm"
                              onClick={() => handleStepAction(steps.indexOf(currentStep), actionIndex)}
                              disabled={currentStep.status === "completed"}
                            >
                              {action.label}
                            </Button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              )}

              {/* Draft Responses Section */}
              {steps[1] && steps[1].content && steps[1].content.some((c) => c.type === "draft") && (
                <Card className="overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between p-4 text-left hover:bg-muted/50 transition-colors"
                    onClick={() => toggleSection("drafts")}
                  >
                    <h3 className="text-sm font-semibold">Draft responses ready</h3>
                    {expandedSections.drafts ? (
                      <ChevronUp className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>

                  {expandedSections.drafts && (
                    <div className="px-4 pb-4 space-y-3">
                      {steps[1].content.map((content, idx) => {
                        if (content.type === "draft") {
                          return (
                            <div key={idx} className="rounded-lg border border-border bg-background p-3 space-y-2">
                              <div className="flex items-center justify-between">
                                <p className="text-xs font-medium text-muted-foreground">{content.label}</p>
                                <Button variant="ghost" size="sm" className="h-6 text-xs">
                                  Edit
                                </Button>
                              </div>
                              <p className="text-sm leading-relaxed">{content.text}</p>
                            </div>
                          )
                        }
                        return null
                      })}

                      {/* Actions for draft step */}
                      {steps[1].actions && steps[1].actions.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2">
                          {steps[1].actions.map((action, actionIndex) => (
                            <Button
                              key={actionIndex}
                              variant={action.variant || "default"}
                              size="sm"
                              onClick={() => handleStepAction(1, actionIndex)}
                            >
                              {action.label}
                            </Button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              )}

              {/* Alternative Actions */}
              <div className="flex flex-col gap-2">
                <Button variant="outline" size="sm" className="w-full justify-start bg-transparent">
                  <MessageSquare className="h-4 w-4 mr-2" />
                  Generate meeting agenda instead
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start bg-transparent">
                  <Sparkles className="h-4 w-4 mr-2" />
                  Create summary email
                </Button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border p-4 space-y-2">
        <Button variant="outline" size="sm" className="w-full bg-transparent" onClick={onSwitchToChat}>
          <MessageSquare className="h-4 w-4 mr-2" />
          Switch to chat for refinement
        </Button>
        <p className="text-xs text-center text-muted-foreground">Chat available for questions or changes</p>
      </div>
    </div>
  )
}
