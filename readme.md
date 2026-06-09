# SkillServer

A personal skill library.This repository stores custom skills, persistent agent memory, and identity configuration files.

## Directory Structure

```
SkillServer/
├── SKILLS/                  # Installed skill definitions
│   ├── schedule-skill/      # Task planning and anti-forgetting skill
│   ├── toolshell/           # Controlled file ops, shell execution & memory skill
│   └── gurobi-expert/       # Gurobi Optimizer 13.0 expert skill
├── memory/
│   ├── FACT.md              # Durable knowledge (active projects, decisions, facts)
│   └── JOURNAL.jsonl        # Append-only event log (session notes, completed tasks)
├── SOUL.md                  # Agent identity: personality, tone, principles
├── USER.md                  # User profile: name, preferences, timezone, context
└── readme.md                # This file
```

## Skills

### schedule-skill

Prevents tasks from being forgotten in long conversations. Maintains a persistent `SCHEDULE.md` file with P0/P1/P2 priority tiers. Auto-loads the plan at session start, tracks task completion, and triggers progress reports at key milestones.

### toolshell

Wraps Claude's built-in file and shell tools with a configurable safety layer. Reads a `memory.json` config from the project root to determine operation mode (`normal` for confirm-before-act, `auto` for fully autonomous), and optionally stores/recalls cross-session memory via SQLite (with optional Qdrant vector search).

### gurobi-expert

A deep-knowledge assistant for Gurobi Optimizer 13.0. Covers LP, MIP, QP, NLP, multi-objective optimization, decomposition methods, and classical OR problems (TSP, VRP, scheduling, etc.). Includes reference documents and code templates.

## Memory

| File | Purpose |
|------|---------|
| `SOUL.md` | Defines the agent's role, tone, and principles for this user |
| `USER.md` | Stores user profile information learned over time |
| `memory/FACT.md` | Long-lived facts: projects, tech decisions, durable knowledge |
| `memory/JOURNAL.jsonl` | Time-stamped event log; never edited directly — use the memory tool |

## Usage

This directory is loaded automatically by the CherryClaw agent at the start of each session. Skills are discovered via symlinks managed by the agent SDK. Memory files are read and written by the agent using dedicated tools — do not edit `JOURNAL.jsonl` by hand.

To add a new skill, use the skill management tool (`mcp__skills__skills`) with the `init` and `register` actions, or install from the marketplace with `install`.
