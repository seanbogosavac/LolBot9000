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

The same works without Discord, from the host or inside the container:

```bash
docker compose exec lolbot python scripts/manage_players.py list
docker compose exec lolbot python scripts/manage_players.py add Maxou 123456789012345678 MaxPseudo#EUW
```

On the first start, if the table is empty, the old `DISCORD_ID_*` / `RIOT_ID_*` variables still
in the environment are imported automatically. After that they are ignored and can be dropped
from `.env`.
