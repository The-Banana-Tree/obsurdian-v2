#!/usr/bin/env python3
"""Obsurdian v2 — Simple Streamlit Documentation Portal"""

import streamlit as st
from pathlib import Path
import re
from datetime import datetime

# --- Config ---
APP_NAME = "Obsurdian v2"

# --- Page Config ---
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Markdown Parser ---
def parse_frontmatter(text):
    metadata = {}
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        in_frontmatter = True
        fm_lines = []
        for line in lines[1:]:
            if line.strip() == "---":
                in_frontmatter = False
                break
            fm_lines.append(line)
        for line in fm_lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key == "tags":
                    metadata[key] = [t.strip() for t in value.split(",") if t.strip()]
                else:
                    metadata[key] = value
    return metadata, text

# --- Auto-number headings (simple) ---
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

# --- Load all docs ---
def load_content():
    content = {}
    root_path = Path("content")
    if not root_path.exists():
        return {}, []
    
    modified_files = []
    for file_path in root_path.rglob("*.md"):
        try:
            text = file_path.read_text()
            metadata, body = parse_frontmatter(text)
            modified_files.append({
                "file": str(file_path),
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d"),
                "title": metadata.get("title", file_path.stem.replace("-", " ").title())
            })
            content[str(file_path)] = {"metadata": metadata, "content": auto_number_headings(body)}
        except Exception as e:
            st.error(f"Error: {e}")
    return content, modified_files

# --- Load ---
content_files, modified_files = load_content()

# --- Sidebar ---
with st.sidebar:
    st.header(f"🤖 {APP_NAME}")
    st.divider()
    
    if content_files:
        st.subheader("📚 Documents")
        for path, info in content_files.items():
            title = info["metadata"].get("title", path.replace(".md", "").replace("_", " ").title())
            st.page_link("app.py", label=f"📄 {title}", disabled=True)
        
        if modified_files:
            st.divider()
            st.subheader("⏰ Recent")
            for f in modified_files[:5]:
                st.caption(f"• {f['title']} ({f['modified']})")
    else:
        st.info("Add `.md` files to `content/` to get started.")

# --- Home ---
st.title(APP_NAME)
st.markdown("Your simple system documentation portal.")

col1, col2 = st.columns(2)
with col1:
    st.metric("Documents", len(content_files))
with col2:
    if content_files:
        folders = set(k.split("/")[0] for k in content_files.keys() if "/" in k)
        st.metric("Folders", len(folders))

st.divider()
st.markdown("💡 *Start adding docs to the `content/` folder!*")
