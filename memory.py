# memory.py — CHAHAT Advanced Memory System v2.0
# ✅ SQLite-backed persistent storage (replaces flat JSON)
# ✅ Smart topic extraction via keyword scoring (not hardcoded if-else)
# ✅ Per-topic mastery tracking with spaced repetition
# ✅ Multi-session history with intelligent summarization
# ✅ Student profile & emotional state tracking
# ✅ Real-time memory hooks (updates DURING session, not just at end)
# ✅ Smart context window (prioritized, token-aware)
# ✅ Key moments tracking (breakthroughs, struggles, questions)

import sqlite3
import json
import os
import re
import threading
from datetime import datetime, timedelta
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
NOTES_DIR = os.path.join(BASE_DIR, "notes")
MEMORY_DB = os.path.join(BASE_DIR, "memory.db")
LEGACY_MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")

_db_lock = threading.Lock()

# ═════════════════════════════════════════════════════════
# MULTI-LANGUAGE CURRICULA REGISTRY
# ═════════════════════════════════════════════════════════

CURRICULA = {
    "python": {
        "name": "Python",
        "icon": "🐍",
        "description": "Python programming — beginner to advanced, plus specializations",
        "run_command": "python3",
        "file_ext": ".py",
        "topic_keywords": {
            "Python Basics & Setup": ["python", "install", "setup", "ide", "pycharm", "vscode", "hello world", "interpreter"],
            "Variables & Data Types": ["variable", "data type", "int", "float", "str", "bool", "type casting", "type conversion", "dynamic typing", "mutable", "immutable"],
            "Operators": ["operator", "arithmetic", "comparison", "logical", "bitwise", "modulo", "floor division"],
            "Strings": ["string", "f-string", "format", "slicing", "split", "join", "strip", "replace", "substring"],
            "Input/Output": ["input", "output", "print", "stdin", "stdout"],
            "Conditionals": ["if", "elif", "else", "condition", "ternary", "match case"],
            "Loops": ["loop", "for", "while", "break", "continue", "range", "enumerate", "iteration"],
            "Lists": ["list", "append", "extend", "pop", "remove", "sort", "sorted", "list comprehension"],
            "Tuples": ["tuple", "namedtuple", "packing", "unpacking"],
            "Sets": ["set", "union", "intersection", "difference", "frozenset"],
            "Dictionaries": ["dictionary", "dict", "key", "value", "items", "keys", "values", "defaultdict"],
            "Comprehensions": ["comprehension", "list comprehension", "dict comprehension", "set comprehension"],
            "Functions": ["function", "def", "return", "parameter", "argument", "args", "kwargs", "scope", "lambda", "recursion"],
            "Error Handling": ["error", "exception", "try", "except", "finally", "raise", "traceback"],
            "File Handling": ["file", "open", "read", "write", "context manager", "csv", "json file"],
            "Modules & Packages": ["module", "package", "import", "pip", "venv", "virtual environment"],
            "OOP Basics": ["class", "object", "oop", "init", "self", "method", "attribute", "instance", "constructor"],
            "OOP Advanced": ["inheritance", "polymorphism", "encapsulation", "abstraction", "super", "mro", "abc"],
            "Magic Methods": ["dunder", "magic method", "__str__", "__repr__", "__len__", "__add__", "__eq__"],
            "Iterators & Generators": ["iterator", "generator", "yield", "next", "iter"],
            "Decorators": ["decorator", "wrapper", "functools", "property", "staticmethod", "classmethod"],
            "Regular Expressions": ["regex", "regular expression", "re module", "match", "findall", "pattern"],
            "Collections Module": ["counter", "defaultdict", "ordereddict", "deque", "namedtuple"],
            "Date & Time": ["datetime", "timedelta", "strftime", "strptime", "timezone"],
            "Testing": ["test", "unittest", "pytest", "assert", "mock", "tdd"],
            "Concurrency": ["thread", "threading", "multiprocessing", "async", "await", "asyncio", "gil"],
            "Memory Management": ["memory", "garbage collection", "gc", "reference counting", "slots"],
            "Design Patterns": ["design pattern", "singleton", "factory", "observer", "strategy"],
            "Type Hints": ["type hint", "typing", "mypy", "annotation", "optional", "union"],
            "Dataclasses": ["dataclass", "attrs", "field", "frozen"],
            "Performance": ["performance", "optimization", "profiling", "cprofile", "timeit", "big o"],
            "Web Development": ["fastapi", "django", "flask", "web", "api", "rest", "endpoint"],
            "Data Science": ["numpy", "pandas", "matplotlib", "dataframe", "visualization"],
            "Database": ["database", "sql", "sqlite", "postgresql", "sqlalchemy", "orm"],
            "Web Scraping": ["scraping", "beautifulsoup", "scrapy", "selenium"],
        },
        "roadmap": [
            {"phase": "Phase 1 — Foundation", "level": "Beginner ⭐", "color": "🟢", "topics": [
                "Python setup, IDE, pehla program", "Variables, Data Types, Type Casting",
                "Operators (Arithmetic, Comparison, Logical, Bitwise)", "Strings (methods, formatting, slicing)",
                "Input/Output", "Conditionals (if/elif/else, ternary)",
                "Loops (for, while, break, continue, else clause)",
                "Lists, Tuples, Sets, Dictionaries (CRUD + methods)", "List/Dict/Set Comprehensions",
                "Functions (args, kwargs, return, scope, docstrings)",
                "Error Handling (try/except/finally/raise)",
                "File Handling (read, write, append, context managers)",
                "Modules and Packages (import system, pip, venv)"
            ], "project": "To-Do List CLI app, Calculator, Simple Quiz Game"},
            {"phase": "Phase 2 — Intermediate", "level": "Intermediate ⭐⭐⭐", "color": "🟡", "topics": [
                "OOP (Classes, Objects, __init__, self)",
                "Inheritance, Polymorphism, Encapsulation, Abstraction",
                "Magic/Dunder Methods (__str__, __repr__, __len__, etc.)",
                "Iterators and Generators (yield, generator expressions)",
                "Decorators (function & class decorators)", "Lambda, Map, Filter, Reduce",
                "Regular Expressions (re module)", "Working with JSON, CSV, XML",
                "Date & Time (datetime, timedelta)",
                "Collections module (Counter, defaultdict, deque, namedtuple)",
                "Virtual Environments & Dependency Management",
                "Unit Testing (unittest, pytest basics)", "Logging"
            ], "project": "Student Management System with OOP, File-based Database"},
            {"phase": "Phase 3 — Advanced", "level": "Advanced ⭐⭐⭐⭐⭐", "color": "🔴", "topics": [
                "Advanced OOP (Metaclasses, Descriptors, ABC)",
                "Context Managers (custom __enter__/__exit__)",
                "Concurrency (Threading, Multiprocessing, asyncio)",
                "Memory Management & Garbage Collection", "Design Patterns in Python",
                "Type Hints & mypy", "Closures & Scope (LEGB rule deep dive)",
                "*args/**kwargs advanced patterns", "Dataclasses & attrs",
                "Slots, Properties, Class methods vs Static methods",
                "Walrus Operator, Match-Case (3.10+)",
                "Performance Optimization & Profiling (cProfile, timeit)"
            ], "project": None},
            {"phase": "Phase 4 — Specialization & Projects", "level": "Expert 🚀", "color": "🚀", "topics": [
                "Web Dev (FastAPI / Django / Flask)", "Data Science (NumPy, Pandas, Matplotlib)",
                "Automation & Scripting", "API Development & Consumption",
                "Database Integration (SQLite, PostgreSQL, SQLAlchemy)",
                "Web Scraping (BeautifulSoup, Scrapy)", "GUI Development (Tkinter, PyQt basics)",
                "Deployment (Docker basics, CI/CD)"
            ], "project": None},
        ],
    },
    "csharp_unity": {
        "name": "C# with Unity",
        "icon": "🎮",
        "description": "C# programming for game development with Unity Engine",
        "run_command": "dotnet-script",
        "file_ext": ".cs",
        "topic_keywords": {
            "C# Basics & Setup": ["c#", "csharp", "dotnet", ".net", "visual studio", "hello world", "console"],
            "C# Variables & Types": ["variable", "int", "float", "double", "string", "bool", "char", "var", "const", "static typing", "value type", "reference type"],
            "C# Operators": ["operator", "arithmetic", "comparison", "logical", "ternary", "null coalescing"],
            "C# Strings": ["string", "interpolation", "format", "substring", "stringbuilder", "concat"],
            "C# Control Flow": ["if", "else", "switch", "case", "ternary", "pattern matching"],
            "C# Loops": ["loop", "for", "foreach", "while", "do while", "break", "continue"],
            "C# Arrays & Collections": ["array", "list", "dictionary", "hashset", "queue", "stack", "linkedlist", "collection", "generic"],
            "C# Functions & Methods": ["method", "function", "return", "parameter", "ref", "out", "params", "overload", "static method"],
            "C# OOP": ["class", "object", "constructor", "property", "encapsulation", "access modifier", "public", "private", "protected"],
            "C# Inheritance & Polymorphism": ["inheritance", "polymorphism", "virtual", "override", "abstract", "interface", "sealed"],
            "C# Advanced OOP": ["delegate", "event", "lambda", "linq", "generic", "extension method"],
            "C# Error Handling": ["exception", "try", "catch", "finally", "throw", "custom exception"],
            "C# Async": ["async", "await", "task", "coroutine", "thread", "concurrent"],
            "Unity Basics": ["unity", "gameobject", "component", "transform", "scene", "prefab", "inspector", "hierarchy"],
            "Unity Scripting": ["monobehaviour", "start", "update", "awake", "fixedupdate", "getcomponent", "instantiate", "destroy"],
            "Unity Physics": ["rigidbody", "collider", "trigger", "raycast", "physics", "force", "velocity", "gravity"],
            "Unity UI": ["canvas", "button", "text", "image", "panel", "ui", "eventsystem", "tmpro"],
            "Unity Animation": ["animation", "animator", "animation controller", "blend tree", "animation clip", "keyframe"],
            "Unity 2D": ["sprite", "tilemap", "2d physics", "sprite renderer", "2d collider", "pixel perfect"],
            "Unity 3D": ["mesh", "material", "shader", "lighting", "camera", "terrain", "skybox", "3d model"],
            "Unity Audio": ["audio source", "audio clip", "audio mixer", "sound", "music", "sfx"],
            "Unity Networking": ["multiplayer", "netcode", "photon", "mirror", "rpc", "server", "client"],
            "Game Design Patterns": ["singleton", "observer", "state machine", "object pool", "command pattern", "mvc"],
        },
        "roadmap": [
            {"phase": "Phase 1 — C# Foundation", "level": "Beginner ⭐", "color": "🟢", "topics": [
                "C# setup, Visual Studio, pehla program", "Variables, Data Types, Type System",
                "Operators & Expressions", "Strings & String Interpolation",
                "Control Flow (if/else, switch, pattern matching)",
                "Loops (for, foreach, while, do-while)",
                "Arrays & Collections (List, Dictionary, HashSet)",
                "Methods, Parameters, ref/out/params", "Error Handling (try/catch/finally)",
                "Basic OOP (Classes, Objects, Constructors, Properties)"
            ], "project": "Console-based Quiz Game, Calculator"},
            {"phase": "Phase 2 — Advanced C# + Unity Intro", "level": "Intermediate ⭐⭐⭐", "color": "🟡", "topics": [
                "Inheritance, Polymorphism, Interfaces, Abstract Classes",
                "Delegates, Events, Lambda Expressions", "LINQ (Language Integrated Query)",
                "Generics & Extension Methods", "Async/Await & Tasks",
                "Unity Installation & Interface", "GameObjects, Components, Transforms",
                "MonoBehaviour Lifecycle (Start, Update, Awake)",
                "Unity Physics (Rigidbody, Colliders, Triggers)",
                "Basic Player Movement & Input System"
            ], "project": "Simple 2D Platformer with Player Movement"},
            {"phase": "Phase 3 — Unity Game Development", "level": "Advanced ⭐⭐⭐⭐⭐", "color": "🔴", "topics": [
                "Unity UI System (Canvas, Buttons, TMP)", "Animation & Animator Controller",
                "2D Game Development (Sprites, Tilemaps)", "3D Basics (Meshes, Materials, Lighting)",
                "Audio System (SFX, Music)", "Scene Management & Loading",
                "Scriptable Objects & Data Management",
                "Game Design Patterns (Singleton, Observer, State Machine, Object Pool)",
                "Particle Systems & VFX", "AI & Pathfinding (NavMesh)"
            ], "project": "Complete 2D/3D Game with Menu, Levels, Score System"},
            {"phase": "Phase 4 — Publishing & Advanced", "level": "Expert 🚀", "color": "🚀", "topics": [
                "Multiplayer Networking (Netcode/Photon/Mirror)",
                "Mobile Build & Optimization", "Performance Profiling",
                "Shader Basics & Visual Effects", "Asset Store & Packages",
                "Publishing to Steam/Play Store/App Store",
                "Version Control with Git for Unity", "Level Design & Game Feel"
            ], "project": None},
        ],
    },
    "cpp_unreal": {
        "name": "C++ with Unreal Engine",
        "icon": "⚙️",
        "description": "C++ programming for AAA game development with Unreal Engine",
        "run_command": "g++",
        "file_ext": ".cpp",
        "topic_keywords": {
            "C++ Basics & Setup": ["c++", "cpp", "gcc", "g++", "compiler", "visual studio", "hello world", "iostream"],
            "C++ Variables & Types": ["variable", "int", "float", "double", "char", "bool", "auto", "const", "constexpr", "static typing", "pointer", "reference"],
            "C++ Operators": ["operator", "arithmetic", "comparison", "logical", "bitwise", "operator overloading"],
            "C++ Strings": ["string", "cstring", "char array", "string stream", "substring"],
            "C++ Control Flow": ["if", "else", "switch", "case", "ternary"],
            "C++ Loops": ["loop", "for", "while", "do while", "range based for", "break", "continue"],
            "C++ Arrays & Containers": ["array", "vector", "map", "unordered_map", "set", "stack", "queue", "deque", "stl", "container"],
            "C++ Functions": ["function", "return", "parameter", "overload", "default parameter", "inline", "template function"],
            "C++ Pointers & Memory": ["pointer", "reference", "new", "delete", "malloc", "free", "smart pointer", "unique_ptr", "shared_ptr", "memory management", "heap", "stack memory", "raii"],
            "C++ OOP": ["class", "object", "constructor", "destructor", "encapsulation", "access specifier", "public", "private", "protected", "this pointer"],
            "C++ Inheritance": ["inheritance", "polymorphism", "virtual", "override", "abstract", "pure virtual", "vtable", "multiple inheritance"],
            "C++ Templates & STL": ["template", "stl", "algorithm", "iterator", "generic programming", "template specialization"],
            "C++ Modern Features": ["c++11", "c++14", "c++17", "c++20", "auto", "lambda", "move semantics", "rvalue", "constexpr", "structured bindings"],
            "C++ Error Handling": ["exception", "try", "catch", "throw", "noexcept"],
            "Unreal Basics": ["unreal", "unreal engine", "ue5", "blueprint", "actor", "pawn", "character", "level", "editor"],
            "Unreal C++ Scripting": ["uclass", "uproperty", "ufunction", "aactor", "uobject", "gameplay framework", "tick", "beginplay"],
            "Unreal Physics & Collision": ["physics", "collision", "sweep", "trace", "line trace", "hit result"],
            "Unreal Materials & Rendering": ["material", "shader", "texture", "lighting", "post process", "niagara", "lumen", "nanite"],
            "Unreal AI": ["behavior tree", "blackboard", "ai controller", "navigation", "eqs", "perception"],
            "Unreal Multiplayer": ["replication", "rpc", "dedicated server", "net mode", "multiplayer"],
        },
        "roadmap": [
            {"phase": "Phase 1 — C++ Foundation", "level": "Beginner ⭐", "color": "🟢", "topics": [
                "C++ setup, Compiler, pehla program", "Variables, Data Types, Const/Constexpr",
                "Operators & Expressions", "Strings (std::string, C-strings)",
                "Control Flow (if/else, switch)", "Loops (for, while, range-based for)",
                "Arrays & Vectors", "Functions, Overloading, Default Parameters",
                "Pointers & References — DEEP DIVE", "Dynamic Memory (new/delete, RAII)",
                "Error Handling (try/catch/throw)"
            ], "project": "Console RPG, Text Adventure Game"},
            {"phase": "Phase 2 — Advanced C++ + Unreal Intro", "level": "Intermediate ⭐⭐⭐", "color": "🟡", "topics": [
                "OOP (Classes, Constructors, Destructors, this pointer)",
                "Inheritance, Polymorphism, Virtual Functions, vtable",
                "Templates & Generic Programming", "STL Containers & Algorithms",
                "Smart Pointers (unique_ptr, shared_ptr, weak_ptr)",
                "Move Semantics & Rvalue References", "Lambda Expressions",
                "Unreal Engine Setup & Interface", "Unreal Gameplay Framework (Actor, Pawn, Character)",
                "UCLASS, UPROPERTY, UFUNCTION macros", "Blueprints + C++ Integration"
            ], "project": "First Person Exploration with C++ Player Controller"},
            {"phase": "Phase 3 — Unreal Game Development", "level": "Advanced ⭐⭐⭐⭐⭐", "color": "🔴", "topics": [
                "Unreal Physics & Collision System", "Materials, Shaders, Lighting (Lumen)",
                "Nanite & LOD System", "AI with Behavior Trees & EQS",
                "Animation (Animation Blueprints, Montages)", "UI with UMG (Unreal Motion Graphics)",
                "Niagara Particle System", "Sound & Audio System",
                "Level Design & World Building", "Optimization & Profiling"
            ], "project": "Complete 3D Game with AI, UI, Physics"},
            {"phase": "Phase 4 — AAA & Publishing", "level": "Expert 🚀", "color": "🚀", "topics": [
                "Multiplayer & Replication", "Dedicated Server Setup",
                "Procedural Generation", "Advanced Rendering & Post Processing",
                "Packaging & Distribution", "Version Control (Perforce/Git for UE)",
                "Performance Optimization (Stat commands, Profiler)", "Marketplace & Plugins"
            ], "project": None},
        ],
    },
    "javascript": {
        "name": "JavaScript & Web Dev",
        "icon": "🌐",
        "description": "JavaScript full-stack web development — frontend to backend",
        "run_command": "node",
        "file_ext": ".js",
        "topic_keywords": {
            "JS Basics & Setup": ["javascript", "js", "node", "nodejs", "browser", "console", "script tag", "vscode"],
            "JS Variables & Types": ["var", "let", "const", "string", "number", "boolean", "undefined", "null", "symbol", "bigint", "typeof", "dynamic typing"],
            "JS Operators": ["operator", "arithmetic", "comparison", "strict equality", "logical", "nullish coalescing", "optional chaining"],
            "JS Strings": ["string", "template literal", "backtick", "slice", "split", "trim", "replace", "regex"],
            "JS Control Flow": ["if", "else", "switch", "ternary"],
            "JS Loops": ["loop", "for", "while", "for of", "for in", "foreach", "break", "continue"],
            "JS Arrays": ["array", "push", "pop", "map", "filter", "reduce", "find", "some", "every", "spread", "destructuring"],
            "JS Objects": ["object", "property", "method", "this", "destructuring", "spread", "rest", "json"],
            "JS Functions": ["function", "arrow function", "callback", "closure", "iife", "hoisting", "scope", "default parameter"],
            "JS DOM": ["dom", "document", "getelementbyid", "queryselector", "event", "addeventlistener", "innerhtml", "classlist"],
            "JS Async": ["async", "await", "promise", "fetch", "then", "catch", "callback hell", "event loop", "settimeout"],
            "JS ES6+ Features": ["es6", "class", "module", "import", "export", "destructuring", "spread", "rest", "symbol", "proxy", "reflect"],
            "JS OOP": ["class", "constructor", "extends", "super", "prototype", "inheritance", "encapsulation"],
            "JS Error Handling": ["error", "try", "catch", "finally", "throw", "custom error"],
            "HTML & CSS": ["html", "css", "flexbox", "grid", "responsive", "media query", "sass", "scss", "tailwind"],
            "React": ["react", "component", "jsx", "state", "props", "usestate", "useeffect", "hook", "virtual dom", "redux"],
            "Node.js & Express": ["node", "express", "middleware", "route", "api", "server", "npm", "package.json"],
            "TypeScript": ["typescript", "ts", "type", "interface", "enum", "generic", "type guard"],
            "Next.js": ["nextjs", "next", "ssr", "ssg", "app router", "server component", "api route"],
            "Database (JS)": ["mongodb", "mongoose", "prisma", "sql", "postgres", "supabase", "firebase"],
        },
        "roadmap": [
            {"phase": "Phase 1 — JavaScript Foundation", "level": "Beginner ⭐", "color": "🟢", "topics": [
                "JS setup, Browser Console, Node.js", "Variables (var, let, const) & Data Types",
                "Operators & Expressions", "Strings & Template Literals",
                "Control Flow (if/else, switch, ternary)",
                "Loops (for, while, for...of, forEach)",
                "Arrays & Array Methods (map, filter, reduce)",
                "Objects & JSON", "Functions, Arrow Functions, Closures",
                "Error Handling (try/catch)", "DOM Manipulation & Events"
            ], "project": "Interactive Todo App, Calculator with DOM"},
            {"phase": "Phase 2 — Advanced JS + Frontend", "level": "Intermediate ⭐⭐⭐", "color": "🟡", "topics": [
                "ES6+ Features (Classes, Modules, Destructuring)",
                "Async JavaScript (Promises, async/await, Fetch API)",
                "Event Loop & Concurrency Model",
                "OOP in JavaScript (Prototypes, Classes)",
                "HTML5 & CSS3 Deep Dive (Flexbox, Grid, Responsive)",
                "React Basics (Components, JSX, Props, State)",
                "React Hooks (useState, useEffect, useRef, useContext)",
                "React Router & Navigation", "State Management (Context API, Redux basics)",
                "API Integration & HTTP Requests"
            ], "project": "Full React App with API Integration (Weather App, Movie DB)"},
            {"phase": "Phase 3 — Full-Stack", "level": "Advanced ⭐⭐⭐⭐⭐", "color": "🔴", "topics": [
                "Node.js & Express.js (Server, Routes, Middleware)",
                "RESTful API Design", "Database (MongoDB + Mongoose / PostgreSQL + Prisma)",
                "Authentication (JWT, OAuth, Sessions)", "TypeScript Fundamentals",
                "Next.js (SSR, SSG, App Router, Server Components)",
                "Testing (Jest, React Testing Library)", "WebSockets & Real-time Apps",
                "Deployment (Vercel, Railway, Docker)", "Performance & Security Best Practices"
            ], "project": "Full-Stack App (E-commerce, Social Media Clone)"},
            {"phase": "Phase 4 — Specialization", "level": "Expert 🚀", "color": "🚀", "topics": [
                "Advanced React Patterns", "Micro-frontends",
                "GraphQL (Apollo Client/Server)", "CI/CD Pipelines",
                "Mobile with React Native", "Desktop with Electron",
                "Serverless Functions", "System Design for Web Apps"
            ], "project": None},
        ],
    },
}

