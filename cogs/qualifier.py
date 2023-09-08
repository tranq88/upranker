import discord
from discord.ext import commands
from discord import app_commands

from env import BOT_TEST_SERVER, RGR_SERVER
from utils.sheets import get_worksheet
from utils.scheduler import (
    get_qual_col_order,
    get_player_from_csv,
    get_qual_lobbies,
    schedule_qual
)
from utils.scheduler import (
    LobbyNotFound,
    FullLobbyError,
    SameLobbyError
)
from config import (
    SPREADSHEET_KEY,
    QUAL_WORKSHEET_NAME,
    QUAL_RANGE,
    QUAL_SLOTS_COL_START,
    QUAL_SLOTS_COL_END
)


@app_commands.guilds(BOT_TEST_SERVER, RGR_SERVER)
class Qualifier(commands.GroupCog, group_name='qualifier'):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name='set',
        description='Schedule or reschedule a qualifier lobby.'
    )
    async def set_(self,
                   interaction: discord.Interaction,
                   match_id: str):
        await interaction.response.defer()

        player = get_player_from_csv(discord_name=interaction.user.name)
        if player is None:
            await interaction.followup.send(
                f"You don't appear to be a team captain (or solo player) "
                f"registered in this tournament. Please contact a tournament "
                f"admin if you believe this is a mistake."
            )
            return

        wks = get_worksheet(
            spreadsheet_key=SPREADSHEET_KEY,
            worksheet_name=QUAL_WORKSHEET_NAME
        )
        qual_lobbies = get_qual_lobbies(
            worksheet=wks,
            qual_range=QUAL_RANGE,
            col_idxs=get_qual_col_order()
        )
        match_id = match_id.upper()

        try:
            schedule_qual(
                worksheet=wks,
                qual_lobbies=qual_lobbies,
                match_id=match_id,
                player=player,
                slots_start=QUAL_SLOTS_COL_START,
                slots_end=QUAL_SLOTS_COL_END
            )
        except LobbyNotFound:
            await interaction.followup.send(
                f'Lobby **{match_id}** was not found!'
            )
            return
        except FullLobbyError:
            await interaction.followup.send(
                f'Lobby **{match_id}** is full!'
            )
            return
        except SameLobbyError:
            await interaction.followup.send(
                f'You are already scheduled in lobby **{match_id}**!'
            )
            return

        await interaction.followup.send(
            f"**{player.team_name}**, you have successfully signed up for "
            f"lobby **{match_id}**!"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Qualifier(bot),
                      guilds=[discord.Object(id=BOT_TEST_SERVER),
                              discord.Object(id=RGR_SERVER)])
