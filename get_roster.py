import os
import sys
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa

APP_KEY = os.getenv("dj0yJmk9UHowcjlnNGZUNEtyJmQ9WVdrOVRtTm9PVFI0VFhBbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTEx")
APP_SECRET = os.getenv("Y9848f466f58cd923e1f107b85854f522671e0ddd")

def get_oauth():
    """
    Returns a valid OAuth2 object.
    Uses oauth2.json to persist tokens so you only auth once.
    """
    # First try to load saved credentials
    if os.path.exists("oauth2.json"):
        oauth = OAuth2(None, None, from_file="oauth2.json")
        if not oauth.token_is_valid():
            oauth.refresh_access_token()
        return oauth

    # Fresh login with env vars
    if not APP_KEY or not APP_SECRET:
        print("Missing YAHOO_CLIENT_ID / YAHOO_CLIENT_SECRET env vars.", file=sys.stderr)
        sys.exit(1)

    oauth = OAuth2(consumer_key=APP_KEY, consumer_secret=APP_SECRET)
    # This opens a browser once; sign in and approve the app.
    if not oauth.token_is_valid():
        oauth.refresh_access_token()
    oauth.save("oauth2.json")
    return oauth

def main():
    oauth = get_oauth()

    # Connect to NBA game
    gm = yfa.Game(oauth, 'nba')

    # List your leagues, pick one
    league_ids = gm.league_ids()
    if not league_ids:
        print("No NBA leagues found for this Yahoo account.")
        return

    print("Your NBA league IDs:", league_ids)
    # If you know the league key, set it here instead of [0]
    league = gm.to_league(league_ids[0])

    # Show your teams in this league
    teams = league.teams()  # dict: {team_key: team_name}
    print("Teams in this league:")
    for k, v in teams.items():
        print(f"  {k} -> {v}")

    # Choose your team (if multiple, pick by name)
    # Default: first team
    my_team_key = next(iter(teams.keys()))
    my_team = league.to_team(my_team_key)

    # Fetch and print roster
    roster = my_team.roster()  # list of dicts
    print("\nYour current roster:")
    for p in roster:
        # p has keys like: name, position, editorial_team_full_name, status, etc.
        name = p.get("name")
        pos = p.get("position")
        team = p.get("editorial_team_abbr") or p.get("editorial_team_full_name")
        print(f"- {name} ({pos}) — {team}")

if __name__ == "__main__":
    main()
