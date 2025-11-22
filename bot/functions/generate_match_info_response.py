import discord
from config import QUEUE_NAMES


def generate_kda_message(player_info, match_data):
    player_data = next(
        (p for p in match_data['participants'] if p['puuid'] == player_info['puuid']), None
    )

    deaths = player_data['deaths'] or 1  # Avoid division by zero
    kda = (player_data['kills'] + player_data['assists']) / deaths
    win = player_data['win']


    message = f"{player_info['name']}"
    if win:
        if kda > 5:
            message += " a retourné l'équipe adverse avec un KDA aussi gros que son sexe\n"
        elif kda < 0.5:
            message += " a gagné sa dernière game mais vu ses stats c'est pas graçe à lui, bref...\n"
        else:
            message += " a gagné sa dernière game\n"
    else:
        if kda > 5:
            message += " t'a perdu ta dernière game mais nonobstant tu restes le goat\n"
        elif kda < 0.5:
            message += " essaie de mieux jouer la prochaine fois nan ? Histoire de pas faire perdre 40 min a tes mates ?\n"
        else:
            message += " a perdu sa dernière game\n"
    return message


def generate_match_embed(player_info, match_data):
    queue_name = QUEUE_NAMES.get(match_data['gameType'], f"Queue {match_data['gameType']}")
    duration = match_data['duration']

    winners = [p for p in match_data['participants'] if p['win']]
    losers = [p for p in match_data['participants'] if not p['win']]

    def build_team_block(team, selected_puuid):
        header = f"{'':2}{'Champion':<12} {'K/D/A':^9} {'CS':^6} {'Gold':^7}"
        separator = f"{'':2}{'-'*12} {'-'*9} {'-'*6} {'-'*7}"
        lines = [header, separator]
        for p in team:
            marker = "*" if p['puuid'] == selected_puuid else " "
            champ = p['champion']
            kda = f"{p['kills']}/{p['deaths']}/{p['assists']}"
            cs = p['cs']
            gold = p['gold']
            row = f"{marker} {champ:<12} {kda:^9} {cs:^6} {gold:^7}"
            lines.append(row)
        return "```\n" + "\n".join(lines) + "\n```"

    winners_text = build_team_block(winners, player_info['puuid'])
    losers_text = build_team_block(losers, player_info['puuid'])

    embed = discord.Embed(
        title=f"Dernier match de {player_info['name'].capitalize()}",
        description=f"**{queue_name}** | **{duration}**",
        color=discord.Color.green() if any(p['puuid'] == player_info['puuid'] and p['win'] for p in match_data['participants']) else discord.Color.red()
    )
    embed.add_field(name="✅ Équipe gagnante", value=winners_text or "Aucun", inline=False)
    embed.add_field(name="❌ Équipe perdante", value=losers_text or "Aucun", inline=False)

    return embed


# Generate and send the match data
def generate_match_info_response(player_info, match_data):
    return generate_kda_message(player_info, match_data), generate_match_embed(player_info, match_data)