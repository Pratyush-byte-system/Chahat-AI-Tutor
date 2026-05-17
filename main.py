# main.py — CHAHAT Teacher Edition
# ✅ Voice-based AI Teacher that teaches by writing
# ✅ Tools: open_app, get_time, save_notes, run_python, save_quiz, search_web, fetch_page, remember
# ✅ Audio: Bidirectional real-time audio with Gemini Live API
# ✅ Transcripts: Both user & CHAHAT speech logged
# ✅ Session logging: Every conversation saved as markdown
# ✅ Auto-reconnect on disconnect
# ✅ Advanced SQLite memory with real-time tracking & spaced repetition

import asyncio
import base64
import json
import os
import sys
import subprocess
import threading

import numpy as np
import sounddevice as sd
import websockets
from datetime import datetime
from prompt import get_full_prompt
from memory import LiveMemory
from app import open_app, APP_ALIASES
from web_search import search_web, fetch_page, cleanup_driver

# ── PyQt5 UI event queue ──────────────────────────────────
from ui import UI_QUEUE, TEXT_QUEUE, PDF_QUEUE, MEMORY_CMD_QUEUE, MIC_MUTED, run_ui

def ui_push(data: dict):
    """Push event to the PyQt5 UI queue."""
    UI_QUEUE.put(data)

