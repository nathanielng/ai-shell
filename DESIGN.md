# ai-shell Design Principles

A reference for building composable, maintainable CLI tools inspired by Unix philosophy.

## Executive Summary

ai-shell follows the Unix philosophy: **build small, focused tools that do one thing well and work together through standard interfaces**. This creates exponential composability — 10 focused tools can create hundreds of useful combinations, whereas monolithic tools plateau quickly.

The cost of this approach is simplicity and discipline. Each new tool requires saying "no" to features and "yes" to fundamental design principles.

---

## Core Design Principles

### 1. Do One Thing and Do It Well
Each tool has a **single, clearly-defined responsibility**. No combining extraction + summarization in one tool. No embedding output logic that belongs to the caller.

**Examples:**
- ✅ `youtube_transcriber.py` — fetch transcript, output to stdout
- ✅ `social_media_extractor.py` — extract metadata, output to stdout
- ✅ `strands_cli.py` — send text to AI, output response to stdout
- ❌ `extract-and-summarize.py` — bundles two separate responsibilities
- ❌ `transcriber.py` that saves directly to database — assumes caller wants database storage instead of letting them choose (pipe, file, process, etc.)

**The Pike & Kernighan Test:** If a job is already done well by existing tools (sed, awk, grep), don't add it as an option to your tool. Don't add `-n` (numbering) to cat when `awk` already does it perfectly. Don't add `-v` (visible chars) to cat when a separate `vis` program is cleaner.

**Test:** Can this tool be described in one sentence without "and"? Does it duplicate functionality better provided by existing tools?

### 2. Text Streams as Universal Interface
All input/output flows as **plain text** through stdin/stdout. This is the contract that enables composition.

**Examples:**
- ✅ `cat urls.csv | social_media_extractor.py | strands_cli.py "Summarize"`
- ✅ Tools output to stdout by default; `-o FILE` redirects to file
- ❌ Tools that write side-effects to hardcoded files without consent
- ❌ Tools that emit JSON/CSV internally instead of plain text

**Implication:** The caller decides format, destination, and chaining — not the tool.

### 3. Stable Interfaces
Input/output contracts stay constant even as implementations change. Tools can evolve internally without breaking pipelines.

**What's stable:**
- Command-line argument structure (`-o`, `-s`, `-m` flags)
- Input format (URLs, text, CSV rows)
- Output format (plain text, one record per line for CSV)
- Exit codes (0 = success, non-zero = failure)

**What can change:**
- Internal API calls (YouTube API, Bedrock API)
- Performance optimizations
- Error recovery logic

### 4. Design for Composition
Build tools that combine in **unexpected ways**. Avoid encoding assumptions about how results will be used.

**Good composition patterns:**
```bash
# Extraction → Processing → Output
youtube_transcriber.py <url> | strands_cli.py "Summarize" > summary.txt

# Filtering → Counting → Reporting
cat urls.csv | social_media_extractor.py | grep -E "high-value" | wc -l

# Multi-stage transformation
youtube_transcriber.py <url> \
  | strands_cli.py "Extract key points" \
  | strands_cli.py -s "You are a tweet writer" "Turn into a tweet"
```

**Anti-patterns (encoding caller intent):**
```bash
# ❌ Tool saves to database without asking
# transcriber.py automatically saves to database
# Now caller CAN'T do: transcriber.py | strands_cli.py "Summarize"
# Or: transcriber.py > file.txt
# The tool removed the caller's choices.

# ✅ Better: Tool outputs to stdout
# transcriber.py outputs transcript to stdout
# Now caller CAN do ANY of these:
transcriber.py <url> | strands_cli.py "Summarize"
transcriber.py <url> > file.txt
transcriber.py <url> | save_to_db.py
transcriber.py <url> | head -50 | less
```

**Other anti-patterns:**

```bash
# ❌ Tool defaults to JSON (breaks pipes)
social_media_extractor.py  # Outputs JSON, caller must use jq
python extractor.py <url> | grep "author"  # Greps JSON structure, not data
# Fixed: python extractor.py <url> | jq '.author' | grep "name"  # Extra overhead

# ✅ Tool defaults to plain text, JSON optional
python extractor.py <url>                  # Outputs CSV (readable)
python extractor.py <url> --json | jq '.author'  # Caller chooses JSON if needed
```

