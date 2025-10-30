"use client"

import React, { type FormEvent, useMemo, useState } from "react"

import { useChat } from "@ai-sdk/react"
import type { UIMessage } from "ai"
import { UIResourceRenderer } from "@mcp-ui/client"
import { ArrowUp, Loader2, Server } from "lucide-react"

import mcpConfig from "../mcp.json"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

type McpConfig = typeof mcpConfig

type McpServerOption = {
  id: string
  label: string
}

type McpDataPart =
  | {
      type: "data-mcp-content"
      data?: {
        serverId?: string
        content?: unknown
      }
    }
  | {
      type: "data-mcp-structured"
      data?: {
        serverId?: string
        content?: unknown
      }
    }

const FALLBACK_SERVER_ID = "sequential-thinking"
const SERVER_OPTIONS = createServerOptions(mcpConfig as McpConfig)
const DEFAULT_SERVER_ID = SERVER_OPTIONS[0]?.id ?? FALLBACK_SERVER_ID

/**
 * Renders the "Model Context Protocol Chat" interface including server selection, message list, streaming response handling, and the input form.
 *
 * The component displays guidance when no servers are configured, a ready state when there are servers but no messages, the list of chat messages (with support for streaming and MCP payload rendering), a loading indicator with a cancel action, and an error card when a request fails. It also provides a server dropdown and a textarea for sending prompts to the selected MCP server.
 *
 * @returns A JSX element containing the chat UI.
 */
export default function ChatSection() {
  const [serverId, setServerId] = useState<string>(DEFAULT_SERVER_ID)
  const chatOptions = useMemo(
    () => ({
      api: "/api/chat",
      body: { mcpServerId: serverId },
    }),
    [serverId],
  )

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    stop,
  } = useChat(chatOptions)

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!input.trim()) return
    handleSubmit()
  }

  const serverListEmpty = SERVER_OPTIONS.length === 0

  return (
    <main className="flex flex-1 flex-col overflow-hidden">
      <div className="mx-auto flex h-full w-full max-w-3xl flex-1 flex-col">
        <header className="border-b border-border px-6 py-5">
          <h1 className="text-xl font-medium text-foreground">Model Context Protocol Chat</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Select an MCP server and send a prompt to stream responses directly into the chat UI.
          </p>
        </header>

        <ScrollArea className="flex-1">
          <div className="space-y-4 px-6 py-6">
            {serverListEmpty && (
              <Card className="border border-dashed border-border/70 bg-muted/30 p-6 text-sm text-muted-foreground">
                <p className="font-medium text-foreground">No MCP servers configured.</p>
                <p className="mt-2">
                  Add servers to <code>mcp.json</code> to enable streaming responses. The dropdown and chat form will
                  unlock automatically once a server is available.
                </p>
              </Card>
            )}

            {!serverListEmpty && messages.length === 0 && (
              <Card className="border border-dashed border-border/70 bg-muted/30 p-6 text-sm text-muted-foreground">
                <p className="font-medium text-foreground">Ready when you are.</p>
                <p className="mt-2">
                  Pick an MCP server below, describe a task, and the response will stream in once the server starts
                  replying.
                </p>
              </Card>
            )}

            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                <span>Awaiting response&hellip;</span>
                <Button type="button" variant="ghost" size="sm" className="h-7 px-2" onClick={stop}>
                  Cancel
                </Button>
              </div>
            )}

            {error && (
              <Card className="border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
                <p className="font-medium">Request failed</p>
                <p className="mt-1 whitespace-pre-line">{error.message}</p>
              </Card>
            )}
          </div>
        </ScrollArea>

        <form onSubmit={onSubmit} className="border-t border-border bg-background/95 px-6 py-5">
          <div className="mb-3 flex items-center gap-3">
            <Select
              value={serverId}
              onValueChange={setServerId}
              disabled={isLoading || serverListEmpty}
            >
              <SelectTrigger className="h-10 w-full max-w-sm">
                <div className="flex w-full items-center gap-2">
                  <Server className="h-4 w-4" aria-hidden />
                  <SelectValue placeholder="Select MCP server" />
                </div>
              </SelectTrigger>
              <SelectContent>
                {SERVER_OPTIONS.map((option) => (
                  <SelectItem key={option.id} value={option.id}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Card className="overflow-hidden border border-border bg-card shadow-sm">
            <Textarea
              value={input}
              onChange={handleInputChange}
              placeholder={serverListEmpty ? "Configure an MCP server to enable chat" : "Describe a task for the selected MCP server"}
              disabled={isLoading || serverListEmpty}
              className="min-h-[120px] resize-none border-0 bg-transparent p-4 text-base focus-visible:ring-0"
            />
            <div className="flex items-center justify-end gap-2 px-4 pb-3">
              <Button type="submit" size="sm" className="h-9 w-9 rounded-full p-0" disabled={isLoading || serverListEmpty}>
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <ArrowUp className="h-4 w-4" />}
                <span className="sr-only">Send message</span>
              </Button>
            </div>
          </Card>
        </form>
      </div>
    </main>
  )
}