# ── Load .env file ────────────────────────────────────────
def load_env(path=None):
    """Load .env file without needing python-dotenv."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

# ── Config ────────────────────────────────────────────────
API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL   = os.environ.get("GEMINI_MODEL", "models/gemini-2.0-flash-live-001")
WS_URL  = ("wss://generativelanguage.googleapis.com/ws/"
           "google.ai.generativelanguage.v1beta."
           "GenerativeService.BidiGenerateContent")

if not API_KEY or API_KEY == "your_api_key_here":
    print("❌ ERROR: GEMINI_API_KEY not set!")
    print("   👉 Open .env file and paste your API key")
    print("   👉 Get one from: https://aistudio.google.com/apikey")
    sys.exit(1)

MIC_RATE = 16000
SPK_RATE = 24000
FRAMES   = int(MIC_RATE * 20 / 1000)

# Notes directory — CHAHAT saves teaching notes here
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTES_DIR = os.path.join(BASE_DIR, "notes")
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(NOTES_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)

# ── Tool Declarations ────────────────────────────────────

OPEN_APP_TOOL = {
    "name": "open_app",
    "description": (
        "Koi bhi application/software open karo user ke PC pe. "
        "Jab bhi user koi app open karne ko bole — "
        "'chrome kholo', 'notepad open karo', 'whatsapp chalao', "
        "'calculator open karo', 'spotify chalaao' — "
        "toh yeh tool call karo. "
        "App name exactly waise do jaise user ne bola."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "App ka naam jo open karna hai, e.g. 'chrome', 'notepad', 'whatsapp'"
            }
        },
        "required": ["app_name"]
    }
}

GET_TIME_TOOL = {
    "name": "get_time",
    "description": (
        "Jab bhi user current time, date ya day puche, yeh tool call karo. "
        "Jaise 'time kya hua hai?', 'aaj konsi tarikh hai?', 'aaj kya din hai?'. "
        "Yeh tool system ka current time aur date return karega."
    ),
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

SAVE_NOTES_TOOL = {
    "name": "save_notes",
    "description": (
        "Jab bhi student bole 'notes save karo', 'yeh likh do', 'notes bana do', "
        "'PDF bana do', 'save this', 'write notes', 'is topic ke notes bana do' — "
        "toh yeh tool call karo. Yeh tool notes ko ek BEAUTIFUL PDF file mein save karega "
        "jo EXACTLY notebook jaisa dikhega — same fonts, colors, code blocks, headings. "
        "Saath mein Markdown backup bhi banta hai. "
        "Topic ka title aur content dono dena padega. "
        "Content mein POORI explanation likho — step by step, saare examples ke saath, "
        "saare code blocks ke saath. SHORTCUTS mat lo — jo notebook par likha hai woh sab likho. "
        "Markdown format mein likho — headings, bullet points, code blocks."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Topic ka title, e.g. 'Python Variables — Complete Deep Guide', 'Loops in Python — Everything You Need'"
            },
            "content": {
                "type": "string",
                "description": "Notes ka FULL content — Markdown format mein likho, with headings, bullet points, code examples, deep explanations, edge cases, common mistakes, summary. SHORTCUT mat lo — PURA content likho."
            }
        },
        "required": ["title", "content"]
    }
}

RUN_PYTHON_TOOL = {
    "name": "run_python",
    "description": (
        "Jab bhi student bole 'yeh code run karo', 'isko chalao', 'run this', "
        "'check karo output kya aata hai', ya jab tum koi concept sikhate time "
        "live code demo dikhana chaho — toh yeh tool call karo. "
        "Python code dena hai aur yeh tool usse run karke output dega. "
        "Sirf safe, educational code hi run karo — file deletion, network requests etc. mat karo."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code jo run karna hai. Sirf safe, educational code — print statements, calculations, loops etc."
            }
        },
        "required": ["code"]
    }
}

SAVE_QUIZ_TOOL = {
    "name": "save_quiz",
    "description": (
        "Jab bhi student bole 'mera quiz lo', 'test lo', 'questions do', "
        "'check karo mujhe aata hai ya nahi' — toh yeh tool call karo. "
        "Topic ka naam aur 5-10 MCQ questions with answers generate karo. "
        "Har question mein 4 options hon aur correct answer marked ho. "
        "Quiz ko file mein save karega taaki baad mein practice kar sake."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Quiz ka topic, e.g. 'Python Basics', 'Loops', 'HTML Tags'"
            },
            "questions": {
                "type": "string",
                "description": "Quiz content in Markdown — har question numbered, 4 options (A-D), aur correct answer marked with ✅"
            }
        },
        "required": ["topic", "questions"]
    }
}

WRITE_NOTEBOOK_TOOL = {
    "name": "write_notebook",
    "description": (
        "Jab bhi tum kuch PADHA rahi ho — koi concept explain kar rahi ho, "
        "code likh rahi ho, example de rahi ho, summary likh rahi ho, "
        "diagram/table bana rahi ho — toh yeh tool ZAROOR call karo. "
        "Yeh content student ke notebook par likhega jaise ek teacher board par likhti hai. "
        "HAR teaching point ke liye yeh tool call karo. "
        "Casual baat-cheet ke liye mat use karo — sirf padhai ka content. "
        "Content Markdown mein likho with headings, code blocks, bullet points."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Teaching content in Markdown format — headings, code blocks, bullet points, explanations. Jaise ek teacher board par likhti hai."
            }
        },
        "required": ["content"]
    }
}

DISMISS_TERMINAL_TOOL = {
    "name": "dismiss_terminal",
    "description": (
        "Jab tum run_python tool se code run karo, toh screen par terminal dikhta hai. "
        "Terminal ko hatane ke liye YEH tool call karo. "
        "LEKIN pehle student se ZAROOR pucho: 'Output samajh aa gaya? Screen se hata dun?' "
        "Jab student 'haan', 'yes', 'samajh gaya', 'hata do', 'ok' bole — TABHI yeh tool call karo. "
        "Bina student ki permission ke terminal KABHI mat hatao."
    ),
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

SEARCH_WEB_TOOL = {
    "name": "search_web",
    "description": (
        "Jab bhi student koi aisi cheez puche jo tumhe PATA NAHI hai — "
        "naya library, naya framework, latest news, current events, "
        "koi specific documentation, ya koi topic jisme tumhe confident nahi lag raha — "
        "toh yeh tool call karo. Yeh Chrome browser open karke Google pe search karega "
        "aur latest results laayega. "
        "GUESS mat karo — Chrome se Google search karo aur sahi information do! "
        "Examples: 'Polars library kya hai?', 'LangChain ka latest version?', "
        "'React 19 mein kya naya hai?', 'UV package manager kya hai?'"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query — English mein likho for best results. E.g. 'Polars python dataframe library', 'FastAPI latest features 2024'"
            }
        },
        "required": ["query"]
    }
}

FETCH_PAGE_TOOL = {
    "name": "fetch_page",
    "description": (
        "Jab tumhe kisi specific webpage ya documentation ka content padhna ho — "
        "jaise official docs, tutorial page, StackOverflow answer, GitHub README — "
        "toh yeh tool call karo URL ke saath. "
        "Pehle search_web se results lo, phir jo page sabse relevant lage uska URL yahan do. "
        "Chrome browser us page ko kholega aur content padhke dega."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Full URL of the page to fetch, e.g. 'https://docs.python.org/3/library/asyncio.html'"
            }
        },
        "required": ["url"]
    }
}
DRAW_DIAGRAM_TOOL = {
    "name": "draw_diagram",
    "description": (
        "Jab bhi tum koi visual concept explain karna chaho — flowchart, "
        "data structure, architecture diagram, class diagram, sequence diagram, "
        "math visualization, tree, graph, ya koi bhi visual — toh yeh tool call karo. "
        "Yeh whiteboard par diagram draw karega. "
        "Mermaid syntax use karo (flowchart, sequence, class, state, ER, pie, etc). "
        "Agar Mermaid se nahi ban sakta toh HTML/SVG code likho. "
        "PROACTIVE RULE: Jab bhi koi concept visual se samjhaya ja sake, "
        "toh KHUD bolo 'Ruko, main isko diagram se samjhati hoon!' aur draw karo."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Diagram ka title, e.g. 'For Loop Flowchart', 'List vs Tuple', 'OOP Class Diagram'"
            },
            "code": {
                "type": "string",
                "description": "Mermaid syntax code ya HTML/SVG code jo diagram render karega. Example Mermaid: 'graph TD; A[Start] --> B{Condition}; B -->|Yes| C[Do Something]; B -->|No| D[End]'"
            },
            "diagram_type": {
                "type": "string",
                "description": "Diagram ka type: 'mermaid' (default, recommended), 'html', or 'svg'",
                "enum": ["mermaid", "html", "svg"]
            }
        },
        "required": ["title", "code", "diagram_type"]
    }
}

REMEMBER_TOOL = {
    "name": "remember",
    "description": (
        "Jab bhi tumhe student ke baare mein koi IMPORTANT fact yaad rakhna ho — "
        "jaise 'student ko loops mein dikkat hai', 'student visual learner hai', "
        "'student ka naam (name) hai', 'student ne OOP seekh liya', "
        "'student college mein hai', 'student ko gaming pasand hai' — "
        "toh yeh tool call karo. Yeh fact PERMANENTLY memory mein save hoga "
        "aur FUTURE sessions mein bhi yaad rahega. "
        "PROACTIVE RULE: Jab bhi koi interesting ya useful fact pata chale student ke baare mein, "
        "toh KHUD yaad rakh lo bina student se puche!"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Fact ki category: 'preference', 'strength', 'weakness', 'personal', 'progress', 'goal'",
                "enum": ["preference", "strength", "weakness", "personal", "progress", "goal"]
            },
            "content": {
                "type": "string",
                "description": "Fact jo yaad rakhna hai, e.g. 'Student ko loops samajhne mein time lagta hai'"
            },
            "importance": {
                "type": "integer",
                "description": "Kitna important hai (1-10). 10 = bahut zaroori, 1 = minor detail"
            }
        },
        "required": ["category", "content"]
    }
}

DISMISS_DIAGRAM_TOOL = {
    "name": "dismiss_diagram",
    "description": (
        "Jab tum draw_diagram tool se diagram draw karo, toh screen par whiteboard dikhta hai. "
        "Whiteboard ko hatane ke liye YEH tool call karo. "
        "LEKIN pehle student se ZAROOR pucho: 'Diagram samajh aa gaya? Hata dun?' "
        "Jab student 'haan', 'samajh gaya', 'hata do', 'ok' bole — TABHI yeh tool call karo. "
        "Bina student ki permission ke diagram KABHI mat hatao."
    ),
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

LEARN_VERIFIED_FACT_TOOL = {
    "name": "learn_verified_fact",
    "description": (
        "Jab student tumhe koi NAYI factual information bataye aur tumne VERIFY kar liya ki woh SAHI hai — "
        "toh yeh tool call karo. Yeh fact PERMANENTLY tumhare knowledge bank mein save hoga aur KABHI delete nahi hoga. "
        "⚠️ IMPORTANT: Sirf VERIFIED, SAHI facts save karo! Agar student galat info de toh politely correct karo, save MAT karo. "
        "Agar unsure ho toh search_web se verify karo pehle. "
        "Yeh tool sirf FACTUAL information ke liye hai — personal info ke liye remember tool use karo. "
        "Examples: 'Python was created by Guido van Rossum', 'List is mutable in Python', 'HTTP status 404 means Not Found'"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "fact": {
                "type": "string",
                "description": "Verified fact jo permanently save karna hai. Clear aur concise likho."
            },
            "source": {
                "type": "string",
                "description": "Fact kahan se aaya: 'student' (student ne bataya), 'self' (khud verify kiya), 'web' (search se mila)",
                "enum": ["student", "self", "web"]
            }
        },
        "required": ["fact"]
    }
}

SWITCH_CURRICULUM_TOOL = {
    "name": "switch_curriculum",
    "description": (
        "Jab bhi student koi NAYI programming language seekhna chahe — "
        "'mujhe C# seekhni hai', 'Unity game banana hai', "
        "'C++ with Unreal Engine padhao', 'JavaScript seekhna hai', "
        "'web development seekhni hai' — toh yeh tool call karo. "
        "Yeh tool naya curriculum activate karega aur session restart hoga fresh context ke saath. "
        "Available curricula: python, csharp_unity, cpp_unreal, javascript. "
        "Action can be 'add' (add alongside existing) or 'switch' (make primary). "
        "Student bole 'bhi seekhni hai' toh action='add', bole 'sirf yeh padho' toh action='switch'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "curriculum_id": {
                "type": "string",
                "description": "Curriculum ID: 'python', 'csharp_unity', 'cpp_unreal', 'javascript'",
                "enum": ["python", "csharp_unity", "cpp_unreal", "javascript"]
            },
            "action": {
                "type": "string",
                "description": "'add' = add alongside current curricula, 'switch' = make this the primary curriculum",
                "enum": ["add", "switch"]
            }
        },
        "required": ["curriculum_id", "action"]
    }
}

ALL_TOOLS = [OPEN_APP_TOOL, GET_TIME_TOOL, SAVE_NOTES_TOOL, RUN_PYTHON_TOOL, SAVE_QUIZ_TOOL, WRITE_NOTEBOOK_TOOL, DISMISS_TERMINAL_TOOL, SEARCH_WEB_TOOL, FETCH_PAGE_TOOL, DRAW_DIAGRAM_TOOL, DISMISS_DIAGRAM_TOOL, REMEMBER_TOOL, LEARN_VERIFIED_FACT_TOOL, SWITCH_CURRICULUM_TOOL]

# ── Setup ─────────────────────────────────────────────────
def build_setup():
    """Build setup config with fresh memory context each session."""
    full_prompt = get_full_prompt()
    print(f"\n🧠 Memory loaded! Prompt size: {len(full_prompt)} chars")
    return {
        "setup": {
            "model": MODEL,
            "generation_config": {
                "temperature": 0.7,
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {"voice_name": "Aoede"}
                    }
                }
            },
            "input_audio_transcription":  {},   # User speech transcript
            "output_audio_transcription": {},   # CHAHAT speech transcript
            "system_instruction": {"parts": [{"text": full_prompt}]},
            "tools": [{"functionDeclarations": ALL_TOOLS}]
        }
    }


def enc(x):
    return json.dumps(x).encode()


# ── Tool Implementations ─────────────────────────────────

def tool_get_time() -> str:
    now = datetime.now()
    return (
        f"Current Time: {now.strftime('%I:%M %p')}, "
        f"Date: {now.strftime('%B %d, %Y')}, "
        f"Day: {now.strftime('%A')}"
    )


def tool_save_notes(title: str, content: str) -> str:
    """Save notes as both Markdown AND a beautiful PDF that mirrors the notebook UI."""
    from fpdf import FPDF
    import re
    import urllib.request

    # Sanitize filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip()
    safe_title = safe_title.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── 1. Save Markdown backup ──
    md_filename = f"{safe_title}_{timestamp}.md"
    md_filepath = os.path.join(NOTES_DIR, md_filename)
    md_content = f"# {title}\n"
    md_content += f"📅 *Saved on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n"
    md_content += f"👩‍🏫 *Teacher: CHAHAT*\n\n"
    md_content += "---\n\n"
    md_content += content
    md_content += "\n"
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    # ── 2. Generate beautiful PDF ──
    pdf_filename = f"{safe_title}_{timestamp}.pdf"
    pdf_filepath = os.path.join(NOTES_DIR, pdf_filename)

    # Download NotoSans font for full Unicode/Hindi support (cached)
    fonts_dir = os.path.join(BASE_DIR, "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    font_regular = os.path.join(fonts_dir, "NotoSans-Regular.ttf")
    font_bold = os.path.join(fonts_dir, "NotoSans-Bold.ttf")
    font_italic = os.path.join(fonts_dir, "NotoSans-Italic.ttf")
    font_mono = os.path.join(fonts_dir, "NotoSansMono-Regular.ttf")

    FONT_BASE = "https://github.com/google/fonts/raw/main/ofl"
    font_urls = {
        font_regular: f"{FONT_BASE}/notosans/NotoSans%5Bwdth%2Cwght%5D.ttf",
        font_bold: f"{FONT_BASE}/notosans/NotoSans%5Bwdth%2Cwght%5D.ttf",
        font_italic: f"{FONT_BASE}/notosans/NotoSans-Italic%5Bwdth%2Cwght%5D.ttf",
        font_mono: f"{FONT_BASE}/notosansmono/NotoSansMono%5Bwdth%2Cwght%5D.ttf",
    }

    for fpath, url in font_urls.items():
        if not os.path.exists(fpath):
            try:
                print(f"   📥 Downloading font: {os.path.basename(fpath)}...")
                urllib.request.urlretrieve(url, fpath)
            except Exception as e:
                print(f"   ⚠️ Font download failed: {e} — using built-in font")

    class NotebookPDF(FPDF):
        """Custom PDF that mirrors CHAHAT's notebook style."""

        def __init__(self, doc_title):
            super().__init__()
            self.doc_title = doc_title
            self._has_noto = False

            # Register NotoSans for Unicode support
            if os.path.exists(font_regular):
                try:
                    self.add_font("NotoSans", "", font_regular, uni=True)
                    self.add_font("NotoSans", "B", font_bold if os.path.exists(font_bold) else font_regular, uni=True)
                    self.add_font("NotoSans", "I", font_italic if os.path.exists(font_italic) else font_regular, uni=True)
                    self._has_noto = True
                except Exception:
                    pass

            if os.path.exists(font_mono):
                try:
                    self.add_font("NotoMono", "", font_mono, uni=True)
                except Exception:
                    pass

        def _f(self, style=""):
            """Get font family name."""
            return "NotoSans" if self._has_noto else "Helvetica"

        def _fm(self):
            """Get mono font family name."""
            return "NotoMono" if self._has_noto and os.path.exists(font_mono) else "Courier"

        def header(self):
            # Gradient-style header bar
            self.set_fill_color(92, 64, 51)  # Brown wood color
            self.rect(0, 0, 210, 22, "F")
            self.set_font(self._f(), "B", 14)
            self.set_text_color(245, 237, 219)
            self.set_y(4)
            self.cell(0, 14, f"  CHAHAT — Your AI Teacher", ln=True, align="L")
            self.ln(8)

        def footer(self):
            self.set_y(-15)
            self.set_font(self._f(), "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"CHAHAT Notes  |  Page {self.page_no()}/{{nb}}  |  {datetime.now().strftime('%B %d, %Y')}", align="C")

        def add_title(self, text):
            """Main document title — like notebook heading."""
            self.set_font(self._f(), "B", 22)
            self.set_text_color(26, 58, 92)  # ink-blue
            self.cell(0, 14, text, ln=True)
            # Date subtitle
            self.set_font(self._f(), "I", 10)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, f"Saved on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}  |  Teacher: CHAHAT", ln=True)
            # Divider line
            self.set_draw_color(232, 236, 240)
            self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
            self.ln(6)

        def add_heading(self, text, level=1):
            """Section heading with red left border — mirrors .hw-heading style."""
            self.ln(4)
            # Red left border
            y = self.get_y()
            self.set_fill_color(192, 57, 43)  # ink-red
            self.rect(10, y, 3, 10, "F")
            # Heading text
            size = {1: 18, 2: 15, 3: 13}.get(level, 13)
            self.set_font(self._f(), "B", size)
            self.set_text_color(192, 57, 43)
            self.set_x(17)
            self.multi_cell(0, 8, text)
            self.ln(2)

        def add_text(self, text):
            """Normal paragraph — mirrors .hw-text style."""
            self.set_font(self._f(), "", 11)
            self.set_text_color(26, 58, 92)  # ink-blue
            self.multi_cell(0, 6, text)
            self.ln(2)

        def add_bullet(self, text):
            """Bullet point — mirrors .hw-bullet style."""
            self.set_font(self._f(), "", 11)
            self.set_text_color(192, 57, 43)
            x = self.get_x()
            self.set_x(14)
            self.cell(6, 6, chr(8226))  # bullet char
            self.set_text_color(26, 58, 92)
            self.multi_cell(0, 6, text)
            self.ln(1)

        def add_code_block(self, code):
            """Code block — mirrors .hw-code dark style."""
            self.ln(2)
            # Dark background
            y_start = self.get_y()
            self.set_fill_color(30, 41, 59)  # dark slate
            # Calculate height needed
            self.set_font(self._fm(), "", 9)
            lines = code.split("\n")
            line_h = 5
            block_h = len(lines) * line_h + 10

            # Check if we need a new page
            if self.get_y() + block_h > self.h - 20:
                self.add_page()
                y_start = self.get_y()

            self.rect(10, y_start, 190, block_h, "F")

            # Border
            self.set_draw_color(51, 65, 85)
            self.rect(10, y_start, 190, block_h, "D")

            self.set_y(y_start + 4)
            self.set_text_color(226, 232, 240)  # light text on dark

            for line in lines:
                self.set_x(16)
                self.cell(0, line_h, line, ln=True)

            self.set_y(y_start + block_h + 2)
            self.ln(2)

    # ── Build the PDF ──
    try:
        pdf = NotebookPDF(title)
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Title
        pdf.add_title(title)

        # Parse the markdown content into blocks
        lines = content.split("\n")
        in_code = False
        code_lines = []

        for line in lines:
            stripped = line.strip()

            # Code block toggle
            if stripped.startswith("```"):
                if in_code:
                    # End of code block
                    pdf.add_code_block("\n".join(code_lines))
                    code_lines = []
                    in_code = False
                else:
                    in_code = True
                continue

            if in_code:
                code_lines.append(line)
                continue

            # Skip empty lines
            if not stripped:
                pdf.ln(2)
                continue

            # Headings
            if stripped.startswith("### "):
                pdf.add_heading(stripped[4:], level=3)
            elif stripped.startswith("## "):
                pdf.add_heading(stripped[3:], level=2)
            elif stripped.startswith("# "):
                pdf.add_heading(stripped[2:], level=1)
            # Bullet points
            elif stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("• "):
                bullet_text = stripped[2:]
                # Remove markdown bold/italic markers for clean PDF
                bullet_text = re.sub(r'\*\*(.+?)\*\*', r'\1', bullet_text)
                bullet_text = re.sub(r'\*(.+?)\*', r'\1', bullet_text)
                pdf.add_bullet(bullet_text)
            # Horizontal rule
            elif stripped in ("---", "***", "___"):
                pdf.set_draw_color(232, 236, 240)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)
            # Normal text
            else:
                # Remove markdown bold/italic markers
                clean = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
                clean = re.sub(r'\*(.+?)\*', r'\1', clean)
                # Remove emoji-only decorative lines? Keep them for expressiveness
                pdf.add_text(clean)

        # Flush any remaining code block
        if code_lines:
            pdf.add_code_block("\n".join(code_lines))

        pdf.output(pdf_filepath)
        print(f"   ✅ PDF generated: {pdf_filename}")
        return f"✅ Notes saved as PDF! File: {pdf_filename} (in notes/ folder) — EXACTLY notebook jaisa!"

    except Exception as e:
        print(f"   ⚠️ PDF generation failed: {e} — saving as Markdown only")
        return f"✅ Notes saved as Markdown! File: {md_filename} (in notes/ folder) — PDF generation failed: {e}"


