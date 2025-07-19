import discord
from config import QUEUE_NAMES

def generate_match_embed(player_name, match_data, player_puuid):
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

    winners_text = build_team_block(winners, player_puuid)
    losers_text = build_team_block(losers, player_puuid)

    embed = discord.Embed(
        title=f"Dernier match de {player_name.capitalize()}",
        description=f"**{queue_name}** | **{duration}**",
        color=discord.Color.green() if any(p['puuid'] == player_puuid and p['win'] for p in match_data['participants']) else discord.Color.red()
    )
    embed.add_field(name="✅ Équipe gagnante", value=winners_text or "Aucun", inline=False)
    embed.add_field(name="❌ Équipe perdante", value=losers_text or "Aucun", inline=False)

    return embed
