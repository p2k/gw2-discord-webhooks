#
#  utils.py
#  gw2-discord-webhooks
#
#  Copyright (c) 2020 Patrick "p2k" Schneider
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
#

import requests
import dateutil.tz
import datetime, itertools, io

EU_RESET_TIME = datetime.time(18, 0, 0)  # UTC
EU_RESET_DAY = 4
NA_RESET_TIME = datetime.time(2, 0, 0)  # UTC
NA_RESET_DAY = 5


def first(iterable):
    return next(iter(iterable), None)


def get_json(url, **params):
    r = requests.get(url, params=params)
    return r.json()


def get_world_names(*world_ids):
    worlds = get_json("https://api.guildwars2.com/v2/worlds", ids=",".join(map(str, itertools.chain.from_iterable(world_ids))))
    return dict((world["id"], world["name"]) for world in worlds)


def get_next_reset(eu=True):
    """
    Returns the next exact reset time from now.
    """
    n = datetime.datetime.utcnow()
    if n.microsecond != 0:
        # Advance to next full second
        n += datetime.timedelta(microseconds=1000000 - n.microsecond)
    d = n.date()
    reset_day = EU_RESET_DAY if eu else NA_RESET_DAY
    reset_time = EU_RESET_TIME if eu else NA_RESET_TIME
    if d.weekday() < reset_day:
        d += datetime.timedelta(days=reset_day - n.weekday())
    elif d.weekday() > reset_day:
        d += datetime.timedelta(days=7 - d.weekday() + reset_day)
    elif n.time() > reset_time:
        d += datetime.timedelta(days=7)
    return datetime.datetime.combine(d, reset_time, dateutil.tz.UTC)


def format_duration(d):
    """
    Formats the given timedelta, printing numbers in bold and adding units.

    Shows days only if > 24h 59m left and hours only if > 59m left
    """
    # Round up to full minute
    if d.microseconds != 0:
        d += datetime.timedelta(microseconds=1000000 - d.microseconds)
    if d.seconds % 60 != 0:
        d += datetime.timedelta(seconds=60 - d.seconds % 60)

    ft = []
    h = d.seconds // 3600
    if d.days == 1 and h == 0:
        h = 24
    elif d.days > 0:
        ft.append(("bold", str(d.days)))
        ft.append(("", "d "))
    if d.days > 0 or h > 0:
        ft.append(("bold", str(h)))
        ft.append(("", "h "))
    ft.append(("bold", str(d.seconds // 60 % 60)))
    ft.append(("", "m"))
    return ft


def formatted_text_to_markdown(ft):
    """
    Simple method to convert formatted text to markdown. Does not escape special characters.
    """
    s = io.StringIO()
    for f, t in ft:
        if f == "":
            s.write(t)
        elif f == "underline":
            s.write(f"__{t}__")
        elif f == "bold":
            s.write(f"**{t}**")
        elif f == "italic":
            s.write(f"*{t}*")
        else:
            raise RuntimeError(f"unknown formatting: {f}")
    return s.getvalue()


def print_formatted_text(ft):
    """
    Renders emoji to unicode and prints the formatted text to console.
    """
    from emoji import emojize
    from prompt_toolkit import print_formatted_text
    from prompt_toolkit.formatted_text import FormattedText

    print_formatted_text(FormattedText((f, emojize(t)) for f, t in ft))


def execute_discord_webhook(url, thumbnail, username, title, color, ft):
    """
    Renders formatted text to markdown and executes the discord webhook.
    """
    from discord_webhook import DiscordWebhook, DiscordEmbed

    webhook = DiscordWebhook(url, username=username)

    embed = DiscordEmbed(title=title, description=formatted_text_to_markdown(ft), color=color)
    if thumbnail is not None:
        embed.set_thumbnail(url=thumbnail)
    embed.set_timestamp()

    webhook.add_embed(embed)
    return webhook.execute()