# Build merged topic keywords from all curricula (used for extraction)
def _build_active_topic_keywords(active_ids=None):
    """Build combined TOPIC_KEYWORDS from active curricula. If none specified, use all."""
    merged = {}
    targets = active_ids if active_ids else list(CURRICULA.keys())
    for cid in targets:
        cur = CURRICULA.get(cid)
        if cur:
            for topic, keywords in cur["topic_keywords"].items():
                prefix = f"[{cur['name']}] " if len(targets) > 1 else ""
                merged[f"{prefix}{topic}"] = keywords
    return merged

# Default: start with Python keywords (will be dynamically updated)
TOPIC_KEYWORDS = CURRICULA["python"]["topic_keywords"]

REVIEW_INTERVALS = [1, 3, 7, 14, 30, 60]  # days


# ═════════════════════════════════════════════════════════
# DATABASE SETUP
# ═════════════════════════════════════════════════════════

def _get_db():
    conn = sqlite3.connect(MEMORY_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db():
    with _db_lock:
        conn = _get_db()
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS student_profile (
                id INTEGER PRIMARY KEY DEFAULT 1,
                name TEXT,
                learning_level TEXT DEFAULT 'beginner',
                joined_date TEXT,
                total_sessions INTEGER DEFAULT 0,
                total_study_minutes INTEGER DEFAULT 0,
                strengths TEXT DEFAULT '[]',
                weaknesses TEXT DEFAULT '[]',
                notes TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date TEXT NOT NULL,
                duration_minutes INTEGER DEFAULT 0,
                summary TEXT DEFAULT '',
                topics_discussed TEXT DEFAULT '[]',
                tools_used TEXT DEFAULT '{}',
                student_lines TEXT DEFAULT '[]',
                teacher_last_words TEXT DEFAULT '',
                last_question_asked TEXT DEFAULT '',
                mood TEXT DEFAULT 'neutral',
                engagement TEXT DEFAULT 'medium'
            );
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT DEFAULT 'general',
                curriculum TEXT DEFAULT 'python',
                mastery_level INTEGER DEFAULT 1,
                times_taught INTEGER DEFAULT 1,
                first_taught TEXT,
                last_reviewed TEXT,
                next_review TEXT,
                review_interval_idx INTEGER DEFAULT 0,
                notes_saved INTEGER DEFAULT 0,
                quiz_score REAL DEFAULT 0,
                struggles TEXT DEFAULT '',
                strengths TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS key_moments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                moment_type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS explicit_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 5,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS verified_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL,
                source TEXT DEFAULT 'student',
                verified INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS active_curricula (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curriculum_id TEXT UNIQUE NOT NULL,
                activated_at TEXT NOT NULL,
                is_primary INTEGER DEFAULT 0
            );
        """)
        # Ensure at least Python is active by default
        c.execute("SELECT COUNT(*) FROM active_curricula")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO active_curricula (curriculum_id, activated_at, is_primary) VALUES ('python', ?, 1)",
                      (datetime.now().isoformat(),))
        conn.commit()
        conn.close()


def _migrate_legacy():
    """Migrate old memory.json → SQLite (one-time)."""
    if not os.path.exists(LEGACY_MEMORY_FILE):
        return
    try:
        with open(LEGACY_MEMORY_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        return

    with _db_lock:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM student_profile")
        if c.fetchone()[0] > 0:
            conn.close()
            return

        c.execute("INSERT INTO student_profile (id, name, joined_date, total_sessions) VALUES (1,?,?,?)",
                  (old.get("student_name"), old.get("last_session_date"), old.get("total_sessions", 0)))

        for topic in old.get("topics_covered", []):
            try:
                c.execute("INSERT OR IGNORE INTO topics (name, mastery_level, first_taught, last_reviewed) VALUES (?,2,?,?)",
                          (topic, old.get("last_session_date"), old.get("last_session_date")))
            except Exception:
                pass

        if old.get("last_topic"):
            c.execute("INSERT OR IGNORE INTO topics (name, mastery_level, first_taught, last_reviewed) VALUES (?,2,?,?)",
                      (old["last_topic"], old.get("last_session_date"), old.get("last_session_date")))

        if old.get("last_session_summary"):
            c.execute("INSERT INTO sessions (session_date, summary, last_question_asked) VALUES (?,?,?)",
                      (old.get("last_session_date", datetime.now().isoformat()),
                       old.get("last_session_summary", ""), old.get("last_question_asked", "")))

        conn.commit()
        conn.close()
        try:
            os.rename(LEGACY_MEMORY_FILE, LEGACY_MEMORY_FILE + ".bak")
        except Exception:
            pass
        print("✅ Memory migrated from memory.json → memory.db!")


_init_db()
_migrate_legacy()


# ═════════════════════════════════════════════════════════
# CURRICULUM MANAGEMENT
# ═════════════════════════════════════════════════════════

def get_active_curricula_ids() -> list:
    """Get list of active curriculum IDs from the database."""
    with _db_lock:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT curriculum_id FROM active_curricula ORDER BY is_primary DESC, activated_at ASC")
        ids = [row["curriculum_id"] for row in c.fetchall()]
        conn.close()
    return ids if ids else ["python"]  # Fallback to python


def get_active_curricula() -> list:
    """Get full curriculum data for all active curricula."""
    ids = get_active_curricula_ids()
    result = []
    for cid in ids:
        cur = CURRICULA.get(cid)
        if cur:
            result.append({"id": cid, **cur})
    return result


def get_primary_curriculum_id() -> str:
    """Get the primary (main) curriculum ID."""
    with _db_lock:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT curriculum_id FROM active_curricula WHERE is_primary = 1 LIMIT 1")
        row = c.fetchone()
        conn.close()
    return row["curriculum_id"] if row else "python"


def set_active_curriculum(curriculum_id: str, make_primary: bool = False) -> str:
    """Add a curriculum to the active list. Returns status message."""
    if curriculum_id not in CURRICULA:
        available = ", ".join(f"{v['icon']} {v['name']} ({k})" for k, v in CURRICULA.items())
        return f"❌ Unknown curriculum '{curriculum_id}'. Available: {available}"

    cur = CURRICULA[curriculum_id]
    with _db_lock:
        conn = _get_db()
        c = conn.cursor()
        # Check if already active
        c.execute("SELECT id FROM active_curricula WHERE curriculum_id = ?", (curriculum_id,))
        if c.fetchone():
            if make_primary:
                c.execute("UPDATE active_curricula SET is_primary = 0")  # Reset all
                c.execute("UPDATE active_curricula SET is_primary = 1 WHERE curriculum_id = ?", (curriculum_id,))
                conn.commit()
                conn.close()
                return f"✅ {cur['icon']} {cur['name']} is now your PRIMARY curriculum!"
            conn.close()
            return f"ℹ️ {cur['icon']} {cur['name']} is already active."

        if make_primary:
            c.execute("UPDATE active_curricula SET is_primary = 0")  # Reset all
        c.execute("INSERT INTO active_curricula (curriculum_id, activated_at, is_primary) VALUES (?,?,?)",
                  (curriculum_id, datetime.now().isoformat(), 1 if make_primary else 0))
        conn.commit()
        conn.close()

    # Update the global TOPIC_KEYWORDS
    global TOPIC_KEYWORDS
    TOPIC_KEYWORDS = _build_active_topic_keywords(get_active_curricula_ids())

    return f"✅ {cur['icon']} {cur['name']} curriculum activated! Ab main tumhe {cur['name']} bhi padha sakti hoon! 🎉"


def remove_active_curriculum(curriculum_id: str) -> str:
    """Remove a curriculum from the active list."""
    if curriculum_id not in CURRICULA:
        return f"❌ Unknown curriculum '{curriculum_id}'"

    cur = CURRICULA[curriculum_id]
    with _db_lock:
        conn = _get_db()
        c = conn.cursor()
        # Don't allow removing the last curriculum
        c.execute("SELECT COUNT(*) FROM active_curricula")
        if c.fetchone()[0] <= 1:
            conn.close()
            return f"⚠️ Cannot remove {cur['name']} — at least one curriculum must be active!"
        c.execute("DELETE FROM active_curricula WHERE curriculum_id = ?", (curriculum_id,))
        # If we removed the primary, make the first remaining one primary
        c.execute("SELECT COUNT(*) FROM active_curricula WHERE is_primary = 1")
        if c.fetchone()[0] == 0:
            c.execute("UPDATE active_curricula SET is_primary = 1 WHERE id = (SELECT MIN(id) FROM active_curricula)")
        conn.commit()
        conn.close()

    global TOPIC_KEYWORDS
    TOPIC_KEYWORDS = _build_active_topic_keywords(get_active_curricula_ids())

    return f"✅ {cur['icon']} {cur['name']} curriculum deactivated."


def get_available_curricula_list() -> str:
    """Get a formatted list of all available curricula for display."""
    active_ids = get_active_curricula_ids()
    lines = []
    for cid, cur in CURRICULA.items():
        status = "✅ ACTIVE" if cid in active_ids else "⬜ Available"
        primary = " (PRIMARY)" if cid == get_primary_curriculum_id() else ""
        lines.append(f"{cur['icon']} **{cur['name']}** ({cid}) — {status}{primary}")
        lines.append(f"   {cur['description']}")
    return "\n".join(lines)


def build_curriculum_prompt() -> str:
    """Build the dynamic curriculum section for the system prompt."""
    active = get_active_curricula()
    if not active:
        return ""

    parts = []

    # Build dynamic intro
    names = [f"{c['icon']} {c['name']}" for c in active]
    if len(active) == 1:
        parts.append(f"\n## 🎯 ACTIVE CURRICULUM: {names[0]}")
        parts.append(f"{active[0]['description']}")
    else:
        parts.append(f"\n## 🎯 ACTIVE CURRICULA: {', '.join(names)}")
        parts.append("Student is learning multiple languages! Jab context switch ho, language-specific approach use karo.")

    # Build roadmaps
    for cur in active:
        parts.append(f"\n### {cur['icon']} {cur['name']} ROADMAP")
        for phase in cur["roadmap"]:
            parts.append(f"\n#### {phase['color']} {phase['phase']} — {phase['level']}")
            for i, topic in enumerate(phase["topics"], 1):
                parts.append(f"{i}. {topic}")
            if phase.get("project"):
                parts.append(f"\n**🛠️ Mini Project**: {phase['project']}")

    # Available curricula list
    all_ids = list(CURRICULA.keys())
    inactive = [cid for cid in all_ids if cid not in [c.get("id", "") for c in active]]
    if inactive:
        parts.append("\n### 📋 OTHER AVAILABLE CURRICULA:")
        parts.append("Student can say 'mujhe [language] bhi seekhni hai' to activate:")
        for cid in inactive:
            c = CURRICULA[cid]
            parts.append(f"- {c['icon']} {c['name']} — {c['description']}")

    return "\n".join(parts)

# ═════════════════════════════════════════════════════════
# SMART TOPIC EXTRACTION
# ═════════════════════════════════════════════════════════

def extract_topics(text: str) -> list:
    """Extract topics using weighted keyword scoring from active curricula."""
    if not text:
        return []
    # Dynamically use active curricula keywords
    active_ids = get_active_curricula_ids()
    keywords_map = _build_active_topic_keywords(active_ids) if active_ids else TOPIC_KEYWORDS
    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))
    scores = {}
    for topic, keywords in keywords_map.items():
        score = 0
        for kw in keywords:
            if ' ' in kw:
                if kw in text_lower:
                    score += 3
            else:
                if kw in words:
                    score += 1
        if score >= 2:
            scores[topic] = score
    return [t[0] for t in sorted(scores.items(), key=lambda x: x[1], reverse=True)]


def detect_mood(text: str) -> str:
    """Detect student emotional state from speech."""
    tl = text.lower()
    if any(w in tl for w in ["kyun nahi", "error", "galat", "wrong", "frustrated", "kaam nahi", "not working"]):
        return "frustrated"
    if any(w in tl for w in ["samajh nahi", "confuse", "nahi samjha", "doubt", "clear nahi", "mushkil"]):
        return "confused"
    if any(w in tl for w in ["wow", "amazing", "cool", "great", "maza", "badiya", "zabardast", "kamaal"]):
        return "excited"
    if any(w in tl for w in ["samajh gaya", "understood", "got it", "clear", "easy", "aage badho", "next"]):
        return "confident"
    if any(w in tl for w in ["kyun", "why", "how", "kaise", "explain", "detail", "internally"]):
        return "curious"
    return "neutral"


# ═════════════════════════════════════════════════════════
# LIVE MEMORY — Real-time session tracking
# ═════════════════════════════════════════════════════════

class LiveMemory:
    """Real-time memory manager for active sessions."""

    def __init__(self):
        self._session_id = None
        self._student_lines = []
        self._teacher_lines = []
        self._tools_used = Counter()
        self._topics = set()
        self._moods = []
        self._start = datetime.now()
        self._last_question = None

        with _db_lock:
            conn = _get_db()
            c = conn.cursor()
            c.execute("INSERT INTO sessions (session_date) VALUES (?)",
                      (self._start.strftime("%Y-%m-%d %H:%M:%S"),))
            self._session_id = c.lastrowid
            c.execute("UPDATE student_profile SET total_sessions = total_sessions + 1 WHERE id = 1")
            if c.rowcount == 0:
                c.execute("INSERT INTO student_profile (id, joined_date, total_sessions) VALUES (1,?,1)",
                          (self._start.strftime("%Y-%m-%d"),))
            conn.commit()
            conn.close()

    def on_student_speech(self, text: str):
        if not text.strip():
            return
        self._student_lines.append(text)
        mood = detect_mood(text)
        self._moods.append(mood)
        topics = extract_topics(text)
        self._topics.update(topics)

        # Detect name
        for pat in [r"(?:mera naam|my name is|i am|main)\s+(\w+)"]:
            m = re.search(pat, text.lower())
            if m:
                name = m.group(1).capitalize()
                if len(name) > 2 and name.lower() not in ["mera", "main", "hoon"]:
                    with _db_lock:
                        conn = _get_db()
                        conn.execute("UPDATE student_profile SET name = ? WHERE id = 1", (name,))
                        conn.commit()
                        conn.close()

        # Store struggle moments
        if mood in ("frustrated", "confused"):
            self._store_moment("struggle", text)
        if "?" in text:
            self._store_moment("question", text)

    def on_teacher_speech(self, text: str):
        if not text.strip():
            return
        self._teacher_lines.append(text)
        topics = extract_topics(text)
        self._topics.update(topics)
        if "?" in text:
            self._last_question = text

    def on_tool_used(self, tool_name: str, args: dict, result: str):
        self._tools_used[tool_name] += 1
        if tool_name == "write_notebook":
            topics = extract_topics(args.get("content", ""))
            for t in topics:
                self._topics.add(t)
                self._upsert_topic(t, 2)
        elif tool_name == "save_notes":
            topics = extract_topics(args.get("title", "") + " " + args.get("content", ""))
            for t in topics:
                self._upsert_topic(t, 3)
                with _db_lock:
                    conn = _get_db()
                    conn.execute("UPDATE topics SET notes_saved = notes_saved + 1 WHERE name = ?", (t,))
                    conn.commit()
                    conn.close()
        elif tool_name == "run_python":
            if "✅" in result:
                self._store_moment("code_success", args.get("code", "")[:200])
            elif "❌" in result:
                self._store_moment("code_error", result[:200])

    def on_session_end(self):
        duration = max(1, int((datetime.now() - self._start).total_seconds() / 60))
        summary = self._build_summary()
        mood = Counter(self._moods).most_common(1)[0][0] if self._moods else "neutral"
        n = len(self._student_lines) + len(self._teacher_lines)
        engagement = "high" if n > 50 else ("medium" if n > 20 else "low")

        with _db_lock:
            conn = _get_db()
            c = conn.cursor()
            c.execute("""UPDATE sessions SET duration_minutes=?, summary=?, topics_discussed=?,
                         tools_used=?, student_lines=?, teacher_last_words=?,
                         last_question_asked=?, mood=?, engagement=? WHERE id=?""",
                      (duration, summary, json.dumps(list(self._topics)),
                       json.dumps(dict(self._tools_used)),
                       json.dumps(self._student_lines[-10:]),
                       " ".join(self._teacher_lines[-20:]),
                       self._last_question or "", mood, engagement, self._session_id))
            c.execute("UPDATE student_profile SET total_study_minutes = total_study_minutes + ? WHERE id = 1",
                      (duration,))
            # Update all topics discussed this session
            for topic in self._topics:
                self._upsert_topic(topic, 2)
            # Update learning level
            c.execute("SELECT COUNT(*) FROM topics WHERE mastery_level >= 3")
            mastered = c.fetchone()[0]
            level = "advanced" if mastered >= 15 else ("intermediate" if mastered >= 7 else "beginner")
            c.execute("UPDATE student_profile SET learning_level = ? WHERE id = 1", (level,))
            conn.commit()
            conn.close()

    def remember_fact(self, category: str, content: str, importance: int = 5) -> str:
        """Explicitly store a fact about the student."""
        with _db_lock:
            conn = _get_db()
            conn.execute("INSERT INTO explicit_memories (category, content, importance, created_at) VALUES (?,?,?,?)",
                         (category, content, importance, datetime.now().isoformat()))
            conn.commit()
            conn.close()
        return f"✅ Yaad rakh liya: {content}"

    def _upsert_topic(self, name: str, mastery: int):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        next_rev = (datetime.now() + timedelta(days=REVIEW_INTERVALS[0])).strftime("%Y-%m-%d")
        with _db_lock:
            conn = _get_db()
            c = conn.cursor()
            c.execute("SELECT id, mastery_level FROM topics WHERE name = ?", (name,))
            row = c.fetchone()
            if row:
                new_mastery = max(row["mastery_level"], mastery)
                c.execute("""UPDATE topics SET mastery_level=?, times_taught=times_taught+1,
                             last_reviewed=?, next_review=? WHERE id=?""",
                          (new_mastery, now, next_rev, row["id"]))
            else:
                c.execute("""INSERT INTO topics (name, mastery_level, first_taught, last_reviewed, next_review)
                             VALUES (?,?,?,?,?)""", (name, mastery, now, now, next_rev))
            conn.commit()
            conn.close()

    def _store_moment(self, mtype: str, content: str):
        with _db_lock:
            conn = _get_db()
            conn.execute("INSERT INTO key_moments (session_id, moment_type, content, timestamp) VALUES (?,?,?,?)",
                         (self._session_id, mtype, content[:500], datetime.now().isoformat()))
            conn.commit()
            conn.close()

    def _build_summary(self) -> str:
        parts = []
        if self._student_lines:
            parts.append("Student: " + " | ".join(self._student_lines[:5]))
        if self._tools_used:
            parts.append("Tools: " + ", ".join(f"{k}({v}x)" for k, v in self._tools_used.items()))
        if self._topics:
            parts.append("Topics: " + ", ".join(list(self._topics)[:8]))
        if self._teacher_lines:
            parts.append("Last taught: " + " ".join(self._teacher_lines[-10:])[:300])
        return "\n".join(parts)


# ═════════════════════════════════════════════════════════
# CONTEXT BUILDER — Smart prompt injection
# ═════════════════════════════════════════════════════════

def build_memory_context() -> str:
    """Build prioritized memory context for the system prompt."""
    with _db_lock:
        conn = _get_db()
        c = conn.cursor()

        # 1. Student profile
        c.execute("SELECT * FROM student_profile WHERE id = 1")
        profile = c.fetchone()

        # 2. Recent sessions (last 5)
        c.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 5")
        sessions = c.fetchall()

        # 3. All topics with mastery
        c.execute("SELECT * FROM topics ORDER BY last_reviewed DESC")
        topics = c.fetchall()

        # 4. Topics needing review (spaced repetition)
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT name, mastery_level, last_reviewed FROM topics WHERE next_review <= ? ORDER BY next_review ASC LIMIT 5", (today,))
        review_due = c.fetchall()

        # 5. Key moments (last 20)
        c.execute("SELECT moment_type, content FROM key_moments ORDER BY id DESC LIMIT 20")
        moments = c.fetchall()

        # 6. Explicit memories
        c.execute("SELECT category, content FROM explicit_memories ORDER BY importance DESC, id DESC LIMIT 15")
        memories = c.fetchall()

        # 7. Saved notes
        notes = _get_saved_notes()

        # 8. Verified Knowledge (permanent)
        c.execute("SELECT fact FROM verified_knowledge ORDER BY created_at DESC")
        verified_facts = [row["fact"] for row in c.fetchall()]

        conn.close()

    if not profile and not sessions and not topics:
        return ""

    parts = ["\n\n## 🧠 MEMORY — Pichle Sessions Ki Yaadein",
             "Tu pehle bhi is student ko padha chuki hai. Yeh raha context:\n"]

    # ── Student Profile ──
    if profile:
        name = profile["name"] or "Unknown"
        parts.append(f"👤 **Student**: {name}")
        parts.append(f"📊 **Level**: {profile['learning_level']}")
        parts.append(f"📈 **Sessions**: {profile['total_sessions']} | Study time: ~{profile['total_study_minutes']} min")
        if profile["strengths"] and profile["strengths"] != "[]":
            parts.append(f"💪 **Strengths**: {profile['strengths']}")
        if profile["weaknesses"] and profile["weaknesses"] != "[]":
            parts.append(f"⚠️ **Weak areas**: {profile['weaknesses']}")

    # ── Topics Mastery Map ──
    if topics:
        levels = {1: "🟡 Introduced", 2: "🟠 Learning", 3: "🔵 Practiced", 4: "🟢 Comfortable", 5: "⭐ Mastered"}
        parts.append(f"\n### 📚 Topics Mastery ({len(topics)} topics tracked):")
        for t in topics[:20]:
            lvl = levels.get(t["mastery_level"], "🟡")
            parts.append(f"- {lvl} **{t['name']}** (taught {t['times_taught']}x, last: {t['last_reviewed'] or 'N/A'})")

    # ── Spaced Repetition — Review Due ──
    if review_due:
        parts.append("\n### 🔄 REVIEW DUE — In topics ko revise karna chahiye:")
        for r in review_due:
            parts.append(f"- ⏰ **{r['name']}** (mastery: {r['mastery_level']}/5, last: {r['last_reviewed']})")
        parts.append("👉 Session shuru hone par student se pucho: 'Pehle ek quick revision kar lete hain!'")

    # ── Recent Sessions ──
    if sessions:
        parts.append(f"\n### 📝 Recent Sessions ({len(sessions)} shown):")
        for s in sessions[:3]:
            topics_list = json.loads(s["topics_discussed"]) if s["topics_discussed"] else []
            topics_str = ", ".join(topics_list[:5]) if topics_list else "N/A"
            parts.append(f"- **{s['session_date']}** ({s['duration_minutes']}min) — Topics: {topics_str} | Mood: {s['mood']} | Engagement: {s['engagement']}")
            if s["summary"]:
                # Truncate summary
                summary = s["summary"][:300]
                parts.append(f"  Summary: {summary}")

        # Last session details
        last = sessions[0]
        if last["last_question_asked"]:
            parts.append(f"\n### ⏩ Jahan Ruke The:")
            parts.append(f"Tumne last time yeh pucha tha: \"{last['last_question_asked']}\"")

        if last["teacher_last_words"]:
            tw = last["teacher_last_words"][:400]
            parts.append(f"\n### 👩‍🏫 Last Session — CHAHAT ne kya padhaya:")
            parts.append(f"\"{tw}\"")

        student_lines = json.loads(last["student_lines"]) if last["student_lines"] else []
        if student_lines:
            parts.append(f"\n### 🗣️ Student ne last session mein kya bola:")
            for line in student_lines[-5:]:
                parts.append(f"- \"{line}\"")

    # ── Key Moments ──
    struggles = [m for m in moments if m["moment_type"] == "struggle"]
    breakthroughs = [m for m in moments if m["moment_type"] == "code_success"]
    if struggles:
        parts.append(f"\n### ⚠️ Student Struggles (recent):")
        for s in struggles[:5]:
            parts.append(f"- {s['content'][:150]}")

    # ── Explicit Memories (CHAHAT remembered facts) ──
    if memories:
        parts.append(f"\n### 💾 Tumne Yeh Yaad Rakha Hai:")
        for m in memories:
            parts.append(f"- [{m['category']}] {m['content']}")

    # ── Saved Notes ──
    if notes:
        parts.append(f"\n### 📚 Saved Notes ({len(notes)} files):")
        for n in notes[:10]:
            parts.append(f"- **{n['title']}**")

    # ── Verified Knowledge Bank (PERMANENT) ──
    if verified_facts:
        parts.append(f"\n### 🔒 Verified Knowledge Bank ({len(verified_facts)} facts):")
        parts.append("Yeh facts tumne verify karke permanently save kiye hain. Inhe kabhi mat bhoolna:")
        for vf in verified_facts:
            parts.append(f"- ✅ {vf}")

    # ── Continuation Rules ──
    parts.append("\n### 🎯 CONTINUATION RULES:")
    parts.append("1. Jab student aaye toh welcome karo AUR batao last time kya padha tha")
    parts.append("2. Pucho: 'Pichli baar hum [topic] padh rahe the, wahi se aage badhein?'")
    parts.append("3. Agar review due hai, toh pehle quick revision suggest karo")
    parts.append("4. Jo topics mastered hain, unhe repeat mat karo unless student puche")
    parts.append("5. Student ka mood track karo — frustrated ho toh slow down, excited ho toh push forward")
    parts.append("6. remember tool use karo jab koi important fact yaad rakhna ho student ke baare mein")
    parts.append("7. Jab student koi NAYI cheez bataye (fact, info, claim) — PEHLE verify karo ki sahi hai ya nahi")
    parts.append("   - Agar SAHI hai → learn_verified_fact tool se permanently save karo")
    parts.append("   - Agar GALAT hai → politely correct karo, galat info mat seekho")
    parts.append("   - Agar UNSURE ho → student ko batao ki tum sure nahi ho, accept mat karo blindly")

    return "\n".join(parts)
    
# ═════════════════════════════════════════════════════════
# DASHBOARD DATA & MANAGEMENT
# ═════════════════════════════════════════════════════════

def get_dashboard_data() -> dict:
    """Fetch all memory data for the UI dashboard."""
    with _db_lock:
        conn = _get_db()
        c = conn.cursor()
        
        # 1. Profile
        c.execute("SELECT name, learning_level, total_sessions, total_study_minutes FROM student_profile WHERE id = 1")
        profile = dict(c.fetchone() or {"name": "Student", "learning_level": "beginner", "total_sessions": 0, "total_study_minutes": 0})
        
        # 2. Topics (Categorized)
        c.execute("SELECT name, mastery_level, times_taught, last_reviewed FROM topics ORDER BY mastery_level DESC, name ASC")
        all_topics = [dict(row) for row in c.fetchall()]
        
        # 3. Explicit Memories
        c.execute("SELECT id, category, content, importance FROM explicit_memories ORDER BY created_at DESC")
        memories = [dict(row) for row in c.fetchall()]
        
        # 4. Verified Knowledge (permanent, non-deletable)
        c.execute("SELECT id, fact, source, created_at FROM verified_knowledge ORDER BY created_at DESC")
        verified = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
    return {
        "profile": profile,
        "topics": all_topics,
        "explicit_memories": memories,
        "verified_knowledge": verified
    }

def update_student_profile(name: str, level: str):
    """Update profile from dashboard."""
    with _db_lock:
        conn = _get_db()
        conn.execute("UPDATE student_profile SET name = ?, learning_level = ? WHERE id = 1", (name, level))
        conn.commit()
        conn.close()

def delete_topic_memory(topic_name: str):
    """Delete a topic from Chahat's memory."""
    with _db_lock:
        conn = _get_db()
        conn.execute("DELETE FROM topics WHERE name = ?", (topic_name,))
        conn.commit()
        conn.close()

def delete_explicit_memory(memory_id: int):
    """Delete a specific remembered fact."""
    with _db_lock:
        conn = _get_db()
        conn.execute("DELETE FROM explicit_memories WHERE id = ?", (memory_id,))
        conn.commit()
        conn.close()


def store_verified_fact(fact: str, source: str = "student") -> str:
    """Store a verified fact in the permanent knowledge bank. NOT deletable."""
    with _db_lock:
        conn = _get_db()
        c = conn.cursor()
        # Check for duplicate
        c.execute("SELECT id FROM verified_knowledge WHERE fact = ?", (fact,))
        if c.fetchone():
            conn.close()
            return "⚠️ Yeh fact pehle se mere knowledge bank mein hai."
        c.execute("INSERT INTO verified_knowledge (fact, source, verified, created_at) VALUES (?,?,1,?)",
                  (fact, source, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    return f"✅ Verified & permanently saved: {fact}"

def get_verified_knowledge() -> list:
    """Get all verified knowledge facts."""
    with _db_lock:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT fact FROM verified_knowledge ORDER BY created_at DESC")
        facts = [row["fact"] for row in c.fetchall()]
        conn.close()
    return facts


def _get_saved_notes() -> list:
    """Get saved notes from notes directory."""
    if not os.path.exists(NOTES_DIR):
        return []
    notes = []
    for f in os.listdir(NOTES_DIR):
        if f.endswith(".md") and f != "Welcome.md":
            try:
                with open(os.path.join(NOTES_DIR, f), "r", encoding="utf-8") as fh:
                    first_line = fh.readline().strip("# \n")
                notes.append({"filename": f, "title": first_line})
            except Exception:
                pass
    return notes


# ═════════════════════════════════════════════════════════
# LEGACY COMPATIBILITY — keep old function name working
# ═════════════════════════════════════════════════════════

def update_memory_after_session():
    """Legacy compatibility — now a no-op since LiveMemory handles it."""
    pass
