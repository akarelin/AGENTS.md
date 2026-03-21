import { ChatOpenAI } from "@langchain/openai";
import { ChatAnthropic } from "@langchain/anthropic";
import { 
  ChatPromptTemplate, 
  MessagesPlaceholder,
  HumanMessagePromptTemplate,
  SystemMessagePromptTemplate,
} from "@langchain/core/prompts";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { RunnableSequence } from "@langchain/core/runnables";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import { ENV } from "../_core/env";

// Resolve the API URL - ensure it ends with /v1 for OpenAI compatibility
const resolveBaseUrl = () => {
  const baseUrl = ENV.forgeApiUrl && ENV.forgeApiUrl.trim().length > 0
    ? ENV.forgeApiUrl.replace(/\/$/, "")
    : "";
  
  // LangChain's ChatOpenAI expects base URL without /v1/chat/completions
  // It will append the path automatically
  return baseUrl.endsWith("/v1") ? baseUrl : `${baseUrl}/v1`;
};

// Initialize the LLM with Forge API (OpenAI-compatible)
const createLLM = () => {
  return new ChatOpenAI({
    openAIApiKey: ENV.forgeApiKey,
    configuration: {
      baseURL: resolveBaseUrl(),
    },
    modelName: "gemini-2.5-flash",
    temperature: 0.7,
    maxTokens: 2048,
  });
};

// ============================================
// CHAT CHAIN - Main conversational AI
// ============================================

const chatSystemPrompt = `You are Гадя (Gadya), a helpful voice AI assistant. You provide clear, concise responses that are easy to understand when read aloud.

Guidelines:
- Keep responses brief but informative (2-4 sentences for simple questions)
- Use natural, conversational language
- Avoid bullet points and complex formatting - responses will be spoken
- If context from user's notes is provided, use it to give personalized answers
- Be friendly and helpful

{context}`;

const chatPrompt = ChatPromptTemplate.fromMessages([
  SystemMessagePromptTemplate.fromTemplate(chatSystemPrompt),
  new MessagesPlaceholder("history"),
  HumanMessagePromptTemplate.fromTemplate("{input}"),
]);

export interface ChatInput {
  input: string;
  context?: string;
  history?: Array<{ role: "user" | "assistant"; content: string }>;
}

export async function runChatChain(params: ChatInput): Promise<string> {
  const llm = createLLM();
  
  const chain = RunnableSequence.from([
    {
      input: (input: ChatInput) => input.input,
      context: (input: ChatInput) => 
        input.context ? `\nContext from user's notes:\n${input.context}` : "",
      history: (input: ChatInput) => {
        if (!input.history || input.history.length === 0) return [];
        return input.history.map(msg => 
          msg.role === "user" 
            ? new HumanMessage(msg.content)
            : new AIMessage(msg.content)
        );
      },
    },
    chatPrompt,
    llm,
    new StringOutputParser(),
  ]);

  const result = await chain.invoke(params);
  return result;
}

// ============================================
// RAG CHAIN - Note search and retrieval
// ============================================

const ragSystemPrompt = `You are a helpful assistant that answers questions based on the user's personal notes.

Given the following context from the user's notes, answer their question. If the context doesn't contain relevant information, say so honestly but try to be helpful with general knowledge.

Context from notes:
{context}

Important:
- Reference specific notes when relevant
- Keep answers concise and suitable for voice output
- If no relevant context is found, acknowledge this and provide general help`;

const ragPrompt = ChatPromptTemplate.fromMessages([
  SystemMessagePromptTemplate.fromTemplate(ragSystemPrompt),
  HumanMessagePromptTemplate.fromTemplate("{question}"),
]);

export interface RAGInput {
  question: string;
  context: string;
}

export async function runRAGChain(params: RAGInput): Promise<string> {
  const llm = createLLM();
  
  const chain = RunnableSequence.from([
    ragPrompt,
    llm,
    new StringOutputParser(),
  ]);

  const result = await chain.invoke(params);
  return result;
}

// ============================================
// REPHRASE CHAIN - Dictation editing
// ============================================

const rephrasePrompts: Record<string, string> = {
  formal: `You are a writing assistant. Rephrase the following text in a more formal, professional tone.
Maintain the original meaning but use more sophisticated vocabulary and structure.
Return only the rephrased text without any explanation.`,

  casual: `You are a writing assistant. Rephrase the following text in a more casual, conversational tone.
Make it sound natural and friendly, as if speaking to a friend.
Return only the rephrased text without any explanation.`,

  concise: `You are a writing assistant. Make the following text more concise and to the point.
Remove unnecessary words while preserving the core meaning.
Return only the rephrased text without any explanation.`,

  expanded: `You are a writing assistant. Expand on the following text with more detail and explanation.
Add relevant context and elaboration while maintaining the original message.
Return only the rephrased text without any explanation.`,

  default: `You are a writing assistant. Improve the following text for clarity and flow.
Fix any grammatical issues and enhance readability while preserving the original meaning.
Return only the rephrased text without any explanation.`,
};

export interface RephraseInput {
  text: string;
  style?: "formal" | "casual" | "concise" | "expanded";
}

