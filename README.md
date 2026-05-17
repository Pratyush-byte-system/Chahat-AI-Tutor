# 📚 CHAHAT — Your AI Teacher & Best Friend

> *"कोई topic मुश्किल नहीं है — बस सही तरीके से समझाने वाला चाहिए 💡"*

CHAHAT is a **voice-based AI teaching assistant** built as a native desktop app. Powered by **Google Gemini's Live Audio API** and a rich **PyQt5 + WebEngine** UI, she teaches you programming by *talking* to you, *writing* on a real-time notebook, *running* live code, *drawing* diagrams on a whiteboard, and *remembering* everything about you across sessions.

She isn't just a teacher — she's an **emotional companion** who adapts to your mood, celebrates your wins, supports you when you're frustrated, and genuinely cares about your learning journey.

---

## ✨ Features at a Glance

| Feature | Description |
|---|---|
| 🎤 **Voice Chat** | Bidirectional real-time audio — talk naturally in Hindi, English, or Hinglish |
| 📝 **Live Notebook** | Beautiful PyQt5 + WebEngine notebook UI — CHAHAT writes on it like a teacher on a board |
| 🐍 **Live Code Execution** | Sandboxed Python execution with AST-level security analysis |
| 🎨 **Interactive Whiteboard** | Draws flowcharts, class diagrams, and visuals using Mermaid.js |
| 📄 **PDF Notes Export** | One-click beautiful PDF generation (NotoSans Unicode support, mirroring notebook style) |
| 🧠 **Persistent Memory** | SQLite-backed memory — remembers your name, progress, strengths, weaknesses, feelings across sessions |
| 🔄 **Spaced Repetition** | Built-in review system tracks mastery and schedules topic reviews |
| 🌐 **Web Search** | DuckDuckGo-powered search + page fetching — never guesses, always looks up latest info |
| 📱 **App Launcher** | Opens any application on your Mac/PC via voice command |
| 🕐 **Time & Date** | Tells current time, date, and day on demand |
| 📜 **Session Logs** | Every conversation auto-saved as a reviewable Markdown transcript |
| 🔄 **Auto Reconnect** | Resilient WebSocket connection — never drops |
| 📝 **Quiz Generation** | Creates and saves MCQ quizzes for any topic |
| 💕 **Emotional Intelligence** | Detects frustration, sadness, excitement — responds with genuine empathy |
| 🔀 **Multi-Language Curricula** | Python, C# + Unity, C++ + Unreal Engine, JavaScript + Web Dev |
| 🎙️ **Mic Toggle** | Mute/unmute microphone with a single click |
| ✍️ **Text Input** | Type messages directly alongside voice — submit code or answers via input bar |

---

## 🖥️ Screenshots

