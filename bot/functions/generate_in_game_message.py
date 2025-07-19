from config import CHAMPIONS

def generate_in_game_message(player_info, match_data):
    champion = "un champion inconnu"
    puuid = None

    if 'players' in match_data and 'champions' in match_data:
        try:
            mention = f"<@{int(player_info['discord_id'])}>"
            if puuid in match_data['players']:
                champ_id = match_data['champions'][match_data['players'].index(puuid)]
                champion = CHAMPIONS.get(champ_id, "un champion inconnu")
        except Exception:
            pass

    game_type = match_data.get("gameType", "")
    if game_type == '400':
        return f"{mention} remet les crampons pour une nouvelle game avec **{champion}**"
    elif game_type == '420':
        return f"Omg {mention} part en ranked sur avec **{champion}** ! Tout pour les e-points"
    elif game_type == '430':
        return f"{mention} a lancé une normale classique vanille #aucuneDraftAucunFun. Je vais même pas dire sur quel champ t'es pour la peine..."
    elif game_type == '450':
        return f"{mention} veut chill et part en ARAM avec **{champion}**"
    elif game_type == '900':
        return f"{mention} joue au mode clash... (Qui fait ça?)"
    else:
        return None
