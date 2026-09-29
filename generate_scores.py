#!/usr/bin/env python3
"""
Generate an e-ink-optimized sports scores HTML page for Kindle dashboard.
Uses ESPN's public API via curl (urllib gets 403 on Windows).
Configure which leagues to show by editing LEAGUES below.
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path
from html import escape

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# ESPN API league codes. Add/remove as desired.
LEAGUES = [
    ("football/nfl", "NFL"),
    ("basketball/nba", "NBA"),
    ("baseball/mlb", "MLB"),
    ("hockey/nhl", "NHL"),
    ("basketball/mens-college-basketball", "NCAA Basketball"),
    ("football/college-football", "NCAA Football"),
]

CACHE_FILE = OUTPUT_DIR / "scores_cache.json"
CACHE_MAX_AGE_S = 300  # Re-fetch after 5 minutes


def should_refresh() -> bool:
    if not CACHE_FILE.exists():
        return True
    age = datetime.now().timestamp() - CACHE_FILE.stat().st_mtime
    return age > CACHE_MAX_AGE_S


def fetch_json(url: str) -> dict | None:
    """Fetch JSON via curl (urllib gets 403 from ESPN on Windows)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "15",
             "-H", "User-Agent: python-requests/2.31.0",
             "-H", "Origin: https://www.espn.com",
             url],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


def fetch_scores() -> list[dict]:
    """Fetch scores for all configured leagues. Returns list of league dicts."""
    if not should_refresh():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    
    all_leagues = []
    for league_path, league_name in LEAGUES:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{league_path}/scoreboard"
        data = fetch_json(url)
        
        if data is None:
            all_leagues.append({"name": league_name, "code": league_path, "error": "fetch failed", "games": []})
            continue
        
        events = data.get("events", [])
        games = []
        for evt in events:
            comps = evt.get("competitions", [])
            for comp in comps:
                status = comp.get("status", {}).get("type", {}).get("description", "")
                competitors = comp.get("competitors", [])
                scores = []
                for team in competitors:
                    scores.append({
                        "name": team.get("team", {}).get("displayName", team.get("team", {}).get("abbreviation", "??")),
                        "score": team.get("score", "-"),
                        "home": team.get("homeAway") == "home",
                    })
                if len(scores) == 2:
                    games.append({
                        "away": scores[0] if not scores[0]["home"] else scores[1],
                        "home": scores[0] if scores[0]["home"] else scores[1],
                        "status": status,
                    })
        all_leagues.append({"name": league_name, "code": league_path, "games": games})
    
    CACHE_FILE.write_text(json.dumps(all_leagues, indent=2))
    return all_leagues


def status_badge(status: str) -> str:
    """Emphasize status (e-ink: use prefix markers)."""
    s = status.upper()
    if s in ("FINAL", "FT", "FULL TIME"):
        return "◼ FINAL"
    if s in ("HALFTIME", "HT"):
        return "⏸ HALF"
    if "QTR" in s or "Q" in s or "PERIOD" in s:
        return f"▶ {status}"
    return status


def build_html(leagues: list[dict]) -> str:
    now = datetime.now()
    hour = now.hour % 12 or 12
    ampm = "AM" if now.hour < 12 else "PM"
    now_str = f"{now:%A}, {now:%B} {now.day}  {hour}:{now.minute:02d} {ampm} ET"
    
    total_games = sum(len(l["games"]) for l in leagues)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="300">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sports Scores</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 24px;
    line-height: 1.4;
    color: #111;
    background: #fff;
    padding: 24px 28px;
    max-width: 800px;
  }}
  .header {{
    border-bottom: 3px solid #111;
    margin-bottom: 18px;
    padding-bottom: 10px;
  }}
  .header h1 {{ font-size: 38px; font-weight: normal; }}
  .header .updated {{ font-size: 18px; color: #666; margin-top: 4px; }}
  .league-section {{ margin-bottom: 24px; page-break-inside: avoid; }}
  .league-name {{
    font-size: 28px;
    font-weight: bold;
    border-bottom: 2px solid #ddd;
    padding-bottom: 4px;
    margin-bottom: 8px;
  }}
  .game-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px dotted #ccc;
  }}
  .teams {{ flex: 1; }}
  .team {{ display: inline-block; min-width: 140px; }}
  .team.home {{ font-weight: bold; }}
  .scores {{ display: flex; gap: 16px; align-items: center; }}
  .score {{ width: 36px; text-align: center; font-variant-numeric: tabular-nums; }}
  .status {{ font-size: 20px; color: #555; width: 90px; text-align: right; }}
  .no-games {{ color: #999; font-style: italic; padding: 12px 0; }}
  .error {{ color: #999; font-size: 18px; }}
  @media (max-width: 600px) {{
    body {{ font-size: 20px; padding: 16px; }}
    .team {{ min-width: 100px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>Sports Scores</h1>
  <div class="updated">Updated {now_str}  ·  {total_games} game{"s" if total_games != 1 else ""}</div>
</div>
"""
    
    for league in leagues:
        html += f'<div class="league-section">\n'
        html += f'  <div class="league-name">{escape(league["name"])}</div>\n'
        
        if league.get("error"):
            html += f'  <div class="error">⚠ {escape(league["error"])}</div>\n'
        elif not league["games"]:
            html += f'  <div class="no-games">No games today</div>\n'
        else:
            for game in league["games"]:
                away = game["away"]
                home = game["home"]
                status = status_badge(game["status"])
                
                html += '  <div class="game-row">'
                html += '<div class="teams">'
                html += f'<span class="team away">{escape(away["name"])}</span>'
                html += f' <span class="team home">{escape(home["name"])}</span>'
                html += '</div>'
                html += '<div class="scores">'
                html += f'<span class="score">{away["score"]}</span>'
                html += f'<span class="score">{home["score"]}</span>'
                html += '</div>'
                html += f'<span class="status">{status}</span>'
                html += '</div>\n'
        
        html += '</div>\n'
    
    html += """
</body>
</html>"""
    return html


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Fetching sports scores...")
    leagues = fetch_scores()
    for league in leagues:
        ng = len(league["games"])
        err = league.get("error", "")
        status = f"⚠ {err}" if err else f"{ng} games"
        print(f"  {league['name']}: {status}")
    
    html = build_html(leagues)
    outpath = OUTPUT_DIR / "scores.html"
    outpath.write_text(html, encoding="utf-8")
    print(f"  Wrote {outpath} ({len(html)} bytes)")


if __name__ == "__main__":
    main()