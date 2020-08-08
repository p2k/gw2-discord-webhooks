#
#  matches.py
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

from datetime import datetime
import os, csv
import dateutil.tz

from .utils import (
    first,
    get_json,
    get_world_names,
    get_next_reset,
    format_duration,
    formatted_text_to_markdown,
    print_formatted_text,
    execute_discord_webhook,
)

# Constants
COLORS = {"red": 0xD32F2F, "green": 0x28B463, "blue": 0x039BE5}
LOG_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def match_ranking(match):
    victory_points = match["victory_points"]
    # Return colors (keys of the dictionary) sorted by their respective points
    return sorted(victory_points.keys(), key=lambda color: victory_points[color], reverse=True)


def match_with_id(all_matches, match_id):
    # Return the first match with the given id
    return first(match for match in all_matches if match["id"] == match_id)


def linked_worlds(all_matches, main_world):
    # Get the list of all worlds of the color for which the given world is the main world
    worlds = first(match["all_worlds"][color] for match in all_matches for (color, world) in match["worlds"].items() if world == main_world)
    # Copy the list and remove the main world (unless it is the only entry)
    if len(worlds) == 1:
        return []
    worlds = list(worlds)
    worlds.remove(main_world)
    return worlds


def predict_matchup(world):
    """
    Returns a matchup prediction for the given world, based on current victory points. Handles standalone, main and linked servers.
    """

    world_overview = get_json("https://api.guildwars2.com/v2/wvw/matches/overview", world=world)
    all_matches = get_json("https://api.guildwars2.com/v2/wvw/matches", ids="all")

    curr_match_id = world_overview["id"]
    region, curr_tier = list(int(i) for i in curr_match_id.split("-"))
    curr_match = match_with_id(all_matches, curr_match_id)
    assert curr_match is not None

    # Get number of tiers for region
    region_tiers_count = sum(1 for match in all_matches if match["id"].startswith(f"{region}-"))

    # Get current world color
    curr_color = first(color for color, wds in world_overview["all_worlds"].items() if world in wds)
    assert curr_color is not None

    # Get main world
    curr_main = world_overview["worlds"][curr_color]

    # Get current position and determine color next match
    curr_ranking = match_ranking(curr_match)
    next_red_main = None
    next_blue_main = None
    next_green_main = None
    if curr_ranking[0] == curr_color:
        # We win
        if curr_tier == 1:
            # It's lonely at the top!
            next_tier = curr_tier
            next_green_main = curr_main
            next_color = "green"
        else:
            # Up we climb
            next_tier = curr_tier - 1
            next_red_main = curr_main
            next_color = "red"
    elif curr_ranking[1] == curr_color:
        # We stay; get ourselves comfortable
        next_tier = curr_tier
        next_blue_main = curr_main
        next_color = "blue"
    else:
        # We lose
        if curr_tier == region_tiers_count:
            # Rock bottom!
            next_tier = curr_tier
            next_red_main = curr_main
            next_color = "red"
        else:
            # Down we fall
            next_tier = curr_tier + 1
            next_green_main = curr_main
            next_color = "green"

    # Get opponents for next match
    if next_green_main is None:
        if next_tier == 1:
            top_tier_match = match_with_id(all_matches, f"{region}-1")
            top_tier_winner = match_ranking(top_tier_match)[0]
            next_green_main = top_tier_match["worlds"][top_tier_winner]
        else:
            tier_above_match = match_with_id(all_matches, f"{region}-{next_tier-1}")
            tier_above_loser = match_ranking(tier_above_match)[2]
            next_green_main = tier_above_match["worlds"][tier_above_loser]

    if next_blue_main is None:
        next_tier_match = match_with_id(all_matches, f"{region}-{next_tier}")
        next_tier_second = match_ranking(next_tier_match)[1]
        next_blue_main = next_tier_match["worlds"][next_tier_second]

    if next_red_main is None:
        if next_tier == region_tiers_count:
            bottom_tier_match = match_with_id(all_matches, f"{region}-{region_tiers_count}")
            bottom_tier_loser = match_ranking(bottom_tier_match)[2]
            next_red_main = bottom_tier_match["worlds"][bottom_tier_loser]
        else:
            tier_below_match = match_with_id(all_matches, f"{region}-{next_tier+1}")
            tier_below_winner = match_ranking(tier_below_match)[0]
            next_red_main = tier_below_match["worlds"][tier_above_loser]

    # Get linked worlds
    next_green_linked = linked_worlds(all_matches, next_green_main)
    next_blue_linked = linked_worlds(all_matches, next_blue_main)
    next_red_linked = linked_worlds(all_matches, next_red_main)

    # Get names
    world_names = get_world_names([next_green_main, next_blue_main, next_red_main], next_green_linked, next_blue_linked, next_red_linked)

    # Get next reset time
    reset = get_next_reset(region == 2)

    return {
        "world": world,
        "reset": reset,
        "tier": next_tier,
        "color": next_color,
        "green_main": next_green_main,
        "green_linked": next_green_linked,
        "blue_main": next_blue_main,
        "blue_linked": next_blue_linked,
        "red_main": next_red_main,
        "red_linked": next_red_linked,
        "world_names": world_names,
    }


def format_world_name(world, main_world, linked_worlds, world_names):
    """
    Returns a formatted text fragment representing the given world plus its linked worlds.

    If any of the worlds is the main world, it will be underlined.
    """

    ft = [
        ("underline" if main_world == world else "", world_names[main_world]),
    ]

    first_lw = True
    for lw in linked_worlds:
        if first_lw:
            ft.append(("", " (+ "))
            first_lw = False
        else:
            ft.append(("", ", "))
        ft.append(("underline" if lw == world else "", world_names[lw]))

    if not first_lw:
        ft.append(("", ")"))

    return ft


