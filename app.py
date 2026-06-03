#!/usr/bin/env python3
"""
Obsurdian v2 — Production-Grade Documentation Platform (P0 Implementation)

Features:
- Recursive folder discovery
- Hierarchical tree navigation with expand/collapse
- Click-to-open docs in sidebar
- Auto-index page generation
- Frontmatter support with badges
- Mobile-responsive layout\n\nv2.2 — Removed metadata badges from doc pages for clean UI
"""

import streamlit as st
from pathlib import Path
import re
import os
import json
from datetime import datetime

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

# --- Session State ---
if "expanded_folders" not in st.session_state:
    st.session_state.expanded_folders = set()
if "selected_doc" not in st.session_state:
    st.session_state.selected_doc = None
if "recent_docs" not in st.session_state:
    st.session_state.recent_docs = []

# --- Parsing Functions ---

def parse_frontmatter(text):
    """Parse YAML frontmatter from markdown, return (metadata, body)."""
    metadata = {}
    lines = text.splitlines()
    
    if lines and lines[0].strip() == "---":
        in_frontmatter = True
        fm_lines = []
        body_lines = []
        
        for i, line in enumerate(lines[1:]):
            if line.strip() == "---":
                in_frontmatter = False
                body_lines = lines[i+2:]  # After closing ---
                break
            fm_lines.append(line)
        
        # Build metadata from frontmatter lines
        for line in fm_lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key == "tags":
                    metadata[key] = [t.strip() for t in value.split(",") if t.strip()]
                else:
                    metadata[key] = value
    else:
        body_lines = lines
    
    return metadata, "\n".join(body_lines)

def auto_number_headings(text):
    """Auto-number headings in markdown."""
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

def extract_headings(text):
    """Extract heading hierarchy for TOC."""
    lines = text.splitlines()
    headings = []
    for line in lines:
        match = re.match(r'^(#{1,6})\s+(.*)$', line)
        if match:
            level = len(match.group(1))
            content = match.group(2).strip()
            # Clean for ID
            clean_text = re.sub(r'[^\w\s-]', '', content).lower().replace(' ', '-')
            headings.append({"level": level, "text": content, "id": clean_text})
    return headings

# --- File Discovery ---

def get_folder_order(folder_name):
    """Extract numeric order from folder prefix like '01-Systems'."""
    match = re.match(r'^(\d+)-', folder_name)
    if match:
        return int(match.group(1))
    return 999  # No prefix = last

def load_all_docs():
    """Load all docs, build folder tree."""
    docs = {}
    folders = {}
    
    if not CONTENT_DIR.exists():
        return docs, folders
    
    # First pass: collect all docs
    for file_path in CONTENT_DIR.rglob("*.md"):
        try:
            text = file_path.read_text()
            clean_path = str(file_path).replace("content/", "").replace("content\\", "")
            
            # Extract folder hierarchy
            parts = clean_path.split("/")
            folder_path = "/".join(parts[:-1]) if len(parts) > 1 else "root"
            
            metadata, body = parse_frontmatter(text)
            
            docs[clean_path] = {
                "path": str(file_path),
                "clean_path": clean_path,
                "folder": folder_path,
                "metadata": metadata,
                "content": auto_number_headings(body),
                "headings": extract_headings(body),
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime),
            }
            
            # Build folder structure
            folder_parts = folder_path.split("/") if folder_path != "root" else []
            current = folders
            for part in folder_parts:
                if part not in current:
                    order = get_folder_order(part)
                    current[part] = {"order": order, "docs": [], "folders": {}}
                current = current[part]["folders"]
            
            # Add doc to leaf folder
            if folder_path != "root":
                parent = folders
                for part in folder_parts[:-1]:
                    parent = parent[part]["folders"]
                leaf = folder_parts[-1]
                parent[leaf]["docs"].append(clean_path)
            else:
                folders["root_docs"] = folders.get("root_docs", [])
                folders["root_docs"].append(clean_path)
                
        except Exception as e:
            st.error(f"Error loading {file_path}: {e}")
    
    return docs, folders

# --- Rendering Functions ---

def render_breadcrumbs(clean_path):
    """Render path breadcrumbs."""
    parts = clean_path.split("/")
    if len(parts) == 1:
        return  # Single file, no breadcrumbs needed
    
    crumb_path = []
    crumb_links = ["[🏠 Home](app.py)"]
    
    for i, part in enumerate(parts[:-1]):
        crumb_path.append(part)
        crumb_links.append(f"[{part}](app.py?folder={'/'.join(crumb_path)})")
    
    crumb_links.append(f"📄 {parts[-1].replace('.md', '')}")
    st.markdown(" > ".join(crumb_links), unsafe_allow_html=True)