def tool_run_python(code: str) -> str:
    """Run Python code in a sandboxed environment."""
    import ast

    # ═══════════════════════════════════════════════════════
    # LAYER 1: Static AST Analysis — Block dangerous code
    # ═══════════════════════════════════════════════════════

    BLOCKED_MODULES = {
        "os", "sys", "subprocess", "shutil", "signal", "ctypes",
        "socket", "http", "urllib", "requests", "pathlib",
        "importlib", "runpy", "code", "codeop", "compileall",
        "multiprocessing", "threading", "_thread",
        "pickle", "shelve", "marshal", "tempfile",
        "webbrowser", "antigravity", "turtle",
        "gc", "resource", "pty", "fcntl", "termios",
        "builtins", "__builtin__",
    }

    # Functions blocked at AST level (checked before code runs)
    BLOCKED_CALLS = {"exec", "eval", "compile", "breakpoint", "exit", "quit"}

    BLOCKED_PATTERNS = [
        "open(",           # File access
        ".__subclasses__", # Class introspection escape
        ".__bases__",      # Base class escape
        ".__mro__",        # MRO escape
        ".__globals__",    # Global namespace escape
        ".__code__",       # Code object manipulation
        ".__import__",     # Import bypass
        "rm -rf",          # Shell injection
        "rmdir",           # Directory deletion
        "unlink",          # File deletion
        "system(",         # Shell execution
    ]

    # Pattern check (fast string scan)
    code_lower = code.lower()
    for pat in BLOCKED_PATTERNS:
        if pat.lower() in code_lower:
            return f"🛡️ Security: '{pat}' is not allowed in sandbox mode.\n(Yeh educational sandbox hai — file system access aur system commands blocked hain.)"

    # AST-level deep scan
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"❌ Syntax Error: {e}\n\n(Code mein typo hai — fix karo!)"

    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_root = alias.name.split(".")[0]
                if mod_root in BLOCKED_MODULES:
                    return f"🛡️ Security: 'import {alias.name}' is blocked.\n(Module '{mod_root}' sandbox mein allowed nahi hai — educational code ke liye zaroorat nahi.)"

        if isinstance(node, ast.ImportFrom):
            if node.module:
                mod_root = node.module.split(".")[0]
                if mod_root in BLOCKED_MODULES:
                    return f"🛡️ Security: 'from {node.module} import ...' is blocked.\n(Module '{mod_root}' sandbox mein allowed nahi hai.)"

        # Check dangerous function calls (exec, eval, compile, etc.)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in BLOCKED_CALLS:
                return f"🛡️ Security: '{func.id}()' is not allowed.\n(Yeh function sandbox mein blocked hai.)"
            if isinstance(func, ast.Attribute) and func.attr in ("system", "popen", "exec", "remove", "rmtree", "unlink"):
                return f"🛡️ Security: '.{func.attr}()' is not allowed.\n(System commands sandbox mein blocked hain.)"

    # ═══════════════════════════════════════════════════════
    # LAYER 2: Runtime Sandbox — Block file writes only
    # ═══════════════════════════════════════════════════════
    # NOTE: We do NOT remove builtins like eval/exec/compile because
    # Python's own stdlib uses them internally (e.g., collections.namedtuple
    # uses eval, importlib uses exec). The AST scanner (Layer 1) already
    # catches all dangerous calls in student code BEFORE execution.

    sandbox_wrapper = '''
# Block open() for writing (allow reading only for educational purposes)
import builtins as _builtins
_original_open = _builtins.open
def _safe_open(file, mode="r", *args, **kwargs):
    if any(m in str(mode) for m in ("w", "a", "x", "+")):
        raise PermissionError("File writing is not allowed in sandbox mode")
    return _original_open(file, mode, *args, **kwargs)
_builtins.open = _safe_open

# Now run the student's code
'''

    sandboxed_code = sandbox_wrapper + code

    # ═══════════════════════════════════════════════════════
    # LAYER 3: Process Isolation — Timeout + resource limits
    # ═══════════════════════════════════════════════════════

    try:
        result = subprocess.run(
            [sys.executable, "-c", sandboxed_code],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env={
                "PATH": os.environ.get("PATH", ""),
                "HOME": os.environ.get("HOME", ""),
                "LANG": os.environ.get("LANG", "en_US.UTF-8"),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
            }
        )
        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode == 0:
            return f"✅ Output:\n{output}" if output else "✅ Code ran successfully (no output)"
        else:
            # Clean up sandbox internals from error message
            clean_error = "\n".join(
                line for line in error.split("\n")
                if "_SandboxImporter" not in line and "_safe_open" not in line
            )
            return f"❌ Error aaya:\n{clean_error}\n\n(Koi baat nahi — galtiyan hoti hain, fix karte hain!)"
    except subprocess.TimeoutExpired:
        return "⏰ Code 10 second se zyada chal raha tha — infinite loop toh nahi hai?"
    except Exception as e:
        return f"❌ Could not run code: {e}"


