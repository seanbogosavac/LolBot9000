import requests

def get_player_info(puuid, api_key):
    # RATE LIMIT 20000/10sec
    url = "https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/" + puuid + "?api_key=" + api_key
    response = requests.get(url)

    if response.status_code == 200:
        player_info = response.json()[0]
        return_info = {
            "rank": player_info['tier'] + " " + player_info['rank'] + " " + str(player_info['leaguePoints']) + " LP",
            "winrate": int(player_info['wins'] / (player_info['wins'] + player_info['losses']) * 100)
        }
        return return_info
    else:
        print("Request failed with status code:", response.status_code)
        return None


def get_current_match(puuid, api_key):
    # RATE LIMIT 20000/10sec
    url = "https://euw1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/" + puuid + "?api_key=" + api_key
    response = requests.get(url)

    if response.status_code == 200:
        match_info = response.json()
        return_info = {
            "gameId": match_info['gameId'],
            "gameType": match_info['gameQueueConfigId'],
            "players": [p['puuid'] for p in match_info['participants']],
            "champions": [p['championId'] for p in match_info['participants']]
        }
        return return_info
    else:
        print("Request failed with status code:", response.status_code)
        return None


def get_last_match_id(puuid, api_key):
    # RATE LIMIT 2000/10sec
    url = "https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/" + puuid + "/ids?start=0&count=1&api_key=" + api_key
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()[0]
    else:
        print("Request failed with status code:", response.status_code)
        return None


def get_match_data(match_id, api_key):
    # RATE LIMIT 2000/10sec
    url = "https://europe.api.riotgames.com/lol/match/v5/matches/" + match_id + "?api_key=" + api_key
    response = requests.get(url)

    if response.status_code == 200:
        match_data = response.json()

        # Retrieve match data
        duration_seconds = match_data['info']['gameDuration']
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        duration_str = f"{minutes}:{seconds:02d}"  # format seconds with leading zero
        return_data = {
            "gameType": match_data['info']['queueId'],
            "duration": duration_str,
            "participants": []
        }

        # Retrieve participants data
        for p in match_data['info']['participants']:
            participant_info = {
                "puuid": p.get('puuid', 'Unknown'),
                "champion": p.get('championName', 'Unknown'),
                "kills": p.get('kills', 0),
                "deaths": p.get('deaths', 0),
                "assists": p.get('assists', 0),
                "win": p.get('win', False),
                "cs": p.get('totalMinionsKilled', 0),
                "gold": p.get('goldEarned', 0)
            }
            return_data['participants'].append(participant_info)

        return return_data
    else:
        print("Request failed with status code:", response.status_code)
        return None