export async function runRephraseChain(params: RephraseInput): Promise<string> {
  const llm = createLLM();
  
  const systemPrompt = rephrasePrompts[params.style || "default"];
  
  const prompt = ChatPromptTemplate.fromMessages([
    SystemMessagePromptTemplate.fromTemplate(systemPrompt),
    HumanMessagePromptTemplate.fromTemplate("{text}"),
  ]);

  const chain = RunnableSequence.from([
    prompt,
    llm,
    new StringOutputParser(),
  ]);

  const result = await chain.invoke({ text: params.text });
  return result;
}

// ============================================
// SUMMARIZE CHAIN - Note summarization
// ============================================

const summarizePrompts: Record<string, string> = {
  brief: `You are a summarization assistant. Provide a very brief summary in 2-3 sentences.
Focus only on the most critical points. This will be read aloud, so keep it concise.`,

  medium: `You are a summarization assistant. Provide a moderate summary covering the main points.
Include key information but keep it suitable for voice output (about 4-6 sentences).`,

  detailed: `You are a summarization assistant. Provide a comprehensive summary covering all important aspects.
Be thorough but still organized and clear for voice output.`,
};

export interface SummarizeInput {
  content: string;
  maxLength?: "brief" | "medium" | "detailed";
}

export async function runSummarizeChain(params: SummarizeInput): Promise<string> {
  const llm = createLLM();
  
  const systemPrompt = summarizePrompts[params.maxLength || "medium"];
  
  const prompt = ChatPromptTemplate.fromMessages([
    SystemMessagePromptTemplate.fromTemplate(systemPrompt),
    HumanMessagePromptTemplate.fromTemplate("Please summarize the following:\n\n{content}"),
  ]);

  const chain = RunnableSequence.from([
    prompt,
    llm,
    new StringOutputParser(),
  ]);

  const result = await chain.invoke({ content: params.content });
  return result;
}

// ============================================
// CLAUDE CHAIN - Ask Claude Opus 4
// ============================================

const createClaudeLLM = () => {
  const apiKey = ENV.anthropicKey;
  if (!apiKey) {
    throw new Error("ANTHROPIC_KEY is not configured");
  }
  
  return new ChatAnthropic({
    anthropicApiKey: apiKey,
    modelName: "claude-sonnet-4-20250514",
    temperature: 0.7,
    maxTokens: 2048,
  });
};

const claudeSystemPrompt = `You are Claude, an AI assistant made by Anthropic. You are being accessed through Гадя (Gadya), a voice AI assistant app.

Guidelines:
- Provide thoughtful, nuanced responses
- Keep responses suitable for voice output (avoid complex formatting)
- Be helpful, harmless, and honest
- You can engage in deeper analysis and reasoning when asked

{context}`;

const claudePrompt = ChatPromptTemplate.fromMessages([
  SystemMessagePromptTemplate.fromTemplate(claudeSystemPrompt),
  new MessagesPlaceholder("history"),
  HumanMessagePromptTemplate.fromTemplate("{input}"),
]);

export interface ClaudeInput {
  input: string;
  context?: string;
  history?: Array<{ role: "user" | "assistant"; content: string }>;
}

export async function runClaudeChain(params: ClaudeInput): Promise<string> {
  const llm = createClaudeLLM();
  
  const chain = RunnableSequence.from([
    {
      input: (input: ClaudeInput) => input.input,
      context: (input: ClaudeInput) => 
        input.context ? `\nContext from user's notes:\n${input.context}` : "",
      history: (input: ClaudeInput) => {
        if (!input.history || input.history.length === 0) return [];
        return input.history.map(msg => 
          msg.role === "user" 
            ? new HumanMessage(msg.content)
            : new AIMessage(msg.content)
        );
      },
    },
    claudePrompt,
    llm,
    new StringOutputParser(),
  ]);

  const result = await chain.invoke(params);
  return result;
}

// ============================================
// VOICE COMMAND PARSER - Detect intents
// ============================================

const intentPrompt = `You are an intent classifier for a voice assistant. Analyze the user's input and determine the intent.

Possible intents:
- "ask_claude": User explicitly wants to ask Claude (e.g., "Ask Claude...", "Hey Claude...", "Claude, ...")
- "search_notes": User wants to search or find something in their notes
- "save_note": User wants to save or create a note
- "summarize": User wants to summarize something
- "rephrase": User wants to rephrase or reword text
- "general_question": General question or conversation
- "stop": User wants to stop or end the conversation

Respond with ONLY the intent name, nothing else.

User input: {input}`;

export async function classifyIntent(input: string): Promise<string> {
  const llm = createLLM();
  
  const prompt = ChatPromptTemplate.fromTemplate(intentPrompt);
  
  const chain = RunnableSequence.from([
    prompt,
    llm,
    new StringOutputParser(),
  ]);

  const result = await chain.invoke({ input });
  return result.trim().toLowerCase();
}

// ============================================
// EXTRACT SEARCH QUERY - For note search
// ============================================

const extractQueryPrompt = `Extract the search query from the user's request about searching their notes.
Return only the key terms to search for, nothing else.

Examples:
- "Search my notes for project deadlines" → "project deadlines"
- "Find notes about machine learning" → "machine learning"
- "What did I write about the meeting with John?" → "meeting John"

User input: {input}`;

export async function extractSearchQuery(input: string): Promise<string> {
  const llm = createLLM();
  
  const prompt = ChatPromptTemplate.fromTemplate(extractQueryPrompt);
  
  const chain = RunnableSequence.from([
    prompt,
    llm,
    new StringOutputParser(),
  ]);

  const result = await chain.invoke({ input });
  return result.trim();
}
