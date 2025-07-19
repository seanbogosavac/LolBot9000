def generate_kda_message(player_data, discord_id):
    """Generate a message based on KDA and win/loss."""
    mention = f"<@{int(discord_id)}>"
    deaths = player_data['deaths'] if player_data['deaths'] > 0 else 1  # avoid div by zero
    player_kda = (player_data['kills'] + player_data['assists']) / deaths
    
    if player_data['win']:
        if player_kda > 5:
            return f"**{mention}** a retourné l'équipe adverse avec un KDA aussi gros que son sexe\n"
        elif player_kda < 0.5:
            return f"**{mention}** a gagné sa dernière game mais vu ses stats c'est pas graçe à lui, bref...\n"
        else:
            return f"**{mention}** a gagné sa dernière game\n"
    else:
        if player_kda > 5:
            return f"**{mention}** t'a perdu ta dernière game mais nonobstant tu restes le goat\n"
        elif player_kda < 0.5:
            return f"**{mention}** essaie de mieux jouer la prochaine fois nan ? Histoire de pas faire perdre 40 min a tes mates ?\n"
        else:
            return f"**{mention}** a perdu sa dernière game\n"
