import discord


class GiveUp(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=30)
        self.ctx = ctx

    @discord.ui.button(label="Give Up", style=discord.ButtonStyle.red)
    async def giveup(self, _, interaction: discord.Interaction):
        await interaction.response.send_message("You've given up!", ephemeral=True)
        self.stop()

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't interact with this!", ephemeral=True)
            return False
        return True


class Confirm(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=10)
        self.ctx = ctx
        self.choice = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, _, interaction: discord.Interaction):
        await interaction.response.send_message("Confirmed!", ephemeral=True)
        self.choice = True
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, _, interaction: discord.Interaction):
        await interaction.response.send_message("Cancelled.", ephemeral=True)
        self.choice = False
        self.stop()

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't interact with this!", ephemeral=True)
            return False
        return True


class Dropdown(discord.ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Choose a country",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.choice = self.values[0]
        self.view.stop()


class ChooseCountryDropdown(discord.ui.View):
    def __init__(self, ctx, options):
        super().__init__(timeout=5)

        self.add_item(Dropdown(options))
        self.ctx = ctx
        self.message = None
        self.choice = ""

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't interact with this.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.message.edit("You didn't respond in time.", view=self)
