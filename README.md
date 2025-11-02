# LolBot9000

Bot Lol pour mes maisonniers


## Launching project :

Create the .env file and fill the information with these commands :
```bash
cp .env.example .env
nano .env
```

Launch container with :
```bash
docker build -t lolbot9000 .
docker run -d --env-file .env lolbot9000
```
