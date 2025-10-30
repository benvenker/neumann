import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { UIMessage } from "ai"
import React from "react"
import { vi, expect, describe, it, beforeEach } from "vitest"

type UseChatState = {
  messages: UIMessage[]
  input: string
  handleInputChange: (event: unknown) => void
  handleSubmit: (event?: unknown) => void
  isLoading: boolean
  error?: Error
  stop: () => void
}

const mockUseChat = vi.fn<(options: unknown) => UseChatState>()
const uiResourceRendererMock = vi.fn(
  ({ resource }: { resource: unknown }) => (
    <div data-testid="ui-resource">{JSON.stringify(resource)}</div>
  ),
)

vi.mock("@ai-sdk/react", () => ({
  useChat: (options: unknown) => mockUseChat(options),
}))

vi.mock("@mcp-ui/client", () => ({
  UIResourceRenderer: uiResourceRendererMock,
}))

function createHookState(overrides: Partial<UseChatState> = {}): UseChatState {
  return {
    messages: [],
    input: "",
    handleInputChange: vi.fn(),
    handleSubmit: vi.fn(),
    isLoading: false,
    error: undefined,
    stop: vi.fn(),
    ...overrides,
  }
}

describe("ChatSection", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("initializes the chat hook with the default MCP server and renders the empty state", async () => {
    mockUseChat.mockImplementation(() => createHookState())

    const { default: ChatSection } = await import("./chat-section")

    render(
      <React.StrictMode>
        <ChatSection />
      </React.StrictMode>,
    )

    expect(mockUseChat).toHaveBeenCalledWith({
      api: "/api/chat",
      body: { mcpServerId: "sequential-thinking" },
    })

    expect(
      screen.getByText("Select an MCP server and send a prompt to stream responses directly into the chat UI."),
    ).toBeInTheDocument()
    expect(screen.getByText("Ready when you are.")).toBeInTheDocument()
  })

  it("renders streamed MCP payloads and allows canceling an in-flight request", async () => {
    const stopMock = vi.fn()
    const messages: UIMessage[] = [
      {
        id: "user-1",
        role: "user",
        parts: [{ type: "text", text: "Generate a plan" }],
      },
      {
        id: "assistant-1",
        role: "assistant",
        parts: [
          { type: "text", text: "Working on it..." },
          {
            type: "data-mcp-content",
            data: {
              serverId: "sequential-thinking",
              content: { kind: "resource", title: "Demo card" },
            },
          } as unknown as UIMessage["parts"][number],
        ],
      },
    ]

    mockUseChat.mockImplementation(() =>
      createHookState({
        messages,
        isLoading: true,
        stop: stopMock,
      }),
    )

    const { default: ChatSection } = await import("./chat-section")

    render(
      <React.StrictMode>
        <ChatSection />
      </React.StrictMode>,
    )

    expect(uiResourceRendererMock).toHaveBeenCalled()
    const calls = uiResourceRendererMock.mock.calls
    const lastCall = calls[calls.length - 1]
    const [{ resource }] = lastCall
    expect(resource).toMatchObject({ kind: "resource", title: "Demo card" })
    expect(screen.getByTestId("ui-resource")).toBeInTheDocument()

    const user = userEvent.setup()
    await user.click(screen.getByRole("button", { name: "Cancel" }))
    expect(stopMock).toHaveBeenCalledTimes(1)
  })
})
