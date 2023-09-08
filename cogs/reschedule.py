import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime
from typing import Optional
from enum import Enum

from env import BOT_TEST_SERVER, RGR_SERVER
from utils.sheets import get_worksheet
from utils.sheets import Worksheet
from utils.scheduler import (
    get_match_col_order,
    get_player_from_csv,
    get_bracket_matches,
    validate_reschedule,
    reschedule_match
)
from utils.scheduler import LobbyNotFound, NotMatchParticipant
from utils.scheduler import BracketMatch
from utils.date_handler import get_stage_dates, weekday_to_dt
from utils.date_handler import StageNotFound
from config import (
    SPREADSHEET_KEY,
    BSTAGE_WORKSHEET_NAME,
    BSTAGE_RANGE,
    BSTAGE_DATE_SHEET_COL,
    BSTAGE_TIME_SHEET_COL,
    STAGE_DATES
)


class Weekday(Enum):
    Monday = 0
    Tuesday = 1
    Wednesday = 2
    Thursday = 3
    Friday = 4
    Saturday = 5
    Sunday = 6


class RescheduleStatus(Enum):
    PENDING = '🟡 Awaiting Response'
    ACCEPTED = '🟢 Accepted'
    DECLINED = '🔴 Declined'
    CANCELLED = '⚪ Cancelled'


class ReschedStatusColour(Enum):
    PENDING = discord.Colour.from_rgb(253, 203, 88)
    ACCEPTED = discord.Colour.from_rgb(120, 177, 89)
    DECLINED = discord.Colour.from_rgb(221, 46, 68)
    CANCELLED = discord.Colour.from_rgb(230, 231, 232)


def change_status(reschedule_embed: discord.Embed,
                  new_status: RescheduleStatus,
                  new_colour: ReschedStatusColour) -> None:
    """
    Change the status and colour of <reschedule_embed> to
    <new_status> and <new_colour>, respectively.
    """
    reschedule_embed.set_field_at(
        index=2,
        name='Status',
        value=new_status.value,
        inline=False
    )
    reschedule_embed.colour = new_colour.value


def create_resched_embed(status: RescheduleStatus,
                         colour: ReschedStatusColour,
                         match: BracketMatch,
                         new_time: datetime,
                         sender_team_name: str,
                         thumbnail_url: str) -> discord.Embed:
    """Create a reschedule embed."""
    # TODO: use - for linux, # for windows
    TIME_FORMAT = '%a, %b %#d at %#H:%M UTC'

    em = discord.Embed(title=f'Match ID: {match.id}', colour=colour.value)
    em.set_author(name=f'{sender_team_name} wants to reschedule')
    em.add_field(
        name='Old Time',
        value=(
            f'{match.time.strftime(TIME_FORMAT)}\n'
            f'(<t:{int(match.time.timestamp())}:F>)'
        ),
        inline=False
    )
    em.add_field(
        name='New Time',
        value=(
            f'{new_time.strftime(TIME_FORMAT)}\n'
            f'(<t:{int(new_time.timestamp())}:F>)'
        ),
        inline=False
    )
    em.add_field(name='Status', value=status.value, inline=False)
    em.set_thumbnail(url=thumbnail_url)

    return em