def format_title(r):
    return f"{r.strftime('%Y-%m-%d')} Reset Matchup Prediction:"


def format_prediction(p, tzs, ampm, include_title=False):
    """
    Returns a formatted text fragment representing the given matchup prediction.

    Note: Emoji are not rendered yet.
    """

    world = p["world"]
    world_names = p["world_names"]
    n = datetime.now(dateutil.tz.tzlocal())
    r = p["reset"]

    ft = []
    if include_title:
        ft.append(("bold", format_title(r)))
        ft.append(("", "\n\n"))

    if len(tzs) > 0:
        ft.append(("", "at "))
        first_tz = True
        for tz in tzs:
            if first_tz:
                first_tz = False
            else:
                ft.append(("", " / "))
            tz_r = r.astimezone(dateutil.tz.gettz(tz))
            ft.append(("bold", tz_r.strftime("%I:%M%p" if ampm else "%H:%M").lower()))
            ft.append(("", tz_r.strftime(" %Z")))
        ft.append(("", "\nor "))
    ft.extend(format_duration(r - n))
    ft.append(("", " from this post.\n\n"))
    ft.append(("bold", f"Tier {p['tier']}"))
    ft.append(("", "\n:green_square: "))
    ft.extend(format_world_name(world, p["green_main"], p["green_linked"], world_names))
    ft.append(("", "\n:blue_square: "))
    ft.extend(format_world_name(world, p["blue_main"], p["blue_linked"], world_names))
    ft.append(("", "\n:red_square: "))
    ft.extend(format_world_name(world, p["red_main"], p["red_linked"], world_names))

    if p.get("changed", False):
        ft.extend([("", "\n\n"), ("italic", "The opponents have changed since last prediction!")])

    return ft


def main():
    """
    Script entrypoint.
    """

    import configargparse

    parser = configargparse.ArgumentParser(default_config_files=["~/.gw2_discord_webhooks", "/etc/"])
    parser.add_argument("-c", "--config", help="config file path", is_config_file=True, env_var="GW2_CONFIG_FILE")
    parser.add_argument("-w", "--world", help="home world id", required=True, env_var="GW2_HOME_WORLD_ID", type=int)
    parser.add_argument("-u", "--webhook-url", help="webhook url", env_var="GW2_WEBHOOK_URL")
    parser.add_argument("-b", "--webhook-thumbnail", help="webhook thumbnail url", env_var="GW2_WEBHOOK_THUMBNAIL")
    parser.add_argument(
        "-x",
        "--change-only",
        help="only execute the webhook on a change (requires -l)",
        action="store_true",
        default=False,
        env_var="GW2_CHANGE_ONLY",
    )
    parser.add_argument("-n", "--matches-username", help="webhook username for this script", env_var="GW2_MATCHES_USERNAME")
    parser.add_argument("-l", "--matches-log", help="log results to a file", env_var="GW2_MATCHES_LOG")
    parser.add_argument("-t", "--timezones", help="comma seperated list of timezones to render", env_var="GW2_TIMEZONES")
    parser.add_argument("-a", "--ampm", help="use 12h clock instead of 24h clock", action="store_true", default=False, env_var="GW2_AMPM")
    parser.add_argument("-p", help="print to console, do not send", action="store_true", default=False)
    parser.add_argument("-m", help="when printing to console, output as markdown", action="store_true", default=False)

    args = parser.parse_args()

    tzs = [] if args.timezones is None else args.timezones.split(",")
    prediction = predict_matchup(args.world)

    if args.log:
        # Parse logfile
        log_exists = os.path.exists(args.log)
        formatted_reset = prediction["reset"].strftime(LOG_TIME_FORMAT)
        lp_matchup = None
        with open(args.log, "r+" if log_exists else "w", newline="") as f:
            if log_exists:
                for row in csv.reader(f, delimiter=";", quotechar='"'):
                    if row[1] == formatted_reset:
                        lp_matchup = [int(row[2]), int(row[3]), int(row[4])]
            w = csv.writer(f, delimiter=";", quotechar='"')
            w.writerow(
                [
                    datetime.utcnow().strftime(LOG_TIME_FORMAT),
                    formatted_reset,
                    prediction["green_main"],
                    prediction["blue_main"],
                    prediction["red_main"],
                ]
            )
        # Mark change or bail out
        if lp_matchup is not None:
            if (
                lp_matchup[0] != prediction["green_main"]
                and lp_matchup[1] != prediction["blue_main"]
                and lp_matchup[2] != prediction["red_main"]
            ):
                prediction["changed"] = True
            elif args.change_only:
                print("Matchup did not change.")
                return 0

    if args.p:
        ft = format_prediction(prediction, tzs, args.ampm, True)
        if args.m:
            print(formatted_text_to_markdown(ft))
        else:
            print_formatted_text(ft)
        return 0
    else:
        if args.webhook_url is None:
            print("No webhook url configured!", file=sys.stderr)
            return 1

        ft = format_prediction(prediction, tzs, args.ampm)
        execute_discord_webhook(
            args.webhook_url,
            args.webhook_thumbnail,
            args.matches_username,
            format_title(prediction["reset"]),
            COLORS[prediction["color"]],
            ft,
        )
        return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
