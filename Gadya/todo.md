# Project TODO

## Core Features

- [x] Voice recognition service (speech-to-text)
- [x] Text-to-speech service for responses
- [x] LLM integration via server API
- [x] Dictation mode with real-time transcription

## Screens

- [x] Home screen with voice button and response display
- [x] Dictation screen with editing controls
- [x] Notes browser screen
- [x] Note detail screen
- [x] Settings screen

## Voice Features

- [x] Large voice activation button with animations
- [x] Waveform visualization during recording
- [x] Status indicators (Listening, Processing, Speaking)
- [x] Read-back functionality for dictation
- [x] Rephrase with AI assistance

## Notes Integration

- [x] Local markdown file storage
- [x] Notes search functionality
- [x] Note creation and editing
- [x] AI summarization of notes

## UI/UX

- [x] iOS-native look and feel
- [x] Dark/light mode support
- [x] Haptic feedback
- [x] Voice-first navigation
- [x] Tab navigation setup

## Branding

- [x] Custom app icon
- [x] App name and configuration

## Branding Update

- [x] Rebrand app as "Гадя"
- [x] Update app icon with user-provided image
- [x] Update app title in UI

## Custom Icons

- [x] Add custom microphone SVG icon with eyes

## Continuous Voice Mode

- [x] Install @react-native-voice/voice for native speech recognition
- [x] Implement continuous listening with auto-resume after response
- [x] Add voice activity detection
- [x] Wire up auto-listen setting toggle
- [x] Add stop command recognition

## Background Audio Mode

- [x] Configure iOS background audio entitlement in app.config.ts
- [x] Configure Android foreground service for background operation
- [x] Set up expo-av audio mode for background playback
- [x] Keep voice recognition active when app is backgrounded
- [ ] Add notification for background listening state (requires native build)

## Conversation Persistence

- [x] Save conversation history to AsyncStorage
- [x] Load conversation history on app start
- [x] Add clear history functionality

## Obsidian/Markdown File Integration

- [x] Configure base path for .md files (/storage/emulated/0/_/_/)
- [x] Implement file system access for Android storage
- [x] Search across all .md files (excluding dot folders)
- [x] Save new notes to Daily Notes subfolder
- [x] Add note search functionality to AI queries
- [x] Add Obsidian settings in Settings screen

## LangChain Backend Integration

- [x] Install LangChain dependencies
- [x] Create LangChain service with chat chain
- [x] Implement RAG chain for note search
- [x] Add rephrase chain for dictation editing
- [x] Add summarization chain
- [x] Keep basic dictation offline (native speech recognition via expo-av)
- [x] Update server routers to use LangChain

## Telemetry & Logging

- [x] Create telemetry service for client-side logging
- [x] Create server-side logging middleware
- [x] Add log collection endpoint (tRPC telemetry routes)
- [x] Implement log viewer/export for analysis

## Android Build Fix

- [x] Fix duplicate class conflicts between AndroidX and Support Library

## App Usability Fixes

- [x] Remove login requirement - app should work without authentication
- [x] Fix build warnings (100s of warnings reported) - Note: All warnings are from third-party libraries (react-native-screens, expo), not app code. Cannot be fixed in this codebase.
- [x] Configure GitHub SSH access using id_rsa app secret to push code
- [x] Update microphone icon with custom Гадя SVG design with status colors

## Claude Integration

- [x] Add "Ask Claude" voice command detection
- [x] Integrate Claude Sonnet 4 via LangChain using ANTHROPIC_KEY
- [x] Route Claude responses through TTS
