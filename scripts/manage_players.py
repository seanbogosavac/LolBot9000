"""Manage the SQLite player roster from the command line.

Works without Discord, which is handy inside the container:

    docker compose exec lolbot python scripts/manage_players.py list
    docker compose exec lolbot python scripts/manage_players.py add Maxime 123456789012345678 Pseudo#EUW

Run it with the same PLAYERS_DB the bot uses, otherwise you'll be editing another file.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import RiotAPIError, RiotClient
from db import DatabaseError, PlayerRepository, seed_from_environment


def resolve_puuid(identifier: str, api_key: str | None) -> str:
    """Return the puuid behind a raw puuid or a "Pseudo#TAG" Riot ID."""
    if "#" not in identifier:
        return identifier
    if not api_key:
        raise SystemExit("RIOT_API_KEY is required to resolve a Riot ID into a puuid.")

    client = RiotClient(api_key=api_key)
    try:
        return client.get_puuid_by_riot_id(identifier)
    except RiotAPIError as e:
        raise SystemExit(str(e))
    finally:
        client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=os.getenv("PLAYERS_DB"), help="path of the SQLite database (default: the bot's)")
    sub = parser.add_subparsers(dest="action", required=True)

    p_add = sub.add_parser("add", help="register a player")
    p_add.add_argument("name")
    p_add.add_argument("discord_id", help="Discord snowflake or <@id> mention")
    p_add.add_argument("riot_id", help="Riot ID (Pseudo#TAG) or raw puuid")

    p_remove = sub.add_parser("remove", help="unregister a player")
    p_remove.add_argument("name")

    p_update = sub.add_parser("update", help="re-link a player to new accounts")
    p_update.add_argument("name")
    p_update.add_argument("--discord-id", dest="discord_id")
    p_update.add_argument("--riot-id", dest="riot_id")

    sub.add_parser("list", help="show every registered player")
    sub.add_parser("seed", help="import the legacy DISCORD_ID_*/RIOT_ID_* env vars when the table is empty")

    args = parser.parse_args(argv)
    db_path = args.db or str(Path(__file__).resolve().parent.parent / "data" / "players.db")

    try:
        repo = PlayerRepository(db_path)
    except DatabaseError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    api_key = os.getenv("RIOT_API_KEY")
    with repo:
        try:
            if args.action == "add":
                player = repo.add(args.name, args.discord_id, resolve_puuid(args.riot_id, api_key))
                print(f"added {player['name']} (discord_id={player['discord_id']}, puuid={player['puuid']})")
            elif args.action == "remove":
                print(f"removed {repo.remove(args.name)['name']}")
            elif args.action == "update":
                puuid = resolve_puuid(args.riot_id, api_key) if args.riot_id else None
                player = repo.update(args.name, discord_id=args.discord_id, puuid=puuid)
                print(f"updated {player['name']} (discord_id={player['discord_id']}, puuid={player['puuid']})")
            elif args.action == "seed":
                print(f"seeded {seed_from_environment(repo)} player(s)")
            else:
                roster = repo.all()
                if not roster:
                    print("no player registered")
                for player in roster:
                    print(f"{player['name']:<16} {player['discord_id']:<20} {player['puuid']}")
        except DatabaseError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