def tool_save_quiz(topic: str, questions: str) -> str:
    """Save a quiz to the notes directory."""
    safe_topic = "".join(c if c.isalnum() or c in " -_" else "" for c in topic).strip()
    safe_topic = safe_topic.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Quiz_{safe_topic}_{timestamp}.md"
    filepath = os.path.join(NOTES_DIR, filename)

    md = f"# 📝 Quiz: {topic}\n"
    md += f"📅 *Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n"
    md += f"👩‍🏫 *By: CHAHAT*\n\n"
    md += "---\n\n"
    md += questions
    md += "\n\n---\n*Answers check karo aur dekho kitne sahi aaye! 💪*\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)

    return f"✅ Quiz saved! File: {filename} (in notes/ folder)"


# ── Transcript extract ────────────────────────────────────
def get_user_transcript(msg: dict) -> str:
    sc = msg.get("serverContent", {})

    # Primary key — newer API
    t = sc.get("inputTranscription", {})
    if isinstance(t, dict) and t.get("text", "").strip():
        return t["text"].strip()

    # Alternate key — older API versions
    t2 = sc.get("inputTranscript", "")
    if isinstance(t2, str) and t2.strip():
        return t2.strip()

    return ""


# ── App name extract (transcript fallback) ────────────────
def extract_app_name(transcript: str) -> str | None:
    text = transcript.lower().strip()

    TRIGGERS = [
        "open", "launch", "start", "run",
        "kholo", "kholdo", "khol do", "khol",
        "chalao", "chalaao", "chala", "chalu karo",
        "launch karo", "launch kro",
        "shuru karo", "shuru kro",
        "run karo", "run kro",
    ]

    KNOWN_APPS = sorted(
        list(APP_ALIASES.keys()),
        key=len, reverse=True
    )

    triggered_text = None
    for trigger in TRIGGERS:
        if trigger in text:
            after = text.split(trigger, 1)[-1].strip()
            for filler in ["please", "kar", "karo", "kro", "do", "na",
                           "zara", "bhai", "yaar", "jaan", "baby"]:
                after = after.replace(filler, "").strip()
            triggered_text = after
            break

    if not triggered_text:
        return None

    for app in KNOWN_APPS:
        if app in triggered_text:
            return app

    words = triggered_text.split()
    return words[0] if words else None


