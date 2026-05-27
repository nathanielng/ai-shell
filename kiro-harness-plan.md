# Kiro Harness Plan

## Overview

Create a Kiro CLI harness that uses the same `.ai` text format as aish.py but sends prompts to Kiro CLI instead of Strands AgentShell. Extends ai-shell to be multi-framework while maintaining composability and Unix philosophy.

## Scope

**In scope:**
- Parse `.ai` format directives (model, skills, system prompt)
- Read input from stdin or file argument
- Invoke Kiro CLI with appropriate configuration
- Output result to stdout
- Error handling and logging

**Out of scope:**
- Temperature, top_p, top_k directives (Kiro doesn't support these)
- Interactive prompts or multi-turn conversations
- File creation without explicit request

## Design Principles

Same as aish.py but adapted for Kiro:
1. **Stateless** — Input → process → stdout
2. **Composable** — Pipe input from other tools
3. **Unix-aligned** — Single responsibility (run Kiro agent)
4. **Configurable** — Environment variables + directives
5. **Secure** — Input validation, zone-1 variable substitution only

## Architecture

### File Structure

```
src/agents/
  kiro.py          # Kiro harness (similar to aish.py)

examples/
  example.kiro.ai  # Example Kiro agent script
```

### .ai Format for Kiro

```
#!/usr/bin/env python3
#@ model: kiro-model-id
#@ skills: skill1, skill2
#@ system-prompt

Your system prompt here.
```

**Directives:**
- `#@ model` — Kiro model ID (required)
- `#@ skills` — Comma-separated list of Kiro tools/plugins (optional)
- `#@ system-prompt` — Custom system prompt flag (optional, default uses what follows)

**Variables (Zone 1 only):**
- `{KIRO_MODEL}` — From env var
- `{KIRO_TEMPERATURE}` — If Kiro supports it

### Kiro CLI Interface (TBD)

**Questions to resolve:**
1. What's the command syntax? `kiro run "prompt"` or `kiro chat`?
2. How are tools/skills passed? `--tools tool1,tool2` or YAML config?
3. What environment variables does Kiro expect?
4. What does output look like? Plain text, JSON, structured?
5. How are errors signaled? Exit code, stderr, specific format?

### Implementation Plan

#### Phase 1: CLI Discovery
- Determine Kiro CLI syntax and options
- Document command structure, flags, environment variables
- Identify supported directives

#### Phase 2: Basic Harness
- Parse `.ai` format (directives + prompt)
- Invoke Kiro CLI with parsed config
- Handle stdin/stdout piping
- Basic error handling

#### Phase 3: Features
- Environment variable substitution
- Logging (LOG_LEVEL env var)
- Tool/skill parsing and passing
- Input validation (model ID, tools)

#### Phase 4: Polish
- Comprehensive tests
- Documentation and examples
- Integration with aish.py (launcher script?)

## Open Questions

1. **Model ID format** — What format does Kiro expect? (e.g., `kiro-3.5-turbo`?)
2. **Tools system** — Does Kiro have built-in tools? How are they invoked?
3. **Configuration** — Can we pass config via CLI args or does it need config files?
4. **Output format** — Does Kiro support different output formats?
5. **Streaming** — Does Kiro support streaming output?
6. **Error handling** — What exit codes and error messages does Kiro use?
7. **Multi-turn** — Should we support multi-turn conversations or keep it single-prompt?

## Related Files

- `src/agents/aish.py` — Strands harness (reference implementation)
- `DESIGN.md` — Design principles and patterns
- `.env.example` — Environment variable documentation
- `lib/validation.py` — Input validation utilities

## Notes

- Keep implementation lightweight (follow aish.py pattern)
- No new dependencies if possible (or minimal)
- Test with actual Kiro CLI before finalizing
- Consider launcher script to unify aish and kiro entry points
