# Aria
Auto update repo for Aria selfbot!

Install the Python runtime dependencies from this directory with:

```bash
python -m pip install -r requirements.txt
```

Real slash command bot setup: see `REAL_SLASH_SETUP.md`.

## MongoDB backend

Aria can store hot runtime state in MongoDB instead of repeatedly writing JSON files.

Enable it in `config.json`:

```json
{
	"mongo_enabled": true,
	"mongo_uri": "mongodb://127.0.0.1:27017",
	"mongo_database": "aria",
	"mongo_collection": "app_state",
	"mongo_timeout_ms": 1500
}
```

Install the driver in the active Python environment:

```bash
pip install pymongo
```

Current Mongo-backed runtime datasets:

- `history_data`
- `account_stats`
- `analytics`
- `dashboard_users`
- `access_requests`

If MongoDB is disabled or unavailable, Aria falls back to the existing JSON files automatically.

## Dashboard session key

The web dashboard creates a private 256-bit session-signing key in
`Aria/.aria_webpanel_secret` on first start and reuses it across restarts. Keep
this runtime file private and out of backups shared with others. To provide a
managed key instead, set `ARIA_WEBPANEL_SECRET` in the process environment.

## RPC presets and message logger

Aria supports named activity presets and timed rotations through the existing
RPC engine:

```text
<prefix>rpc preset save desk
<prefix>rpc preset list
<prefix>rpc preset load desk
<prefix>rpc rotation set 45 desk,away
<prefix>rpc rotation start
<prefix>rpc rotation stop
```

Message logging is disabled by default. Enable it with `<prefix>logger on`, add
terms with `<prefix>logger add release notes`, and set an optional scope with
`<prefix>logger scope dms`, `guilds`, `guild <id>`, or `channel <id>`. The
dashboard can also configure mention, edit, delete, and own-message filtering.
The live feed is bounded to 400 events and held in memory; only its settings
are written to `Aria/message_logger.json`.

These RPC profile and logger workflows are inspired by
[Beyond](https://github.com/kzfq/beyond), which is MIT-licensed. Aria keeps its
own Discord API and gateway implementation.
