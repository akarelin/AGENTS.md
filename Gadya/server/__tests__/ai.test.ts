import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the LangChain service
vi.mock("../services/langchain", () => ({
  runChatChain: vi.fn().mockResolvedValue("This is a mocked AI response."),
  runRephraseChain: vi.fn().mockResolvedValue("This is a rephrased text."),
  runSummarizeChain: vi.fn().mockResolvedValue("This is a summary."),
  runRAGChain: vi.fn().mockResolvedValue("Based on your notes, here is the answer."),
  classifyIntent: vi.fn().mockResolvedValue("general_question"),
  extractSearchQuery: vi.fn().mockResolvedValue("test query"),
}));

import { appRouter } from "../routers";
import type { TrpcContext } from "../_core/context";
import * as langchain from "../services/langchain";

type AuthenticatedUser = NonNullable<TrpcContext["user"]>;

function createAuthContext(): TrpcContext {
  const user: AuthenticatedUser = {
    id: 1,
    openId: "test-user",
    email: "test@example.com",
    name: "Test User",
    loginMethod: "oauth",
    role: "user",
    createdAt: new Date(),
    updatedAt: new Date(),
    lastSignedIn: new Date(),
  };

  return {
    user,
    req: {
      protocol: "https",
      headers: {
        host: "localhost:3000",
      },
    } as TrpcContext["req"],
    res: {
      clearCookie: vi.fn(),
    } as unknown as TrpcContext["res"],
  };
}

describe("AI Routes with LangChain", () => {
  let ctx: TrpcContext;

  beforeEach(() => {
    vi.clearAllMocks();
    ctx = createAuthContext();
  });

  it("should call LangChain chat chain for chat requests", async () => {
    const caller = appRouter.createCaller(ctx);

    const result = await caller.ai.chat({
      message: "What is the weather like?",
    });

    expect(result.response).toBe("This is a mocked AI response.");
    expect(langchain.runChatChain).toHaveBeenCalledWith({
      input: "What is the weather like?",
      context: undefined,
      history: undefined,
    });
  });

  it("should call LangChain rephrase chain for rephrase requests", async () => {
    const caller = appRouter.createCaller(ctx);

    const result = await caller.ai.rephrase({
      text: "Hello world",
      style: "formal",
    });

    expect(result.rephrased).toBe("This is a rephrased text.");
    expect(langchain.runRephraseChain).toHaveBeenCalledWith({
      text: "Hello world",
      style: "formal",
    });
  });

  it("should call LangChain summarize chain for summarize requests", async () => {
    const caller = appRouter.createCaller(ctx);

    const result = await caller.ai.summarize({
      content: "This is a long text that needs to be summarized.",
      maxLength: "brief",
    });

    expect(result.summary).toBe("This is a summary.");
    expect(langchain.runSummarizeChain).toHaveBeenCalledWith({
      content: "This is a long text that needs to be summarized.",
      maxLength: "brief",
    });
  });

  it("should call LangChain RAG chain for note search requests", async () => {
    const caller = appRouter.createCaller(ctx);

    const result = await caller.ai.searchNotes({
      query: "project deadlines",
      noteContext: "Note 1: Project deadline is Friday.\nNote 2: Meeting scheduled.",
    });

    expect(result.response).toBe("Based on your notes, here is the answer.");
    expect(langchain.runRAGChain).toHaveBeenCalledWith({
      question: "project deadlines",
      context: "Note 1: Project deadline is Friday.\nNote 2: Meeting scheduled.",
    });
  });
});
