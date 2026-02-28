"""
TalentScout Hiring Assistant Chatbot
=====================================
API calls: ONLY 2 types
  1. generate_questions()  — called once after tech stack collected
  2. evaluate_answer()     — called once per technical question answer

Everything else (greeting, info gathering, farewell) uses scripted replies — zero API calls.
"""

import streamlit as st
import google.generativeai as genai
import sqlite3
import json
import re
from datetime import datetime

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
import os
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = "models/gemini-2.5-flash-lite"
DB_PATH        = "talentscout.db"

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="TalentScout | Hiring Assistant",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0d0f14;
    color: #e8e4dc;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

.hero {
    text-align: center; padding: 2rem 1rem 1.2rem;
    border-bottom: 1px solid #2a2d38; margin-bottom: 1.2rem;
}
.hero h1 { font-family: 'DM Serif Display', serif; font-size: 2.5rem; color: #f5c842; margin: 0 0 0.2rem; }
.hero p   { color: #8e92a3; font-size: 0.9rem; margin: 0; }

.chat-wrapper { display: flex; flex-direction: column; gap: 0.9rem; margin-bottom: 1rem; }
.msg-user, .msg-bot { display: flex; gap: 0.6rem; align-items: flex-start; }
.msg-user { flex-direction: row-reverse; }

.avatar {
    width: 34px; height: 34px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.95rem; flex-shrink: 0;
}
.avatar-bot  { background: #f5c842; color: #0d0f14; }
.avatar-user { background: #2a3560; color: #e8e4dc; }

.bubble {
    max-width: 78%; padding: 0.7rem 0.95rem; border-radius: 14px;
    font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap;
}
.bubble-bot  { background: #181b24; border: 1px solid #2a2d38; border-top-left-radius: 4px; }
.bubble-user { background: #1d2b52; border: 1px solid #2a3560; border-top-right-radius: 4px; text-align: right; }

.progress-wrap {
    margin: 0.4rem 0 1.2rem; padding: 0.7rem 1rem;
    background: #181b24; border-radius: 10px; border: 1px solid #2a2d38;
}
.progress-label { font-size: 0.72rem; color: #8e92a3; margin-bottom: 0.35rem; }
.progress-bar-bg { background: #2a2d38; border-radius: 100px; height: 5px; overflow: hidden; }
.progress-bar-fill {
    height: 5px; background: linear-gradient(90deg, #f5c842, #f59e0b);
    border-radius: 100px; transition: width 0.5s ease;
}

.info-card {
    background: #181b24; border: 1px solid #2a2d38;
    border-radius: 10px; padding: 0.8rem; margin-bottom: 0.6rem; font-size: 0.82rem;
}
.info-card h4 {
    color: #f5c842; margin: 0 0 0.35rem;
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px;
}
.info-card p { margin: 0.15rem 0; color: #c4c8d6; }

.final-score-box {
    background: linear-gradient(135deg, #1a1f2e, #0f1319);
    border: 2px solid #f5c842; border-radius: 14px;
    padding: 1.5rem; text-align: center; margin: 1rem 0;
}
.final-score-box h2 { color: #f5c842; font-size: 3rem; margin: 0; }
.final-score-box p  { color: #8e92a3; font-size: 0.88rem; margin: 0.3rem 0 0; }

.stTextInput > div > div > input {
    background: #181b24 !important; border: 1px solid #2a2d38 !important;
    color: #e8e4dc !important; border-radius: 10px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #f5c842 !important;
    box-shadow: 0 0 0 2px rgba(245,200,66,0.15) !important;
}
.stButton > button {
    background: #f5c842 !important; color: #0d0f14 !important;
    font-weight: 600 !important; border: none !important;
    border-radius: 10px !important; padding: 0.45rem 1.2rem !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
hr { border-color: #2a2d38 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SQLite
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT, phone TEXT,
            experience TEXT, position TEXT, location TEXT,
            tech_stack TEXT, final_score REAL, created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS qa_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER, technology TEXT,
            question TEXT, answer TEXT, score INTEGER, feedback TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)
    conn.commit()
    conn.close()

def save_candidate(candidate: dict, final_score: float) -> int:
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    c.execute("""
        INSERT INTO candidates
            (name, email, phone, experience, position, location, tech_stack, final_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate.get("name"),    candidate.get("email"),
        candidate.get("phone"),   candidate.get("experience"),
        candidate.get("position"),candidate.get("location"),
        candidate.get("tech_stack"), final_score,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    cid = c.lastrowid
    conn.commit()
    conn.close()
    return cid

def save_qa(cid: int, tech: str, question: str, answer: str, score: int, feedback: str):
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    c.execute("""
        INSERT INTO qa_responses (candidate_id, technology, question, answer, score, feedback)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (cid, tech, question, answer, score, feedback))
    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────────
# Scripted replies — ZERO API calls
# ─────────────────────────────────────────────
SCRIPTED = {
    "greeting":           "👋 Hi! I'm Scout, your hiring assistant at TalentScout.\n\nI'll collect a few details and then ask some technical questions to assess your skills. It'll only take a few minutes!\n\nLet's start — what's your **full name**?",
    "collect_name":       "Nice to meet you, {name}! 😊\n\nWhat's your **email address**?",
    "collect_email":      "Got it! 📧\n\nWhat's your **phone number**?",
    "collect_phone":      "Thanks! 📱\n\nHow many **years of professional experience** do you have?",
    "collect_experience": "Great! 💼\n\nWhat **position(s)** are you applying for?",
    "collect_position":   "Excellent! 🎯\n\nWhat is your **current city / location**?",
    "collect_location":   "Perfect! 📍\n\nNow please list your **tech stack** — programming languages, frameworks, databases, and tools you work with.\n\n(e.g. Python, Django, PostgreSQL, Docker)",
    "collect_tech_stack": "Awesome stack! 🚀\n\nGenerating your technical questions now — one moment…",
}

STAGE_ORDER = [
    "greeting", "collect_name", "collect_email", "collect_phone",
    "collect_experience", "collect_position", "collect_location",
    "collect_tech_stack", "technical_questions", "farewell",
]

STAGE_LABELS = {
    "greeting":            "Welcome",
    "collect_name":        "Full Name",
    "collect_email":       "Email",
    "collect_phone":       "Phone",
    "collect_experience":  "Experience",
    "collect_position":    "Desired Role",
    "collect_location":    "Location",
    "collect_tech_stack":  "Tech Stack",
    "technical_questions": "Technical Assessment",
    "farewell":            "Complete",
}

EXIT_KEYWORDS = {"exit", "quit", "bye", "goodbye", "stop", "end"}

# ─────────────────────────────────────────────
# Gemini — only 2 functions use the API
# ─────────────────────────────────────────────
def gemini_call(prompt: str) -> str:
    """Raw Gemini call — used only by generate_questions and evaluate_answer."""
    genai.configure(api_key=GEMINI_API_KEY)
    model    = genai.GenerativeModel(model_name=GEMINI_MODEL)
    response = model.generate_content(prompt)
    return response.text

def generate_questions(tech_stack: str, experience: str) -> list:
    """
    API CALL #1 — called ONCE after tech stack is collected.
    Returns list of {technology, question}.
    """
    prompt = f"""You are a technical interviewer.
Candidate experience: {experience} years
Tech stack: {tech_stack}

Generate exactly 5 technical interview questions spread across the main technologies.
Difficulty should match {experience} years of experience.

Return ONLY a valid JSON array, no markdown, no explanation:
[
  {{"technology": "Python", "question": "..."}},
  {{"technology": "Django", "question": "..."}}
]"""
    raw = re.sub(r"```json|```", "", gemini_call(prompt)).strip()
    try:
        qs = json.loads(raw)
        return [q for q in qs if "technology" in q and "question" in q]
    except Exception:
        return [{"technology": "General", "question": f"Describe your overall experience with {tech_stack}."}]

def evaluate_answer(question: str, answer: str, technology: str, experience: str) -> dict:
    """
    API CALL #2 — called ONCE per technical answer.
    Returns {score: int, feedback: str}.
    """
    prompt = f"""You are evaluating a technical interview answer.
Technology: {technology}
Candidate experience: {experience} years
Question: {question}
Answer: {answer}

Score out of 100:
- Technical accuracy (40 pts)
- Completeness (30 pts)
- Clarity (30 pts)

Score 0 if answer is blank, "i don't know", or irrelevant.

Return ONLY valid JSON, no markdown:
{{"score": <0-100>, "feedback": "<1-2 sentence constructive feedback>"}}"""
    raw = re.sub(r"```json|```", "", gemini_call(prompt)).strip()
    try:
        result = json.loads(raw)
        result["score"] = max(0, min(100, int(result.get("score", 0))))
        return result
    except Exception:
        return {"score": 0, "feedback": "Could not evaluate. Please try again."}

# ─────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "messages":          [],
        "stage":             "greeting",
        "candidate":         {},
        "questions":         [],
        "q_index":           0,
        "scores":            [],
        "conversation_over": False,
        "candidate_id":      None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def scripted(stage: str) -> str:
    name = st.session_state.candidate.get("name", "")
    return SCRIPTED.get(stage, "Let's continue.").replace("{name}", name)

def next_stage(current: str) -> str:
    idx = STAGE_ORDER.index(current) if current in STAGE_ORDER else 0
    return STAGE_ORDER[min(idx + 1, len(STAGE_ORDER) - 1)]

def update_candidate(msg: str, stage: str):
    c = st.session_state.candidate
    if   stage == "collect_name"       and "name"       not in c: c["name"]       = msg.strip().title()
    elif stage == "collect_email"      and "email"      not in c:
        if "@" in msg: c["email"] = msg.strip().lower()
    elif stage == "collect_phone"      and "phone"      not in c: c["phone"]      = msg.strip()
    elif stage == "collect_experience" and "experience" not in c: c["experience"] = msg.strip()
    elif stage == "collect_position"   and "position"   not in c: c["position"]   = msg.strip()
    elif stage == "collect_location"   and "location"   not in c: c["location"]   = msg.strip().title()
    elif stage == "collect_tech_stack" and "tech_stack" not in c: c["tech_stack"] = msg.strip()
    st.session_state.candidate = c

def get_progress() -> float:
    stage = st.session_state.stage
    if stage in STAGE_ORDER:
        idx = STAGE_ORDER.index(stage)
        if stage == "technical_questions":
            total = len(st.session_state.questions) or 1
            return 0.8 + (st.session_state.q_index / total) * 0.15
        return idx / (len(STAGE_ORDER) - 1)
    return 0.0

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
def render_message(role: str, content: str):
    if role in ("model", "assistant"):
        st.markdown(f"""
        <div class="msg-bot">
            <div class="avatar avatar-bot">🎯</div>
            <div class="bubble bubble-bot">{content}</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="msg-user">
            <div class="avatar avatar-user">👤</div>
            <div class="bubble bubble-user">{content}</div>
        </div>""", unsafe_allow_html=True)

def render_progress():
    pct   = get_progress()
    stage = st.session_state.stage
    if stage == "technical_questions":
        total = len(st.session_state.questions)
        label = f"Question {st.session_state.q_index}/{total}"
    else:
        label = STAGE_LABELS.get(stage, "")
    st.markdown(f"""
    <div class="progress-wrap">
        <div class="progress-label">Step: {label} &nbsp;·&nbsp; {int(pct*100)}% complete</div>
        <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width:{int(pct*100)}%"></div>
        </div>
    </div>""", unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.markdown("### 📋 Candidate Profile")
        c      = st.session_state.candidate
        fields = {
            "Full Name":  c.get("name"),
            "Email":      c.get("email"),
            "Phone":      c.get("phone"),
            "Experience": c.get("experience"),
            "Position":   c.get("position"),
            "Location":   c.get("location"),
            "Tech Stack": c.get("tech_stack"),
        }
        for label, value in fields.items():
            if value:
                st.markdown(f'<div class="info-card"><h4>{label}</h4><p>{value}</p></div>',
                            unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🔄 Start Over"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# ─────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🎯 TalentScout</h1>
    <p>AI-Powered Hiring Assistant · Technology Recruitment</p>
</div>
""", unsafe_allow_html=True)

render_sidebar()
render_progress()

# ── Boot greeting — scripted, NO API call ─────
if not st.session_state.messages:
    st.session_state.messages.append({"role": "model", "content": scripted("greeting")})
    st.session_state.stage = "collect_name"

# ── Render chat history ───────────────────────
st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    render_message(msg["role"], msg["content"])
st.markdown("</div>", unsafe_allow_html=True)

# ── End screen ────────────────────────────────
if st.session_state.conversation_over:
    if st.session_state.scores:
        avg   = sum(s["score"] for s in st.session_state.scores) / len(st.session_state.scores)
        grade = ("Excellent 🌟" if avg >= 80 else "Good 👍" if avg >= 60 else "Average ⚡" if avg >= 40 else "Needs Improvement 📚")
        st.markdown(f"""
        <div class="final-score-box">
            <p>Overall Technical Score</p>
            <h2>{avg:.0f}/100</h2>
            <p>{grade}</p>
        </div>""", unsafe_allow_html=True)
    st.info("✅ Interview complete! Results saved to **talentscout.db**. Click **Start Over** for a new session.")

else:
    # ── Input ─────────────────────────────────
    with st.form(key="chat_form", clear_on_submit=True):
        cols       = st.columns([5, 1])
        user_input = cols[0].text_input("r", placeholder="Type your answer…", label_visibility="collapsed")
        send       = cols[1].form_submit_button("Send")

    if send and user_input.strip():
        user_text = user_input.strip()
        stage     = st.session_state.stage

        # Exit check
        if set(re.findall(r"\w+", user_text.lower())) & EXIT_KEYWORDS:
            st.session_state.messages.append({"role": "user",  "content": user_text})
            st.session_state.messages.append({"role": "model", "content": "Thank you for your time! Our team will review your application and be in touch within 3–5 business days. Best of luck! 🎯"})
            st.session_state.conversation_over = True
            st.rerun()

        st.session_state.messages.append({"role": "user", "content": user_text})

        # ══════════════════════════════════════
        # INFO GATHERING — all scripted, 0 API calls
        # ══════════════════════════════════════
        if stage in ("collect_name", "collect_email", "collect_phone",
                     "collect_experience", "collect_position", "collect_location"):
            update_candidate(user_text, stage)
            st.session_state.messages.append({"role": "model", "content": scripted(stage)})
            st.session_state.stage = next_stage(stage)

        elif stage == "collect_tech_stack":
            update_candidate(user_text, stage)
            st.session_state.messages.append({"role": "model", "content": scripted("collect_tech_stack")})

            # ── API CALL #1: generate questions ──
            with st.spinner("Generating questions…"):
                questions = generate_questions(
                    st.session_state.candidate.get("tech_stack", ""),
                    st.session_state.candidate.get("experience", "unknown"),
                )
            st.session_state.questions = questions
            st.session_state.q_index   = 0
            st.session_state.stage     = "technical_questions"

            q    = questions[0]
            qmsg = f"Here we go! 💡\n\n[{q['technology']}] — Question 1 of {len(questions)}:\n\n{q['question']}"
            st.session_state.messages.append({"role": "model", "content": qmsg})

        # ══════════════════════════════════════
        # TECHNICAL Q&A — 1 API call per answer
        # ══════════════════════════════════════
        elif stage == "technical_questions":
            questions = st.session_state.questions
            q_index   = st.session_state.q_index
            current_q = questions[q_index]

            # ── API CALL #2: evaluate answer ──
            with st.spinner("Evaluating…"):
                result = evaluate_answer(
                    question   = current_q["question"],
                    answer     = user_text,
                    technology = current_q["technology"],
                    experience = st.session_state.candidate.get("experience", "unknown"),
                )

            st.session_state.scores.append({
                "technology": current_q["technology"],
                "question":   current_q["question"],
                "answer":     user_text,
                "score":      result["score"],
                "feedback":   result["feedback"],
            })

            # Show feedback only, no score shown to user
            st.session_state.messages.append({"role": "model", "content": result["feedback"]})

            next_idx = q_index + 1
            st.session_state.q_index = next_idx

            if next_idx < len(questions):
                nq   = questions[next_idx]
                nmsg = f"[{nq['technology']}] — Question {next_idx + 1} of {len(questions)}:\n\n{nq['question']}"
                st.session_state.messages.append({"role": "model", "content": nmsg})
            else:
                # All done — save to DB
                scores      = st.session_state.scores
                final_score = sum(s["score"] for s in scores) / len(scores)

                with st.spinner("Saving results…"):
                    cid = save_candidate(st.session_state.candidate, round(final_score, 2))
                    for s in scores:
                        save_qa(cid, s["technology"], s["question"], s["answer"], s["score"], s["feedback"])
                    st.session_state.candidate_id = cid

                name  = st.session_state.candidate.get("name", "candidate")
                grade = ("Excellent 🌟" if final_score >= 80 else "Good 👍" if final_score >= 60 else "Average ⚡" if final_score >= 40 else "Needs Improvement 📚")
                farewell = (
                    f"That's all the questions! 🎉\n\n"
                    f"Thank you, {name}! Your application has been saved.\n\n"
                    f"Our team will review everything and reach out within 3–5 business days. Best of luck! 🎯"
                )
                st.session_state.messages.append({"role": "model", "content": farewell})
                st.session_state.stage             = "farewell"
                st.session_state.conversation_over = True

        st.rerun()