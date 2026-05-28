import sqlite3
import os
import json
import hmac
import hashlib
import secrets
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory="templates")

DB_PATH = os.getenv("DB_PATH", "/data/suggestions.db")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
SITE_TITLE = os.getenv("SITE_TITLE", "Suggestion Box")

STATUS_LABELS = {
    "open":      ("Open",      "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"),
    "reviewing": ("Reviewing", "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300"),
    "done":      ("Done",      "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300"),
    "rejected":  ("Rejected",  "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"),
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            author      TEXT DEFAULT 'Anonymous',
            votes       INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'open',
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


init_db()


def make_session_token() -> str:
    return hmac.new(
        key=ADMIN_PASSWORD.encode(),
        msg=b"admin-session",
        digestmod=hashlib.sha256,
    ).hexdigest()


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get("admin_token", "")
    return secrets.compare_digest(token, make_session_token())


def get_voted_ids(request: Request) -> list:
    try:
        return json.loads(request.cookies.get("voted", "[]"))
    except Exception:
        return []


# ── Public routes ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, sort: str = "votes"):
    conn = get_db()
    order = "votes DESC, created_at DESC" if sort == "votes" else "created_at DESC"
    rows = conn.execute(f"SELECT * FROM suggestions ORDER BY {order}").fetchall()
    conn.close()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "suggestions": rows,
        "voted_ids": get_voted_ids(request),
        "sort": sort,
        "title": SITE_TITLE,
        "status_labels": STATUS_LABELS,
    })


@app.post("/suggest")
async def create_suggestion(
    title: str = Form(...),
    description: str = Form(""),
    author: str = Form(""),
):
    title = title.strip()
    if not title:
        return RedirectResponse("/", status_code=303)
    conn = get_db()
    conn.execute(
        "INSERT INTO suggestions (title, description, author) VALUES (?, ?, ?)",
        (title, description.strip(), author.strip() or "Anonymous"),
    )
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)


@app.post("/vote/{suggestion_id}")
async def vote(request: Request, suggestion_id: int, sort: str = Form("votes")):
    voted_ids = get_voted_ids(request)
    conn = get_db()
    if suggestion_id in voted_ids:
        conn.execute(
            "UPDATE suggestions SET votes = MAX(0, votes - 1) WHERE id = ?",
            (suggestion_id,),
        )
        voted_ids.remove(suggestion_id)
    else:
        conn.execute(
            "UPDATE suggestions SET votes = votes + 1 WHERE id = ?",
            (suggestion_id,),
        )
        voted_ids.append(suggestion_id)
    conn.commit()
    conn.close()
    resp = RedirectResponse(f"/?sort={sort}", status_code=303)
    resp.set_cookie("voted", json.dumps(voted_ids), max_age=365 * 24 * 3600, httponly=True)
    return resp


# ── Auth routes ──────────────────────────────────────────────────────────────

@app.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request, error: int = 0):
    if is_authenticated(request):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "title": SITE_TITLE,
        "error": bool(error),
    })


@app.post("/admin/login")
async def login(password: str = Form(...)):
    if secrets.compare_digest(password, ADMIN_PASSWORD):
        resp = RedirectResponse("/admin", status_code=303)
        resp.set_cookie(
            "admin_token", make_session_token(),
            httponly=True, samesite="lax", max_age=8 * 3600,
        )
        return resp
    return RedirectResponse("/admin/login?error=1", status_code=303)


@app.get("/admin/logout")
async def logout():
    resp = RedirectResponse("/admin/login", status_code=303)
    resp.delete_cookie("admin_token")
    return resp


# ── Admin routes ─────────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_view(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/admin/login", status_code=303)
    conn = get_db()
    rows = conn.execute("SELECT * FROM suggestions ORDER BY created_at DESC").fetchall()
    conn.close()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "suggestions": rows,
        "title": SITE_TITLE,
        "status_labels": STATUS_LABELS,
        "statuses": list(STATUS_LABELS.keys()),
    })


@app.post("/admin/status/{suggestion_id}")
async def update_status(request: Request, suggestion_id: int, status: str = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse("/admin/login", status_code=303)
    conn = get_db()
    conn.execute("UPDATE suggestions SET status = ? WHERE id = ?", (status, suggestion_id))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/delete/{suggestion_id}")
async def delete_suggestion(request: Request, suggestion_id: int):
    if not is_authenticated(request):
        return RedirectResponse("/admin/login", status_code=303)
    conn = get_db()
    conn.execute("DELETE FROM suggestions WHERE id = ?", (suggestion_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)
