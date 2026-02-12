import discord
from discord import app_commands
from discord.ext import commands


class PingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Prefijo =
    @commands.command(name="ping")
    async def ping_prefix(self, ctx: commands.Context):
        await ctx.send("pong ✅")

    # Slash /ping
    @app_commands.command(name="ping", description="Responde pong para probar el bot.")
    async def ping_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("pong ✅", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PingCog(bot))
