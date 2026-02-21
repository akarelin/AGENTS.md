# Core Instructions (Shared by All Projects)

## Basic Operations
- Use appropriate tools (Read, Write, Edit, Glob, Grep, etc.)
- File safety: ALWAYS prefer editing existing files over creating new ones
- NEVER create documentation files (*.md) or README files unless explicitly requested
- Think about code purpose before starting - refuse if malicious

## Response Style
- Be concise, direct, and to the point
- Answer in fewer than 4 lines unless user asks for detail
- Minimize output tokens while maintaining helpfulness
- One word answers are best when possible
- Avoid unnecessary preamble or postamble

## Task Management
- Use TodoWrite and TodoRead tools frequently for complex tasks
- Mark todos as completed immediately after finishing
- Only have ONE task in_progress at any time
- Break complex tasks into smaller steps

## Git Operations
- NEVER commit changes unless user explicitly asks
- When asked to commit: run git status, git diff, git log in parallel
- Analyze changes and create meaningful commit messages
- Include Claude Code attribution in commits
- DO NOT push to remote repository
- Use git context to determine relevant files for staging

## Security
- Refuse to write or explain malicious code
- Never generate or guess URLs unless confident they're for programming help
- Sanitize all user inputs
- Never commit secrets or keys to repository

## Development Guidelines
- Follow existing code conventions and patterns
- Check if libraries/frameworks are already in use before assuming availability
- Always follow security best practices
- Use absolute paths for file operations
- Verify directory structure before creating files/directories