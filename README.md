# suggestion-box

A lightweight self-hosted suggestion box. Users submit ideas, vote on them, and an admin triages each entry with a status label.

Built with **FastAPI + Jinja2 + Tailwind CSS**. Data stored in a single SQLite file — no external database required.

## Features

- Submit suggestions with optional description and author name
- Toggle upvote (stored in a browser cookie — no account required)
- Sort by votes or newest
- Status labels: **Open**, **Reviewing**, **Done**, **Rejected**
- Password-protected admin panel — update status, delete entries
- Dark mode toggle with a warm color palette (soft black / warm beige / coral / golden)
- Configurable title and admin password via environment variables
- Persistent data via a single volume-mounted SQLite file

## Quick Start

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

Access at `http://localhost:8000` — admin panel at `http://localhost:8000/admin`.

## Behind Traefik

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

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ADMIN_PASSWORD` | `changeme` | Password for `/admin` |
| `SITE_TITLE` | `Suggestion Box` | Page title shown to users |
| `DB_PATH` | `/data/suggestions.db` | Path to the SQLite database file |

## Routes

| Route | Description |
|---|---|
| `GET /` | Public suggestion feed |
| `POST /suggest` | Submit a new suggestion |
| `POST /vote/{id}` | Toggle vote on a suggestion |
| `GET /admin` | Admin panel (password protected) |
| `POST /admin/status/{id}` | Update suggestion status |
| `POST /admin/delete/{id}` | Delete a suggestion |

## Stack

- [FastAPI](https://fastapi.tiangolo.com/) — async Python web framework
- [Jinja2](https://jinja.palletsprojects.com/) — HTML templating
- [Tailwind CSS](https://tailwindcss.com/) — styling (CDN)
- SQLite — embedded database, zero ops overhead
