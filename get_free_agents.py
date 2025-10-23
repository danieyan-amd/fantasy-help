import os
import sys
import csv
from dotenv import load_dotenv
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa

# Load YAHOO_CLIENT_ID / YAHOO_CLIENT_SECRET from .env
load_dotenv()
APP_KEY = os.getenv("YAHOO_CLIENT_ID")
APP_SECRET = os.getenv("YAHOO_CLIENT_SECRET")
TOKEN_FILE = "oauth2.json"


def load_oauth():
    """
    Return a valid OAuth2 object.
    - If TOKEN_FILE exists, load from it.
    - Else do first-time login and save TOKEN_FILE.
    """
    # Try reusing saved creds
    if os.path.exists(TOKEN_FILE):
        try:
            oauth = OAuth2(None, None, from_file=TOKEN_FILE)
            if not oauth.token_is_valid():
                oauth.refresh_access_token()
            return oauth
        except Exception as e:
            print(f"Warning: bad token file '{TOKEN_FILE}': {e}. Removing and re-authing...", file=sys.stderr)
            try:
                os.remove(TOKEN_FILE)
            except OSError:
                pass

    # First-time login
    if not APP_KEY or not APP_SECRET:
        print("Missing YAHOO_CLIENT_ID / YAHOO_CLIENT_SECRET in .env", file=sys.stderr)
        sys.exit(1)

    # Pass from_file parameter so yahoo-oauth will auto-save tokens after auth
    oauth = OAuth2(consumer_key=APP_KEY, consumer_secret=APP_SECRET, from_file=TOKEN_FILE)
    if not oauth.token_is_valid():
        oauth.refresh_access_token()
    return oauth


def clean_field(p, *keys):
    for k in keys:
        v = p.get(k)
        if v:
            return v
    return None


def format_position(p):
    # Try typical fields, then eligible_positions
    pos = clean_field(p, "display_position", "position")
    if pos:
        return pos
    elig = p.get("eligible_positions")
    if isinstance(elig, list) and elig:
        return ",".join(elig)
    return "-"


def format_nba_team(p):
    return (
        clean_field(
            p, "editorial_team_abbr", "editorial_team_full_name", "editorial_team_key"
        )
        or "-"
    )


def pick_my_league(gm: yfa.Game):
    """
    Find the first league for the current login.
    Returns league object.
    """
    league_ids = gm.league_ids()
    if not league_ids:
        raise RuntimeError("No NBA leagues found on this Yahoo account.")
    
    return gm.to_league(league_ids[0])


def main():
    oauth = load_oauth()
    gm = yfa.Game(oauth, "nba")

    league = pick_my_league(gm)
    print(f"Fetching free agents from league: {league.league_id}")

    # Get free agents - you can specify position and count
    # Available positions: PG, SG, G, SF, PF, F, C, Util
    # Let's get top 100 available players across all positions
    print("\nFetching free agents (this may take a moment)...")
    
    # Free agents API: league.free_agents(position)
    # We'll fetch all positions - you can filter by specific position if needed
    try:
        free_agents = league.free_agents("ALL")
    except:
        # Fallback: try without position filter
        try:
            free_agents = league.free_agents()
        except Exception as e:
            print(f"Error fetching free agents: {e}")
            print("Trying alternative method...")
            # Some versions need position specified
            free_agents = []
            for pos in ["PG", "SG", "SF", "PF", "C"]:
                try:
                    agents = league.free_agents(pos)
                    if agents:
                        free_agents.extend(agents)
                except:
                    pass

    if not free_agents:
        print("No free agents found or unable to fetch.")
        return

    print(f"\nFound {len(free_agents)} free agents:")
    rows = []
    
    for p in free_agents:
        name = p.get("name", "-")
        pos = format_position(p)
        nba_team = format_nba_team(p)
        status = p.get("status") or p.get("injury_note") or ""
        
        # Try to get player stats/rank info if available
        ownership = p.get("percent_owned", "")
        if ownership:
            ownership = f"{ownership}%"
        
        print(f"- {name} ({pos}) — {nba_team} {('[' + status + ']') if status else ''} {('Own: ' + ownership) if ownership else ''}")
        
        rows.append(
            {
                "name": name,
                "position": pos,
                "nba_team": nba_team,
                "status": status,
                "ownership": ownership,
            }
        )

    # Save CSV
    out_path = "free_agents.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "position", "nba_team", "status", "ownership"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
