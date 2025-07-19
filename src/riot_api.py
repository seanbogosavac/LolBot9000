import requests

def get_player_info(puuid, api_key):

    URL = "https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/" + puuid + "?api_key=" + api_key

    print(URL)
    response = requests.get(URL)

    if response.status_code == 200:
        print(response.json())
    else:
        print("Request failed with status code:", response.status_code)