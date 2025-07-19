import requests

def get_player_info(puuid, api_key):

    URL = "https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/" + puuid + "?api_key=" + api_key
    response = requests.get(URL)

    if response.status_code == 200:
        player_info = response.json()[0]
        return_info = {"rank": player_info['tier'] + " " + player_info['rank'] + " " + str(player_info['leaguePoints']) + " LP",
                       "winrate": int(player_info['wins'] / (player_info['wins'] + player_info['losses']) * 100)}
        return return_info
    else:
        print("Request failed with status code:", response.status_code)
