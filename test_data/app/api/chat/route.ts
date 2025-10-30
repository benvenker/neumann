import { randomUUID } from "node:crypto"

import { createUIMessageStream, createUIMessageStreamResponse } from "ai"

import { getMcpClient } from "@/lib/mcp/client"

export const runtime = "nodejs"

const DEFAULT_SERVER_ID = "sequential-thinking"

type IncomingMessagePart = {
  type: string
  text?: string
}

type IncomingMessage = {
  id?: string
  role: string
  content?: string | null
  parts?: IncomingMessagePart[]
}

type ChatRequestBody = {
  messages?: IncomingMessage[]
  data?: {
    mcpServerId?: string
  }
}

const JSON_HEADERS = {
  "content-type": "application/json",
}

/**
 * Finds the most recent message with role "user" in the provided chat request body.
 *
 * @param body - The chat request payload; the function inspects `body.messages` if present.
 * @returns The last `IncomingMessage` whose `role` is `"user"`, or `undefined` if no such message exists.
 */
function extractUserMessage(body?: ChatRequestBody): IncomingMessage | undefined {
  if (!body?.messages || !Array.isArray(body.messages)) return undefined

  for (let i = body.messages.length - 1; i >= 0; i -= 1) {
    const message = body.messages[i]
    if (message?.role === "user") {
      return message
    }
  }

  return undefined
}

/**
 * Extracts the primary textual content from a chat message.
 *
 * Returns the trimmed `content` string if present and non-empty; otherwise concatenates `parts[*].text`, trims the result, and returns that string if non-empty. Returns `null` when no usable text is found.
 *
 * @param message - The incoming message object to extract text from
 * @returns The extracted text string, or `null` if no text is available
 */
function extractTextFromMessage(message?: IncomingMessage): string | null {
  if (!message) return null

  if (typeof message.content === "string" && message.content.trim().length > 0) {
    return message.content
  }

  if (Array.isArray(message.parts)) {
    const combined = message.parts
      .map((part) => part?.text ?? "")
      .join("")
      .trim()

    return combined.length > 0 ? combined : null
  }

  return null
}

/**
 * Normalize a requested MCP server identifier, falling back to the default when empty or invalid.
 *
 * @param requestedId - Value to interpret as a server id; if a non-empty string it will be trimmed
 * @returns The trimmed `requestedId` when it is a string with length greater than zero, otherwise `DEFAULT_SERVER_ID`
 */
function normalizeServerId(requestedId?: unknown): string {
  return typeof requestedId === "string" && requestedId.trim().length > 0
    ? requestedId.trim()
    : DEFAULT_SERVER_ID
}

type UIStreamWriter = Parameters<typeof createUIMessageStream>[0] extends {
  execute: (options: { writer: infer W }) => Promise<void> | void
}
  ? W
  : never

/**
 * Handle POST /api/chat requests by validating input, invoking an MCP "converse" tool, and streaming a UI message response.
 *
 * Parses the request body to extract the latest user message, resolves an MCP client for the requested server ID (or a default), calls the MCP "converse" tool with the user input, and returns a streaming UI response that emits text chunks and MCP content events. The stream is closed if the request is aborted.
 *
 * @returns A Response that streams UI messages:
 * - 200: streaming UI response with events for text chunks and MCP content/structured payloads when the request and MCP call succeed.
 * - 400: JSON parse failure, missing user message content, or MCP server-not-found errors (response includes `serverId` when relevant).
 * - 502: MCP client resolution failures unrelated to "not found".
 */
export async function POST(request: Request) {
  let body: ChatRequestBody

  try {
    body = (await request.json()) as ChatRequestBody
  } catch {
    return new Response(
      JSON.stringify({ error: "Invalid JSON body" }),
      { status: 400, headers: JSON_HEADERS },
    )
  }

  const latestUserMessage = extractUserMessage(body)
  const userInput = extractTextFromMessage(latestUserMessage)

  if (!userInput) {
    return new Response(
      JSON.stringify({ error: "Missing user message content" }),
      { status: 400, headers: JSON_HEADERS },
    )
  }

  const serverId = normalizeServerId(body?.data?.mcpServerId)

  let clientHandle: Awaited<ReturnType<typeof getMcpClient>>
  try {
    clientHandle = await getMcpClient(serverId)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    const status = /not found/i.test(message) ? 400 : 502

    return new Response(
      JSON.stringify({ error: message, serverId }),
      { status, headers: JSON_HEADERS },
    )
  }

  let aborted = false

  const abortHandler = () => {
    aborted = true
  }

  request.signal.addEventListener("abort", abortHandler, { once: true })

  const stream = createUIMessageStream({
    async execute({ writer }) {
      const shouldStop = () => aborted || request.signal.aborted
      const textChunk = createTextChunkWriter(writer, shouldStop)

      if (shouldStop()) {
        textChunk.end()
        return
      }

      try {
        const result = await clientHandle.client.callTool({
          name: "converse",
          arguments: { input: userInput },
        })

        if (shouldStop()) {
          textChunk.end()
          return
        }

        if (result.isError) {
          textChunk.write(`MCP server returned an error: ${result.error?.message ?? "Unknown error"}`)
        }

        for (const content of result.content ?? []) {
          if (shouldStop()) {
            break
          }

          if (content?.type === "text" && typeof content.text === "string") {
            textChunk.write(content.text)
            continue
          }

          if (shouldStop()) {
            break
          }

          writer.write({
            type: "data-mcp-content",
            data: {
              serverId,
              content,
            },
          })
        }

        if (shouldStop()) {
          textChunk.end()
          return
        }

        if (result.structuredContent) {
          writer.write({
            type: "data-mcp-structured",
            data: {
              serverId,
              content: result.structuredContent,
            },
          })
        }

        if (shouldStop()) {
          textChunk.end()
          return
        }

        if (!result.content?.length && !result.structuredContent) {
          textChunk.write("MCP server responded with no content.")
        }
      } catch (error) {
        console.error("MCP tool invocation failed", error)
        const message = error instanceof Error ? error.message : "Unknown error"
        textChunk.write(`Failed to contact MCP server: ${message}`)
      } finally {
        textChunk.end()
      }
    },
    onFinish: () => {
      request.signal.removeEventListener("abort", abortHandler)
    },
  })

  return createUIMessageStreamResponse({
    stream,
    headers: {
      "x-mcp-server-id": serverId,
    },
  })
}

/**
 * Creates a helper that groups successive text fragments into a single text chunk stream.
 *
 * @param writer - The UI stream writer used to emit framed text events.
 * @param shouldStop - A predicate that returns `true` when no further stream events should be emitted (for example, when the HTTP request was aborted).
 * @returns An object with `write(text)` to emit text deltas (automatically emitting a `text-start` before the first delta) and `end()` to emit the corresponding `text-end`.
 */
function createTextChunkWriter(writer: UIStreamWriter, shouldStop: () => boolean = () => false) {
  let textChunkId: string | null = null

  return {
    write(text: string) {
      if (!text) return
      if (shouldStop()) return

      if (!textChunkId) {
        textChunkId = randomUUID()
        writer.write({ type: "text-start", id: textChunkId })
      }

      writer.write({ type: "text-delta", id: textChunkId, delta: text })
    },
    end() {
      if (shouldStop()) return
      if (!textChunkId) return
      writer.write({ type: "text-end", id: textChunkId })
    },
  }
}
