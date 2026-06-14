"""Generate macOS launchd jobs that fire each desk session at the right time.

Schedule is defined in US/Eastern (market time) and converted to YOUR machine's
local time automatically (DST-aware), since launchd uses local clock.

Usage:
    python scripts/gen_schedule.py            # preview the plists + local times
    python scripts/gen_schedule.py --install  # write to ~/Library/LaunchAgents and load
    python scripts/gen_schedule.py --uninstall # unload + remove the jobs
"""
from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "scripts" / "run_session.sh"
LA_DIR = Path.home() / "Library" / "LaunchAgents"
LABEL = "com.tothemoon"

# session -> (ET hour, ET minute, weekday or None for every weekday Mon-Fri)
# weekday: None = Mon-Fri (1-5 in launchd); 0 = Sunday
SCHEDULE = {
    "premarket":       (8, 30, None),
    "open":            (9, 30, None),
    "midmorning":      (10, 30, None),
    "powerhour":       (15, 0, None),
    "postmarket":      (16, 15, None),
    "weekly-longterm": (17, 0, 0),     # Sunday 17:00 ET
}

ET = ZoneInfo("America/New_York")
LOCAL = datetime.now().astimezone().tzinfo


def et_to_local(h: int, m: int) -> tuple[int, int]:
    ref = datetime.now(ET).replace(hour=h, minute=m, second=0, microsecond=0)
    loc = ref.astimezone(LOCAL)
    return loc.hour, loc.minute


def plist(session: str, h: int, m: int, weekday) -> str:
    lh, lm = et_to_local(h, m)
    if weekday is None:  # Mon-Fri
        cal = "\n".join(
            f"""    <dict><key>Weekday</key><integer>{d}</integer>
      <key>Hour</key><integer>{lh}</integer>
      <key>Minute</key><integer>{lm}</integer></dict>"""
            for d in range(1, 6)
        )
        cal_block = f"  <key>StartCalendarInterval</key>\n  <array>\n{cal}\n  </array>"
    else:
        cal_block = f"""  <key>StartCalendarInterval</key>
  <dict><key>Weekday</key><integer>{weekday}</integer>
    <key>Hour</key><integer>{lh}</integer>
    <key>Minute</key><integer>{lm}</integer></dict>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{LABEL}.{session}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>{RUNNER}</string>
    <string>{session}</string>
  </array>
{cal_block}
  <key>RunAtLoad</key><false/>
  <key>StandardErrorPath</key><string>{REPO}/reports/logs/{session}.launchd.log</string>
</dict>
</plist>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()

    print(f"Local timezone: {LOCAL}  (schedule defined in US/Eastern)\n")
    for session, (h, m, wd) in SCHEDULE.items():
        lh, lm = et_to_local(h, m)
        when = "Sun" if wd == 0 else "Mon-Fri"
        print(f"  /{session:16s} {h:02d}:{m:02d} ET  ->  {lh:02d}:{lm:02d} local  ({when})")
        path = LA_DIR / f"{LABEL}.{session}.plist"
        if args.uninstall:
            subprocess.run(["launchctl", "unload", str(path)], capture_output=True)
            path.unlink(missing_ok=True)
        elif args.install:
            LA_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(plist(session, h, m, wd))
            subprocess.run(["launchctl", "unload", str(path)], capture_output=True)
            subprocess.run(["launchctl", "load", str(path)], capture_output=True)

    if args.install:
        print("\n✅ Installed & loaded. Jobs run only when your Mac is awake at those times.")
        print("   (System Settings → Energy: allow wake, or keep the Mac on for market hours.)")
    elif args.uninstall:
        print("\n🗑️  Uninstalled.")
    else:
        print("\nPreview only. Re-run with --install to activate, --uninstall to remove.")


if __name__ == "__main__":
    main()