More anti-patterns:
```bash
# Tool decides output location (breaks composition)
social_media_extractor.py  # Assumes caller wants urls.csv

# Tool embeds domain logic (can't reuse)
extract-and-categorize.py  # Assumes caller wants categorization
```

### 5. Optimize for Understanding
**Simple, transparent designs are more maintainable than clever ones.** Code clarity > performance micro-optimizations. Error messages should explain failure reasons, not just fail silently.

**Critical Rule: Programs must not be aware of their execution context.** Don't change behavior based on whether output is a terminal vs. a pipe. Example: Berkeley's `ls` prints in columns to a terminal but single-column to a pipe — this is "distasteful" and breaks composition. Programs should produce the same output regardless of destination.

**Examples:**
- Clear function names: `extract_video_id()` over `parse_url()`
- Minimal abstractions: solve the immediate problem, not hypothetical futures
- Verbose error output: `Could not fetch transcript for VIDEO_ID: [reason]`
- Helpful usage messages on `-h`/invalid args
- ✅ **OK**: Check `sys.stdin.isatty()` to determine if input is piped (affects reading stdin)
- ❌ **Never**: Check `sys.stdout.isatty()` to change output format (breaks composition)
- ❌ Never assume output goes to terminal and add special formatting (like Berkeley's `ls` does)

### 6. Plan for Change
Systems should grow incrementally without requiring wholesale redesign. As the tool count grows, maintain structure and prevent cognitive overload.

---

## The Option Creep Problem (Crucial)

Pike & Kernighan documented this in their seminal paper: Unix programs accumulate options over time until they become unrecognizable. The `cat` program went from having **zero options** to Berkeley adding:
- `-s` — strip multiple blank lines
- `-n` — number output lines
- `-b` — number non-blank lines only
- `-v` — make non-printing characters visible

**The problem:** Each of these jobs is already done well by existing tools:
- Line numbering: `awk '{ print NR "\t" $0 }'` or `nl`
- Blank line stripping: `sed '/^$/d'`
- Making chars visible: a separate `vis` program

**The rule:** When you're tempted to add an option, ask:
1. **Is there an existing tool that does this?** If yes, use that tool in a pipeline instead.
2. **Does this option belong to the tool's core responsibility?** If not, it's option creep.
3. **Would this make sense as a separate tool?** If yes, build it as a separate tool.

**Example Decision Tree:**

```
Feature request: "Add -n flag to youtube_transcriber.py to number lines"

├─ Is this the transcriber's job? NO
├─ Does numbering exist elsewhere? YES (awk, nl, cat with -n)
├─ Decision: REJECT. User runs: youtube_transcriber.py <url> | awk '{ print NR "\t" $0 }'
```

```
Feature request: "Add -o flag to strands_cli.py to write output to file"

├─ Is this the agent's job? It's related to output delivery.
├─ Does output control exist elsewhere? YES (shell redirection >)
├─ Decision: ACCEPT (but as -o, not a pipeline, since interactive tools need it)
```

The temptation to add options grows proportionally with a tool's age. **Resist it.** Options should be for variations on the core task, not for entirely different tasks.

---

## Design Patterns

### Pattern: Tool Symmetry
All tools follow a consistent structure for discoverability:

```python
#!/usr/bin/env python3
"""Single-sentence description.

Usage examples with common scenarios.
"""

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("input", nargs="?", help="Primary input")
    parser.add_argument("-o", "--output", help="Write to file instead of stdout")
    # ... other flags
    args = parser.parse_args()

    # Read stdin if piped (OK to check isatty for input availability, NOT for output format)
    stdin_text = None
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read().strip()

    # Combine args + stdin
    if args.input and stdin_text:
        data = f"{args.input}\n\n---\n\n{stdin_text}"
    else:
        data = args.input or stdin_text

    # Process
    result = process(data)

    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
    else:
        print(result)

if __name__ == "__main__":
    main()
```

This pattern ensures:
- All tools accept stdin + args (supports piping and direct invocation)
- All tools output to stdout (piping-friendly) with `-o` for file redirection
- All tools have consistent help (`-h`)
- All tools can be imported as modules

### Pattern: CSV as Sequence Format
For multi-record operations (e.g., `social_media_extractor.py`), use CSV:
- **Output to stdout** as CSV (one row per record)
- **Input from stdin** as CSV or as a file arg
- Let the **caller** decide if results move to platform-specific files or merge

```bash
# Reader decides destination
cat urls.csv | social_media_extractor.py | tee linkedin.csv instagram.csv
```

### Pattern: Module + CLI Duality
Tools are usable both as CLI and as Python modules:

```python
# CLI
python youtube_transcriber.py https://youtube.com/watch?v=...

# Module
from youtube_transcriber import get_transcript
text = get_transcript("VIDEO_ID")
```

This allows embedding in larger workflows without subprocess overhead.

### Pattern: Strands Agent Scripts (.ai Format)

Agent scripts define AI agent instances in a declarative, Unix-friendly format. Each `.ai` file specifies model, parameters, tools, and system prompt.

**Format:**
```
#!/usr/bin/env aish.py
#@ model: {BEDROCK_MODEL}
#@ temperature: 0.3
#@ max_tokens: 2048
#@ tools: file_read, file_write
#@ skills: summarize, format

You are an executive assistant that processes meeting notes...
```

**Components:**
- **Shebang**: `#!/usr/bin/env aish.py` makes the script executable
- **Directives** (`#@`): Configuration with environment variable substitution
- **System prompt**: Everything below directives is the agent's instructions

**Environment Variable Substitution (Zone 1: Directives Only)**

Directives support `{VAR_NAME}` syntax to substitute environment variables from `.env`:

```
#@ model: {BEDROCK_MODEL}        # Expands to value of $BEDROCK_MODEL
#@ temperature: {AISH_TEMP}      # Expands to value of $AISH_TEMP
```

**Security Design:**

Variable substitution is restricted to directives (not system prompts) for safety:

1. **Trusted zone (directives):** `{VAR_NAME}` substitution allowed
   - Reason: Directives are configuration (metadata), not language
   - Examples: model ID, temperature, tool names, skills
   - Safe: System can't be reinterpreted by variable values

2. **Untrusted zone (system prompt):** No substitution
   - Reason: Prevents prompt injection attacks
   - Risk: `You are {ROLE}` with untrusted `ROLE` could inject instructions
   - Defense: System prompt is fixed; environment only affects configuration

3. **Variable source:** `.env` only (not stdin/args)
   - Reason: `.env` is filesystem-protected; user input is untrusted
   - Pattern: `load_dotenv()` reads from project `.env` before parsing

**Example with .env:**

`.env`:
```
BEDROCK_MODEL=us.amazon.nova-lite-v1:0
AISH_TEMPERATURE=0.3
AISH_MAX_TOKENS=2048
```

`summarize.ai`:
```
#!/usr/bin/env aish.py
#@ model: {BEDROCK_MODEL}
#@ temperature: {AISH_TEMPERATURE}
#@ max_tokens: {AISH_MAX_TOKENS}

You are a summarization expert. Analyze the input and produce a concise summary...
```

**Why This Design:**

- **Composability:** Scripts are text files, can be versioned, templated, shared
- **Unix alignment:** Shebang makes them executable; `.env` follows 12-factor app conventions
- **Security:** Clear separation between configuration (variable) and instructions (fixed)
- **Simplicity:** Minimal parsing; directives are key-value pairs

**Supported Directives:**
- `model`: Bedrock model ID (supports variable substitution)
- `temperature`: Sampling temperature 0-1 (supports variable substitution)
- `max_tokens`: Max output tokens (supports variable substitution)
- `tools`: Comma-separated tool names (supports variable substitution)
- `skills`: Comma-separated skill names (supports variable substitution, for Agent Skills standard)

### Pattern: Optional JSON Output (Not Default)

**When JSON makes sense:**
- Data structure is complex (nested objects, variable fields)
- Primary consumer is other programs, not humans
- Plain text/CSV can't represent the structure adequately

**The rule:** JSON is **always optional via `--json` flag**, never the default.

**Why:** Plain text default keeps pipes working without extra parsing:

```bash
# Plain text (default) — works in pipes naturally
python extractor.py <url> | grep "author"

# JSON (optional) — requires jq for piping
python extractor.py <url> --json | jq '.author' | grep "name"
```

**Implementation:**

```python
import json
import argparse
import csv
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--json", action="store_true",
                       help="Output as JSON (default: plain text)")
    args = parser.parse_args()

    # Tool does its job
    result = extract_metadata(args.url)  # Returns dict

    # Format based on caller's choice
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Plain text: human-readable, pipe-friendly (DEFAULT)
        print(f"Title: {result['title']}")
        print(f"Author: {result['author']}")
```

**Usage comparison:**

```bash
# Plain text (human-readable, works in pipes)
python extractor.py https://linkedin.com/posts/...
# Output:
# Title: How to Build Unix Tools
# Author: Jane Doe

# JSON (for programs that need structure)
python extractor.py https://linkedin.com/posts/... --json
# Output:
# {
#   "title": "How to Build Unix Tools",
#   "author": "Jane Doe",
#   "engagement": {"likes": 234, "comments": 12}
# }
```

**For multiple records: Use JSONL (JSON Lines)**

When a tool outputs multiple records (like `social_media_extractor.py`), use JSONL format — one JSON object per line:

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output as JSON Lines")
    args = parser.parse_args()

    results = extract_all_urls()  # List of dicts

    if args.json:
        # JSONL: one JSON object per line (parseable by jq, sed, awk)
        for result in results:
            print(json.dumps(result))
    else:
        # CSV (default, human-readable)
        writer = csv.DictWriter(sys.stdout, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
```

**Usage:**

```bash
# CSV (default)
python extractor.py urls.csv
# Output:
# title,author,platform
# Post 1,Jane,linkedin
# Post 2,Bob,twitter

# JSONL (one JSON object per line)
python extractor.py urls.csv --json | jq '.author'
# Output:
# "Jane"
# "Bob"

# JSONL with jq for filtering
python extractor.py urls.csv --json | jq 'select(.platform == "twitter")'
```

**Key points:**
- Default is always plain text (CSV, line-by-line output, etc.)
- `--json` is optional and doesn't break pipes if used with `jq`
- JSONL (one JSON object per line) is better than array format for streaming
- Callers who need JSON use `--json | jq` for processing
- Callers who need simple output use default (no extra flags)

**Handling JSON-heavy pipelines:**

If you frequently use JSON across multiple tools, three approaches work well:

```bash
# Option 1: Explicit (clear, but repetitive)
tool1 --json | tool2 --json | tool3 --json | jq ...

# Option 2: Wrapper script (reusable pattern)
# Create: ./json-pipe <tool> <args>
# Usage:
tool1 --json | json-pipe tool2 "args" | json-pipe tool3 "args" | jq ...

# Option 3: Tool-specific shortcuts (best UX)
# Create: ./tools-json/tool1, ./tools-json/tool2 (symlinks that add --json)
# Usage:
tools-json/tool1 <url> | tools-json/tool2 "Summarize" | jq ...
```

All three preserve explicitness and composability. Choose based on your workflow. **Never use environment variables to change tool behavior implicitly** (`JSON=true tool1 | tool2`) — it breaks transparency and composition.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Breaks Unix Philosophy | Alternative |
|---|---|---|
| **Option Creep** — adding `-n`, `-v`, `-s` flags for tangential tasks | Each option adds complexity; confuses the tool's core purpose; duplicates existing tools | Create separate tools (e.g., `vis` for visibility, `awk` for numbering). Options are for variations *within* the tool's responsibility, not for new responsibilities. |
| **Context-Aware Output** — changing format based on terminal vs. pipe | Makes tool unpredictable; breaks composition; tools can't trust each other's output | Always output the same format regardless of destination. Let the shell and separate tools (like `pager`) handle presentation. |
| **Side-effect I/O** — tool writes files without caller consent | Breaks composability; can't integrate into pipelines | Output to stdout; let caller redirect with `>`  or `-o` |
| **Embedded domain logic** — tool assumes how results are used | Can't reuse in unexpected ways; forces monolithic rewrites | Keep tool focused; delegate combination logic to pipelines |
| **Non-text formats** — JSON/binary output by default | Breaks pipes; requires parsing overhead (`jq` overhead); harder to debug | Plain text default (CSV, line-by-line); optional `--json` flag only |
| **Tightly coupled tools** — tool A imports tool B directly | Violates modularity; circular dependencies | Use pipes/files as the integration layer |
| **Silent failures** — tool fails without explanation | Pipelines fail mysteriously; hard to debug | Log errors to stderr with context; exit non-zero |
| **Monolithic "convenience" tools** — `do-everything.py` | Single point of failure; can't compose; defeats Unix philosophy | Split into focused tools; provide shell wrapper scripts if needed |
| **Feature Embedding** — adding generic features to specific tools | Prevents centralization; duplicates across tools; inconsistent behavior | Put features in the shell or a dedicated tool (e.g., history in terminal, not in each program) |

---

## Directory Structure

As the project grows, use this structure to maintain clarity:

```
ai-shell/
├── DESIGN.md                         # This file
├── README.md                         # Usage guide
├── .env                              # Credentials (gitignored)
├── .gitignore                        # Ignore patterns
├── .pre-commit-config.yaml          # Code quality hooks
│
├── src/
│   ├── __init__.py
│   ├── extractors/                   # Extraction tools
│   │   ├── youtube_transcriber.py
│   │   ├── social_media_extractor.py
│   │   └── web_to_markdown.py
│   ├── agents/                       # AI reasoning tools
│   │   └── strands_cli.py
│   ├── monitors/                     # Long-running monitors
│   │   └── clipboard_url_monitor.py
│   └── requirements.txt
│
├── lib/                              # Shared utilities (if needed)
│   ├── __init__.py
│   └── extraction.py                 # URL parsing, deduplication, etc.
│
├── output/                           # Generated files (gitignored)
│   └── .gitkeep
│
└── examples/                         # Real-world usage scripts
    ├── transcribe-and-summarize.sh
    └── extract-and-categorize.sh
```

**Rationale:**
- `src/` groups related tools without root clutter
- Subdirectories (extractors, agents, monitors) organize by responsibility
- `lib/` holds shared utilities only if multiple tools need them (avoid premature abstraction)
- `examples/` shows composition patterns without being "official tools"

---

## Best Practices

### Naming
- Tool names are **verbs**: `youtube_transcriber.py`, `social_media_extractor.py` (what it does)
- File names use **snake_case**: `my_tool.py`
- Functions are **clear and specific**: `extract_video_id()`, not `parse()`
- Avoid abbreviations unless universally known (e.g., `csv` ok, `xtr` bad)

### Configuration
- **Environment variables** for defaults that rarely change: `AWS_BEDROCK_REGION`, `YOUTUBE_API_KEY`
- **CLI args** for per-invocation overrides: `-o`, `-s`, `-m`
- **.env files** for local secrets (gitignored)
- **No hardcoded paths** or credentials — always externalize

### Error Handling
- Log errors to **stderr**, not stdout (stdout is for data)
- Exit code **0** on success, **non-zero** on failure
- Error messages should answer: *What happened? Why? What should I do?*
- Example: `Error: Could not fetch transcript for dQw4w9WgXcQ: Private video`

### Testing
- **Integration tests**: Fetch a real public YouTube video, verify output format
- **Edge cases**: Malformed URLs, missing metadata, network timeouts
- **No mocking** of external APIs — test against real services for confidence

### Documentation
- **Shebang** in each tool: `#!/usr/bin/env python3`
- **Docstring** with usage examples (CLI + module)
- **Comments** only for the "why" — not what the code does (code should be self-documenting)
- **README** with real pipelines; show composition payoff

### Dependencies
- Use `uv` (as per your global settings): `uv pip install <package>`
- Keep dependencies minimal — each dependency increases coupling
- Pin versions in `requirements.txt` for reproducibility
- List platform-specific dependencies clearly

---

## Extending the Project

### When to Add a New Tool
- ✅ It has a **single, clear responsibility**
- ✅ It **composes well** with existing tools
- ✅ It takes **plain text input** (stdin or file)
- ✅ It produces **plain text output** (stdout)
- ❌ It tries to combine two unrelated tasks
- ❌ It requires callers to use it in a specific way
- ❌ It encodes domain logic that belongs in pipelines

### When NOT to Add a New Tool
- If the functionality is a **convenience wrapper** — make a shell script in `examples/` instead
- If it **duplicates logic** — extract to `lib/` and reuse
- If it's **a feature request** for an existing tool — reconsider; is this "one thing"?

### Centralizing Features (Pike & Kernighan Insight)

Some features should **never** be in individual tools — they should be in the shell, terminal, or a dedicated tool:

| Feature | Where It Belongs | Why NOT in Every Tool |
|---|---|---|
| **History / Command Recall** | Shell or terminal | Every tool shouldn't reimplement this; inconsistent behavior; wastes effort |
| **Pagination / Paging** | Separate tool (like `more`, `less`) or terminal | Every tool shouldn't implement paging; use `| less` instead |
| **Line Editing / Text Editing** | Terminal interface or dedicated editor | Don't embed full editors in mail, viewers, etc.; terminal handles it uniformly |
| **Filename Expansion (wildcards)** | Shell only | All programs get `*` expansion from shell automatically; never in individual tools |
| **Output Redirection** | Shell only | All programs inherit `>` and pipes from shell; never in individual tools |
| **Input Validation** | Where input crosses system boundary | Validate user input at entry points; don't repeat in every tool |

**The principle:** If a feature could benefit *all* programs, put it in the shell or terminal. If it's specific to one tool's job, keep it there. Never embed generic features in individual tools.

### Checklist for New Tools
- [ ] Single responsibility (can describe in one sentence)
- [ ] Reads from stdin + file args (pipes-compatible)
- [ ] Writes to stdout by default; `-o FILE` for file output
- [ ] Handles errors gracefully (stderr + non-zero exit code)
- [ ] Can be imported as a module
- [ ] Has `-h` / `--help` with examples
- [ ] Has docstring with usage (CLI + module)
- [ ] Minimal dependencies
- [ ] No hardcoded paths/credentials
- [ ] No context-aware behavior (same output regardless of terminal/pipe/file)
- [ ] No options that duplicate existing tools' jobs
- [ ] No embedded features that belong in the shell or a central location

---

## Real-World Examples

### Good Pipeline
```bash
# Transcribe, summarize, and create a tweet
youtube_transcriber.py "https://youtube.com/watch?v=..." \
  | strands_cli.py "Extract 3 key points" \
  | strands_cli.py -s "You are a Twitter writer" "Turn this into a tweet (280 chars max)"
```

Why this works:
- Each tool does one thing
- Plain text flows between them
- Caller decides the chain
- Easy to debug (insert `tee` to inspect)

### Bad Pipeline (Anti-Pattern)
```bash
# Don't do this:
extract-and-summarize-and-tweet.py "https://youtube.com/watch?v=..."
```

Why this fails:
- Monolithic; can't reuse extraction or summarization separately
- Embeds Twitter's 280-char limit in the tool (breaks reuse)
- No intermediate inspection/debugging possible
- One failure brings down all three steps

---

## Metrics for Success

A healthy ai-shell project:
- **Modularity**: Tools can be used independently or in any combination
- **Composability**: New combinations work without modifying existing tools
- **Clarity**: A new user can understand each tool's purpose in 30 seconds
- **Stability**: Existing pipelines don't break when you update a tool
- **Discoverability**: `python tool.py -h` gives enough info to use it

If a change violates any of these, reconsider the design.

---

## The Right Place for Features

Pike & Kernighan's core insight: **"The key to problem-solving on the UNIX system is to identify the right primitive operations and to put them at the right place."**

This applies to ai-shell:

| Decision | Right Place | Wrong Place |
|---|---|---|
| **Extracting YouTube transcripts** | `youtube_transcriber.py` | Every other tool shouldn't know how to fetch YouTube |
| **Summarization logic** | `strands_cli.py` with different system prompts | Not in the extractor; not hardcoded in tools |
| **CSV parsing/writing** | `social_media_extractor.py` | Not in every tool; use pipes + existing tools (awk, cut, sort) |
| **Terminal pagination** | Shell: `\| less` | Not in individual tools |
| **Error formatting** | Tool stderr output | Not in a central logging service that silences tool details |
| **Caching results** | Caller's choice via pipes + temp files | Not built into tools (breaks composition) |
| **Batching multiple inputs** | Shell loops or xargs | Not in individual tools (they process one at a time) |

When you're unsure where a feature belongs, ask: **"Will this serve many tools equally well, or is it specific to this tool's job?"**
- Many tools → put it in the shell, a library, or a dedicated tool
- This tool only → keep it in the tool

---

## References

- Sau Sheong's "[Why design is important in engineering](https://sausheong.com/why-design-is-important-in-engineering-3b8a47d20e7f)" — Unix philosophy history and principles (2025)
- Rob Pike & Brian Kernighan, "[Program Design in the Unix Environment](https://harmful.cat-v.org/cat-v/unix_prog_design.pdf)" — Foundational paper on option creep, context-aware output, and feature placement (1984)
- Mike Gancarz, *The Unix Philosophy*
- Eric S. Raymond, *[The Art of Unix Programming](https://www.catb.org/~esr/writings/taoup/html/)*
