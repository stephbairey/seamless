#!/usr/bin/env python3
"""
Get a Google OAuth2 refresh token for Seamless.

Usage:
    python scripts/get_oauth_token.py --scope gmail
    python scripts/get_oauth_token.py --scope calendar

Scopes:
    gmail       Gmail read/write/compose (for email triage module)
    calendar    Google Calendar read/write (for calendar sync module)
    drive       Google Drive read/write (for file management module)

You'll need your Client ID and Client Secret from Google Cloud Console.
If you've already set them in secrets.env, the script will read them
from there automatically.

The script opens a browser window for Google login. Log in with the
account you want the token for, authorize, and the refresh token is
printed at the end. Paste it into secrets.env.

Requires: pip install google-auth-oauthlib
(Run outside Docker, on your local machine where you have a browser.)
"""

import argparse
import json
import os
import sys
from pathlib import Path

SCOPE_MAP = {
    "gmail": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.compose",
    ],
    "calendar": [
        "https://www.googleapis.com/auth/calendar",
    ],
    "drive": [
        "https://www.googleapis.com/auth/drive",
    ],
}

ENV_VAR_HINTS = {
    "gmail": "GMAIL_REFRESH_TOKEN",
    "calendar": (
        "GCAL_LINGUAINKMEDIA_TOKEN  (if you logged in as linguainkmedia@gmail.com)\n"
        "  GCAL_MJBAIREY_TOKEN        (if you logged in as mjbairey@gmail.com)\n"
        "  GCAL_STEPHBAIREY_TOKEN      (if you logged in as stephbairey@gmail.com)"
    ),
    "drive": "GDRIVE_REFRESH_TOKEN",
}


def load_secrets_env() -> dict[str, str]:
    """Try to read client_id/secret from secrets.env if it exists."""
    env = {}
    # Check a few possible locations
    for candidate in [
        Path(__file__).resolve().parent.parent / "secrets.env",
        Path.cwd() / "secrets.env",
    ]:
        if candidate.exists():
            with open(candidate) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        env[key.strip()] = val.strip()
            break
    return env


def main():
    parser = argparse.ArgumentParser(
        description="Get a Google OAuth2 refresh token for Seamless."
    )
    parser.add_argument(
        "--scope",
        required=True,
        choices=list(SCOPE_MAP.keys()),
        help="Which API scope to authorize",
    )
    parser.add_argument(
        "--client-id",
        default="",
        help="OAuth Client ID (reads from secrets.env if not provided)",
    )
    parser.add_argument(
        "--client-secret",
        default="",
        help="OAuth Client Secret (reads from secrets.env if not provided)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Local port for OAuth redirect (0 = auto)",
    )
    args = parser.parse_args()

    # Try to import the library
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Missing dependency. Install it with:")
        print("  pip install google-auth-oauthlib")
        sys.exit(1)

    # Resolve client ID and secret
    client_id = args.client_id
    client_secret = args.client_secret

    if not client_id or not client_secret:
        env = load_secrets_env()
        if not client_id:
            client_id = env.get("GMAIL_CLIENT_ID", "")
        if not client_secret:
            client_secret = env.get("GMAIL_CLIENT_SECRET", "")

    if not client_id:
        client_id = input("Client ID: ").strip()
    if not client_secret:
        client_secret = input("Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required.")
        print("Get them from: https://console.cloud.google.com/apis/credentials")
        sys.exit(1)

    scopes = SCOPE_MAP[args.scope]

    print(f"\nScope: {args.scope}")
    print(f"Scopes: {', '.join(scopes)}")
    print(f"Client ID: {client_id[:20]}...")
    print()
    print("A browser window will open. Log in with the Google account")
    print("you want to authorize and click Allow.")
    print()

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=scopes,
    )

    creds = flow.run_local_server(port=args.port)

    print()
    print("=" * 60)
    print("REFRESH TOKEN (copy this into secrets.env):")
    print("=" * 60)
    print()
    print(creds.refresh_token)
    print()
    print(f"Add it to secrets.env as:")
    print(f"  {ENV_VAR_HINTS[args.scope]}")
    print()
    print("Then restart: docker-compose down && docker-compose up -d --build")
    print("(from the docker/ directory)")


if __name__ == "__main__":
    main()
