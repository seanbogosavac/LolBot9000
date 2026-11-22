# LolBot9000

Bot Lol pour mes maisonniers


## Launching project :

Create the .env file and fill the information with these commands :
```bash
cp .env.example .env
nano .env
```

Launch container with :
```bash
docker compose up -d --build
```

Updating after a `git pull` :
```bash
docker compose up -d --build
```
The `--build` flag matters: plain `docker compose up -d` reuses the existing image and
keeps running the old code without any warning.

## Project layout

```
lolbot/                 the application (run with `python -m lolbot`)
  settings.py           environment variables and constants (no side effects)
  services.py           lazily built shared objects: player database, Riot client, champions
  bot/                  Discord commands, polling loop and message formatting
  api/                  Riot API client and Data Dragon
  db/                   SQLite player repository and migrations
  manage_players.py     command-line roster management
tests/                  pytest suite
pyproject.toml          dependencies and pytest configuration
```

Local development:

```bash
pip install -e ".[dev]"
pytest
python -m lolbot
```

## Players

Players live in a SQLite database (`data/players.db`, or `PLAYERS_DB` when set) instead of
the `.env` file, so the roster can change without rebuilding or restarting anything. The file
is kept in the `players-db` docker volume, so it survives rebuilds.

Register a player from Discord: the name, the Discord account, then the Riot account as
`Pseudo#TAG` (resolved through the Riot API) or as a raw puuid:

```
!addplayer Maxou <@123456789012345678> MaxPseudo#EUW
!players
!updateplayer Maxou <@222222222222222222>
!removeplayer Maxou
```

`!players` shows each player's in-game Riot name (`Pseudo#TAG`) rather than their puuid. The
name is stored in the `riot_name` column: it comes straight from the `Pseudo#TAG` you register,
and rows that don't have one yet (registered with a bare puuid, or added before the column
existed) are resolved through the Riot Account API the next time `!players` runs — or up front
with `python -m lolbot.manage_players syncnames`.

The same works without Discord, from the host or inside the container:

```bash
docker compose exec lolbot python -m lolbot.manage_players list
docker compose exec lolbot python -m lolbot.manage_players add Maxou 123456789012345678 MaxPseudo#EUW
docker compose exec lolbot python -m lolbot.manage_players syncnames
```

## Version

Versions are `MAJOR.MINOR.PATCH`, stored as `vX.Y.Z` git tags. Every push to `master` makes the
deploy workflow tag the next version and bake it (with the commit sha) into the image. The patch
number is incremented by default; put `[minor]` or `[major]` in the PR title to bump that part
instead (the merge commit message carries it). A manual run of the workflow offers the same choice
in a dropdown. Redeploying a commit that already has a tag keeps its version.

To see what is running:

```bash
docker compose exec lolbot python -m lolbot --version   # e.g. "lolbot 1.2.3 (a1b2c3d)"
```

or send `!version` in Discord. A manual `docker compose up -d --build` outside the workflow
reports `dev`. The version is also logged at startup.

The database is the only source of the roster: the old `DISCORD_ID_*` / `RIOT_ID_*` variables
are no longer read, and a fresh (or wiped) `players-db` volume starts empty. Re-register the
players with `!addplayer`, or with `python -m lolbot.manage_players add` straight from the host.
