from config import PLAYERS;

async def get_targeted_player_info(ctx, target):
    discord_id = ""
    player_info = None

    if len(ctx.message.mentions) > 0:
        discord_id = str(ctx.message.mentions[0].id)

    for name, data in PLAYERS.items():
        if data["discord_id"] == discord_id or name == target.lower():
            player_info = data

    return player_info
