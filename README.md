# Kindle E-Ink Dashboard

Turn old Amazon Kindles into live-updating wall displays — calendar, sports scores, weather, or anything you can render as static HTML. Designed for e-ink screens: high contrast, large fonts, zero animations.

**Runs on any Kindle with WiFi and an Experimental Browser** (Paperwhite 3+, 7th gen+). No soldering, no new hardware — just point the Kindle's browser at a URL and it becomes a live dashboard that lasts weeks on one charge.

## What you get

- **Calendar dashboard** — pulls your Google Calendar (next 7 days), updates every 10 min
- **Sports scores** — scrapes ESPN's public API for NFL, NBA, MLB, NHL, NCAA football & basketball
- **Auto-refresh** — `<meta http-equiv="refresh">` keeps the page current on the Kindle
- **Uploads to any web server** — VPS, Raspberry Pi, nginx, whatever you run

## How it works

```
┌────────────┐     ┌──────────────┐     ┌────────────┐
│  Cron job  │────▶│  Static HTML │────▶│   Kindle   │
│ (every 5m) │     │  on your VPS │     │  browser   │
└────────────┘     └──────────────┘     └────────────┘
```

1. A cron job (or manual run) fetches calendar events and sports scores  
2. Generates clean, e-ink-optimized HTML pages  
3. Pushes them to your web server  
4. Your Kindle's Experimental Browser loads the page and auto-refreshes  

## Quick start

```bash
# Clone
git clone https://github.com/goodrica/kindle-dash.git
cd kindle-dash

# Test locally
python generate_calendar.py    # → output/calendar.html
python generate_scores.py      # → output/scores.html

# Open output/calendar.html in a browser to preview
```

### Calendar setup

Requires Google Calendar OAuth. If you haven't set this up before:

```bash
# Check if authenticated (Hermes users)
python %HERMES_HOME%/skills/google-workspace-gmail/scripts/setup.py --check

# If not, follow the Google Workspace skill's setup flow
```

The calendar generator calls `google_api.py` from Hermes's Google Workspace integration. If running outside Hermes, point `GAPI` in `generate_calendar.py` to your own Google Calendar API client.

### Deploy to a web server

Edit `generate_all.py` to match your server (it uses SCP to a VPS by default), then:

```bash
python generate_all.py
```

Or wire it into cron:

```bash
# Every 5 minutes
*/5 * * * * cd /path/to/kindle-dash && python generate_all.py
```

## On the Kindle

1. Open the **Experimental Browser** (Menu → Experimental Browser)
2. Navigate to `https://your-server.com/kindle/calendar.html`  
3. To prevent the screensaver: in the browser's URL bar, type `~ds` and press Enter (disables sleep until next reboot)
4. Bookmark the page for easy return after reboots

## Project structure

```
kindle-dash/
├── generate_calendar.py   # Google Calendar → calendar.html
├── generate_scores.py     # ESPN API → scores.html
├── generate_all.py        # Master runner + SCP upload
├── output/                # Generated HTML (gitignored)
├── .gitignore
└── README.md
```

## Customize

**Different leagues:** Edit the `LEAGUES` list in `generate_scores.py`.

**Different calendar range:** Change `DAYS_AHEAD` in `generate_calendar.py`.

**Add your own dashboards:** Any script that writes an HTML file to `output/` will get picked up by `generate_all.py`. The HTML just needs to be e-ink-friendly: large serif fonts, black on white, no CSS animations, `<meta http-equiv="refresh">` for auto-update.

## Kindle tips

- **Jailbreak for kiosk mode:** If your Kindle model supports it, [kindle-dash](https://github.com/pascalw/kindle-dash) handles auto-launch on boot, WiFi reconnects, and prevents the browser from closing
- **Battery:** E-ink only draws power on page refresh — a Kindle on a static calendar page with 10-min refreshes lasts **weeks** on one charge
- **Mount it:** A simple stand or wall mount turns your old Kindle into a permanent household dashboard

## License

MIT — do whatever you want with it. Built for repurposing old hardware, not locking it down.