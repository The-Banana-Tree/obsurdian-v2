#!/usr/bin/env python3
"""Obsurdian v2 — Pure Markdown Docs, Simple Streamlit UI"""

import streamlit as st
from pathlib import Path
import re
import os

# --- Config ---
APP_NAME = "Obsurdian v2"
CONTENT_DIR = Path(os.environ.get("CONTENT_DIR", "content"))

# --- Page Config ---
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
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
            # Clean path: remove leading "content/" or "content\\" 
            clean_path = str(file_path).replace("content/", "").replace("content\\", "")
            
            # Extract folder path
            if "/" in clean_path or "\\" in clean_path:
                folder = clean_path.split("/")[0] if "/" in clean_path else clean_path.split("\\")[0]
            else:
                folder = "root"
            
            docs[clean_path] = {
                "content": auto_number_headings(text),
                "folder": folder,
                "modified": file_path.stat().st_mtime
            }
            
            # Track folders
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(clean_path)
            
        except Exception as e:
            st.error(f"Error loading {file_path}: {e}")
    
    return docs, folders

# --- Load ---
docs, folders = load_all_docs()

# --- Sidebar ---
with st.sidebar:
    st.header(f"🤖 {APP_NAME}")
    st.divider()
    
    if not docs:
        st.info("📁 Add `.md` files to `content/` folder to get started!")
    else:
        # Group by folder
        for folder in sorted(folders.keys()):
            st.subheader(f"📁 {folder}")
            for doc_path in sorted(folders[folder]):
                title = doc_path.replace(".md", "").replace("_", " ").title()
                # Create page link (Streamlit multi-page auto-detects subdirs)
                st.page_link("app.py", label=f"📄 {title}", disabled=True)
        
        st.divider()
        st.caption(f"{len(docs)} documents across {len(folders)} folders")

# --- Route: folder view or doc view ---
query = st.query_params.get("folder")
if query and query in folders:
    # Folder view
    folder_name = query
    st.title(f"📁 {folder_name}")
    st.divider()
    for doc_path in sorted(folders[folder_name]):
        title = doc_path.replace(".md", "").replace("_", " ").title()
        st.page_link("app.py", label=f"📄 {title}", disabled=True)

else:
    # Home view
    st.title(APP_NAME)
    st.markdown("Your simple, markdown-powered documentation portal.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Documents", len(docs))
    with col2:
        st.metric("Folders", len(folders))
    with col3:
        st.metric("Ready", "✅")
    
    st.divider()
    st.markdown("💡 *Click any folder in sidebar to browse docs!*")
