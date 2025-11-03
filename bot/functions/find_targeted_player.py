from typing import Optional

from bot.exceptions.NoPlayerMentioned import NoPlayerMentioned
from bot.exceptions.UnknownPlayer import UnknownPlayer
from config import PLAYERS


async def find_targeted_player(ctx, target) -> Optional[str]:
        # Case where noone is mentioned
        if target is None:
            raise NoPlayerMentioned

        player_name = ""

        if len(ctx.message.mentions) > 0:
            discord_id = str(ctx.message.mentions[0].id)

            for name, data in PLAYERS.items():
                if data["discord_id"] == discord_id:
                    player_name = name
                    break
        else:
            player_name = target.lower()

        # If the person mentioned is not recognized
        if player_name not in PLAYERS:
            raise UnknownPlayer

        return player_name
