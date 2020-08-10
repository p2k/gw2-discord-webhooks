#
#  population.py
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

from .utils import (
    get_json,
    get_worlds,
    get_next_relink,
    print_formatted_text,
    execute_discord_webhook,
)

# Constants
POPULATION_DESCR = {
    "Full": (5, ":red_square:"),
    "VeryHigh": (4, ":orange_square:"),
    "High": (3, ":yellow_square:"),
    "Medium": (2, ":green_square:"),
    "Low": (1, ":blue_square:"),
    "Undefined": (0, ""),
}
LOG_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def fetch_population(world):
    """
    Returns the current world population and server links in the region of the given world plus the next relink date.
    """

    world_overview = get_json("https://api.guildwars2.com/v2/wvw/matches/overview", world=world)
    all_matches = get_json("https://api.guildwars2.com/v2/wvw/matches", ids="all")

    # Get involved worlds with links in current region
    region, tier = list(int(i) for i in world_overview["id"].split("-"))
    world_links = {}
    world_ids = []
    for match in all_matches:
        if match["id"].startswith(f"{region}-"):
            for color in ["red", "blue", "green"]:
                main = match["worlds"][color]
                world_ids.append(main)
                links = match["all_worlds"][color]
                links.remove(main)
                world_ids.extend(links)
                world_links[main] = links

    # Get world names and population
    world_names = {}
    population = {}
    for w in get_worlds(world_ids):
        world_names[w["id"]] = w["name"]
        population[w["id"]] = w["population"]

    return {
        "world": world,
        "population": population,
        "world_links": world_links,
        "world_names": world_names,
        "relink": get_next_relink(),
    }


def format_world_population(home_world, world, population, lp_population, world_names):
    """
    Formats the world name with population information.

    If the given world is the home world, it will be underlined.
    """

    p_rank, p_emoji = POPULATION_DESCR[population[world]]
    l_rank, l_emoji = POPULATION_DESCR[lp_population.get(world, "Undefined")]

    ft = [("", p_emoji)]
    if l_rank != 0:
        if p_rank > l_rank:
            ft.append(("", " :arrow_upper_right:"))
        elif p_rank < l_rank:
            ft.append(("", " :arrow_lower_right:"))
        else:
            ft.append(("", " :left_right_arrow:"))
    ft.append(("", " "))
    ft.append(("underline" if world == home_world else "", world_names[world]))
    return ft


def format_population(p, lp_population):
    """
    Returns a formatted text fragment representing the given population development.

    Note: Emoji are not rendered yet.
    """

    home_world = p["world"]
    population = p["population"]
    world_links = p["world_links"]
    world_names = p["world_names"]

    main_worlds = []
    linked_worlds1 = []
    linked_worlds2 = []
    first = True
    has_linked_worlds2 = False
    for main_world in sorted(world_links.keys(), key=lambda world: world_names[world]):
        linked_worlds = world_links[main_world]
        if first:
            first = False
        else:
            main_worlds.append(("", "\n"))
            linked_worlds1.append(("", "\n"))
            linked_worlds2.append(("", "\n"))

        main_worlds.extend(format_world_population(home_world, main_world, population, lp_population, world_names))

        if len(linked_worlds) == 0:
            linked_worlds1.append(("", ":negative_squared_cross_mark:"))
            linked_worlds2.append(("", ":negative_squared_cross_mark:"))
        elif len(linked_worlds) == 1:
            linked_worlds1.extend(format_world_population(home_world, linked_worlds[0], population, lp_population, world_names))
            linked_worlds2.append(("", ":negative_squared_cross_mark:"))
        else:
            linked_worlds1.extend(format_world_population(home_world, linked_worlds[0], population, lp_population, world_names))
            linked_worlds2.extend(format_world_population(home_world, linked_worlds[1], population, lp_population, world_names))
            has_linked_worlds2 = True

    fields = [("Main Worlds", main_worlds)]
    if has_linked_worlds2:
        fields.append(("Linked Worlds (1)", linked_worlds1))
        fields.append(("Linked Worlds (2)", linked_worlds2))
    else:
        fields.append(("Linked Worlds", linked_worlds1))

    return ([("", f"Next relink: {p['relink'].strftime('%Y-%m-%d')}")], fields)


def main():
    """
    Script entrypoint.
    """

    import configargparse

    parser = configargparse.ArgumentParser(default_config_files=["~/.gw2_discord_webhooks", "/etc/"])
    parser.add_argument("-c", "--config", help="config file path", is_config_file=True, env_var="GW2_CONFIG_FILE")
    parser.add_argument("-w", "--world", help="home world id", required=True, env_var="GW2_HOME_WORLD_ID", type=int)
    parser.add_argument("-u", "--webhook-url", help="webhook url", env_var="GW2_WEBHOOK_URL")
    parser.add_argument(
        "-x",
        "--change-only",
        help="only execute the webhook on a change (requires -l)",
        action="store_true",
        default=False,
        env_var="GW2_CHANGE_ONLY",
    )
    parser.add_argument("-n", "--population-username", help="webhook username for this script", env_var="GW2_POPULATION_USERNAME")
    parser.add_argument("-l", "--population-log", help="log results to a file", env_var="GW2_POPULATION_LOG")
    parser.add_argument("-p", help="print to console, do not send", action="store_true", default=False)
    parser.add_argument("-m", help="when printing to console, output as markdown", action="store_true", default=False)

    # Options from other scripts
    parser.add_argument("--timezones", help=configargparse.SUPPRESS)
    parser.add_argument("--ampm", help=configargparse.SUPPRESS)
    parser.add_argument("--matches-username", help=configargparse.SUPPRESS)
    parser.add_argument("--matches-log", help=configargparse.SUPPRESS)
    parser.add_argument("--webhook-thumbnail", help=configargparse.SUPPRESS)

    args = parser.parse_args()

    population = fetch_population(args.world)

    population_by_name = list((world, population["world_names"][world], pop) for world, pop in population["population"].items())
    population_by_name.sort(key=lambda item: item[1])

    sorted_ids, sorted_names, sorted_pops = map(list, zip(*population_by_name))

    lp_population = None
    if args.population_log:
        # Parse logfile
        log_exists = os.path.exists(args.population_log)
        changed = False
        with open(args.population_log, "r+" if log_exists else "w", newline="") as f:
            if log_exists:
                for row in csv.reader(f, delimiter=";", quotechar='"'):
                    lp_population = row[1:]
            w = csv.writer(f, delimiter=";", quotechar='"')
            if lp_population is None:
                w.writerow(["Timestamp"] + sorted_names)
            if lp_population != sorted_pops:
                changed = True
                w.writerow([datetime.utcnow().strftime(LOG_TIME_FORMAT)] + sorted_pops)
        # Check for change
        if args.change_only:
            if lp_population is None:
                print("Script run for the first time.")
                return 0
            if not changed:
                print("Population did not change.")
                return 0

    description, fields = format_population(population, dict(zip(sorted_ids, lp_population)) if lp_population is not None else {})

    if args.p:
        print_formatted_text("Population Update", description, fields, args.m)
    else:
        if args.webhook_url is None:
            print("No webhook url configured!", file=sys.stderr)
            return 1

        execute_discord_webhook(args.webhook_url, None, args.population_username, None, "Population Update", description, fields)


if __name__ == "__main__":
    import sys

    sys.exit(main())
