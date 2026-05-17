# ui.py — CHAHAT Desktop Teaching UI (PyQt5 + WebEngine Notebook)
# Beautiful native desktop app with handwriting-style notebook
# Run: python3 main.py

import sys
import os
import queue
import json
from datetime import datetime

from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
from PyQt5.QtWebChannel import QWebChannel

# ── Shared event queue (main.py pushes, UI polls) ──────────
UI_QUEUE = queue.Queue()

# ── Text input queue (UI pushes, main.py reads to send to Gemini) ──
TEXT_QUEUE = queue.Queue()

# ── PDF save queue (UI pushes notebook content, main.py generates PDF) ──
PDF_QUEUE = queue.Queue()

# ── Memory Command queue (UI pushes updates/deletes, main.py or ui polls) ──
MEMORY_CMD_QUEUE = queue.Queue()

# ── Mic mute state (UI toggles, main.py reads) ──────────
import threading
MIC_MUTED = threading.Event()  # When set, mic is MUTED (send silence)

# ── Notebook HTML (embedded — no server needed) ────────────
NOTEBOOK_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CHAHAT — Notebook</title>
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&family=Fira+Code:wght@400;500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <script>
        // Polyfill for older WebEngine versions
        if (typeof structuredClone === 'undefined') {
            window.structuredClone = function(obj) { return JSON.parse(JSON.stringify(obj)); };
        }
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@9/dist/mermaid.min.js"></script>
    <style>
        :root {
            --paper: #ffffff;
            --paper-dark: #f8f9fa;
            --ink-blue: #1a3a5c;
            --ink-red: #c0392b;
            --ink-green: #27774a;
            --line-color: #e8ecf0;
            --margin-line: #e8a0a0;
            --pencil: #4a4a4a;
            --highlight: #fff9c4;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background: #3a3226;
            font-family: 'Inter', sans-serif;
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        /* ── Memory Dashboard Styles ── */
        .memory-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(26, 21, 15, 0.85);
            backdrop-filter: blur(12px);
            z-index: 2000;
            display: none; /* Hidden by default */
            align-items: center;
            justify-content: center;
            padding: 40px;
            opacity: 0;
            transition: opacity 0.4s ease;
        }
        .memory-overlay.show {
            display: flex;
            opacity: 1;
        }
        .dashboard-container {
            width: 100%;
            max-width: 900px;
            height: 85vh;
            background: #fff;
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transform: scale(0.9) translateY(20px);
            transition: transform 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
        }
        .memory-overlay.show .dashboard-container {
            transform: scale(1) translateY(0);
        }
        .dashboard-header {
            padding: 24px 32px;
            background: #f8f9fa;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .dashboard-header h2 { font-family: 'Nunito', sans-serif; color: #1a3a5c; font-size: 24px; }
        .close-dash { cursor: pointer; font-size: 24px; color: #aaa; transition: color 0.2s; }
        .close-dash:hover { color: #e74c3c; }

        .dashboard-content {
            flex: 1;
            overflow-y: auto;
            padding: 32px;
            display: flex;
            flex-direction: column;
            gap: 32px;
        }

        .dash-section h3 {
            font-family: 'Nunito', sans-serif;
            font-size: 18px;
            color: #c0392b;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Profile Card */
        .profile-card {
            background: #f1f4f8;
            border-radius: 16px;
            padding: 24px;
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            align-items: flex-end;
        }
        .input-group { display: flex; flex-direction: column; gap: 8px; flex: 1; min-width: 200px; }
        .input-group label { font-size: 12px; font-weight: 700; color: #666; text-transform: uppercase; }
        .input-group input, .input-group select {
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s;
        }
        .input-group input:focus { border-color: #1a3a5c; }
        .save-prof-btn {
            background: #1a3a5c;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 10px;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.2s;
        }
        .save-prof-btn:hover { background: #2c537d; }

        /* Topics Grid */
        .topics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 16px;
        }
        .topic-item {
            background: #fff;
            border: 1px solid #eee;
            border-radius: 12px;
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
        }
        .topic-item:hover { border-color: #1a3a5c; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .topic-info h4 { font-size: 15px; color: #333; margin-bottom: 4px; }
        .topic-info span { font-size: 12px; color: #888; }
        .del-btn {
            background: #fff0f0;
            color: #e74c3c;
            border: none;
            width: 32px; height: 32px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex; align-items: center; justify-content: center;
        }
        .del-btn:hover { background: #e74c3c; color: white; }

        /* Memory List */
        .mem-list { display: flex; flex-direction: column; gap: 12px; }
        .mem-item {
            background: #fdf2f2;
            border-left: 4px solid #c0392b;
            padding: 16px;
            border-radius: 4px 12px 12px 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .mem-content { flex: 1; font-size: 14px; color: #444; line-height: 1.5; }
        .mem-meta { font-size: 11px; color: #999; margin-top: 4px; font-weight: 600; text-transform: uppercase; }

        .empty-state { text-align: center; padding: 40px; color: #aaa; font-style: italic; }
        
        .dash-badge {
            padding: 2px 8px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: 700;
            margin-left: 8px;
        }
        .badge-mastered { background: #e6f7ed; color: #27774a; }
        .badge-learning { background: #fff8e6; color: #b7791f; }

        /* ── Header (Wooden desk bar) ── */
        .header {
            background: linear-gradient(180deg, #5c4033 0%, #4a3428 100%);
            border-bottom: 3px solid #3a2418;
            padding: 10px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            z-index: 10;
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .save-pdf-btn {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 7px 16px;
            font-family: 'Nunito', sans-serif;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 2px 8px rgba(231, 76, 60, 0.3);
            letter-spacing: 0.5px;
        }

        .save-pdf-btn:hover {
            background: linear-gradient(135deg, #c0392b 0%, #a93226 100%);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(231, 76, 60, 0.4);
        }

        .save-pdf-btn:active {
            transform: scale(0.96);
        }

        .save-pdf-btn.saving {
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            pointer-events: none;
        }

        /* ── Mic Toggle Button ── */
        .mic-btn {
            position: relative;
            width: 42px;
            height: 42px;
            border-radius: 50%;
            border: 2px solid rgba(76, 175, 80, 0.6);
            background: rgba(76, 175, 80, 0.15);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
            outline: none;
            flex-shrink: 0;
        }

        .mic-btn .mic-icon {
            font-size: 20px;
            transition: transform 0.3s ease;
            line-height: 1;
        }

        .mic-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 0 16px rgba(76, 175, 80, 0.4);
        }

        .mic-btn:active {
            transform: scale(0.92);
        }

        /* Active/Listening state — green glow */
        .mic-btn.listening {
            border-color: #4caf50;
            background: rgba(76, 175, 80, 0.2);
            box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.5);
            animation: micPulse 2s infinite;
        }

        @keyframes micPulse {
            0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.5); }
            70% { box-shadow: 0 0 0 10px rgba(76, 175, 80, 0); }
            100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); }
        }

        /* Muted state — red, no pulse */
        .mic-btn.muted {
            border-color: rgba(231, 76, 60, 0.6);
            background: rgba(231, 76, 60, 0.15);
            animation: none;
        }

        .mic-btn.muted:hover {
            box-shadow: 0 0 16px rgba(231, 76, 60, 0.4);
        }

        /* Muted slash overlay */
        .mic-btn .mic-slash {
            position: absolute;
            width: 28px;
            height: 3px;
            background: #e74c3c;
            border-radius: 2px;
            transform: rotate(-45deg);
            opacity: 0;
            transition: opacity 0.25s ease;
            pointer-events: none;
        }

        .mic-btn.muted .mic-slash {
            opacity: 1;
        }

        .mic-btn.muted .mic-icon {
            opacity: 0.5;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header h1 {
            font-family: 'Nunito', sans-serif;
            font-size: 26px;
            font-weight: 800;
            color: #f5eddb;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }

        .header h1 span {
            font-size: 15px;
            font-weight: 400;
            color: #c4a882;
            font-family: 'Inter', sans-serif;
        }

        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #c4a882;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #666;
            transition: all 0.3s;
        }

        .status-dot.connected {
            background: #4caf50;
            box-shadow: 0 0 8px rgba(76,175,80,0.5);
        }

        .status-dot.speaking {
            background: #ff6b6b;
            box-shadow: 0 0 8px rgba(255,107,107,0.5);
            animation: pulse 1.2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.4); }
        }

        /* ── Main content ── */
        .main {
            flex: 1;
            display: flex;
            overflow: hidden;
        }

        /* ── Chat sidebar (small) ── */
        .sidebar {
            width: 280px;
            background: #2e2519;
            border-right: 2px solid #1a1510;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .sidebar-title {
            padding: 12px 16px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #8a7560;
            border-bottom: 1px solid #3a3028;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .chat-messages::-webkit-scrollbar { width: 4px; }
        .chat-messages::-webkit-scrollbar-thumb { background: #4a3a2e; border-radius: 2px; }

        .msg {
            padding: 8px 12px;
            border-radius: 10px;
            font-size: 12.5px;
            line-height: 1.5;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .msg.student {
            background: rgba(124, 58, 237, 0.15);
            border: 1px solid rgba(124, 58, 237, 0.25);
            color: #d4bfff;
            align-self: flex-end;
            max-width: 85%;
        }

        .msg.teacher {
            background: rgba(255, 200, 120, 0.1);
            border: 1px solid rgba(255, 200, 120, 0.15);
            color: #e8d5b0;
            align-self: flex-start;
            max-width: 85%;
        }

        .msg.tool {
            background: rgba(76, 175, 80, 0.1);
            border: 1px solid rgba(76, 175, 80, 0.15);
            color: #81c784;
            font-size: 11px;
            text-align: center;
            align-self: center;
            border-radius: 20px;
            padding: 4px 14px;
        }

        .msg-label {
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 2px;
            opacity: 0.6;
        }

        /* ── Notebook (main area) ── */
        .notebook {
            flex: 1;
            background: #ffffff;
            overflow-y: auto;
            position: relative;
            padding: 0;
        }

        .notebook::-webkit-scrollbar { width: 8px; }
        .notebook::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }

        /* Clean white page */
        .notebook-inner {
            min-height: 100%;
            padding: 28px 40px;
            position: relative;
        }

        /* Empty state */
        .nb-empty {
            text-align: center;
            padding-top: 100px;
            font-family: 'Nunito', sans-serif;
            color: #b0a080;
        }

        .nb-empty .pen-icon {
            font-size: 56px;
            margin-bottom: 12px;
        }

        .nb-empty h2 {
            font-size: 28px;
            font-weight: 700;
            color: var(--ink-blue);
            opacity: 0.4;
        }

        .nb-empty p {
            font-size: 18px;
            margin-top: 8px;
            opacity: 0.35;
        }

        /* ── Handwritten text blocks ── */
        .hw-block {
            margin-bottom: 8px;
            position: relative;
        }

        .hw-block .hw-label {
            font-family: 'Inter', sans-serif;
            font-size: 9px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--ink-red);
            opacity: 0.5;
            margin-bottom: 2px;
        }

        .hw-text {
            font-family: 'Nunito', sans-serif;
            font-size: 16px;
            line-height: 28px;
            color: var(--ink-blue);
            white-space: pre-wrap;
            word-wrap: break-word;
            font-weight: 500;
        }

        .hw-text .cursor-blink {
            display: inline-block;
            width: 2px;
            height: 18px;
            background: var(--ink-blue);
            margin-left: 1px;
            animation: blink 0.6s infinite;
            vertical-align: text-bottom;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }

        /* Code blocks in notebook */
        .hw-code {
            font-family: 'Fira Code', 'Consolas', 'Courier New', monospace;
            font-size: 14px;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 8px 0;
            color: #e2e8f0;
            line-height: 24px;
            white-space: pre-wrap;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        }

        /* Headings in notebook */
        .hw-heading {
            font-family: 'Nunito', sans-serif;
            font-weight: 800;
            color: var(--ink-red);
            font-size: 22px;
            border-left: 4px solid var(--ink-red);
            padding-left: 12px;
            margin: 16px 0 8px;
            line-height: 30px;
        }

        /* Bullet points */
        .hw-bullet {
            font-family: 'Nunito', sans-serif;
            font-size: 16px;
            font-weight: 500;
            color: var(--ink-blue);
            padding-left: 20px;
            line-height: 28px;
            position: relative;
        }

        .hw-bullet::before {
            content: '\2022';
            position: absolute;
            left: 4px;
            color: var(--ink-red);
            font-size: 20px;
        }

        /* Tool result on notebook */
        .hw-tool {
            background: rgba(39, 119, 74, 0.08);
            border: 1px dashed var(--ink-green);
            border-radius: 8px;
            padding: 10px 14px;
            margin: 8px 0;
            font-family: 'Nunito', sans-serif;
            font-size: 14px;
            font-weight: 600;
            color: var(--ink-green);
            line-height: 24px;
        }

        /* Student question on notebook */
        .hw-student {
            font-family: 'Nunito', sans-serif;
            font-size: 15px;
            font-weight: 600;
            color: #7c3aed;
            font-style: italic;
            margin: 10px 0;
            padding: 6px 0;
            border-bottom: 1px dotted #c4b0e0;
            line-height: 26px;
        }

        /* ══════ Input Bar ══════ */
        .input-bar {
            background: #f8f9fa;
            border-top: 1px solid #e5e7eb;
            padding: 10px 16px;
            display: flex;
            gap: 8px;
            align-items: flex-end;
        }

        .input-bar textarea {
            flex: 1;
            resize: none;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 10px 14px;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.5;
            color: #1f2937;
            background: #ffffff;
            outline: none;
            min-height: 42px;
            max-height: 150px;
            transition: border-color 0.2s;
        }

        .input-bar textarea:focus {
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }

        .input-bar textarea::placeholder {
            color: #9ca3af;
            font-family: 'Nunito', sans-serif;
            font-style: italic;
        }

        .input-bar .send-btn {
            background: #6366f1;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 18px;
            font-family: 'Nunito', sans-serif;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            white-space: nowrap;
            transition: background 0.2s, transform 0.1s;
        }

        .input-bar .send-btn:hover {
            background: #4f46e5;
        }

        .input-bar .send-btn:active {
            transform: scale(0.95);
        }

        .input-bar .attach-btn {
            background: transparent;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 10px 12px;
            font-size: 18px;
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s;
            line-height: 1;
        }

        .input-bar .attach-btn:hover {
            background: #f3f4f6;
            border-color: #6366f1;
        }

        .input-bar .file-name {
            font-family: 'Nunito', sans-serif;
            font-size: 11px;
            color: #6366f1;
            font-weight: 600;
            max-width: 120px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* ══════ Terminal Overlay ══════ */
        .terminal-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: #0d1117;
            z-index: 100;
            display: none;
            flex-direction: column;
            opacity: 0;
            transition: opacity 0.4s ease;
        }

        .terminal-overlay.show {
            display: flex;
            opacity: 1;
        }

        .terminal-overlay.hiding {
            opacity: 0;
        }

        .terminal-header {
            background: linear-gradient(180deg, #1a1f2e 0%, #161b22 100%);
            padding: 10px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #30363d;
        }

        .terminal-header-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .terminal-dots {
            display: flex;
            gap: 6px;
        }

        .terminal-dots span {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }

        .terminal-dots span:nth-child(1) { background: #ff5f56; }
        .terminal-dots span:nth-child(2) { background: #ffbd2e; }
        .terminal-dots span:nth-child(3) { background: #27c93f; }

        .terminal-title {
            font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 13px;
            color: #8b949e;
            margin-left: 8px;
        }

        .terminal-badge {
            background: rgba(56, 139, 253, 0.15);
            border: 1px solid rgba(56, 139, 253, 0.3);
            color: #58a6ff;
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 12px;
            font-family: 'SF Mono', 'Fira Code', monospace;
        }

        .terminal-body {
            flex: 1;
            padding: 20px 24px;
            overflow-y: auto;
            font-family: 'SF Mono', 'Fira Code', 'Consolas', 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.7;
        }

        .terminal-body::-webkit-scrollbar { width: 6px; }
        .terminal-body::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

        .terminal-section {
            margin-bottom: 20px;
        }

        .terminal-section-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #484f58;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .terminal-section-label::after {
            content: '';
            flex: 1;
            height: 1px;
            background: #21262d;
        }

        .terminal-code {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px 20px;
            position: relative;
            overflow: hidden;
        }

        .terminal-code .line-numbers {
            position: absolute;
            left: 0;
            top: 16px;
            bottom: 16px;
            width: 40px;
            border-right: 1px solid #21262d;
            text-align: right;
            padding-right: 10px;
            font-size: 12px;
            color: #484f58;
            line-height: 1.7;
        }

        .terminal-code .code-content {
            margin-left: 48px;
            color: #e6edf3;
            white-space: pre-wrap;
        }

        /* Syntax highlighting */
        .tk-keyword { color: #ff7b72; }
        .tk-string { color: #a5d6ff; }
        .tk-function { color: #d2a8ff; }
        .tk-comment { color: #8b949e; font-style: italic; }
        .tk-number { color: #79c0ff; }
        .tk-operator { color: #ff7b72; }
        .tk-builtin { color: #ffa657; }

        .terminal-output {
            background: #0d1117;
            border: 1px solid #1f6b2a;
            border-radius: 8px;
            padding: 16px 20px;
            position: relative;
        }

        .terminal-prompt {
            color: #3fb950;
            display: flex;
            gap: 4px;
        }

        .terminal-prompt .prompt-symbol { color: #3fb950; }
        .terminal-prompt .prompt-text { color: #e6edf3; }

        .terminal-output-text {
            color: #e6edf3;
            white-space: pre-wrap;
            margin-top: 4px;
            padding-left: 0;
        }

        .terminal-cursor-block {
            display: inline-block;
            width: 8px;
            height: 16px;
            background: #3fb950;
            animation: termBlink 1s step-end infinite;
            vertical-align: text-bottom;
        }

        @keyframes termBlink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }

        .terminal-status {
            padding: 8px 20px;
            background: #161b22;
            border-top: 1px solid #30363d;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
            color: #484f58;
            font-family: 'SF Mono', 'Fira Code', monospace;
        }

        .terminal-status .status-success {
            color: #3fb950;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .terminal-status .status-info {
            color: #8b949e;
        }

        /* Notebook return animation */
        .terminal-returning {
            text-align: center;
            padding: 12px;
            color: #8b949e;
            font-size: 13px;
            font-family: 'SF Mono', monospace;
            animation: fadeIn 0.3s ease;
        }

        /* Diagram / Whiteboard Overlay */
        .diagram-overlay {
            position: absolute; top: 0; left: 0; right: 0; bottom: 0;
            background: #ffffff; z-index: 90;
            display: none; flex-direction: column;
            opacity: 0; transition: opacity 0.4s ease;
        }
        .diagram-overlay.show { display: flex; opacity: 1; }
        .diagram-overlay.hiding { opacity: 0; }

        .diagram-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 10px 20px; display: flex; align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 12px rgba(102, 126, 234, 0.3);
        }
        .diagram-title {
            font-family: 'Nunito', sans-serif; font-size: 15px;
            font-weight: 700; color: #ffffff;
        }
        .diagram-badge {
            background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3);
            color: #fff; font-size: 11px; padding: 3px 10px;
            border-radius: 12px; font-family: 'Nunito', sans-serif; font-weight: 600;
        }
        .diagram-body {
            flex: 1; overflow: auto; display: flex;
            align-items: center; justify-content: center; padding: 24px;
            background: #fafbfc;
            background-image: radial-gradient(circle, #e0e5ec 1px, transparent 1px);
            background-size: 20px 20px;
        }
        .diagram-canvas {
            background: #ffffff; border-radius: 12px; padding: 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            max-width: 95%; max-height: 90%; overflow: auto;
            animation: diagramZoomIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        @keyframes diagramZoomIn {
            from { transform: scale(0.8); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        .diagram-canvas svg { max-width: 100%; height: auto; }
        .diagram-canvas .mermaid { display: flex; justify-content: center; }
        .diagram-footer {
            padding: 8px 20px; background: #f0f2f5;
            border-top: 1px solid #e5e7eb; display: flex;
            align-items: center; justify-content: space-between;
            font-size: 11px; color: #6b7280; font-family: 'Nunito', sans-serif;
        }
        .diagram-footer .diagram-hint { font-style: italic; }
        .diagram-footer .diagram-type { font-weight: 700; color: #667eea; }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="header-left">
            <h1>✏️ CHAHAT <span>— Your AI Teacher</span></h1>
        </div>
        <div class="header-right">
            <button class="save-pdf-btn" id="savePdfBtn" onclick="saveNotebookAsPdf()" title="Save notebook as PDF">📄 Save PDF</button>
            <button class="save-pdf-btn" style="background: #1a3a5c;" onclick="openMemoryDashboard()">🧠 Memory Hub</button>
            <button class="mic-btn listening" id="micToggleBtn" onclick="toggleMic()" title="Mic On — Click to mute">
                <span class="mic-icon">🎤</span>
                <span class="mic-slash"></span>
            </button>
            <div class="status">
                <div class="status-dot" id="statusDot"></div>
                <span id="statusText">Connecting...</span>
            </div>
        </div>
    </div>

    <!-- Memory Dashboard Overlay -->
    <div class="memory-overlay" id="memoryDashboard">
        <div class="dashboard-container">
            <div class="dashboard-header">
                <h2>🧠 CHAHAT Memory Hub</h2>
                <div class="close-dash" onclick="closeMemoryDashboard()">✕</div>
            </div>
            <div class="dashboard-content">
                <!-- Profile Section -->
                <div class="dash-section">
                    <h3>👤 Student Profile</h3>
                    <div class="profile-card">
                        <div class="input-group">
                            <label>Student Name</label>
                            <input type="text" id="dash_name" placeholder="Apna naam likho...">
                        </div>
                        <div class="input-group">
                            <label>Learning Level</label>
                            <select id="dash_level">
                                <option value="beginner">Beginner (Basics se shuru)</option>
                                <option value="intermediate">Intermediate (Thoda aata hai)</option>
                                <option value="advanced">Advanced (Deep dive)</option>
                                <option value="expert">Expert (Mastery)</option>
                            </select>
                        </div>
                        <button class="save-prof-btn" onclick="saveProfile()">Update Profile</button>
                    </div>
                </div>

                <!-- Learning Progress -->
                <div class="dash-section">
                    <h3>📚 Learning Progress <span id="topic_count" style="font-size:12px; color:#888; font-weight:normal;">(0 topics)</span></h3>
                    <div class="topics-grid" id="dash_topics">
                        <!-- Topics injected here -->
                    </div>
                </div>

                <!-- Explicit Memories -->
                <div class="dash-section">
                    <h3>💾 Saved Facts <span id="mem_count" style="font-size:12px; color:#888; font-weight:normal;">(0 facts)</span></h3>
                    <div class="mem-list" id="dash_memories">
                        <!-- Memories injected here -->
                    </div>
                </div>

                <!-- Verified Knowledge Bank (READ-ONLY) -->
                <div class="dash-section">
                    <h3>🔒 Verified Knowledge Bank <span id="vk_count" style="font-size:12px; color:#888; font-weight:normal;">(0 facts)</span></h3>
                    <p style="font-size:12px; color:#999; margin-bottom:12px;">Yeh permanently saved facts hain — inhe delete nahi kar sakte.</p>
                    <div class="mem-list" id="dash_verified">
                        <!-- Verified Knowledge injected here -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Main -->
    <div class="main">
        <!-- Sidebar chat -->
        <div class="sidebar">
            <div class="sidebar-title">💬 Voice Chat</div>
            <div class="chat-messages" id="chatMessages"></div>
        </div>

        <!-- Notebook -->
        <div style="flex:1; display:flex; flex-direction:column; overflow:hidden;">
            <div class="notebook" id="notebook" style="flex:1;">
                <div class="notebook-inner" id="nbInner">
                    <div class="nb-empty" id="nbEmpty">
                        <div class="pen-icon">✏️📓</div>
                        <h2>CHAHAT ka Notebook</h2>
                        <p>Bolo kuch bhi — main likh ke samjhaungi!</p>
                    </div>
                </div>

                <!-- Terminal Overlay (slides in over notebook) -->
                <div class="terminal-overlay" id="terminalOverlay">
                    <div class="terminal-header">
                        <div class="terminal-header-left">
                            <div class="terminal-dots">
                                <span></span><span></span><span></span>
                            </div>
                            <span class="terminal-title">🐍 CHAHAT Terminal — Python</span>
                        </div>
                        <span class="terminal-badge">LIVE CODE</span>
                    </div>
                    <div class="terminal-body" id="terminalBody"></div>
                    <div class="terminal-status" id="terminalStatus">
                        <span class="status-success" id="termStatus">⏳ Running...</span>
                        <span class="status-info">CHAHAT AI Teacher</span>
                    </div>
                </div>

                <!-- Diagram / Whiteboard Overlay -->
                <div class="diagram-overlay" id="diagramOverlay">
                    <div class="diagram-header">
                        <span class="diagram-title">🎨 CHAHAT's Whiteboard</span>
                        <span class="diagram-badge" id="diagramBadge">DIAGRAM</span>
                    </div>
                    <div class="diagram-body">
                        <div class="diagram-canvas" id="diagramCanvas"></div>
                    </div>
                    <div class="diagram-footer">
                        <span class="diagram-hint">CHAHAT will dismiss when ready — bolo "samajh gaya" ✨</span>
                        <span class="diagram-type" id="diagramType"></span>
                    </div>
                </div>
            </div>

            <!-- Input Bar -->
            <div class="input-bar">
                <input type="file" id="fileInput" accept=".py,.txt,.js,.java,.c,.cpp,.html,.css,.json,.md" style="display:none" onchange="handleFileSelect(this)">
                <button class="attach-btn" onclick="document.getElementById('fileInput').click()" title="File attach karo">📎</button>
                <span class="file-name" id="fileName"></span>
                <textarea id="studentInput" rows="1" placeholder="Apna code ya answer yahan paste karo..."
                    onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendStudentText();}"
                    oninput="autoResize(this)"></textarea>
                <button class="send-btn" onclick="sendStudentText()">📨 Send</button>
            </div>
        </div>
    </div>

    <script>
        // ── State ──
        let teacherBuffer = '';
        let bufferTimer = null;
        const BUFFER_DELAY = 700;

        // ── DOM ──
        const chatMessages = document.getElementById('chatMessages');
        const notebook = document.getElementById('notebook');
        const nbInner = document.getElementById('nbInner');
        const nbEmpty = document.getElementById('nbEmpty');
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const studentInput = document.getElementById('studentInput');

        // ── Text input queue (Python polls this) ──
        var pendingTexts = [];

        // ── PDF save queue (Python polls this) ──
        var pendingPdfSaves = [];

        // ── Memory action queue (Python polls this) ──
        var pendingMemoryCmds = [];

        // ── Mic mute state ──
        var micMuted = false;
        var pendingMicState = null;  // null = no change, true/false = new state

        function toggleMic() {
            micMuted = !micMuted;
            pendingMicState = micMuted;
            var btn = document.getElementById('micToggleBtn');
            if (micMuted) {
                btn.className = 'mic-btn muted';
                btn.title = 'Mic Off — Click to unmute';
                statusText.textContent = 'Mic Muted 🔇';
                statusDot.className = 'status-dot';
            } else {
                btn.className = 'mic-btn listening';
                btn.title = 'Mic On — Click to mute';
                statusText.textContent = 'Listening 🎤';
                statusDot.className = 'status-dot connected';
            }
        }

        function getPendingMicState() {
            if (pendingMicState === null) return 'none';
            var state = pendingMicState ? 'muted' : 'unmuted';
            pendingMicState = null;
            return state;
        }

        function openMemoryDashboard() {
            // Signal python to fetch fresh data
            pendingMemoryCmds.push({ action: 'fetch' });
            document.getElementById('memoryDashboard').classList.add('show');
        }

        function closeMemoryDashboard() {
            document.getElementById('memoryDashboard').classList.remove('show');
        }

        function saveProfile() {
            const name = document.getElementById('dash_name').value;
            const level = document.getElementById('dash_level').value;
            pendingMemoryCmds.push({ action: 'update_profile', name, level });
            alert('Profile updated! Chahat will remember this.');
        }

        function deleteTopic(name) {
            if(confirm('Kya aap chahte hain ki Chahat "' + name + '" ke baare mein sab bhool jaye?')) {
                pendingMemoryCmds.push({ action: 'delete_topic', name });
                // Optimistic UI update
                const items = document.querySelectorAll('.topic-item');
                items.forEach(el => {
                    if(el.querySelector('h4').textContent === name) el.remove();
                });
            }
        }

        function deleteMemory(id) {
            pendingMemoryCmds.push({ action: 'delete_memory', id });
            // Optimistic UI update
            const el = document.getElementById('mem-' + id);
            if(el) el.remove();
        }

        function renderMemoryDashboard(data) {
            // 1. Profile
            document.getElementById('dash_name').value = data.profile.name || '';
            document.getElementById('dash_level').value = data.profile.learning_level || 'beginner';

            // 2. Topics
            const topicsGrid = document.getElementById('dash_topics');
            document.getElementById('topic_count').textContent = '(' + data.topics.length + ' topics tracked)';
            topicsGrid.innerHTML = '';
            if(data.topics.length === 0) {
                topicsGrid.innerHTML = '<div class="empty-state">Abhi tak koi topic nahi padha...</div>';
            } else {
                data.topics.forEach(t => {
                    const badge = t.mastery_level >= 4 ? 'badge-mastered' : 'badge-learning';
                    const badgeText = t.mastery_level >= 4 ? 'MASTERED' : 'LEARNING';
                    const item = document.createElement('div');
                    item.className = 'topic-item';
                    item.innerHTML = `
                        <div class="topic-info">
                            <h4>${t.name} <span class="dash-badge ${badge}">${badgeText}</span></h4>
                            <span>Mastery: ${t.mastery_level}/5 | Taught ${t.times_taught}x</span>
                        </div>
                        <button class="del-btn" onclick="deleteTopic('${t.name}')" title="Bhool jao">🗑️</button>
                    `;
                    topicsGrid.appendChild(item);
                });
            }

            // 3. Memories
            const memList = document.getElementById('dash_memories');
            document.getElementById('mem_count').textContent = '(' + data.explicit_memories.length + ' facts)';
            memList.innerHTML = '';
            if(data.explicit_memories.length === 0) {
                memList.innerHTML = '<div class="empty-state">Koi special fact yaad nahi hai...</div>';
            } else {
                data.explicit_memories.forEach(m => {
                    const item = document.createElement('div');
                    item.className = 'mem-item';
                    item.id = 'mem-' + m.id;
                    item.innerHTML = `
                        <div class="mem-content">
                            <div class="mem-meta">${m.category} (Imp: ${m.importance})</div>
                            <div>${m.content}</div>
                        </div>
                        <button class="del-btn" onclick="deleteMemory(${m.id})" title="Delete fact">🗑️</button>
                    `;
                    memList.appendChild(item);
                });
            }

            // 4. Verified Knowledge (read-only, no delete)
            const vkList = document.getElementById('dash_verified');
            const vkData = data.verified_knowledge || [];
            document.getElementById('vk_count').textContent = '(' + vkData.length + ' permanent facts)';
            vkList.innerHTML = '';
            if(vkData.length === 0) {
                vkList.innerHTML = '<div class="empty-state">Abhi tak koi verified fact nahi seekha...</div>';
            } else {
                vkData.forEach(v => {
                    const item = document.createElement('div');
                    item.className = 'mem-item';
                    item.style.borderLeftColor = '#27774a';
                    item.style.background = '#f0faf4';
                    item.innerHTML = `
                        <div class="mem-content">
                            <div class="mem-meta" style="color:#27774a;">🔒 VERIFIED (${v.source})</div>
                            <div>${v.fact}</div>
                        </div>
                        <span style="font-size:20px; opacity:0.3;" title="Permanently saved — cannot delete">🔒</span>
                    `;
                    vkList.appendChild(item);
                });
            }
        }

        function sendStudentText() {
            var text = studentInput.value.trim();
            if (!text) return;
            pendingTexts.push(text);
            addChatMsg('student', text);
            studentInput.value = '';
            studentInput.style.height = '42px';
            document.getElementById('fileName').textContent = '';
        }

        function getPendingTexts() {
            var msgs = pendingTexts.slice();
            pendingTexts = [];
            return JSON.stringify(msgs);
        }

        function autoResize(el) {
            el.style.height = '42px';
            el.style.height = Math.min(el.scrollHeight, 150) + 'px';
        }

        function handleFileSelect(input) {
            var file = input.files[0];
            if (!file) return;
            var reader = new FileReader();
            reader.onload = function(e) {
                var content = e.target.result;
                studentInput.value = '# File: ' + file.name + '\n' + content;
                autoResize(studentInput);
                document.getElementById('fileName').textContent = file.name;
                studentInput.focus();
            };
            reader.readAsText(file);
            input.value = '';  // Reset so same file can be re-selected
        }

        // ── Called from Python via runJavaScript ──
        function handleEvent(data) {
            switch (data.type) {
                case 'student':
                    flushTeacherBuffer();
                    addChatMsg('student', data.text);
                    statusDot.className = 'status-dot connected';
                    statusText.textContent = 'Listening 🎤';
                    break;

                case 'teacher':
                    teacherBuffer += data.text + ' ';
                    clearTimeout(bufferTimer);
                    bufferTimer = setTimeout(flushTeacherBuffer, BUFFER_DELAY);
                    statusDot.className = 'status-dot speaking';
                    statusText.textContent = 'CHAHAT is speaking... 🗣️';
                    break;

                case 'tool':
                    flushTeacherBuffer();
                    addChatMsg('tool', '🔧 ' + data.name + ': ' + data.result);
                    // If it's run_python, show terminal
                    if (data.name === 'run_python') {
                        showTerminal(data.code || '', data.result || '');
                    }
                    break;

                case 'terminal':
                    showTerminal(data.code || '', data.output || '');
                    break;

                case 'notebook':
                    handwriteOnNotebook(data.content);
                    statusDot.className = 'status-dot speaking';
                    statusText.textContent = 'CHAHAT is writing... ✏️';
                    break;

                case 'connected':
                    if (!micMuted) {
                        statusDot.className = 'status-dot connected';
                        statusText.textContent = 'Listening 🎤';
                    }
                    break;

                case 'listening':
                    if (!micMuted) {
                        statusDot.className = 'status-dot connected';
                        statusText.textContent = 'Listening 🎤';
                    }
                    break;

                case 'dismiss_terminal':
                    hideTerminal();
                    break;

                case 'diagram':
                    flushTeacherBuffer();
                    showDiagram(data.code, data.diagram_type || 'mermaid', data.title || 'Diagram');
                    statusDot.className = 'status-dot speaking';
                    statusText.textContent = 'CHAHAT is drawing... 🎨';
                    break;

                case 'dismiss_diagram':
                    hideDiagram();
                    break;
                    
                case 'dashboard_data':
                    renderMemoryDashboard(data.payload);
                    break;
            }
        }

        function flushTeacherBuffer() {
            if (!teacherBuffer.trim()) return;
            const text = teacherBuffer.trim();
            teacherBuffer = '';
            clearTimeout(bufferTimer);
            addChatMsg('teacher', text);
            statusDot.className = 'status-dot connected';
            statusText.textContent = 'Listening 🎤';
        }

        // ── Chat messages ──
        function addChatMsg(type, text) {
            const msg = document.createElement('div');
            msg.className = 'msg ' + type;

            if (type === 'tool') {
                msg.textContent = text;
            } else {
                const label = document.createElement('div');
                label.className = 'msg-label';
                label.textContent = type === 'student' ? '🗣️ You' : '✏️ Chahat';
                const body = document.createElement('div');
                body.textContent = text;
                msg.appendChild(label);
                msg.appendChild(body);
            }

            chatMessages.appendChild(msg);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // ── Notebook handwriting ──
        function hideEmpty() {
            if (nbEmpty) nbEmpty.style.display = 'none';
        }

        function addNotebookStudent(text) {
            hideEmpty();
            const el = document.createElement('div');
            el.className = 'hw-student';
            el.textContent = '"' + text + '"';
            nbInner.appendChild(el);
            notebook.scrollTop = notebook.scrollHeight;
        }

        function addNotebookTool(name, result) {
            hideEmpty();
            const el = document.createElement('div');
            el.className = 'hw-tool';
            el.textContent = '🔧 ' + name + ': ' + result;
            nbInner.appendChild(el);
            notebook.scrollTop = notebook.scrollHeight;
        }

        function handwriteOnNotebook(text) {
            hideEmpty();
            const blocks = parseBlocks(text);
            blocks.forEach(function(block, i) {
                setTimeout(function() {
                    if (block.type === 'code') {
                        typewriteCode(block.content);
                    } else if (block.type === 'heading') {
                        typewriteHeading(block.content);
                    } else if (block.type === 'bullet') {
                        typewriteBullet(block.content);
                    } else {
                        typewriteText(block.content);
                    }
                }, i * 100);
            });
        }

        function parseBlocks(text) {
            var lines = text.split('\n');
            var blocks = [];
            var inCode = false;
            var codeContent = [];

            for (var idx = 0; idx < lines.length; idx++) {
                var line = lines[idx];
                if (line.trim().startsWith('```')) {
                    if (inCode) {
                        blocks.push({ type: 'code', content: codeContent.join('\n') });
                        codeContent = [];
                        inCode = false;
                    } else {
                        inCode = true;
                    }
                    continue;
                }

                if (inCode) {
                    codeContent.push(line);
                    continue;
                }

                var trimmed = line.trim();
                if (!trimmed) continue;

                if (trimmed.startsWith('# ') || trimmed.startsWith('## ') || trimmed.startsWith('### ')) {
                    var cleaned = trimmed.replace(/^#+\s*/, '');
                    blocks.push({ type: 'heading', content: cleaned });
                } else if (trimmed.startsWith('- ') || trimmed.startsWith('\u2022 ')) {
                    blocks.push({ type: 'bullet', content: trimmed.substring(2) });
                } else {
                    blocks.push({ type: 'text', content: trimmed });
                }
            }

            if (inCode && codeContent.length > 0) {
                blocks.push({ type: 'code', content: codeContent.join('\n') });
            }

            return blocks;
        }

        function typewriteText(text) {
            var block = document.createElement('div');
            block.className = 'hw-block';
            var content = document.createElement('div');
            content.className = 'hw-text';
            block.appendChild(content);
            nbInner.appendChild(block);
            animateWrite(content, text);
        }

        function typewriteHeading(text) {
            var el = document.createElement('div');
            el.className = 'hw-heading';
            nbInner.appendChild(el);
            animateWrite(el, text);
        }

        function typewriteBullet(text) {
            var el = document.createElement('div');
            el.className = 'hw-bullet';
            nbInner.appendChild(el);
            animateWrite(el, text);
        }

        function typewriteCode(text) {
            var el = document.createElement('div');
            el.className = 'hw-code';
            nbInner.appendChild(el);
            animateWrite(el, text, 15);
        }

        function animateWrite(el, text, speed) {
            speed = speed || 25;
            var i = 0;
            var cursor = document.createElement('span');
            cursor.className = 'cursor-blink';
            el.appendChild(cursor);

            function writeChar() {
                if (i < text.length) {
                    var charNode = document.createTextNode(text[i]);
                    el.insertBefore(charNode, cursor);
                    i++;
                    notebook.scrollTop = notebook.scrollHeight;

                    var delay = speed + Math.random() * 20;
                    if (text[i - 1] === '.' || text[i - 1] === '!' || text[i - 1] === '?') {
                        delay += 80;
                    } else if (text[i - 1] === ',') {
                        delay += 40;
                    } else if (text[i - 1] === '\n') {
                        delay += 60;
                    }

                    setTimeout(writeChar, delay);
                } else {
                    cursor.remove();
                }
            }

            writeChar();
        }

        // ══════ Terminal Functions ══════
        const terminalOverlay = document.getElementById('terminalOverlay');
        const terminalBody = document.getElementById('terminalBody');
        const termStatus = document.getElementById('termStatus');
        let terminalTimeout = null;

        function showTerminal(code, output) {
            // Clear previous content and timers
            if (terminalTimeout) clearTimeout(terminalTimeout);
            terminalBody.innerHTML = '';
            termStatus.innerHTML = '⏳ Running...';

            // Show overlay with animation
            terminalOverlay.classList.remove('hiding');
            terminalOverlay.classList.add('show');

            // Build code section
            var codeSection = document.createElement('div');
            codeSection.className = 'terminal-section';

            var codeLabel = document.createElement('div');
            codeLabel.className = 'terminal-section-label';
            codeLabel.textContent = '📝 CODE';
            codeSection.appendChild(codeLabel);

            var codeBox = document.createElement('div');
            codeBox.className = 'terminal-code';

            // Line numbers
            var codeLines = code.split('\n');
            var lineNums = document.createElement('div');
            lineNums.className = 'line-numbers';
            for (var ln = 1; ln <= codeLines.length; ln++) {
                lineNums.innerHTML += ln + '<br>';
            }
            codeBox.appendChild(lineNums);

            // Syntax highlighted code
            var codeContent = document.createElement('div');
            codeContent.className = 'code-content';
            codeContent.innerHTML = highlightPython(code);
            codeBox.appendChild(codeContent);

            codeSection.appendChild(codeBox);
            terminalBody.appendChild(codeSection);

            // Show output after a typing delay
            setTimeout(function() {
                var outputSection = document.createElement('div');
                outputSection.className = 'terminal-section';

                var outLabel = document.createElement('div');
                outLabel.className = 'terminal-section-label';
                outLabel.textContent = '💻 OUTPUT';
                outputSection.appendChild(outLabel);

                var outBox = document.createElement('div');
                outBox.className = 'terminal-output';

                // Prompt line
                var prompt = document.createElement('div');
                prompt.className = 'terminal-prompt';
                prompt.innerHTML = '<span class="prompt-symbol">❯</span> <span class="prompt-text">python3 code.py</span>';
                outBox.appendChild(prompt);

                // Clean output text (remove the ✅ prefix)
                var cleanOutput = output.replace(/^✅ (Output:\n?)?/i, '').trim();
                var isError = output.includes('❌');
                if (isError) {
                    cleanOutput = output.replace(/^❌ /i, '').trim();
                }

                var outText = document.createElement('div');
                outText.className = 'terminal-output-text';
                outText.style.color = isError ? '#f85149' : '#e6edf3';
                outBox.appendChild(outText);
                outputSection.appendChild(outBox);
                terminalBody.appendChild(outputSection);

                // Typewrite the output
                typewriteTerminal(outText, cleanOutput, function() {
                    // Update status bar
                    if (isError) {
                        termStatus.innerHTML = '❌ Error — CHAHAT will help fix it!';
                        termStatus.style.color = '#f85149';
                    } else {
                        termStatus.innerHTML = '✅ Code ran successfully! — CHAHAT will dismiss when ready';
                        termStatus.style.color = '#3fb950';
                    }
                    // Terminal stays open — CHAHAT will dismiss it via dismiss_terminal tool
                });
            }, 800);
        }

        function typewriteTerminal(el, text, callback) {
            var i = 0;
            var cursor = document.createElement('span');
            cursor.className = 'terminal-cursor-block';
            el.appendChild(cursor);

            function typeChar() {
                if (i < text.length) {
                    var ch = document.createTextNode(text[i]);
                    el.insertBefore(ch, cursor);
                    i++;
                    terminalBody.scrollTop = terminalBody.scrollHeight;
                    setTimeout(typeChar, 20 + Math.random() * 15);
                } else {
                    cursor.remove();
                    if (callback) callback();
                }
            }
            typeChar();
        }

        function hideTerminal() {
            terminalOverlay.classList.add('hiding');
            setTimeout(function() {
                terminalOverlay.classList.remove('show', 'hiding');
                terminalBody.innerHTML = '';
                termStatus.style.color = '';
            }, 400);
        }

        // ══════ Diagram / Whiteboard Functions ══════
        const diagramOverlay = document.getElementById('diagramOverlay');
        const diagramCanvas = document.getElementById('diagramCanvas');
        const diagramBadge = document.getElementById('diagramBadge');
        const diagramTypeEl = document.getElementById('diagramType');

        function showDiagram(code, type, title) {
            diagramCanvas.innerHTML = '';
            diagramOverlay.classList.remove('hiding');
            diagramOverlay.classList.add('show');

            if (type === 'mermaid') {
                diagramBadge.textContent = 'MERMAID';
                diagramTypeEl.textContent = '📊 Mermaid Diagram';

                // Clean up the mermaid code
                var cleanCode = code
                    .replace(/\\n/g, '\n')  // unescape newlines
                    .replace(/\\t/g, '  ')  // unescape tabs
                    .trim();

                var mermaidDiv = document.createElement('div');
                diagramCanvas.appendChild(mermaidDiv);

                try {
                    if (typeof mermaid !== 'undefined' && mermaid.mermaidAPI) {
                        mermaid.mermaidAPI.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });
                        var diagramId = 'diagram-' + Date.now();
                        mermaid.mermaidAPI.render(diagramId, cleanCode, function(svgCode) {
                            mermaidDiv.innerHTML = svgCode;
                        });
                    } else {
                        // Fallback: render via mermaid.ink service
                        var encoded = btoa(unescape(encodeURIComponent(cleanCode)));
                        mermaidDiv.innerHTML = '<img src="https://mermaid.ink/svg/' + encoded + '" style="max-width:100%;">';
                    }
                } catch(e) {
                    console.error('Mermaid local render failed, using mermaid.ink:', e);
                    var encoded2 = btoa(unescape(encodeURIComponent(cleanCode)));
                    mermaidDiv.innerHTML = '<img src="https://mermaid.ink/svg/' + encoded2 + '" style="max-width:100%;">';
                }
            } else if (type === 'html' || type === 'svg') {
                diagramBadge.textContent = type.toUpperCase();
                diagramTypeEl.textContent = type === 'svg' ? '🖼️ SVG Drawing' : '📐 HTML Diagram';
                diagramCanvas.innerHTML = code;
            } else {
                diagramBadge.textContent = 'DIAGRAM';
                diagramTypeEl.textContent = '📊 Diagram';
                diagramCanvas.innerHTML = code;
            }

            addChatMsg('tool', '🎨 Diagram: ' + title);
        }

        function hideDiagram() {
            diagramOverlay.classList.add('hiding');
            setTimeout(function() {
                diagramOverlay.classList.remove('show', 'hiding');
                diagramCanvas.innerHTML = '';
            }, 400);
        }

        function highlightPython(code) {
            // Simple Python syntax highlighter
            var escaped = code
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');

            // Comments
            escaped = escaped.replace(/(#.*)/g, '<span class="tk-comment">$1</span>');

            // Strings (double and single quoted)
            escaped = escaped.replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, '<span class="tk-string">$1</span>');

            // f-strings
            escaped = escaped.replace(/(f"(?:[^"\\]|\\.)*"|f'(?:[^'\\]|\\.)*')/g, '<span class="tk-string">$1</span>');

            // Keywords
            var keywords = ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'return',
                           'import', 'from', 'as', 'try', 'except', 'finally', 'with',
                           'in', 'not', 'and', 'or', 'is', 'True', 'False', 'None',
                           'break', 'continue', 'pass', 'lambda', 'yield', 'raise'];
            keywords.forEach(function(kw) {
                var re = new RegExp('\\b(' + kw + ')\\b', 'g');
                escaped = escaped.replace(re, '<span class="tk-keyword">$1</span>');
            });

            // Built-in functions
            var builtins = ['print', 'len', 'range', 'int', 'str', 'float', 'list',
                           'dict', 'set', 'tuple', 'type', 'input', 'open', 'map',
                           'filter', 'zip', 'enumerate', 'sorted', 'reversed', 'sum',
                           'min', 'max', 'abs', 'round'];
            builtins.forEach(function(fn) {
                var re = new RegExp('\\b(' + fn + ')(?=\\()', 'g');
                escaped = escaped.replace(re, '<span class="tk-builtin">$1</span>');
            });

            // Numbers
            escaped = escaped.replace(/\b(\d+\.?\d*)\b/g, '<span class="tk-number">$1</span>');

            return escaped;
        }

        // ── Save Notebook as PDF ──
        function saveNotebookAsPdf() {
            var btn = document.getElementById('savePdfBtn');
            // Gather all notebook content as markdown-like text
            var blocks = nbInner.querySelectorAll('.hw-heading, .hw-text, .hw-bullet, .hw-code, .hw-student, .hw-tool, .hw-block');
            if (blocks.length === 0) {
                alert('Notebook is empty — pehle kuch padho!');
                return;
            }

            var mdParts = [];
            blocks.forEach(function(block) {
                var text = block.textContent || '';
                if (block.classList.contains('hw-heading')) {
                    mdParts.push('## ' + text.trim());
                } else if (block.classList.contains('hw-code')) {
                    mdParts.push('```python\n' + text.trim() + '\n```');
                } else if (block.classList.contains('hw-bullet')) {
                    mdParts.push('- ' + text.trim());
                } else if (block.classList.contains('hw-student')) {
                    mdParts.push('> Student: ' + text.trim());
                } else if (block.classList.contains('hw-tool')) {
                    mdParts.push('> Tool: ' + text.trim());
                } else {
                    mdParts.push(text.trim());
                }
            });

            var markdownContent = mdParts.join('\n\n');
            pendingPdfSaves.push({
                title: 'CHAHAT_Notebook_' + new Date().toISOString().slice(0,10),
                content: markdownContent
            });

            // Visual feedback
            btn.textContent = '✅ Saving...';
            btn.classList.add('saving');
            setTimeout(function() {
                btn.textContent = '📄 Save PDF';
                btn.classList.remove('saving');
            }, 2500);
        }

        function getPendingPdfSaves() {
            var saves = pendingPdfSaves.slice();
            pendingPdfSaves = [];
            return JSON.stringify(saves);
        }

        function getPendingMemoryCmds() {
            var cmds = pendingMemoryCmds.slice();
            pendingMemoryCmds = [];
            return JSON.stringify(cmds);
        }

        // Mark ready
        statusDot.className = 'status-dot connected';
        statusText.textContent = 'Listening 🎤';
    </script>
</body>
</html>'''


class ChahatUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CHAHAT — Your AI Teacher 📚")
        self.setMinimumSize(1100, 700)
        self._page_ready = False
        self._pending_events = []
        self._build_ui()
        self._start_polling()

    def _build_ui(self):
        # Single QWebEngineView fills the entire window
        self.webview = QWebEngineView(self)
        self.setCentralWidget(self.webview)

        # Allow loading CDN scripts (Mermaid.js, Google Fonts) from file:// pages
        settings = self.webview.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

        # Wait for page to load before pushing events
        self.webview.loadFinished.connect(self._on_page_loaded)

        # Save HTML to temp file so CDN scripts (Mermaid.js) can load properly
        # setHtml() blocks external scripts; file:// loading does not
        import tempfile
        self._html_path = os.path.join(tempfile.gettempdir(), "chahat_notebook.html")
        with open(self._html_path, "w", encoding="utf-8") as f:
            f.write(NOTEBOOK_HTML)
        self.webview.load(QUrl.fromLocalFile(self._html_path))

    def _on_page_loaded(self, ok):
        """Called when the HTML page finishes loading."""
        if ok:
            self._page_ready = True
            print("✅ Notebook UI loaded")
            # Replay any events that arrived before page was ready
            for event in self._pending_events:
                self._push_to_webview(event)
            self._pending_events.clear()

    def _start_polling(self):
        """Poll UI_QUEUE every 50ms and push events to the web view."""
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_events)
        self.poll_timer.start(50)

        # Also poll for text input from student every 200ms
        self.text_timer = QTimer()
        self.text_timer.timeout.connect(self._poll_text_input)
        self.text_timer.start(200)

        # Poll for PDF save requests every 500ms
        self.pdf_timer = QTimer()
        self.pdf_timer.timeout.connect(self._poll_pdf_saves)
        self.pdf_timer.start(500)

        # Poll for Memory Commands every 200ms
        self.mem_timer = QTimer()
        self.mem_timer.timeout.connect(self._poll_memory_cmds)
        self.mem_timer.start(200)

        # Poll for Mic state changes every 100ms
        self.mic_timer = QTimer()
        self.mic_timer.timeout.connect(self._poll_mic_state)
        self.mic_timer.start(100)

    def _poll_events(self):
        while not UI_QUEUE.empty():
            try:
                event = UI_QUEUE.get_nowait()
                if self._page_ready:
                    self._push_to_webview(event)
                else:
                    self._pending_events.append(event)
            except queue.Empty:
                break

    def _poll_text_input(self):
        """Poll JavaScript for any text the student typed/pasted."""
        if not self._page_ready:
            return
        self.webview.page().runJavaScript(
            "if(typeof getPendingTexts==='function'){getPendingTexts();}else{'[]'}",
            self._handle_text_result
        )

    def _handle_text_result(self, result):
        """Process text messages from JavaScript."""
        if not result:
            return
        try:
            messages = json.loads(result)
            for msg in messages:
                if msg and msg.strip():
                    TEXT_QUEUE.put(msg.strip())
        except (json.JSONDecodeError, TypeError):
            pass

    def _poll_pdf_saves(self):
        """Poll JavaScript for PDF save requests from the Save PDF button."""
        if not self._page_ready:
            return
        self.webview.page().runJavaScript(
            "if(typeof getPendingPdfSaves==='function'){getPendingPdfSaves();}else{'[]'}",
            self._handle_pdf_result
        )

    def _handle_pdf_result(self, result):
        """Process PDF save requests from JavaScript."""
        if not result:
            return
        try:
            saves = json.loads(result)
            for save in saves:
                if save and save.get('title') and save.get('content'):
                    PDF_QUEUE.put(save)
        except (json.JSONDecodeError, TypeError):
            pass

    def _poll_memory_cmds(self):
        """Poll JavaScript for memory hub commands (delete, edit)."""
        if not self._page_ready:
            return
        self.webview.page().runJavaScript(
            "if(typeof getPendingMemoryCmds==='function'){getPendingMemoryCmds();}else{'[]'}",
            self._handle_memory_cmd_result
        )

    def _handle_memory_cmd_result(self, result):
        if not result:
            return
        try:
            cmds = json.loads(result)
            for cmd in cmds:
                if cmd:
                    MEMORY_CMD_QUEUE.put(cmd)
        except (json.JSONDecodeError, TypeError):
            pass

    def _poll_mic_state(self):
        """Poll JavaScript for mic mute/unmute toggle."""
        if not self._page_ready:
            return
        self.webview.page().runJavaScript(
            "if(typeof getPendingMicState==='function'){getPendingMicState();}else{'none'}",
            self._handle_mic_state_result
        )

    def _handle_mic_state_result(self, result):
        """Process mic state change from JavaScript."""
        if not result or result == 'none':
            return
        if result == 'muted':
            MIC_MUTED.set()
            print("🔇 Mic MUTED by user")
        elif result == 'unmuted':
            MIC_MUTED.clear()
            print("🎤 Mic UNMUTED by user")

    def _push_to_webview(self, event):
        """Call the JavaScript handleEvent() function with the event data."""
        event_json = json.dumps(event)
        js = f"if(typeof handleEvent==='function'){{handleEvent({event_json});}}"
        self.webview.page().runJavaScript(js)


def run_ui():
    """Start the PyQt5 UI. Call this from main thread."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette for window chrome
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#3a3226"))
    palette.setColor(QPalette.WindowText, QColor("#f5eddb"))
    app.setPalette(palette)

    window = ChahatUI()
    window.show()
    return app, window


# ── Standalone test ──────────────────────────────────────
if __name__ == "__main__":
    app, window = run_ui()

    # Push test events after 2s
    def test_events():
        UI_QUEUE.put({"type": "connected"})
        UI_QUEUE.put({"type": "student", "text": "Python kya hai?"})
        UI_QUEUE.put({"type": "teacher", "text": "Python ek programming language hai, bohot easy hai!"})
        UI_QUEUE.put({"type": "notebook", "content": "# Python Basics\n\nPython ek **programming language** hai.\n\n### Pehla Code:\n\n```python\nprint('Hello Python!')\n```\n\n- Simple syntax\n- Beginner friendly\n- Used everywhere!"})

    QTimer.singleShot(2000, test_events)
    sys.exit(app.exec_())
