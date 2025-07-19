import requests

def get_player_info(puuid, api_key):
    # RATE LIMIT 20000/10sec 1200000/10min
    URL = "https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/" + puuid + "?api_key=" + api_key
    response = requests.get(URL)

    if response.status_code == 200:
        player_info = response.json()[0]
        return_info = {"rank": player_info['tier'] + " " + player_info['rank'] + " " + str(player_info['leaguePoints']) + " LP",
                       "winrate": int(player_info['wins'] / (player_info['wins'] + player_info['losses']) * 100)}
        return return_info
    else:
        print("Request failed with status code:", response.status_code)


def get_current_match(puuid, api_key):
    # RATE LIMIT 20000/10sec 1200000/10min
    URL = "https://euw1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/" + puuid + "?api_key=" + api_key
    response = requests.get(URL)

    if response.status_code == 200:
        match_info = response.json()
        return_info = {"gameId": match_info['gameId'],
                       "gameType": match_info['gameQueueConfigId'],
                       "players": [p['puuid'] for p in match_info['participants']],
                       "champions": [p['championId'] for p in match_info['participants']]}
        return return_info
    else:
        print("Request failed with status code:", response.status_code)

# A FIX
def get_last_match(puuid, api_key):
    # RATE LIMIT 2000/10sec
    URL = "https://euw1.api.riotgames.com/lol/match/v5/matches/by-puuid/" + puuid + "/ids?start=0&count=1&api_key=" + api_key
    response = requests.get(URL)

    if response.status_code == 200:
        match_info = response.json()[0]
        return_info = {"gameMode": match_info['gameMode'],
                       "players": [p['id'] for p in match_info['participants']]}
        return return_info
    else:
        print("Request failed with status code:", response.status_code)