# ── Session Logger ────────────────────────────────────────
class SessionLogger:
    """Saves every teaching session as a markdown transcript."""

    def __init__(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = os.path.join(SESSIONS_DIR, f"session_{ts}.md")
        self._lines = []
        self._add(f"# 📚 CHAHAT Teaching Session")
        self._add(f"📅 *{datetime.now().strftime('%B %d, %Y — %I:%M %p')}*\n")
        self._add("---\n")
        self._flush()

    def student(self, text: str):
        self._add(f"**🗣️ Student:** {text}")
        self._flush()

    def teacher(self, text: str):
        self._add(f"**👩‍🏫 CHAHAT:** {text}")
        self._flush()

    def tool(self, name: str, result: str):
        self._add(f"*🔧 Tool [{name}]: {result}*")
        self._flush()

    def _add(self, line: str):
        self._lines.append(line)

    def _flush(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(self._lines))
                f.write("\n")
        except Exception:
            pass


# ── Global reference for cross-thread access ─────────────
_chahat_instance = None

# ── Main CHAHAT class ────────────────────────────────────
class CHAHAT:
    def __init__(self):
        global _chahat_instance
        self.running  = True
        self._ws      = None
        self.logger   = SessionLogger()
        self._speaking = threading.Event()  # Echo cancellation flag
        self._memory  = None  # LiveMemory instance per session
        _chahat_instance = self  # Store for cross-thread access

    def force_reconnect(self):
        """Force-close the WebSocket so the reconnect loop rebuilds with fresh memory."""
        if self._ws:
            try:
                import asyncio
                asyncio.get_event_loop().call_soon_threadsafe(
                    lambda: asyncio.ensure_future(self._ws.close())
                )
            except Exception:
                # Fallback: just set ws to None, the recv loop will raise and reconnect
                try:
                    self._ws.transport.close()
                except Exception:
                    pass
            print("🔄 Memory changed — reconnecting with fresh context...")

    async def start(self):
        print("=" * 50)
        print("  📚 CHAHAT — Your AI Teacher")
        print("  🎤 Bolo kuch bhi — main samjhaungi!")
        print("  🖥️  Desktop UI running")
        print("=" * 50)
        print()

        retry = 0
        while self.running:
            try:
                await self._session()
                retry = 0
            except Exception as e:
                retry += 1
                wait = min(2 ** retry, 30)
                print(f"[CHAHAT] Error: {e} — {wait}s mein reconnect...")
                await asyncio.sleep(wait)

    async def _session(self):
        async with websockets.connect(
            f"{WS_URL}?key={API_KEY}",
            max_size=None,
            ping_interval=20,
            ping_timeout=30,
            compression=None,
        ) as ws:
            self._ws = ws
            print("✅ Connected to CHAHAT")

            # Build setup with fresh memory context each reconnect
            setup = build_setup()
            await ws.send(enc(setup))
            await ws.recv()
            print("✅ Setup complete — ab bolo, kya seekhna hai! 📚\n")

            # Start real-time memory tracking for this session
            self._memory = LiveMemory()
            print("🧠 LiveMemory started — tracking in real-time!")

            import queue as _queue
            audio_q   = _queue.Queue()
            play_stop = asyncio.Event()

            def _play_thread():
                BUF = int(SPK_RATE * 0.20)
                buf = np.array([], dtype=np.float32)
                stream = sd.OutputStream(
                    samplerate=SPK_RATE, channels=1,
                    dtype="float32", blocksize=BUF, latency="high"
                )
                stream.start()
                while not play_stop.is_set():
                    try:
                        chunk = audio_q.get(timeout=0.20)
                        if chunk is None:
                            continue
                        buf = np.concatenate([buf, chunk])
                        while len(buf) >= BUF:
                            stream.write(buf[:BUF])
                            buf = buf[BUF:]
                    except _queue.Empty:
                        # Queue drained — flush remaining audio and unmute
                        if len(buf) > 0:
                            pad = np.zeros(BUF - len(buf), dtype=np.float32)
                            stream.write(np.concatenate([buf, pad]))
                            buf = np.array([], dtype=np.float32)
                        # Small cooldown so speaker sound dissipates before unmuting
                        import time
                        time.sleep(0.25)
                        self._speaking.clear()  # Mic mute OFF
                stream.stop(); stream.close()

            import threading
            play_t = threading.Thread(target=_play_thread, daemon=True)
            play_t.start()

            try:
                await asyncio.gather(
                    self._send_audio(ws),
                    self._send_text(ws),
                    self._recv(ws, audio_q),
                )
            finally:
                play_stop.set()
                audio_q.put(None)
                play_t.join(timeout=2.0)
                # Finalize memory for this session
                try:
                    if self._memory:
                        self._memory.on_session_end()
                    print("🧠 Memory saved to SQLite for next session!")
                except Exception as e:
                    print(f"⚠️ Memory save failed: {e}")
                # Close Chrome driver if it was used
                try:
                    cleanup_driver()
                except Exception:
                    pass

    async def _send_audio(self, ws):
        SILENCE = bytes(FRAMES * 2)  # 16-bit silence frame
        cooldown = 0                 # Post-speech cooldown counter
        COOLDOWN_FRAMES = 25         # ~500ms of silence after CHAHAT stops
        was_speaking = False

        with sd.InputStream(
            samplerate=MIC_RATE, channels=1,
            dtype="int16", blocksize=FRAMES, latency="low"
        ) as mic:
            print("🎤 Listening...")
            while self.running:
                pcm, _ = mic.read(FRAMES)

                # User manually muted the mic via UI toggle
                if MIC_MUTED.is_set():
                    data = base64.b64encode(SILENCE).decode()
                elif self._speaking.is_set():
                    # CHAHAT is speaking — send silence, mute mic
                    data = base64.b64encode(SILENCE).decode()
                    was_speaking = True
                    cooldown = COOLDOWN_FRAMES
                elif cooldown > 0:
                    # CHAHAT just stopped — keep sending silence during cooldown
                    # This prevents echo from the last words
                    data = base64.b64encode(SILENCE).decode()
                    cooldown -= 1
                    if cooldown == 0:
                        was_speaking = False
                        # Flush mic buffer by reading and discarding
                        try:
                            mic.read(FRAMES)
                        except Exception:
                            pass
                else:
                    # Normal — send real mic audio
                    data = base64.b64encode(pcm.tobytes()).decode()

                await ws.send(enc({
                    "realtimeInput": {
                        "audio": {
                            "mimeType": "audio/pcm;rate=16000",
                            "data": data
                        }
                    }
                }))
                await asyncio.sleep(0.001)

    async def _send_text(self, ws):
        """Poll TEXT_QUEUE for typed/pasted student input and send to Gemini."""
        while self.running:
            try:
                text = TEXT_QUEUE.get_nowait()
                if text:
                    print(f"⌨️ Student (typed): {text[:80]}{'...' if len(text) > 80 else ''}")
                    self.logger.student(text)
                    ui_push({"type": "student", "text": text})
                    await ws.send(enc({
                        "clientContent": {
                            "turns": [{
                                "role": "user",
                                "parts": [{"text": text}]
                            }],
                            "turnComplete": True
                        }
                    }))
            except Exception:
                pass
            await asyncio.sleep(0.1)

    async def _recv(self, ws, audio_q):
        while self.running:
            try:
                raw = await ws.recv()
                msg = json.loads(raw)
            except websockets.exceptions.ConnectionClosed:
                break

            # ── Handle Tool Calls ──
            for call in msg.get("toolCall", {}).get("functionCalls", []):
                name = call.get("name", "")
                args = call.get("args", {})
                call_id = call.get("id", "")

                result = ""

                if name == "open_app":
                    app_name = args.get("app_name", "")
                    print(f"🔧 Tool: open_app('{app_name}')")
                    result = open_app(app_name)

                elif name == "get_time":
                    print(f"🔧 Tool: get_time()")
                    result = tool_get_time()

                elif name == "save_notes":
                    title = args.get("title", "Untitled Notes")
                    content = args.get("content", "")
                    print(f"📝 Tool: save_notes('{title}')")
                    result = tool_save_notes(title, content)

                elif name == "run_python":
                    code = args.get("code", "")
                    print(f"🐍 Tool: run_python()")
                    print(f"   Code: {code[:100]}{'...' if len(code) > 100 else ''}")
                    result = tool_run_python(code)

                elif name == "save_quiz":
                    topic = args.get("topic", "General")
                    questions = args.get("questions", "")
                    print(f"📝 Tool: save_quiz('{topic}')")
                    result = tool_save_quiz(topic, questions)

                elif name == "write_notebook":
                    content = args.get("content", "")
                    print(f"✏️ Tool: write_notebook()")
                    print(f"   Content: {content[:80]}...")
                    # Send directly to notebook UI
                    ui_push({"type": "notebook", "content": content})
                    result = "✅ Notebook par likh diya!"

                elif name == "dismiss_terminal":
                    print(f"🖥️ Tool: dismiss_terminal()")
                    ui_push({"type": "dismiss_terminal"})
                    result = "✅ Terminal hata diya! Notebook wapas aa gaya."

                elif name == "search_web":
                    query = args.get("query", "")
                    print(f"🌐 Tool: search_web('{query}')")
                    result = search_web(query)

                elif name == "fetch_page":
                    url = args.get("url", "")
                    print(f"📄 Tool: fetch_page('{url[:60]}')")
                    result = fetch_page(url)

                elif name == "draw_diagram":
                    title = args.get("title", "Diagram")
                    code = args.get("code", "")
                    dtype = args.get("diagram_type", "mermaid")
                    print(f"🎨 Tool: draw_diagram('{title}', type={dtype})")
                    print(f"   Code: {code[:100]}...")
                    ui_push({"type": "diagram", "code": code, "diagram_type": dtype, "title": title})
                    result = f"✅ Whiteboard par '{title}' diagram draw kar diya!"

                elif name == "dismiss_diagram":
                    print(f"🎨 Tool: dismiss_diagram()")
                    ui_push({"type": "dismiss_diagram"})
                    result = "✅ Diagram hata diya! Notebook wapas aa gaya."

                elif name == "remember":
                    cat = args.get("category", "personal")
                    content = args.get("content", "")
                    imp = args.get("importance", 5)
                    print(f"💾 Tool: remember('{cat}', '{content[:60]}'...)")
                    if self._memory:
                        result = self._memory.remember_fact(cat, content, imp)
                    else:
                        result = "⚠️ Memory not initialized"

                elif name == "learn_verified_fact":
                    fact = args.get("fact", "")
                    source = args.get("source", "student")
                    print(f"🔒 Tool: learn_verified_fact('{fact[:60]}'...)")
                    from memory import store_verified_fact
                    result = store_verified_fact(fact, source)

                elif name == "switch_curriculum":
                    cid = args.get("curriculum_id", "python")
                    action = args.get("action", "add")
                    print(f"🔀 Tool: switch_curriculum('{cid}', action='{action}')")
                    from memory import set_active_curriculum
                    make_primary = (action == "switch")
                    result = set_active_curriculum(cid, make_primary=make_primary)
                    # Force reconnect so prompt rebuilds with new curriculum
                    if "✅" in result:
                        print("🔄 Curriculum changed — will reconnect with fresh prompt...")
                        # Reconnect happens after tool response is sent
                        asyncio.get_event_loop().call_later(2.0, self.force_reconnect)

                else:
                    result = f"Unknown tool: {name}"

                print(f"   Result: {result}")
                self.logger.tool(name, result)

                # Track tool usage in live memory
                if self._memory:
                    self._memory.on_tool_used(name, args, result)

                # For run_python, include code so terminal UI can display it
                tool_event = {"type": "tool", "name": name, "result": result}
                if name == "run_python":
                    tool_event["code"] = args.get("code", "")
                ui_push(tool_event)

                # Send tool response back to Gemini
                await ws.send(enc({
                    "toolResponse": {
                        "functionResponses": [{
                            "id": call_id,
                            "name": name,
                            "response": {"result": result}
                        }]
                    }
                }))


            # ── User speech transcript ──
            transcript = get_user_transcript(msg)
            if transcript:
                print(f"🗣️ Student: {transcript}")
                self.logger.student(transcript)
                ui_push({"type": "student", "text": transcript})
                # Real-time memory tracking
                if self._memory:
                    self._memory.on_student_speech(transcript)

                # Transcript fallback for app opening
                app_name = extract_app_name(transcript)
                if app_name:
                    print(f"📱 Transcript fallback: open_app('{app_name}')")
                    result = open_app(app_name)
                    print(f"   Result: {result}")

            # ── CHAHAT speech transcript ──
            sc = msg.get("serverContent", {})
            chahat_text = sc.get("outputTranscription", {})
            if isinstance(chahat_text, dict) and chahat_text.get("text", "").strip():
                chahat_speech = chahat_text['text'].strip()
                print(f"👩‍🏫 CHAHAT: {chahat_speech}")
                self.logger.teacher(chahat_speech)
                ui_push({"type": "teacher", "text": chahat_speech})
                # Real-time memory tracking
                if self._memory:
                    self._memory.on_teacher_speech(chahat_speech)

            # ── Audio playback ──
            for part in sc.get("modelTurn", {}).get("parts", []):
                d = part.get("inlineData")
                if d and "audio/pcm" in d.get("mimeType", ""):
                    # Mute mic IMMEDIATELY when audio arrives
                    self._speaking.set()
                    raw_bytes = base64.b64decode(d["data"])
                    pcm = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                    try:
                        audio_q.put_nowait(pcm)
                    except Exception:
                        pass


# ── Run ───────────────────────────────────────────────
def _run_chahat_thread():
    """Run CHAHAT's async loop in a background thread."""
    async def _start():
        chahat = CHAHAT()
        ui_push({"type": "connected"})
        await chahat.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


def _pdf_worker_thread():
    """Background thread that polls PDF_QUEUE and generates PDFs."""
    import time
    while True:
        try:
            save_req = PDF_QUEUE.get(timeout=1.0)
            title = save_req.get("title", "CHAHAT_Notes")
            content = save_req.get("content", "")
            if content.strip():
                print(f"\n📄 Generating PDF: {title}")
                result = tool_save_notes(title, content)
                print(f"   {result}")
                ui_push({"type": "tool", "name": "save_pdf", "result": result})
        except Exception:
            pass  # Queue.get timeout — normal


def _memory_worker_thread():
    """Background thread that polls MEMORY_CMD_QUEUE and manages the database."""
    import memory
    import time
    needs_reconnect = False
    while True:
        try:
            cmd = MEMORY_CMD_QUEUE.get(timeout=0.5)
            action = cmd.get("action")
            
            if action == "fetch":
                # Get fresh data and push to UI
                data = memory.get_dashboard_data()
                ui_push({"type": "dashboard_data", "payload": data})
                
            elif action == "update_profile":
                name = cmd.get("name")
                level = cmd.get("level")
                memory.update_student_profile(name, level)
                print(f"💾 Profile updated: {name} ({level})")
                needs_reconnect = True
                
            elif action == "delete_topic":
                topic = cmd.get("name")
                memory.delete_topic_memory(topic)
                print(f"🗑️ Deleted topic memory: {topic}")
                needs_reconnect = True
                
            elif action == "delete_memory":
                mem_id = cmd.get("id")
                memory.delete_explicit_memory(mem_id)
                print(f"🗑️ Deleted explicit memory ID: {mem_id}")
                needs_reconnect = True
                
        except Exception:
            # Queue.get timeout — check if we need to reconnect
            # We batch: wait for the queue to drain before reconnecting
            if needs_reconnect and _chahat_instance:
                time.sleep(1.0)  # Wait a moment for any remaining dashboard edits
                _chahat_instance.force_reconnect()
                needs_reconnect = False


if __name__ == "__main__":
    # 1. Start CHAHAT in a background thread
    chahat_thread = threading.Thread(target=_run_chahat_thread, daemon=True)
    chahat_thread.start()

    # 2. Start PDF worker thread
    pdf_thread = threading.Thread(target=_pdf_worker_thread, daemon=True)
    pdf_thread.start()

    # 3. Start Memory worker thread
    mem_thread = threading.Thread(target=_memory_worker_thread, daemon=True)
    mem_thread.start()

    # 4. Run PyQt5 UI on main thread (required by Qt)
    app, window = run_ui()
    sys.exit(app.exec_())