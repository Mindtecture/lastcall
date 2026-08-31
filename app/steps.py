"""Dump the agent_steps log chronologically (console mirror of the GCP view).

    python -m app.steps
"""

from __future__ import annotations

import io
import sys
from zoneinfo import ZoneInfo

from app import config, db

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def main() -> None:
    tz = ZoneInfo(config.BUSINESS_TZ)
    steps = [d.to_dict() for d in db.client().collection("agent_steps").stream()]
    steps = [s for s in steps if s.get("ts")]
    steps.sort(key=lambda s: s["ts"])
    for s in steps:
        ts = s["ts"].astimezone(tz).strftime("%H:%M:%S")
        print(f"{ts}  {s['step']:<8} {s['detail']}")


if __name__ == "__main__":
    main()
