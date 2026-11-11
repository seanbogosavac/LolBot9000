import pytest

import bot.commands as commands
from api import RiotAPIError
from bot.exceptions import NoPlayerMentioned, UnknownPlayer
from tests.conftest import (
    DISCORD_MAXIME,
    DISCORD_SEAN,
    DISCORD_THOMAS,
    PUUID_MAXIME,
    PUUID_SEAN,
    PUUID_THOMAS,
    RIOT_NAME_MAXIME,
    RIOT_NAME_SEAN,
    run,
)


def call(command, ctx, *args):
    """Invoke the callback behind a discord.py Command and return what it sent."""
    run(command.callback(ctx, *args))
    return ctx.sent


class TestTargetResolution:
    def test_a_mentioned_player_is_found_by_discord_id(self, seeded_roster, ctx):
        player = run(commands.find_targeted_player(ctx(DISCORD_SEAN), "<@123456789012345678>"))
        assert player["name"] == "Sean"

    def test_the_mention_wins_over_the_text_typed_with_it(self, seeded_roster, ctx):
        player = run(commands.find_targeted_player(ctx(DISCORD_SEAN), "whatever"))
        assert player["name"] == "Sean"

    def test_a_name_is_matched_case_insensitively(self, seeded_roster, ctx):
        assert run(commands.find_targeted_player(ctx(), "sEaN"))["discord_id"] == DISCORD_SEAN

    def test_no_target_is_reported(self, seeded_roster, ctx):
        with pytest.raises(NoPlayerMentioned):
            run(commands.find_targeted_player(ctx(), None))

    def test_an_unknown_player_is_reported(self, seeded_roster, ctx):
        with pytest.raises(UnknownPlayer):
            run(commands.find_targeted_player(ctx(), "ghost"))

    def test_an_unregistered_mention_is_reported(self, seeded_roster, ctx):
        with pytest.raises(UnknownPlayer):
            run(commands.find_targeted_player(ctx(DISCORD_THOMAS), "<@555555555555555555>"))


class TestParsePlayerArgs:
    def test_name_discord_and_riot_id_are_split_out(self):
        name, discord_id, riot_id = commands.parse_player_args(
            ["Max", "Oume", "<@222222222222222222>", "Max#EUW"], require_riot_id=True
        )
        assert (name, discord_id, riot_id) == ("Max Oume", "222222222222222222", "Max#EUW")

    def test_arguments_may_come_in_any_order(self):
        name, discord_id, riot_id = commands.parse_player_args(["Thomas#EUW", "Tom", DISCORD_THOMAS])
        assert (name, discord_id, riot_id) == ("Tom", DISCORD_THOMAS, "Thomas#EUW")

    def test_a_long_trailing_token_is_taken_as_a_puuid(self):
        name, discord_id, riot_id = commands.parse_player_args(["Guy", DISCORD_THOMAS, PUUID_THOMAS])
        assert (name, discord_id, riot_id) == ("Guy", DISCORD_THOMAS, PUUID_THOMAS)

    def test_a_short_trailing_token_stays_part_of_the_name(self):
        name, discord_id, riot_id = commands.parse_player_args(["Oncle Ben", DISCORD_THOMAS])
        assert (name, discord_id, riot_id) == ("Oncle Ben", DISCORD_THOMAS, None)

    def test_a_missing_riot_id_is_rejected_when_required(self):
        with pytest.raises(commands.PlayerActionError, match="compte Riot"):
            commands.parse_player_args(["Guy", DISCORD_THOMAS], require_riot_id=True)


class TestRosterCommands:
    def test_addplayer_registers_the_player(self, roster, fake_riot, ctx):
        out = call(commands.addplayer, ctx(), "Max", "Oume", f"<@{DISCORD_MAXIME}>", "Maxime#EUW")
        assert "Max Oume" in out[0]
        assert roster.get("max oume")["puuid"] == PUUID_MAXIME

    def test_addplayer_can_use_a_raw_puuid(self, roster, fake_riot, ctx):
        call(commands.addplayer, ctx(), "Thomas", DISCORD_THOMAS, PUUID_THOMAS)
        assert roster.get("Thomas")["puuid"] == PUUID_THOMAS

    @pytest.mark.parametrize("args,expected", [
        (("Guy",), "compte Riot"),
        (("Guy", DISCORD_THOMAS), "compte Riot"),
        ((f"<@{DISCORD_THOMAS}>", "Thomas#EUW"), "pseudo"),
        (("Guy", "12345", "Thomas#EUW"), "Tag la personne"),
    ])
    def test_addplayer_asks_for_what_is_missing(self, roster, fake_riot, ctx, args, expected):
        out = call(commands.addplayer, ctx(), *args)
        assert expected in out[0]
        assert roster.count() == 0

    def test_addplayer_reports_a_duplicate(self, seeded_roster, fake_riot, ctx):
        out = call(commands.addplayer, ctx(), "Sean", DISCORD_THOMAS, "Thomas#EUW")
        assert "déjà enregistré" in out[0]

    def test_updateplayer_relinks_a_discord_account(self, seeded_roster, fake_riot, ctx):
        out = call(commands.updateplayer, ctx(), "Sean", DISCORD_THOMAS)
        assert "mis à jour" in out[0]
        assert seeded_roster.get("Sean")["discord_id"] == DISCORD_THOMAS

    def test_updateplayer_needs_something_to_change(self, seeded_roster, ctx):
        assert "Donne-moi" in call(commands.updateplayer, ctx(), "Sean")[0]

    def test_removeplayer_unregisters_a_player(self, seeded_roster, ctx):
        assert "n'est plus dans la base" in call(commands.removeplayer, ctx(), "Maxime")[0]
        assert seeded_roster.count() == 1
        assert "pas dans la liste" in call(commands.removeplayer, ctx(), "Maxime")[0]

    def test_players_lists_the_roster(self, seeded_roster, fake_riot, ctx):
        out = call(commands.listplayers, ctx())[0]
        assert "2 joueur" in out and "Sean" in out and RIOT_NAME_SEAN in out

    def test_players_shows_the_in_game_name_not_the_puuid(self, seeded_roster, fake_riot, ctx):
        out = call(commands.listplayers, ctx())[0]
        assert PUUID_SEAN[:16] not in out and RIOT_NAME_MAXIME in out

    def test_players_resolves_names_missing_from_old_rows(self, roster, fake_riot, ctx):
        roster.add("Sean", DISCORD_SEAN, PUUID_SEAN)  # registered before the riot_name column
        out = call(commands.listplayers, ctx())[0]
        assert RIOT_NAME_SEAN in out
        assert roster.get("Sean")["riot_name"] == RIOT_NAME_SEAN

    def test_players_falls_back_to_the_puuid_when_riot_is_unreachable(self, roster, fake_riot, monkeypatch, ctx):
        roster.add("Sean", DISCORD_SEAN, PUUID_SEAN)

        def unavailable(puuid):
            raise RiotAPIError("unreachable")

        monkeypatch.setattr(commands.riot_client, "get_riot_id_by_puuid", unavailable)
        out = call(commands.listplayers, ctx())[0]
        assert f"`{PUUID_SEAN[:16]}…`" in out

    def test_players_hints_at_addplayer_when_empty(self, roster, ctx):
        assert "!addplayer" in call(commands.listplayers, ctx())[0]


