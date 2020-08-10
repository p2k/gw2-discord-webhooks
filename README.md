
Discord Webhooks for Guild Wars 2
=================================

This is a collection of useful scripts for your GW2 WvW Community server.

Installing
----------

```
python setup.py install
```

Commands
--------

* `post_gw2_matches`
* `post_gw2_population`

Configuration
-------------

You can either specify options on the command line, set environment variables or
create a configuration file. Use `--help` on the respective command to get a
list of options.

Any long option can be placed in a config file which roughly resembles an ini
format. Use the option name without leading dashes (but keep dashes in between).

Example Config
--------------

```
world=2008
webhook-url=https://discordapp.com/api/webhooks/.../...
webhook-thumbnail=https://cdn.discordapp.com/attachments/.../.../LOGO.png
timezones=Europe/Berlin,Europe/London
matches-username=Matches
matches-log=matches.log
population-username=Population
population-log=population.log
change-only=true
```

Notes
-----

* Works for any server in any region (untested, though)
* Timezones respect daylight saving time
* All commands have a "print only" mode for testing

License
-------

MIT License - see LICENSE
