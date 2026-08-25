"""Terminal runner for the parse agent.

    python -m agents.run "12 salads left, close at 9"     # one message -> JSON
    python -m agents.run "YES" "4821"                     # several messages
    python -m agents.run                                  # interactive, q to quit
"""

from __future__ import annotations

import asyncio
import logging
import sys

from agents.parse_agent import parse_message_async


def _to_json(result) -> str:
    return result.model_dump_json(indent=2)


async def _run_batch(messages: list[str]) -> None:
    for i, text in enumerate(messages):
        result = await parse_message_async(text)
        if len(messages) > 1:
            if i:
                print()
            print(f"> {text}")
        print(_to_json(result))


async def _run_interactive() -> None:
    print("LastCall parse agent - type a business message, 'q' to quit.")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in {"q", "quit", "exit"}:
            break
        if not text:
            continue
        result = await parse_message_async(text)
        print(_to_json(result))


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.WARNING)
    # google-genai logs an advisory about automatic function calling on every
    # call even though we use no tools; it is noise for a CLI.
    logging.getLogger("google_genai.models").setLevel(logging.ERROR)
    if argv:
        asyncio.run(_run_batch(argv))
    else:
        asyncio.run(_run_interactive())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