The desktop UI features:
- **Wooden-desk themed header** with connection status and mic toggle
- **Sidebar chat panel** showing real-time transcripts (student & teacher)
- **Full notebook area** with headings, code blocks, bullet points, and Mermaid diagrams
- **Terminal overlay** for live code execution output
- **Whiteboard overlay** for interactive diagrams
- **Memory dashboard** to view/edit student profile, topics, and remembered facts
- **Text input bar** for typed submissions

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **A Gemini API Key** — get one free from [Google AI Studio](https://aistudio.google.com/apikey)

### 1. Clone the Repository
```bash
git clone https://github.com/Pratyush-byte-system/Chahat-AI-Tutor.git
cd Chahat
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

> **Note:** PyQt5 and PyQtWebEngine are also required but not listed in requirements.txt to avoid platform issues. Install them separately:
> ```bash
> pip install PyQt5 PyQtWebEngine
> ```

### 3. Configure API Key
Create a `.env` file in the project root (or edit the existing one):
```env
# Get your API key from: https://aistudio.google.com/apikey
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=models/gemini-2.0-flash-live-001
```

### 4. Run CHAHAT
```bash
python main.py
```

### 5. Start Learning!
Just talk:
- *"Python kya hai?"*
- *"For loop samjhao"*
- *"Yeh code run karo"*
- *"Notes save karo"*
- *"Mujhe C# seekhni hai"*

---

## 📁 Project Structure

```
Chahat/
├── main.py             # Core engine — audio pipeline, WebSocket, tool dispatch
├── ui.py               # PyQt5 + WebEngine desktop UI (notebook, terminal, whiteboard, dashboard)
├── prompt.py           # CHAHAT's personality, teaching methodology & system prompt
├── memory.py           # SQLite-backed persistent memory, spaced repetition, multi-curricula
├── app.py              # Cross-platform app launcher (macOS + Windows)
├── web_search.py       # DuckDuckGo search + page content extraction
├── requirements.txt    # Python dependencies
├── .env                # API key configuration (gitignored)
├── .gitignore          # Git ignore rules
├── memory.db           # SQLite database — student profile, topics, memories (auto-created)
├── fonts/              # NotoSans fonts for PDF Unicode support (auto-downloaded)
├── notes/              # 📝 Saved teaching notes & quizzes (Markdown + PDF)
├── sessions/           # 📜 Auto-saved session transcripts
└── README.md           # This file
```

---

## 🛠️ Tools & Capabilities

CHAHAT has **14 built-in tools** that she uses proactively during teaching:

### 📝 `write_notebook`
Writes teaching content on the notebook UI in real-time — headings, code blocks, bullet points, tables. This is her primary teaching tool, like a teacher writing on a board.

### 🐍 `run_python`
Executes Python code in a **3-layer sandboxed environment**:
1. **AST Analysis** — blocks dangerous imports, functions, and patterns at parse time
2. **Runtime Sandbox** — restricts file writes via `open()` monkey-patching
3. **Process Isolation** — runs in a separate process with minimal env, 10s timeout

### 🎨 `draw_diagram`
Renders interactive diagrams on the whiteboard overlay using **Mermaid.js** — flowcharts, class diagrams, sequence diagrams, state machines, and more. Also supports raw HTML/SVG.

### 📄 `save_notes`
Generates **beautiful PDF notes** using `fpdf2` with NotoSans Unicode fonts — mirrors the notebook UI style exactly (headings, code blocks, bullet points). Also saves a Markdown backup.

### 📝 `save_quiz`
Creates MCQ quizzes (5-10 questions with A-D options and ✅ answers) and saves them as Markdown files.

### 🌐 `search_web`
Searches the web via **DuckDuckGo HTML** (no API key needed, no CAPTCHA issues). Used when CHAHAT doesn't know something or needs the latest information.

### 📄 `fetch_page`
Fetches and extracts readable content from any URL using `requests` + `BeautifulSoup`. Strips noise elements and extracts structured text.

### 📱 `open_app`
Opens applications on macOS or Windows. Supports 30+ common app aliases (Chrome, VS Code, WhatsApp, Spotify, etc.) with fuzzy matching.

### 🕐 `get_time`
Returns current system time, date, and day.

### 💾 `remember`
Permanently stores facts about the student in SQLite — preferences, strengths, weaknesses, personal info, progress milestones, and goals. Recalled in future sessions.

### 🔒 `learn_verified_fact`
Saves verified factual knowledge to a permanent, non-deletable knowledge bank. Follows a strict verification protocol before saving.

### 🔀 `switch_curriculum`
Switches or adds programming language curricula. Available: `python`, `csharp_unity`, `cpp_unreal`, `javascript`. Each has its own roadmap and topic tracking.

### ❌ `dismiss_terminal` / `dismiss_diagram`
Removes the terminal or whiteboard overlay — but **only after asking the student** if they've understood the content.

---

## 🧠 Memory System

CHAHAT uses an **advanced SQLite-backed memory system** (`memory.db`) that tracks:

| Table | Purpose |
|---|---|
| `student_profile` | Name, level, total sessions, study minutes, strengths, weaknesses |
| `sessions` | Session history with summaries, topics, tools used, mood, engagement |
| `topics` | Per-topic mastery levels, review schedule, notes saved, quiz scores |
| `key_moments` | Breakthroughs, struggles, questions, code successes/errors |
| `explicit_memories` | Facts stored via `remember` tool (preferences, personal info, goals) |
| `verified_knowledge` | Permanent, verified factual knowledge bank |
| `active_curricula` | Currently active programming language curricula |

### Spaced Repetition
Topics are tracked with review intervals: **1 → 3 → 7 → 14 → 30 → 60 days**. CHAHAT proactively reviews topics that are due at the start of each session.

### Legacy Migration
If a `memory.json` file exists from an older version, it's automatically migrated to SQLite on first run.

---

## 🎓 Multi-Language Curricula

CHAHAT supports **4 programming curricula**, each with a structured roadmap:

| Curriculum | ID | Phases |
|---|---|---|
| 🐍 **Python** | `python` | Foundation → Intermediate → Advanced → Specialization |
| 🎮 **C# + Unity** | `csharp_unity` | C# Foundation → Advanced C# + Unity Intro → Game Dev → Publishing |
| ⚙️ **C++ + Unreal** | `cpp_unreal` | C++ Foundation → Advanced C++ + UE Intro → Game Dev → AAA |
| 🌐 **JavaScript + Web** | `javascript` | JS Foundation → Advanced JS + Frontend → Full-Stack → Specialization |

Switch anytime by saying: *"Mujhe C# seekhni hai"* or *"JavaScript bhi seekhni hai"*.

---

## 💡 Teaching Style

CHAHAT teaches with a unique methodology:

- **Extreme Depth** — 800-1200 words per topic, internal Python mechanics, memory-level insights
- **"WHY" before "HOW"** — explains why a concept exists before how to use it
- **Real-life Analogies** — Variable = डिब्बा 📦, Function = Recipe 📋
- **3-5 Code Examples** per concept — Good vs Better vs Best (Pythonic)
- **Step-by-Step Flow** — Explain → Demonstrate → Confirm → Challenge (never all at once)
- **Common Mistakes** — minimum 3-5 pitfalls per topic with example code
- **"Socho" Moments** — interactive thinking prompts to keep you engaged
- **Under the Hood** — CPython internals, bytecode, object model when relevant
- **Interview Prep** — relevant interview questions woven into explanations
- **Code Reviews** — structured feedback with ✅ Good / ❌ Fix / 🔄 Refactored / 🎯 Score

---

## 💕 Emotional Intelligence

CHAHAT is not just a teacher — she's your best friend:

- **Feelings First** — if you're sad or stressed, she pauses teaching and listens
- **Mood Detection** — recognizes frustration, confusion, excitement, tiredness from your words
- **Genuine Empathy** — no generic motivational quotes; responds like a real friend
- **Proactive Care** — asks how you're doing, suggests breaks, follows up on personal matters
- **Emotional Memory** — remembers your feelings and references them in future sessions
- **Seamless Mode Switching** — transitions between Teacher Mode ↔ Friend Mode based on context

---

## ⚙️ Configuration

### Environment Variables (`.env`)

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API key (required) | — |
| `GEMINI_MODEL` | Gemini model to use | `models/gemini-2.0-flash-live-001` |

### Audio Settings (in `main.py`)

| Setting | Value |
|---|---|
| Microphone sample rate | 16,000 Hz |
| Speaker sample rate | 24,000 Hz |
| Audio frame size | 320 samples (20ms) |

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `numpy` | Audio buffer processing |
| `sounddevice` | Microphone input & speaker output |
| `websockets` | Gemini Live API WebSocket connection |
| `requests` | Web search & page fetching |
| `beautifulsoup4` | HTML parsing for web content extraction |
| `fpdf2` | PDF note generation with Unicode support |
| `PyQt5` | Desktop application UI framework |
| `PyQtWebEngine` | Embedded web view for notebook rendering |

---

## 👨‍💻 Made By

**Pratyush Sir** ❤️

---

<p align="center">
  <i>CHAHAT — Because every student deserves a teacher who never gives up on them.</i> 🌟
</p>
