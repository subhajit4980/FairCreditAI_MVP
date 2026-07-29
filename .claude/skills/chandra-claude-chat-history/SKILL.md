---
name: chandra-claude-chat-history
description: >-
  Maintain a verbatim-style transcript of the current session in chat-history.md.
  Use when the user asks to log, record, capture, or update the chat history
  "the way we interact" / "do not summarize" — e.g. "log our chat history",
  "write chat-history.md", "keep a transcript of this session", "append this to
  the chat history". Records user messages quoted exactly as written and
  assistant replies reproduced as sent (NOT summarized), appending new turns
  without rewriting prior history.
---

# Chandra — Claude Chat History

Maintain a running, **verbatim-style** transcript of the session in a
`chat-history.md` file. The whole point is fidelity: capture the actual
back-and-forth, not a summary.

## Where to write

- Default: `chat-history.md` at the **repository root** (or the project root if
  not a git repo). If the user names a different path, use that.
- If the file already exists, **Read it first, then append** — never discard or
  rewrite earlier turns.

## Format

Group by session, newest content appended within the current session. Use this
structure:

```markdown
# Chat History — <Project Name>

> Verbatim-style transcript. User messages quoted as written; assistant replies
> reproduced as sent. System/automated events marked _[system]_. This is a
> record, not a summary.

---

# Session — <YYYY-MM-DD> · Branch `<branch>` · <user-identifier>

---

**User:**
> <the user's message, quoted EXACTLY as written — keep typos, casing, links>

**Claude:**
<the assistant's reply, reproduced as it was actually sent>

---

**User:**
> <next message verbatim>

**Claude:**
<next reply as sent>
```

End the file with an HTML-comment template for the next turn so future updates
are easy.

## Rules

1. **Do not summarize, paraphrase, or "clean up" the user's words.** Quote each
   user message verbatim inside a `>` blockquote — including typos, casing, and
   URLs.
2. **Reproduce assistant replies as they were sent.** If a reply is very long or
   was mostly tool-call narration, you may collapse the pure "what I did between
   messages" parts into a short italic note in parentheses, e.g.
   `_(Explored the repo and read the provider services.)_`, but keep the actual
   prose that was shown to the user intact.
3. **Mark non-dialogue events** with `_[system]_` — e.g. a user message that
   arrived mid-task, an agent/tool completion that drove the next reply, or a
   stop-hook. These keep the flow readable without pretending they were part of
   the conversation.
4. **Chronological order**, oldest turn at the top of the session.
5. **Append, don't rewrite.** New turns go after the last recorded turn (before
   the trailing template comment). Start a new `# Session —` header when a new
   day/branch/session begins.
6. Keep a one-line **session header** with date, git branch (`git branch
   --show-current`), and a user identifier (email/name) when known.
7. After updating, if the project's convention is to commit logs, stage and
   commit `chat-history.md` only when the user has asked you to keep it updated
   or explicitly requests a commit — otherwise just save the file.

## Trigger examples

- "log our chat history" / "keep a chat history of this session"
- "write chat-history.md the way you and me are interacting, do not summarize"
- "append this conversation to the chat history"
- "update the chat history log"

## Non-goals

- Not a decisions/summary doc (that belongs in a separate features/decisions log).
- Do not include raw tool output, full system prompts, or secrets verbatim;
  reference them as `_[system]_` events instead.
</content>
