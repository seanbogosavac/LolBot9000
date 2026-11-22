import discord
from lolbot.settings import QUEUE_NAMES


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


def _build_team_block(team, selected_puuids) -> str:
    header = f"{'':2}{'Champion':<12} {'K/D/A':^9} {'CS':^6} {'Gold':^7}"
    separator = f"{'':2}{'-'*12} {'-'*9} {'-'*6} {'-'*7}"
    lines = [header, separator]
    for p in team:
        marker = "*" if p["puuid"] in selected_puuids else " "
        kda = f"{p['kills']}/{p['deaths']}/{p['assists']}"
        lines.append(f"{marker} {p['champion']:<12} {kda:^9} {p['cs']:^6} {p['gold']:^7}")
    return "```\n" + "\n".join(lines) + "\n```"


def generate_group_match_embed(player_infos, match_data) -> discord.Embed:
    """Build the recap embed for one or several tracked players who shared the same game."""
    puuids = {info["puuid"] for info in player_infos}
    participants = match_data["participants"]
    results = [next(p for p in participants if p["puuid"] == puuid)["win"] for puuid in puuids]

    queue_name = QUEUE_NAMES.get(match_data["gameType"], f"Queue {match_data['gameType']}")
    winners = [p for p in participants if p["win"]]
    losers = [p for p in participants if not p["win"]]

    if all(results):
        color = discord.Color.green()
    elif not any(results):
        color = discord.Color.red()
    else:
        color = discord.Color.gold()

    names = ", ".join(info["name"].capitalize() for info in player_infos)
    embed = discord.Embed(
        title=f"Dernier match de {names}",
        description=f"**{queue_name}** | **{match_data['duration']}**",
        color=color,
    )
    embed.add_field(name="✅ Équipe gagnante", value=_build_team_block(winners, puuids) or "Aucun", inline=False)
    embed.add_field(name="❌ Équipe perdante", value=_build_team_block(losers, puuids) or "Aucun", inline=False)
    return embed


def generate_group_message(player_infos, match_data) -> str:
    """One line per tracked player saying whether they won or lost the shared game."""
    lines = ["Game terminée pour plusieurs joueurs :"]
    for info in player_infos:
        player = next(p for p in match_data["participants"] if p["puuid"] == info["puuid"])
        lines.append(f"✅ {info['name']} a gagné" if player["win"] else f"❌ {info['name']} a perdu")
    return "\n".join(lines)


def generate_match_info_response(player_info, match_data) -> tuple[str, discord.Embed]:
    return generate_kda_message(player_info, match_data), generate_group_match_embed([player_info], match_data)


def generate_group_match_info_response(player_infos, match_data) -> tuple[str, discord.Embed]:
    """A solo player keeps the detailed KDA message; several players share one summary."""
    if len(player_infos) == 1:
        return generate_match_info_response(player_infos[0], match_data)
    return generate_group_message(player_infos, match_data), generate_group_match_embed(player_infos, match_data)
