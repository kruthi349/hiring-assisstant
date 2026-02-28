# 🎯 TalentScout – AI Hiring Assistant Chatbot

An intelligent chatbot for initial candidate screening built with **Streamlit** and **Google Gemini API**.

---

## 📌 Project Overview

TalentScout is a conversational hiring assistant that conducts structured screening interviews for technology candidates. It collects candidate information step by step, then asks tailored technical questions one by one based on their declared tech stack. Answers are evaluated and scored internally, and all data is stored in a local SQLite database.

### Key Features
- Collects candidate profile (name, email, phone, experience, position, location, tech stack)
- Generates 5 technical questions tailored to the candidate's tech stack and experience level
- Asks questions **one at a time** — not all at once
- Evaluates each answer using Gemini and stores scores internally
- Shows **overall performance score** at the end only (individual scores hidden from candidate)
- Saves everything to **SQLite database** (`talentscout.db`)
- Progress bar and live candidate profile sidebar
- Graceful exit on keywords like `bye`, `quit`, `exit`

---

## 🗂️ Project Structure

```
talentscout/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── talentscout.db      # SQLite database (auto-created on first run)
└── README.md
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9+
- A free Google Gemini API key from [aistudio.google.com](https://aistudio.google.com/app/apikey)

### Steps

```bash
# 1. Clone or download the project
cd talentscout

# 2. Create a virtual environment (recommended)
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501` automatically.

---

## 📦 Requirements

```
streamlit>=1.32.0
google-generativeai>=0.7.0
```

---

## 🚀 Usage Guide

1. Run `streamlit run app.py`
2. Scout greets you and collects info step by step:
   - Full Name → Email → Phone → Experience → Position → Location → Tech Stack
3. Once tech stack is provided, Gemini generates 5 technical questions
4. Answer each question one by one
5. After all questions, your **overall score out of 100** is shown
6. Results are saved to `talentscout.db`
7. Type `bye`, `exit`, or `quit` at any time to end the session
8. Click **Start Over** in the sidebar to begin a new session

---

## 🛠️ Technical Details

| Component | Details |
|---|---|
| Frontend | Streamlit |
| LLM | Google Gemini (`gemini-2.5-flash-lite`) |
| API Client | `google-generativeai` Python SDK |
| Database | SQLite via Python `sqlite3` |
| Styling | Custom CSS (dark theme, Google Fonts) |
| State Management | `st.session_state` |

### Database Schema

**`candidates` table** — stores candidate profile + final score
```
id, name, email, phone, experience, position, location, tech_stack, final_score, created_at
```

**`qa_responses` table** — stores each question, answer, score, and feedback
```
id, candidate_id, technology, question, answer, score, feedback
```

---

## 🧠 Prompt Design

### API Usage — Only 2 Functions Call the API

| Function | When Called | Purpose |
|---|---|---|
| `generate_questions()` | Once, after tech stack collected | Generates 5 tailored technical questions as JSON |
| `evaluate_answer()` | Once per answer (5 times max) | Scores answer 0–100 and returns feedback |

**Everything else is scripted** — greetings, info collection acknowledgements, and farewell messages use hardcoded text. This keeps API usage to a minimum (6 calls per full interview).

### Question Generation Prompt
Instructs Gemini to generate exactly 5 questions spread across the candidate's technologies, calibrated to their experience level, returned as a clean JSON array.

### Answer Evaluation Prompt
Scores answers on 3 criteria: Technical Accuracy (40 pts), Completeness (30 pts), Clarity (30 pts). Returns score + 1–2 sentence feedback as JSON.

---

## 🔐 Data Handling & Privacy

- API key is stored directly in `app.py` (line 19) — replace with your own key
- All candidate data is stored locally in `talentscout.db` — nothing is sent to external servers except the Gemini API prompts
- No personal data is logged or retained by Google on the free tier beyond standard API usage
- For production use, consider: environment variables for API keys, encrypted storage, GDPR consent banner, and data retention policies

---

## ⚡ Challenges & Solutions

| Challenge | Solution |
|---|---|
| API quota exceeded (20 req/day on free tier) | Switched to `gemini-1.5-flash` (1500 req/day) and replaced all non-essential API calls with scripted responses |
| Model not found error | Used `models/gemini-1.5-flash` prefix format for older SDK compatibility |
| Too many API calls per session | Info gathering uses zero API calls; only question generation + evaluation use the API |
| Showing scores during interview | Score stored internally in session state and SQLite but not shown in chat UI — only final average shown at end |

---

## 📊 Scoring

Each answer is evaluated by Gemini out of 100:
- **Technical Accuracy** — 40 points
- **Completeness** — 30 points  
- **Clarity** — 30 points

Final score is the average across all 5 answers.

| Score | Grade |
|---|---|
| 80–100 | Excellent 🌟 |
| 60–79  | Good 👍 |
| 40–59  | Average ⚡ |
| 0–39   | Needs Improvement 📚 |

---

## 🔗 Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Google Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- [Get Free Gemini API Key](https://aistudio.google.com/app/apikey)
- [Gemini Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