class RescheduleButtons(discord.ui.View):
    def __init__(self,
                 worksheet: Worksheet,
                 match: BracketMatch,
                 new_time: datetime,
                 sender: discord.User,
                 receiver: discord.Member):
        super().__init__(timeout=259200)  # 3 days
        self.worksheet = worksheet  # TODO: make sure this doesn't mess w api
        self.match = match
        self.new_time = new_time
        self.sender = sender
        self.receiver = receiver

        self.message: discord.Message

    async def on_timeout(self):
        self.clear_items()
        await self.message.edit(view=self)

    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def accept(self,
                     interaction: discord.Interaction,
                     button: discord.ui.Button):
        if interaction.user != self.receiver:
            return

        reschedule_match(
            worksheet=self.worksheet,
            match=self.match,
            new_time=self.new_time,
            date_col=BSTAGE_DATE_SHEET_COL,
            time_col=BSTAGE_TIME_SHEET_COL
        )

        # ping sender and ref to let them know it's been rescheduled
        if self.match.referee:
            ref = interaction.guild.get_member_named(
                self.match.referee.discord_name
            )
        else:
            ref = None

        # TODO: handle case where the ref's disc name is wrong in the csv
        # clean this up later
        if ref:
            await self.message.reply(
                f'<@{self.sender.id}> <@{ref.id}> '
                f'This match has been rescheduled.'
            )
        else:
            await self.message.reply(
                f'<@{self.sender.id}> '
                f'This match has been rescheduled.'
            )

        embed = self.message.embeds[0]
        change_status(
            reschedule_embed=embed,
            new_status=RescheduleStatus.ACCEPTED,
            new_colour=ReschedStatusColour.ACCEPTED
        )

        await self.message.edit(
            embed=embed,
            view=self
        )
        await self.on_timeout()

    @discord.ui.button(label='Decline', style=discord.ButtonStyle.red)
    async def decline(self,
                      interaction: discord.Interaction,
                      button: discord.ui.Button):
        if interaction.user != self.receiver:
            return

        embed = self.message.embeds[0]
        change_status(
            reschedule_embed=embed,
            new_status=RescheduleStatus.DECLINED,
            new_colour=ReschedStatusColour.DECLINED
        )

        await self.message.edit(
            embed=embed,
            view=self
        )
        await self.on_timeout()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.gray)
    async def cancel(self,
                     interaction: discord.Interaction,
                     button: discord.ui.Button):
        if interaction.user != self.sender:
            return

        embed = self.message.embeds[0]
        change_status(
            reschedule_embed=embed,
            new_status=RescheduleStatus.CANCELLED,
            new_colour=ReschedStatusColour.CANCELLED
        )

        await self.message.edit(
            embed=embed,
            view=self
        )
        await self.on_timeout()


class Reschedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name='reschedule',
        description='Send a request to an opponent to reschedule a match.'
    )
    @app_commands.guilds(BOT_TEST_SERVER, RGR_SERVER)
    async def reschedule(self,
                         interaction: discord.Interaction,
                         match_id: str,
                         weekday: Weekday,
                         hour: app_commands.Range[int, 0, 23],
                         minute: Optional[app_commands.Range[int, 0, 59]] = 0):
        await interaction.response.defer()

        player = get_player_from_csv(discord_name=interaction.user.name)
        if player is None:
            await interaction.followup.send(
                f"You don't appear to be a team captain (or solo player) "
                f"registered in this tournament. Please contact a tournament "
                f"admin if you believe this is a mistake."
            )
            return

        stage_dates = get_stage_dates(STAGE_DATES)
        try:
            new_time = weekday_to_dt(
                stage_dates=stage_dates,
                reference_date=datetime(2023, 8, 19),  # TODO: change to datetime.now() for prod
                weekday=weekday.value,
                hour=hour,
                minute=minute
            )
        except StageNotFound:
            await interaction.followup.send(
                'Reschedules are currently unavailable.'
            )
            return

        wks = get_worksheet(
            spreadsheet_key=SPREADSHEET_KEY,
            worksheet_name=BSTAGE_WORKSHEET_NAME
        )
        matches = get_bracket_matches(
            worksheet=wks,
            match_range=BSTAGE_RANGE,
            col_idxs=get_match_col_order()
        )

        try:
            # TODO: this raises AttributeError if the csv is missing a player
            match = validate_reschedule(
                matches=matches,
                match_id=match_id,
                player=player
            )
        except LobbyNotFound:
            await interaction.followup.send(
                f'Match **{match_id}** was not found!'
            )
            return
        except NotMatchParticipant:
            await interaction.followup.send(
                f"You don't appear to be a participant of this match. "
                f"Please contact a tournament admin if you believe "
                f"this is a mistake."
            )
            return

        # get the opponent's discord username
        opp_discord_name = (
            match.player1.discord_name if match.player1 != player
            else match.player2.discord_name
        )
        # get the discord.Member object of the opponent
        opponent = interaction.guild.get_member_named(opp_discord_name)

        view = RescheduleButtons(
            worksheet=wks,
            match=match,
            new_time=new_time,
            sender=interaction.user,
            receiver=opponent
        )

        webhook_msg: discord.WebhookMessage = await interaction.followup.send(
            content=f'<@{opponent.id}>',
            embed=create_resched_embed(
                status=RescheduleStatus.PENDING,
                colour=ReschedStatusColour.PENDING,
                match=match,
                new_time=new_time,
                sender_team_name=player.team_name,
                thumbnail_url=interaction.guild.icon.url
            ),
            view=view
        )

        view.message = await webhook_msg.fetch()


async def setup(bot: commands.Bot):
    await bot.add_cog(Reschedule(bot),
                      guilds=[discord.Object(id=BOT_TEST_SERVER),
                              discord.Object(id=RGR_SERVER)])
