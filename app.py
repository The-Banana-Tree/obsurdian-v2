#!/usr/bin/env python3
"""Obsurdian v2 — Mobile-First Streamlit Docs Portal"""

import streamlit as st
from pathlib import Path
import re
import os

# --- Config ---
APP_NAME = "Obsurdian v2"
CONTENT_DIR = Path(os.environ.get("CONTENT_DIR", "content"))

# --- Page Config (Mobile Optimized) ---
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",  # Sidebar hidden on mobile by default
)

# --- Auto-number headings ---
def auto_number_headings(text):
    lines = text.splitlines()
    numbers = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    result = []
    for line in lines:
        match = re.match(r'^(#{1,6})\s+(.*)$', line)
        if match:
            level = len(match.group(1))
            content = match.group(2)
            if re.match(r'^\d+\.\d*\s', content):
                result.append(line)
                continue
            numbers[level] += 1
            for lvl in range(level + 1, 7):
                numbers[lvl] = 0
            number_parts = [str(numbers[lvl]) for lvl in range(1, level + 1)]
            number_str = ".".join(number_parts)
            result.append(f"{'#' * level} {number_str} {content}")
        else:
            result.append(line)
    return "\n".join(result)

# --- Load all docs (recursive) ---
def load_all_docs():
    docs = {}
    folders = {}
    
    if not CONTENT_DIR.exists():
        return docs, folders
    
    for file_path in CONTENT_DIR.rglob("*.md"):
        try:
            text = file_path.read_text()
            clean_path = str(file_path).replace("content/", "").replace("content\\", "")
            
            if "/" in clean_path or "\\" in clean_path:
                folder = clean_path.split("/")[0] if "/" in clean_path else clean_path.split("\\")[0]
            else:
                folder = "root"
            
            docs[clean_path] = {
                "content": auto_number_headings(text),
                "folder": folder,
                "modified": file_path.stat().st_mtime
            }
            
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(clean_path)
            
        except Exception as e:
            st.error(f"Error loading {file_path}: {e}")
    
    return docs, folders

# --- Load ---
docs, folders = load_all_docs()

# --- Mobile-First Layout ---
st.title(f"🤖 {APP_NAME}")

# Mobile card layout
if not docs:
    st.info("📁 Add `.md` files to `content/` folder to get started!")
else:
    # Show folder cards
    st.subheader("📚 Documents")
    
    for folder in sorted(folders.keys()):
        with st.expander(f"📁 {folder} ({len(folders[folder])} docs)", expanded=False):
            for doc_path in sorted(folders[folder]):
                title = doc_path.replace(".md", "").replace("_", " ").title()
                # Create page link
                st.page_link("app.py", label=f"📄 {title}", disabled=True)

# Stats (mobile-friendly)
col1, col2 = st.columns(2)
with col1:
    st.metric("Documents", len(docs))
with col2:
    st.metric("Folders", len(folders))

st.divider()
st.caption("💡 *Tap folders to browse docs on mobile!*")
