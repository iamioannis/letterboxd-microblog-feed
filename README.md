# Letterboxd → Micro.blog feed

This repository publishes every item from [Ioannis's Letterboxd RSS feed](https://letterboxd.com/iamioannis/rss/) in the format used on [iamioannis.com](https://iamioannis.com/):

> 🍿 Film, year - ★★★  
> Review text, when present  
> 🔗 Letterboxd link

The live feed is [feed.xml](https://iamioannis.github.io/letterboxd-microblog-feed/feed.xml). Micro.blog imports it into `iamioannis.micro.blog`, which serves `iamioannis.com`.

GitHub Actions refreshes the feed every 15 minutes. The converter keeps each Letterboxd item's stable GUID and retains entries from the previously published feed, so an entry is not lost when it drops out of Letterboxd's short RSS feed. `cutoff.txt` excludes entries already published before the switch from EchoFeed. The old EchoFeed echo was made inactive on 27 October 2026.

To change the post format, edit `make_post()` in `feed.py`, then run the **Publish Letterboxd feed** workflow or wait for its next scheduled run. The feed will stay empty until a new Letterboxd item appears after the cutoff. The first new imported post should be checked on iamioannis.com to confirm Micro.blog renders it as intended.
