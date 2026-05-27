# suggestion-box App

A lightweight self-hosted suggestion box. Users submit ideas, vote on them (one toggle-vote per browser), and an admin can triage each entry with a status label.

Built with FastAPI + Jinja2 + Tailwind CSS. Data is stored in a single SQLite file.

## Features

- Submit suggestions with optional description and author name
- Toggle upvote (stored in a browser cookie — no account required)
- Sort by votes or newest
- Status labels: **Open**, **Reviewing**, **Done**, **Rejected**
- Password-protected admin panel — update status, delete entries
- Configurable title and admin password via environment variables
- Persistent data via a single volume-mounted SQLite file

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ADMIN_PASSWORD` | `changeme` | Password for `/admin` |
| `SITE_TITLE` | `Suggestion Box` | Page title shown to users |
| `DB_PATH` | `/data/suggestions.db` | Path to the SQLite database file |

## Docker Compose — standalone

Runs the app directly on a host port. Suitable for local use or simple setups without a reverse proxy.

```yaml
services:
  suggest:
    image: cathode/suggestion-box:latest
    container_name: suggest
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      ADMIN_PASSWORD: changeme
      SITE_TITLE: "My Suggestion Box"
    volumes:
      - suggest_data:/data

volumes:
  suggest_data:
```

Access at `http://localhost:8000`.  
Admin panel at `http://localhost:8000/admin`.

## Docker Compose — behind Traefik

Assumes Traefik is already running on an external Docker network (`proxy` in this example) with a `websecure` entrypoint and TLS configured.

```yaml
services:
  suggest:
    image: cathode/suggestion-box:latest
    container_name: suggest
    restart: unless-stopped
    networks:
      - proxy
    environment:
      ADMIN_PASSWORD: changeme
      SITE_TITLE: "My Suggestion Box"
    volumes:
      - suggest_data:/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.suggest.rule=Host(`suggest.example.com`)"
      - "traefik.http.routers.suggest.entrypoints=websecure"
      - "traefik.http.routers.suggest.tls=true"
      - "traefik.http.services.suggest.loadbalancer.server.port=8000"

volumes:
  suggest_data:

networks:
  proxy:
    external: true
```

Replace `suggest.example.com` with your actual hostname.  
If you use Let's Encrypt via Traefik, add `traefik.http.routers.suggest.tls.certresolver=letsencrypt` to the labels.

## Building from source

```bash
git clone https://github.com/your-org/suggest-app.git
cd suggest-app
docker build -t suggest-app:local .
```

Then replace `cathode/suggestion-box:latest` in either compose example above with `suggest-app:local`.

## Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Public suggestion feed |
| `/suggest` | POST | Submit a new suggestion |
| `/vote/{id}` | POST | Toggle vote on a suggestion |
| `/admin` | GET | Admin panel (requires auth) |
| `/admin/login` | GET / POST | Admin login |
| `/admin/logout` | GET | Logout |
| `/admin/status/{id}` | POST | Update suggestion status |
| `/admin/delete/{id}` | POST | Delete a suggestion |
