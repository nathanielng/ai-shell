#!/usr/bin/env python3
"""
Simple Strands SDK CLI agent using Bedrock.

Reads input from a prompt argument, stdin (pipe/redirect), or interactive input.
Outputs to stdout by default, or to a file with -o/--output.

Usage:
    # Prompt argument
    python strands_cli.py "Summarize this text"

    # Piped input
    cat transcript.txt | python strands_cli.py "Summarize this"
    pbpaste | python strands_cli.py "Clean up these notes"

    # Interactive (no args, no pipe)
    python strands_cli.py

    # Output to file
    cat transcript.txt | python strands_cli.py -o summary.txt "Summarize this"

    # System prompt override
    python strands_cli.py -s "You are a translator" "Translate to French: Hello"

    # JSON output (for programmatic use)
    python strands_cli.py --json "What is 2+2?"
    python strands_cli.py --json "Summarize this" < input.txt | jq .response

Environment:
    AWS_BEARER_TOKEN_BEDROCK  Bedrock API key (or use standard AWS creds)
    AWS_BEDROCK_REGION        Region (default: us-east-1)
    BEDROCK_MODEL_ID          Model (default: us.anthropic.claude-sonnet-4-6)
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from strands import Agent
from strands.models import BedrockModel

load_dotenv()


def build_agent(system_prompt: str, model_id: str, region: str) -> Agent:
    model = BedrockModel(model_id=model_id, region_name=region)
    return Agent(
        model=model,
        system_prompt=system_prompt,
        callback_handler=None,
    )


def main():
    parser = argparse.ArgumentParser(description="Strands SDK CLI agent (Bedrock)")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to the agent")
    parser.add_argument("-o", "--output", help="Write response to file")
    parser.add_argument("-s", "--system", default="You are a helpful assistant.", help="System prompt")
    parser.add_argument("-m", "--model", default=os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"))
    parser.add_argument("-r", "--region", default=os.getenv("AWS_BEDROCK_REGION", "us-east-1"))
    parser.add_argument("--json", action="store_true", help="Output as JSON (includes metadata)")
    args = parser.parse_args()

    # Read stdin if piped
    stdin_text = None
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read().strip()

    # Build the message
    if args.prompt and stdin_text:
        message = f"{args.prompt}\n\n---\n\n{stdin_text}"
    elif args.prompt:
        message = args.prompt
    elif stdin_text:
        message = stdin_text
    else:
        # Interactive: read from terminal
        print("Enter your prompt (Ctrl+D to send):", file=sys.stderr)
        message = sys.stdin.read().strip()

    if not message:
        print("No input provided.", file=sys.stderr)
        sys.exit(1)

    agent = build_agent(args.system, args.model, args.region)
    result = agent(message)
    response_text = "".join(
        block["text"] for block in result.message.get("content", []) if "text" in block
    )

    # Prepare output
    if args.json:
        output = json.dumps({
            "prompt": message,
            "response": response_text,
            "model": args.model,
            "stop_reason": result.message.get("stop_reason", "unknown"),
            "system_prompt": args.system,
        })
    else:
        output = response_text

    if args.output:
        with open(args.output, "w") as f:
            f.write(output + "\n")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