/**
 * Render a chat message bubble aligned and styled according to the message role.
 *
 * Renders each part of the provided `message` using MessagePart and aligns the bubble
 * to the right for user messages and to the left for assistant messages.
 *
 * @param message - The chat message to render, including its role and parts
 * @returns The JSX element containing the styled message bubble
 */
function MessageBubble({ message }: { message: UIMessage }) {
  const isUser = message.role === "user"
  const isAssistant = message.role === "assistant"
  const bubbleClasses = cn(
    "max-w-full rounded-xl border px-4 py-3 text-sm shadow-sm md:max-w-[75%]",
    isUser ? "border-transparent bg-primary text-primary-foreground" : "border-border bg-card text-foreground",
  )

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div className={bubbleClasses}>
        <div className="space-y-3">
          {message.parts.map((part, index) => (
            <MessagePart
              key={`${message.id}-${index}-${getPartTypeKey(part)}`}
              part={part}
              isAssistant={isAssistant}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

/**
 * Render a single message part into its appropriate UI representation.
 *
 * Renders:
 * - `text`: a paragraph preserving whitespace,
 * - `reasoning`: a small italicized note that appends an underscore while streaming,
 * - MCP data parts: the MCP payload renderer,
 * - any other type: a preformatted JSON fallback.
 *
 * @param part - One part of a `UIMessage` describing its content and type
 * @param isAssistant - Whether the message part comes from the assistant (affects MCP payload styling)
 * @returns A React element that visually represents the provided message part
 */
function MessagePart({
  part,
  isAssistant,
}: {
  part: UIMessage["parts"][number]
  isAssistant: boolean
}) {
  if (part.type === "text") {
    return <p className="whitespace-pre-wrap break-words">{part.text}</p>
  }

  if (part.type === "reasoning") {
    return (
      <p className="text-xs italic text-muted-foreground">
        {part.text}
        {part.state === "streaming" ? "_" : null}
      </p>
    )
  }

  if (isMcpDataPart(part)) {
    return <McpPayload part={part} isAssistant={isAssistant} />
  }

  return (
    <pre className="whitespace-pre-wrap break-words rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
      {JSON.stringify(part, null, 2)}
    </pre>
  )
}

/**
 * Renders an MCP data payload as a rich resource view or a JSON fallback.
 *
 * Renders the part's `data.content` with UIResourceRenderer inside a styled container when the part is a `data-mcp-content` and the content is a plain object; otherwise renders a preformatted JSON fallback of the part's data.
 *
 * @param part - The MCP data part to render.
 * @param isAssistant - When true, apply assistant-specific container styling.
 * @returns A React element that displays the MCP payload or its JSON fallback.
 */
function McpPayload({ part, isAssistant }: { part: McpDataPart; isAssistant: boolean }) {
  if (part.type === "data-mcp-content" && isPlainObject(part.data?.content)) {
    return (
      <div
        className={cn("rounded-md border p-3", isAssistant ? "border-border bg-muted/60" : "border-border/40")}
      >
        <UIResourceRenderer resource={part.data!.content as Record<string, unknown>} />
      </div>
    )
  }

  const fallback = part.data?.content ?? part.data

  return (
    <pre className="whitespace-pre-wrap break-words rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
      {JSON.stringify(fallback, null, 2)}
    </pre>
  )
}

/**
 * Build an array of server selection options from the MCP configuration.
 *
 * @param config - The MCP configuration object that contains an `mcpServers` map
 * @returns An array of `{ id, label }` options derived from the keys of `config.mcpServers`
 */
function createServerOptions(config: McpConfig): McpServerOption[] {
  const servers = config?.mcpServers ?? {}
  return Object.keys(servers).map((id) => ({
    id,
    label: formatServerLabel(id),
  }))
}

/**
 * Convert a server identifier into a human-readable label.
 *
 * @param id - Server identifier with segments separated by `-` or `_`
 * @returns The identifier formatted as space-separated, capitalized words (falls back to `id` if formatting produces an empty string)
 */
function formatServerLabel(id: string): string {
  const label = id
    .split(/[-_]/g)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ")

  return label.length > 0 ? label : id
}

/**
 * Checks whether a chat message part represents MCP data.
 *
 * @param part - A single part from a UI message
 * @returns `true` if the part's type is `"data-mcp-content"` or `"data-mcp-structured"`, `false` otherwise.
 */
function isMcpDataPart(part: UIMessage["parts"][number]): part is McpDataPart {
  const type = getPartTypeKey(part)
  return type === "data-mcp-content" || type === "data-mcp-structured"
}

/**
 * Extracts the type discriminator string from a message part.
 *
 * @param part - A message part object which may include a `type` field
 * @returns The `type` string from `part` if present and a string, otherwise `"unknown"`.
 */
function getPartTypeKey(part: UIMessage["parts"][number]): string {
  return typeof (part as { type?: unknown }).type === "string" ? (part as { type: string }).type : "unknown"
}

/**
 * Checks whether a value is a plain object (an object that is not null and not an array).
 *
 * @param value - The value to test
 * @returns `true` if `value` is an object, not `null`, and not an array; `false` otherwise.
 */
function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}