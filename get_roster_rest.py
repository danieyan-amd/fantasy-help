import os
import sys
import requests
import csv
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("YAHOO_CLIENT_ID")
CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("YAHOO_REFRESH_TOKEN")
TEAM_KEY = os.getenv("Y_TEAM_KEY")  # e.g., 466.l.207335.t.2

TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
BASE = "https://fantasysports.yahooapis.com/fantasy/v2"

def get_access_token():
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        print("Missing YAHOO_CLIENT_ID / YAHOO_CLIENT_SECRET / YAHOO_REFRESH_TOKEN in .env", file=sys.stderr)
        sys.exit(1)
    resp = requests.post(
        TOKEN_URL,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "refresh_token",
            "redirect_uri": "oob",
            "refresh_token": REFRESH_TOKEN,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def get_roster(access_token, team_key, date=None):
    # NBA supports daily roster by date=YYYY-MM-DD; if not provided, current roster
    suffix = f";date={date}" if date else ""
    url = f"{BASE}/team/{team_key}/roster/players{suffix}?format=json"
    r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    # Walk the response tree to list players
    team = data["fantasy_content"]["team"]
    roster = team[1]["roster"]
    players = roster["players"]
    names = []
    rows = []
    for i in range(players["count"]):
        p = players[str(i)]["player"]
        # name
        name_obj = p[0][2]["name"]
        full = name_obj["full"]
        # position(s)
        display_pos = None
        for part in p:
            if isinstance(part, dict) and "display_position" in part:
                display_pos = part["display_position"]
        if not display_pos:
            # fallback to eligible_positions list
            try:
                elig = p[1]["eligible_positions"]
                display_pos = ",".join([x["position"] for x in elig]) if isinstance(elig, list) else "-"
            except Exception:
                display_pos = "-"
        # team abbr
        nba_team = "-"
        try:
            meta = p[0][0]  # player_id block also contains editorial fields
            # sometimes abbr sits in p[0][1] or p[0][3], so we scan
            for part in p[0:3]:
                if isinstance(part, dict) and "editorial_team_abbr" in part:
                    nba_team = part["editorial_team_abbr"]
                    break
        except Exception:
            pass
        names.append(full)
        rows.append({"name": full, "position": display_pos, "nba_team": nba_team})
    return names, rows

def main():
    if not os.getenv("Y_TEAM_KEY"):
        print("Set Y_TEAM_KEY in .env (e.g., Y_TEAM_KEY=466.l.207335.t.2)", file=sys.stderr)
        sys.exit(1)

    at = get_access_token()
    names, rows = get_roster(at, TEAM_KEY)

    print("Your current roster:")
    for r in rows:
        print(f"- {r['name']} ({r['position']}) — {r['nba_team']}")

    # Save CSV
    with open("roster.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "position", "nba_team"])
        w.writeheader()
        w.writerows(rows)
    print("\nSaved: roster.csv")

if __name__ == "__main__":
    main()