class TestStatCommands:
    def test_lol_mentions_the_player_with_their_rank(self, seeded_roster, fake_riot, ctx):
        out = call(commands.lol, ctx(), "sean")[0]
        assert f"<@{DISCORD_SEAN}>" in out and "GOLD II 45 LP" in out and "win streak" in out

    def test_lol_shows_a_lose_streak(self, seeded_roster, fake_riot, ctx):
        assert "lose streak" in call(commands.lol, ctx(), "Maxime")[0]

    def test_lol_tells_an_unranked_player_to_queue(self, seeded_roster, fake_riot, ctx):
        seeded_roster.add("Thomas", DISCORD_THOMAS, PUUID_THOMAS)
        assert "pas de rang" in call(commands.lol, ctx(), "Thomas")[0]

    def test_lol_answers_who_is_missing(self, seeded_roster, ctx):
        assert "Dis les termes" in call(commands.lol, ctx())[0]
        assert "C'est qui frère" in call(commands.lol, ctx(), "ghost")[0]

    def test_leaderboard_ranks_the_roster_and_crowns_the_goat(self, seeded_roster, fake_riot, ctx):
        out = call(commands.leaderboard, ctx())[0]
        assert f"<@{DISCORD_MAXIME}>" in out
        assert out.index("Maxime") < out.index("Sean")

    def test_leaderboard_says_so_when_nobody_is_registered(self, roster, ctx):
        assert "no player data" in call(commands.leaderboard, ctx())[0]

    def test_leaderboard_survives_a_riot_api_failure(self, seeded_roster, monkeypatch, ctx):
        from api import RiotAPIError

        def failing(puuid):
            raise RiotAPIError("boom")

        monkeypatch.setattr(commands.riot_client, "get_player_info", failing)
        out = call(commands.leaderboard, ctx())[0]
        assert "Unranked" in out and "Maxime" in out

    def test_lastgame_posts_the_kda_message_and_embed(self, seeded_roster, monkeypatch, ctx):
        match = {
            "gameType": 420,
            "duration": "27:04",
            "participants": [
                {"puuid": PUUID_SEAN, "champion": "Yasuo", "kills": 12, "deaths": 2, "assists": 7,
                 "win": True, "cs": 210, "gold": 15000},
                {"puuid": PUUID_MAXIME, "champion": "Leona", "kills": 1, "deaths": 9, "assists": 20,
                 "win": False, "cs": 40, "gold": 9000},
            ],
        }
        monkeypatch.setattr(commands.riot_client, "get_last_match_id", lambda puuid: "EUW_1")
        monkeypatch.setattr(commands.riot_client, "get_match_data", lambda match_id: match)

        sent = []

        class RecordingContext:
            message = type("M", (), {"mentions": []})()
            author = None

            async def send(self, content=None, **kwargs):
                sent.append((content, kwargs.get("embed")))

        run(commands.lastgame.callback(RecordingContext(), "sean"))
        message, embed = sent[0]
        assert "Sean a retourné" in message  # KDA 9.5 -> the spicy one
        assert embed.title == "Dernier match de Sean"

    def test_lastgame_reports_a_riot_api_failure(self, seeded_roster, monkeypatch, ctx):
        from api import RiotAPIError

        def failing(puuid):
            raise RiotAPIError("boom")

        monkeypatch.setattr(commands.riot_client, "get_last_match_id", failing)
        assert "Impossible de récupérer les données" in call(commands.lastgame, ctx(), "sean")[0]


class TestDatabaseFailure:
    def test_commands_stay_polite_when_the_database_is_gone(self, roster, fake_riot, ctx):
        roster.close()
        assert "indisponible" in call(commands.addplayer, ctx(), "Guy", DISCORD_THOMAS, PUUID_THOMAS)[0]
        assert "indisponible" in call(commands.listplayers, ctx())[0]
        assert "indisponible" in call(commands.lol, ctx(), "sean")[0]
