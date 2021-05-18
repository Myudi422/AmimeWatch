# MIT License
#
# Copyright (c) 2021 Andriel Rodrigues for Amano Team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import asyncio
import datetime

import anilist

from amime.config import CHATS
from amime.database import Episodes


async def load(bot):
    now = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)

    sent = await bot.send_message(CHATS["staff"], "Checking the day's releases...")

    animes = {}

    def check_repeated(episode):
        nonlocal animes

        if episode.anime in animes.keys():
            return None
        else:
            animes[episode.anime] = []
            return episode

    async with anilist.AsyncClient() as client:
        episodes = await Episodes.all()
        episodes = [
            *filter(lambda episode: check_repeated(episode) is not None, episodes)
        ]

        for episode in episodes:
            bot.day_releases = animes

            anime = await client.get(episode.anime, "anime")
            while anime is None:
                anime = await client.get(episode.anime, "anime")
                await asyncio.sleep(3)

            if anime.status.lower() == "releasing":
                if hasattr(anime, "next_airing"):
                    number = anime.next_airing.episode
                    date = datetime.datetime.fromtimestamp(
                        anime.next_airing.at
                    ).replace(tzinfo=datetime.timezone.utc)

                    if date.day == now.day:
                        animes[episode.anime] = [
                            anime.title.romaji,
                            number,
                            date,
                            False,
                        ]
                        continue

            del animes[episode.anime]

    await sent.edit_text(
        f"<code>{len(animes)}</code> animes have episodes to be released today, check them out using /today"
    )


async def reload(bot):
    now = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)

    animes = bot.day_releases

    if animes is not None:
        for key, value in animes.items():
            if value[3]:
                continue

            if (
                now.hour >= value[2].hour
                and now.minute >= value[2].minute
                and now.second >= value[2].second
            ):
                await bot.send_message(
                    CHATS["staff"],
                    f"Episode <code>{value[1]}</code> of <b>{value[0]}</b> (<code>{key}</code>) has just been released. <code>{now.strftime('%H:%M:%S')}</code>",
                )

                animes[key][0] = f"<s>{value[0]}</s>"
                animes[key][3] = True

        bot.day_releases = animes
