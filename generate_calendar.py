#!/usr/bin/env python3
"""
Generate an e-ink-optimized calendar HTML page for Kindle dashboard.
Fetches Google Calendar events via google_api.py, renders for Kindle browser.
"""
import json
import subprocess
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from html import escape

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
GAPI = Path.home() / "AppData/Local/hermes/skills/google-workspace-gmail/scripts/google_api.py"
HERMES_PYTHON = Path.home() / "AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
DAYS_AHEAD = 7  # How many days forward to fetch

def fetch_events() -> list[dict]:
    """Call google_api.py calendar list and return parsed events."""
    result = subprocess.run(
        [str(HERMES_PYTHON), str(GAPI), "calendar", "list"],
        capture_output=True, text=True, timeout=30,
        env={**__import__("os").environ, "PYTHONPATH": ""},
    )
    if result.returncode != 0:
        print(f"ERROR: google_api.py failed: {result.stderr}", file=sys.stderr)
        return []
    return json.loads(result.stdout)


def parse_date(date_str: str) -> date:
    """Parse a Google Calendar date string (date-only or datetime)."""
    # "2026-09-29" or "2026-09-29T14:00:00-04:00"
    if "T" in date_str:
        return datetime.fromisoformat(date_str).date()
    return date.fromisoformat(date_str)


def parse_time(date_str: str) -> str:
    """Extract human-readable time from datetime string."""
    if "T" not in date_str:
        return ""  # All-day event
    dt = datetime.fromisoformat(date_str)
    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{hour}:{dt.minute:02d} {ampm}"


def group_by_date(events: list[dict], today: date) -> dict[date, list[dict]]:
    """Group events by date, filter to DAYS_AHEAD range."""
    end_date = today + timedelta(days=DAYS_AHEAD)
    grouped: dict[date, list[dict]] = {}
    
    for event in events:
        d = parse_date(event["start"])
        if today <= d <= end_date:
            grouped.setdefault(d, []).append(event)
    
    return dict(sorted(grouped.items()))


def fmt_now() -> str:
    """Cross-platform timestamp (Windows %-d doesn't work)."""
    now = datetime.now()
    hour = now.hour % 12 or 12
    ampm = "AM" if now.hour < 12 else "PM"
    # Fix strftime format: use now.minute:02d not now:%M:02d
    return f"{now:%A}, {now:%B} {now.day}  {hour}:{now.minute:02d} {ampm} ET"


def build_html(grouped: dict[date, list[dict]], today: date) -> str:
    """Generate e-ink optimized HTML."""
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    
    now_str = fmt_now()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="600">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Calendar — Andrew Goodrich</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 26px;
    line-height: 1.4;
    color: #111;
    background: #fff;
    padding: 24px 28px;
    max-width: 800px;
    -webkit-font-smoothing: antialiased;
  }}
  .header {{
    border-bottom: 3px solid #111;
    margin-bottom: 18px;
    padding-bottom: 10px;
  }}
  .header h1 {{ font-size: 42px; font-weight: normal; letter-spacing: -0.5px; }}
  .header .updated {{ font-size: 18px; color: #666; margin-top: 4px; }}
  .day-section {{ margin-bottom: 28px; page-break-inside: avoid; }}
  .day-label {{
    font-size: 30px;
    font-weight: bold;
    border-bottom: 2px solid #ddd;
    padding-bottom: 4px;
    margin-bottom: 8px;
  }}
  .day-label .date-num {{ color: #444; font-weight: normal; }}
  .today .day-label {{ border-bottom-color: #111; }}
  .event-row {{
    display: flex;
    padding: 6px 0;
    border-bottom: 1px dotted #ccc;
  }}
  .event-time {{
    width: 110px;
    flex-shrink: 0;
    color: #555;
    font-variant-numeric: tabular-nums;
  }}
  .event-summary {{ flex: 1; }}
  .all-day {{ color: #888; font-style: italic; }}
  .no-events {{ color: #999; font-style: italic; padding: 12px 0; }}
  @media (max-width: 600px) {{
    body {{ font-size: 22px; padding: 16px 18px; }}
    .header h1 {{ font-size: 34px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>Andrew's Calendar</h1>
  <div class="updated">Updated {now_str}</div>
</div>
"""

    if not grouped:
        html += '<p class="no-events">No events in the next week.</p>\n'
    else:
        for d, events in grouped.items():
            day_name = day_names[d.weekday()]
            month = month_names[d.month - 1]
            date_label = f"{day_name}, {month} {d.day}"
            is_today = d == today
            css_class = "day-section today" if is_today else "day-section"
            
            html += f'<div class="{css_class}">\n'
            html += f'  <div class="day-label">{day_name} <span class="date-num">{month} {d.day}</span></div>\n'
            
            # Sort: timed events first, then all-day
            timed = sorted([e for e in events if "T" in e.get("start", "")], key=lambda e: e["start"])
            allday = [e for e in events if "T" not in e.get("start", "")]
            
            for event in timed:
                time_str = parse_time(event["start"])
                summary = escape(event.get("summary", "Busy"))
                html += f'  <div class="event-row"><span class="event-time">{time_str}</span><span class="event-summary">{summary}</span></div>\n'
            
            for event in allday:
                summary = escape(event.get("summary", "Busy"))
                html += f'  <div class="event-row"><span class="event-time all-day">all day</span><span class="event-summary">{summary}</span></div>\n'
            
            html += '</div>\n'
    
    html += """
</body>
</html>"""
    return html


def main():
    today = date.today()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Fetching calendar events (next {DAYS_AHEAD} days)...")
    events = fetch_events()
    print(f"  Got {len(events)} events")
    
    grouped = group_by_date(events, today)
    html = build_html(grouped, today)
    
    outpath = OUTPUT_DIR / "calendar.html"
    outpath.write_text(html, encoding="utf-8")
    print(f"  Wrote {outpath} ({len(html)} bytes)")
    
    # Print summary
    for d, evts in grouped.items():
        names = [e["summary"] for e in evts]
        print(f"  {d.strftime('%a %b')} {d.day}: {', '.join(names)}")


if __name__ == "__main__":
    main()