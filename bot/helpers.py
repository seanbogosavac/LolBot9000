import discord
from config import QUEUE_NAMES


def generate_kda_message(player_info, match_data) -> str:
    player = next(p for p in match_data["participants"] if p["puuid"] == player_info["puuid"])
    kda = (player["kills"] + player["assists"]) / (player["deaths"] or 1)
    win = player["win"]

    name = player_info["name"]
    if win:
        if kda > 5:
            return f"{name} a retourné l'équipe adverse avec un KDA aussi gros que son sexe\n"
        elif kda < 0.5:
            return f"{name} a gagné sa dernière game mais vu ses stats c'est pas graçe à lui, bref...\n"
        else:
            return f"{name} a gagné sa dernière game\n"
    else:
        if kda > 5:
            return f"{name} t'a perdu ta dernière game mais nonobstant tu restes le goat\n"
        elif kda < 0.5:
            return f"{name} essaie de mieux jouer la prochaine fois nan ? Histoire de pas faire perdre 40 min a tes mates ?\n"
        else:
            return f"{name} a perdu sa dernière game\n"


def _build_team_block(team, selected_puuid) -> str:
    header = f"{'':2}{'Champion':<12} {'K/D/A':^9} {'CS':^6} {'Gold':^7}"
    separator = f"{'':2}{'-'*12} {'-'*9} {'-'*6} {'-'*7}"
    lines = [header, separator]
    for p in team:
        marker = "*" if p["puuid"] == selected_puuid else " "
        kda = f"{p['kills']}/{p['deaths']}/{p['assists']}"
        lines.append(f"{marker} {p['champion']:<12} {kda:^9} {p['cs']:^6} {p['gold']:^7}")
    return "```\n" + "\n".join(lines) + "\n```"


def generate_match_embed(player_info, match_data) -> discord.Embed:
    puuid = player_info["puuid"]
    participants = match_data["participants"]
    player = next(p for p in participants if p["puuid"] == puuid)

    queue_name = QUEUE_NAMES.get(match_data["gameType"], f"Queue {match_data['gameType']}")
    winners = [p for p in participants if p["win"]]
    losers = [p for p in participants if not p["win"]]

    embed = discord.Embed(
        title=f"Dernier match de {player_info['name'].capitalize()}",
        description=f"**{queue_name}** | **{match_data['duration']}**",
        color=discord.Color.green() if player["win"] else discord.Color.red(),
    )
    embed.add_field(name="✅ Équipe gagnante", value=_build_team_block(winners, puuid) or "Aucun", inline=False)
    embed.add_field(name="❌ Équipe perdante", value=_build_team_block(losers, puuid) or "Aucun", inline=False)
    return embed


def generate_match_info_response(player_info, match_data) -> tuple[str, discord.Embed]:
    return generate_kda_message(player_info, match_data), generate_match_embed(player_info, match_data)

