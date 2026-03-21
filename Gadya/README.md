# Gadya (Гадя)

A voice-first iOS/Android mobile assistant built with React Native / Expo and TypeScript. Designed for hands-free, one-handed interaction with LLMs — speak a question, get an AI answer read aloud, and optionally save or search personal notes via voice.
**Status:** All major features are implemented and checked complete.

### Core Capabilities

- **Continuous voice mode** — tap once to start; the app listens, transcribes, sends to AI, speaks the response via TTS, then auto-resumes listening. Stop with "stop", "стоп", "хватит", or "enough".
- **Dual LLM routing** — default model is Gemini 2.5 Flash; say "Ask Claude..." or "Клод,..." to route to Claude Sonnet 4 via Anthropic API.
- **Dictation mode** — record speech, transcribe, then rephrase with AI (formal / casual / concise / expanded) and save as a markdown note.
- **Obsidian integration** — reads `.md` files from Android external storage, searches them for context, and injects the top 3 matching notes into the AI prompt (RAG).
- **Background audio** — keeps listening while the app is backgrounded (iOS audio/voip/fetch/processing entitlements; Android foreground service with microphone).

### Screens

| Screen | Purpose |
|--------|---------|
| **Home** | Main voice interface — large mic button, conversation cards, mode toggle (Ask AI / Dictate) |
| **Dictate** | Dedicated dictation mode with rephrase and save-to-note |
| **Notes** | Browse and search local markdown notes |
| **Note Detail** | View and edit a single note |
| **Settings** | App configuration |

### LangChain Chains (Backend)

The backend (`server/services/langchain.ts`) implements seven chains:

| Chain | Model | Purpose |
|-------|-------|---------|
| **Chat** | Gemini 2.5 Flash | Main conversational AI with conversation history and Obsidian context |
| **Claude** | Claude Sonnet 4 | On-demand Claude routing triggered by voice commands |
| **RAG** | Gemini 2.5 Flash | Answers questions grounded in personal notes, cites sources |
| **Rephrase** | Gemini 2.5 Flash | Rewrites dictated text in a chosen style |
| **Summarize** | Gemini 2.5 Flash | Summarizes notes at brief/medium/detailed length |
| **Intent Classifier** | Gemini 2.5 Flash | Detects voice command intent (ask_claude, search_notes, save_note, etc.) |
| **Search Query Extractor** | Gemini 2.5 Flash | Pulls search terms from natural language |

### Voice System

The continuous voice mode (`hooks/use-continuous-voice.ts`) is a state machine:

```
idle → listening → processing → speaking → (auto-resume) → listening
                                         → (manual) → idle
```

- Uses `@react-native-voice/voice` (native) with Web Speech API fallback
- Partial results displayed while user speaks
- Error recovery: auto-restarts on "No match" and "Client side" errors
- App backgrounding: pauses/resumes gracefully

### Technology Stack

Expo ~54, React Native 0.81, React 19, TypeScript. Backend: Express + tRPC v11, Drizzle ORM (MySQL/TiDB), S3 storage. Voice: `@react-native-voice/voice`, `expo-speech` (TTS), `expo-av` (audio recording). LLM: `@langchain/openai`, `@langchain/anthropic`, `langchain` (TypeScript).

### Build & CI

GitHub Actions workflow (`.github/workflows/build-android.yml`) for automated Android builds. App works without authentication (login requirement removed).