def render_document(doc_data):
    """Render a single document."""
    metadata = doc_data["metadata"]
    content = doc_data["content"]
    
    # Title
    title = metadata.get("title", doc_data["clean_path"].replace(".md", "").replace("_", " ").title())
    st.title(title)
    
    # Breadcrumbs
    render_breadcrumbs(doc_data["clean_path"])
    
    st.divider()
    
    # Table of Contents (if headings exist)
    if doc_data["headings"]:
        with st.expander("📋 On This Page", expanded=False):
            for h in doc_data["headings"]:
                indent = "  " * (h["level"] - 2)
                st.markdown(f"{indent}- [{h['text']}](#{h['id']})")
    
    st.divider()
    
    # Content
    st.markdown(content, unsafe_allow_html=False)
    
    # Navigation (Prev/Next)
    doc_path = doc_data["clean_path"]
    parts = doc_path.split("/")
    folder_path = "/".join(parts[:-1]) if len(parts) > 1 else "root"
    
    docs_in_folder = [d for d in st.session_state.all_docs.values() 
                     if d["folder"] == folder_path]
    
    if docs_in_folder:
        idx = docs_in_folder.index(doc_data)
        col1, col2 = st.columns(2)
        with col1:
            if idx > 0:
                prev = docs_in_folder[idx - 1]
                if st.button("⬅️ Previous", key=f"prev_{doc_path}"):
                    st.session_state.selected_doc = prev["clean_path"]
        with col2:
            if idx < len(docs_in_folder) - 1:
                next_doc = docs_in_folder[idx + 1]
                if st.button("Next ➡️", key=f"next_{doc_path}"):
                    st.session_state.selected_doc = next_doc["clean_path"]

# --- Sidebar Navigation ---

def render_tree(folder_data, prefix=""):
    """Recursively render folder tree in sidebar."""
    # Skip root_docs which is a list, not a folder dict
    items = sorted(
        [(k, v) for k, v in folder_data.items() if k != "root_docs"],
        key=lambda x: (x[1].get("order", 999), x[0].lower())
    )
    
    for name, data in items:
        # Skip order field
        if name == "order":
            continue
            
        folder_name = re.sub(r'^\d+-', '', name)  # Remove prefix for display
        
        # Count docs in this folder
        doc_count = len(data.get("docs", []))
        
        # Create expandable section
        exp_key = f"exp_{prefix}_{name}" if prefix else f"exp_{name}"
        is_expanded = exp_key in st.session_state.expanded_folders
        
        with st.expander(f"📁 {folder_name} ({doc_count} docs)", expanded=is_expanded):
            # Update expanded state
            if is_expanded:
                st.session_state.expanded_folders.add(exp_key)
            else:
                st.session_state.expanded_folders.discard(exp_key)
            
            # Render subfolders recursively
            subfolders = {k: v for k, v in data.items() if k != "order" and k != "docs"}
            if subfolders:
                render_tree(subfolders, f"{prefix}_{name}")
            
            # Render docs in this folder
            for doc_path in data.get("docs", []):
                doc = st.session_state.all_docs.get(doc_path)
                if doc:
                    title = doc["metadata"].get("title", doc_path.replace(".md", "").replace("_", " ").title())
                    if st.button(f"📄 {title}", key=f"doc_{doc_path}"):
                        st.session_state.selected_doc = doc_path
                        if doc_path not in st.session_state.recent_docs:
                            st.session_state.recent_docs.insert(0, doc_path)
                            st.session_state.recent_docs = st.session_state.recent_docs[:5]

# --- Main App ---

# Load docs
st.session_state.all_docs, folder_tree = load_all_docs()

# --- Sidebar ---
with st.sidebar:
    st.header(f"🤖 {APP_NAME}")
    st.divider()
    
    # Search (simple in-memory)
    search_query = st.text_input("🔍 Search...", "", placeholder="Search docs...")
    
    # Recent docs
    if st.session_state.recent_docs:
        st.subheader("⏰ Recent")
        for doc_path in st.session_state.recent_docs:
            doc = st.session_state.all_docs.get(doc_path)
            if doc:
                title = doc["metadata"].get("title", doc_path.replace(".md", "").replace("_", " ").title())
                st.caption(f"• {title}")
        st.divider()
    
    # Folder tree
    st.subheader("📚 Documents")
    render_tree(folder_tree)
    
    # Global stats
    st.divider()
    st.caption(f"**Total:** {len(st.session_state.all_docs)} docs")

# --- Main Content ---
st.title(f"🤖 {APP_NAME}")

# Stats - only on home page
if not st.session_state.selected_doc and not search_query:
    st.markdown("Your internal documentation platform.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Documents", len(st.session_state.all_docs))
    with col2:
        st.metric("Folders", len(folder_tree) - 1)
    with col3:
        st.metric("Status", "✅ Online")

    st.divider()

# Filter by search
if search_query:
    search_query = search_query.lower()
    matching_docs = [
        doc for doc in st.session_state.all_docs.values()
        if search_query in doc["metadata"].get("title", "").lower() or
           search_query in doc["content"].lower() or
           any(search_query in tag.lower() for tag in doc["metadata"].get("tags", []))
    ]
    
    if matching_docs:
        st.subheader(f"Searching: '{search_query}'")
        for doc in matching_docs:
            title = doc["metadata"].get("title", doc["clean_path"].replace(".md", "").replace("_", " ").title())
            if st.button(f"📄 {title}", key=f"search_{doc['clean_path']}"):
                st.session_state.selected_doc = doc["clean_path"]
    else:
        st.info("No matches found.")
else:
    # Home page or selected doc
    if st.session_state.selected_doc:
        doc = st.session_state.all_docs[st.session_state.selected_doc]
        render_document(doc)
    else:
        # Home page (check for root index)
        home_doc = st.session_state.all_docs.get("index.md")
        if home_doc:
            render_document(home_doc)
        else:
            st.markdown("""
            ## Welcome to Obsurdian v2 🤖
            
            This is your internal documentation platform.
            
            ### How it works:
            1. Add `.md` files to the `content/` folder
            2. Folder structure becomes navigation
            3. Click any doc to view
            
            ### Features:
            - Auto-numbered headings
            - Hierarchical navigation
            - Frontmatter support
            - Mobile-responsive
            """)
# Version: 2.2
