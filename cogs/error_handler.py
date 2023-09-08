import discord
from discord.ext import commands

from env import BOT_TEST_SERVER, RGR_SERVER


class ErrorHandler(commands.Cog):
    """Handle errors."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        bot.tree.on_error = self.on_app_command_error

    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError
    ):
        await interaction.followup.send(
            f'Oops, an error with the bot occurred. '
            f'You should probably let <@187679550841290752> know.'
        )
        await interaction.followup.send(error, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot),
                      guilds=[discord.Object(id=BOT_TEST_SERVER),
                              discord.Object(id=RGR_SERVER)])
