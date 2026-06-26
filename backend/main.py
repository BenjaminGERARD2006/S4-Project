"""
main.py
-------
FastAPI backend for the Study Flashcard Bot.

Endpoints:
  POST /signup           -> create a user
  POST /login            -> authenticate, returns session token (no subject yet)
  POST /sessions          -> start a new study session for a subject
  POST /chat              -> send a message in a session, get bot reply
  GET  /history/{token}   -> get all messages for a session

Auth model: the client sends a 'token' (returned at login) to identify
the session/user on each request. Stored in the `sessions` table.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from database import init_db, get_conn
from auth import hash_password, verify_password, generate_token
from llm import get_chat_reply

load_dotenv()

app = FastAPI(title="Study Flashcard Bot")

# Allow the simple frontend (served separately, e.g. via `python -m http.server`)
# to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ---------- Request/response models ----------

class SignupRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class NewSessionRequest(BaseModel):
    user_token: str
    subject: str


class ChatRequest(BaseModel):
    session_token: str
    message: str


# ---------- Auth endpoints ----------

@app.post("/signup")
def signup(req: SignupRequest):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (req.username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")

        password_hash = hash_password(req.password)
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (req.username, password_hash),
        )
        conn.commit()
    return {"message": "Signup successful. You can now log in."}


@app.post("/login")
def login(req: LoginRequest):
    with get_conn() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (req.username,)
        ).fetchone()
        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # We reuse the 'sessions' table token as a generic "logged in" token too,
        # with subject=NULL until a study session is actually started.
        token = generate_token()
        conn.execute(
            "INSERT INTO sessions (user_id, token, subject) VALUES (?, ?, NULL)",
            (user["id"], token),
        )
        conn.commit()

    return {"user_token": token, "username": req.username}


# ---------- Study session endpoints ----------

@app.post("/sessions")
def create_session(req: NewSessionRequest):
    """Start a new study session tied to a subject. Returns a session_token
    used for all subsequent /chat and /history calls."""
    with get_conn() as conn:
        user_session = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (req.user_token,)
        ).fetchone()
        if not user_session:
            raise HTTPException(status_code=401, detail="Invalid or expired login token")

        new_token = generate_token()
        conn.execute(
            "INSERT INTO sessions (user_id, token, subject) VALUES (?, ?, ?)",
            (user_session["user_id"], new_token, req.subject),
        )
        conn.commit()

    return {"session_token": new_token, "subject": req.subject}


# ---------- Chat endpoint ----------

@app.post("/chat")
def chat(req: ChatRequest):
    with get_conn() as conn:
        session = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (req.session_token,)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=401, detail="Invalid session token")
        if not session["subject"]:
            raise HTTPException(status_code=400, detail="This session has no subject set")

        # Save the user's message
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, 'user', ?)",
            (session["id"], req.message),
        )
        conn.commit()

        # Rebuild conversation history for context
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session["id"],),
        ).fetchall()
        history = [{"role": r["role"], "content": r["content"]} for r in rows]

        try:
            reply = get_chat_reply(session["subject"], history)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, 'assistant', ?)",
            (session["id"], reply),
        )
        conn.commit()

    return {"reply": reply}


# ---------- History endpoint ----------

@app.get("/history/{session_token}")
def get_history(session_token: str):
    with get_conn() as conn:
        session = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (session_token,)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=401, detail="Invalid session token")

        rows = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session["id"],),
        ).fetchall()

    return {
        "subject": session["subject"],
        "messages": [dict(r) for r in rows],
    }


@app.get("/")
def root():
    return {"status": "Study Flashcard Bot API is running"}
