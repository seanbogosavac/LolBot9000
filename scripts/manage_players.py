"""Manage the SQLite player roster from the command line.

Works without Discord, which is handy inside the container:

    docker compose exec lolbot python scripts/manage_players.py list
    docker compose exec lolbot python scripts/manage_players.py add Maxime 123456789012345678 Pseudo#EUW
    docker compose exec lolbot python scripts/manage_players.py syncnames

Run it with the same PLAYERS_DB the bot uses, otherwise you'll be editing another file.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import RiotAPIError, RiotClient
from db import DatabaseError, PlayerInfos, PlayerRepository


def resolve_puuid(identifier: str, api_key: str | None) -> str:
    """Return the puuid behind a raw puuid or a "Pseudo#TAG" Riot ID."""
    if "#" not in identifier:
        return identifier
    client = _client(api_key)
    try:
        return client.get_puuid_by_riot_id(identifier)
    except RiotAPIError as e:
        raise SystemExit(str(e))
    finally:
        client.close()


def resolve_riot_name(identifier: str) -> str | None:
    """Return the in-game name carried by a "Pseudo#TAG" identifier.

    A raw puuid doesn't tell us the name, so the row is stored without one; `syncnames`
    (or the bot on the next `!players`) resolves it from the Account API.
    """
    if "#" not in identifier:
        return None
    return identifier.strip().lstrip("@")


def _client(api_key: str | None) -> RiotClient:
    if not api_key:
        raise SystemExit("RIOT_API_KEY is required to talk to the Riot API.")
    return RiotClient(api_key=api_key)


def sync_riot_names(repo: PlayerRepository, api_key: str | None) -> int:
    """Resolve and store the in-game name of every player that doesn't have one yet."""
    missing = [player for player in repo.all() if not player["riot_name"]]
    if not missing:
        return 0

    client = _client(api_key)
    updated = 0
    try:
        for player in missing:
            try:
                riot_name = client.get_riot_id_by_puuid(player["puuid"])
            except RiotAPIError as e:
                print(f"warning: {player['name']}: {e}", file=sys.stderr)
                continue

            repo.update(player["name"], riot_name=riot_name)
            updated += 1
    finally:
        client.close()
    return updated


def format_roster(roster: list[PlayerInfos]) -> str:
    lines = [f"{'Name':<16} {'Riot':<28} {'Discord':<20} puuid"]
    for player in roster:
        riot_name = player["riot_name"] or "-"
        lines.append(f"{player['name']:<16} {riot_name:<28} {player['discord_id']:<20} {player['puuid']}")
    return "\n".join(lines)


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
    sub.add_parser("syncnames", help="fill in the in-game Riot name of players that have none")

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
                puuid = resolve_puuid(args.riot_id, api_key)
                player = repo.add(args.name, args.discord_id, puuid, resolve_riot_name(args.riot_id))
                print(f"added {player['name']} (riot={player['riot_name'] or 'unknown'}, discord_id={player['discord_id']}, puuid={player['puuid']})")
            elif args.action == "remove":
                print(f"removed {repo.remove(args.name)['name']}")
            elif args.action == "update":
                puuid = resolve_puuid(args.riot_id, api_key) if args.riot_id else None
                riot_name = resolve_riot_name(args.riot_id) if args.riot_id else None
                player = repo.update(args.name, discord_id=args.discord_id, puuid=puuid, riot_name=riot_name)
                print(f"updated {player['name']} (riot={player['riot_name'] or 'unknown'}, discord_id={player['discord_id']}, puuid={player['puuid']})")
            elif args.action == "syncnames":
                print(f"resolved {sync_riot_names(repo, api_key)} in-game name(s)")
            else:
                roster = repo.all()
                if not roster:
                    print("no player registered")
                else:
                    print(format_roster(roster))
        except DatabaseError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
