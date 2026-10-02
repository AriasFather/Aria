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

## Electron desktop app

Public browser and mobile access notes are on the website's `/docs` page.

The Electron app opens only the protected dashboard at `/dashboard`; public pages such as `/`, `/home`, `/features`, `/get-token`, `/terms`, and `/privacy` remain website pages and open in the regular browser. Both the dashboard and website remain available on the local web server at `http://127.0.0.1:8080` (or the next available port through `8084`).

For development, install the Python dependencies above, then run:

```bash
npm install
npm start
```

The desktop app starts the Aria bot executable when packaged (or `aria.py` during development) if no dashboard is already running. On first launch, a token setup window opens. Remembered tokens are saved through Aria's encrypted config; if you turn off **Remember token**, Aria uses it only for the current run. The token is never sent to renderer storage or printed to a terminal. Use **Aria > Set / Change Token...** to update it later, **Open Dashboard in Browser** for `/dashboard`, or **Open Aria Website** for the public home page. Closing the desktop app stops a backend it started, but does not stop a backend that was already running.

To build an installer for the current operating system, install the Python build dependencies and run `npm run dist`:

```bash
python -m pip install -r requirements.txt aiohttp curl-cffi colorama pyinstaller
npm run dist
```

Build on the target operating system. The packaged backend and its runtime data are copied to the user's writable application-data folder, and existing JSON, text, and database state is retained when the app version changes.

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
