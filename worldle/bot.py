import asyncio
import csv
import difflib
import discord
from discord.ext import commands
from io import BytesIO
import requests
from bs4 import BeautifulSoup
from PIL import Image
import pandas as pd
from geopy import distance
from interactions import ChooseCountryDropdown, Confirm, GiveUp

client = commands.Bot("w ")
client.in_game = []
client.df = pd.read_csv("country_data.csv")
client.df.rename(columns={"CountryName": "country", "CapitalName": "capital", "CapitalLatitude": "lat",
                          "CapitalLongitude": "lon", "CountryCode": "code", "ContinentName": "continent"},
                 inplace=True)
client.df.sample(3)


def cancel_task(done, pending):
    for future in done:
        future.cancel()
    for future in pending:
        future.cancel()


@client.command()
async def play(ctx):
    r = requests.get("https://gadm.org/maps/MOZ.html")
    soup = BeautifulSoup(r.content, "lxml")

    suffix = soup.find("ul", {"id": "thumb_img"}).findAll("img")[-1]["src"][2:]

    response = requests.get("https://gadm.org" + suffix)
    img = Image.open(BytesIO(response.content))

    img = img.convert("RGBA")

    pixdata = img.load()

    width, height = img.size
    for y in range(height):
        for x in range(width):
            if pixdata[x, y] == (255, 255, 255, 255):
                pixdata[x, y] = (255, 255, 255, 0)
            else:
                pixdata[x, y] = (0, 0, 0, 255)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    file = discord.File(buffer, filename="picture.png")

    embed = discord.Embed(title="Guess the Country", color=discord.Color.blue())
    embed.set_image(url="attachment://picture.png")

    view = GiveUp(ctx)
    await ctx.send(embed=embed, file=file, view=view)

    country = "Mozambique"

    def check(m):
        return ctx.author == m.author and ctx.channel == m.channel

    guesses = 0
    while guesses < 6:
        done, pending = await asyncio.wait([
            client.loop.create_task(client.wait_for('message', check=check)),
            client.loop.create_task(view.wait())
        ], return_when=asyncio.FIRST_COMPLETED, timeout=30)

        try:
            msg = done.pop().result()
        except KeyError:
            cancel_task(done, pending)
            return await ctx.send("You ran out of time! So, you lost.")
        except BaseException:
            return
        for future in done:
            future.exception()

        if type(msg) == bool:
            cancel_task(done, pending)
            return

        with open('country_data.csv') as csvfile:
            rows = csv.reader(csvfile)
            country_names = list(zip(*rows))[0][1:]

        country_names2 = [x.lower() for x in country_names]

        if msg.content.lower() not in country_names2:
            best_matches = difflib.get_close_matches(msg.content.lower(), country_names2, 3, 0.75)
            for country_name in country_names2:
                if any(x in country_name.split() for x in msg.content.lower().split()) or \
                        any(x in msg.content.lower().split() for x in country_name.split()):
                    best_matches.append(country_name)

            if len(best_matches) == 0:
                await ctx.send("Not a valid country. Choose a different country.")
                continue
            elif len(best_matches) == 1:
                c_view = Confirm(ctx)
                msg = await ctx.reply(embed=discord.Embed(description=f"Did you mean **{best_matches[0].title()}**?",
                                                          color=discord.Color.blue()),
                                      view=c_view)
                c_view.message = msg
                timed_out = await c_view.wait()

            else:
                c_view = ChooseCountryDropdown(ctx, [discord.SelectOption(label=x.title()) for x in best_matches])
                msg = await ctx.reply("Did you mean...", view=c_view)
                c_view.message = msg
                timed_out = await c_view.wait()

            if timed_out:
                await ctx.send("You ran out of time. Choose a different country.")
                continue
            else:
                if len(best_matches) > 1:
                    guess = country_names[country_names2.index(c_view.choice.lower())]
                else:
                    if c_view.choice:
                        guess = country_names[country_names2.index(best_matches[0])]
                    else:
                        await ctx.send("Cancelled. Choose a different country.")
                        continue

        else:
            guess = country_names[country_names2.index(msg.content.lower())]

        dis = client.df[client.df["country"].isin([country, guess])].reset_index()

        if len(dis) == 1:
            await ctx.send("Not a valid country!")
            continue

        d = distance.distance((dis.loc[0, "lat"], dis.loc[0, "lon"]), (dis.loc[1, "lat"], dis.loc[1, "lon"]))

        if dis.loc[0, "country"] == guess:
            cindex, gindex = 1, 0
        else:
            cindex, gindex = 0, 1

        lat1, lon1 = dis.loc[cindex, "lat"], dis.loc[cindex, "lon"]
        lat2, lon2 = dis.loc[gindex, "lat"], dis.loc[gindex, "lon"]

        up = lat2 > lat1
        west = lon1 > lon2

        if round(abs(lat1 - lat2)) / 5 > round(abs(lon1 - lon2)):
            west = None
        if round(abs(lon1 - lon2)) / 5 > round(abs(lat1 - lat2)):
            up = None

        direction_dict = {(True, None): "⬆️",
                          (False, None): "⬇️",
                          (None, False): "➡️",
                          (None, True): "⬅️",
                          (True, True): "↖️",
                          (True, False): "↗️",
                          (False, True): "↙️",
                          (False, False): "↘️"}

        embed.add_field(name=f"{guess}", inline=False,
                        value=f"**Distance:** `{round(d.km)}km` {direction_dict[(not up if up is not None else None, not west if west is not None else None)]}")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(buffer, filename="picture.png")
        embed.set_image(url="attachment://picture.png")

        guesses += 1
        await ctx.send(embed=embed, file=file, view=view)


client.run("TOKEN")
