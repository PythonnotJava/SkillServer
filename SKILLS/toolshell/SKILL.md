# ToolShell - LLM Tool Shell Skill

> When this skill is active, you gain controlled file operations, shell command execution, and persistent memory capabilities.

## Trigger Conditions

Auto-activates when a `memory.json` file exists in the project root, or when the user explicitly requests ToolShell mode.

## Startup Flow

Upon activation, execute in order:

1. Read `memory.json` in the project root and parse the configuration
2. Determine the operation mode (MODE) and memory strategy (MIND / REMIND)
3. If REMIND=true, retrieve relevant historical memory from `.toolshell/memory.db`
4. Inject the retrieved memory into the current context and begin work

## Configuration Fields

Read from `memory.json`:

| Field | Value | Meaning |
|-------|-------|---------|
| MODE | "normal" | Prompt the user for confirmation before each file operation or command execution |
| MODE | "auto" | Fully autonomous — execute all operations directly |
| REMIND | true/false | Whether to recall historical memory before starting a task |
| MIND | true | Long-term memory: persisted across sessions |
| MIND | false | Short-term memory: valid for the current session only |

## Operation Mode Behavior

### normal mode

Before every destructive operation, confirm using this format:

```
[ToolShell] Operation: WRITE → src/main.dart (new file, 42 lines)
Proceed? [y/N/always]
```

User replies:
- y → execute this time
- N → skip
- always → switch to auto mode for this session

### auto mode

All operations execute directly without confirmation. Safety boundaries still apply.

## Safety Boundaries (apply to both modes)

Paths that must never be touched:
- `.git/` directory
- `.env` / `.env.*` files
- `node_modules/`
- `*.pem` / `*.key` private key files
- Any path outside the project root

## Memory System

### Storage Location

`.toolshell/memory.db` (SQLite) under the project root

### When to Store Memory

Proactively identify and store the following:
- **fact**: Facts stated by the user, project conventions, technology choices
- **decision**: Decisions made and their rationale
- **context**: Project background and architecture information
- **error**: Mistakes encountered, failed approaches
- **outcome**: Task completion results

### Importance Scoring

- 0.8–1.0: Core architecture decisions, strongly emphasized user preferences
- 0.5–0.7: General context, moderately important facts
- 0.1–0.4: Temporary information, trivial details

Guiding question: Will this information still matter in 6 months? Yes → score ≥ 0.7

### When to Recall Memory

- When REMIND=true, automatically recall before each new task begins
- When the user asks "what have we worked on before?" — recall proactively
- When encountering a problem that may have a relevant historical decision — recall proactively

### Vector Search (optional)

If `memory.json` provides the following three fields and the API is reachable:
- QDRANT_EMBED_MODEL_URL
- QDRANT_EMBED_MODEL_KEY
- QDRANT_EMBED_MODEL_NAME

Then generate vector embeddings when storing memory and use semantic similarity ranking during recall.
Otherwise fall back to SQLite keyword matching.

## Tool Usage Guidelines

Rules for using your existing tools (Read / Write / Bash, etc.) under this skill:

### File Reading
Use the Read tool normally. Record key file paths that were read into memory.

### File Writing
- normal mode: display the changes first, then write after confirmation
- auto mode: write directly

### Command Execution
- Use the Bash tool to execute shell commands
- For long-running commands (build, install), warn the user that waiting may be required
- On command failure, store the error information in memory (type=error)

### File Deletion
- normal mode: must confirm
- auto mode: execute directly, but record to memory

## Session End

At the end of a session:
- If MIND=true: memory is retained
- If MIND=false: generate a summary of this session stored as a single fact entry, then clear all other memory
