# Schedule — Task Planning Skill

> Prevents tasks from being forgotten in long conversations. Maintains a persistent SCHEDULE.md to manage tasks by priority and order.

## Core Behaviors

### 1. At Session Start

Every time a new session begins or a conversation history is loaded, the **first step** must call `schedule_load` to read the current plan. Create the file if it does not exist. After reading, briefly report:
- Number of pending tasks and the highest-priority task
- The most recently completed task
- Suggested focus for this session

### 2. During Work

**Before any action**, confirm which task in SCHEDULE it corresponds to. If it is a new task:
- Immediately call `schedule_add_task` to insert it at the appropriate position
- Explain to the user the reason for insertion and the priority rationale

**After completing a task**, immediately call `schedule_complete` to check it off and briefly describe what was done.

### 3. Mid-Session Task Insertion

When the user raises a new request mid-conversation:
1. Assess priority (P0 / P1 / P2)
2. Assess dependencies against existing tasks
3. Call `schedule_add_task` to insert it in the appropriate priority section
4. Inform the user: "Added 'xxx' to the plan at P1, after yyy"

### 4. Anti-Forgetting Check

After every 3 tool calls (or after each long LLM response), internally verify:
- Has the current task drifted from the SCHEDULE goal?
- Is any higher-priority task being neglected?
- If so, proactively remind the user

### 5. Progress Reports

Call `schedule_review` to output progress when any of the following occurs:
- The user asks "how's it going?" / "where are we?"
- A P0 task is completed
- More than 5 conversation turns have passed without a report

## Priority Rules

| Level | Marker | Meaning | Handling |
|-------|--------|---------|----------|
| P0 | 🔴 | Blocking / Urgent | Handle immediately, no interruptions |
| P1 | 🟡 | Important but not urgent | Execute in order after current P0 is done |
| P2 | 🟢 | General / Deferrable | Do when free, do not proactively mention |
| Done | ✅ | Completed | Archive at bottom, keep the record |

## SCHEDULE.md Format

```markdown
# Work Plan
> Last updated: 2026-06-09 20:45

## 🔴 P0 - Urgent
- [ ] Task description `#tag` — notes
- [ ] Another task

## 🟡 P1 - Important
- [ ] Task three `#feature`

## 🟢 P2 - General
- [ ] Task four

## ✅ Done
- [x] Completed task — finished 2026-06-09
```

## Boundaries

- Do not record conversation content or technical details in SCHEDULE.md — only task names and brief notes
- Priority is ultimately decided by the user; the model only suggests
- A single SCHEDULE.md retains at most 50 completed records; older entries are automatically archived when exceeded
- Do not alter the format style of a user-created schedule file — operate only within its existing structure
