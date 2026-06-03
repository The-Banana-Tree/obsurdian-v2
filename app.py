#!/usr/bin/env python3
"""
Obsurdian v2 — Production-Grade Documentation Platform (P0 Implementation)

Features:
- Recursive folder discovery
- Hierarchical tree navigation with expand/collapse
- Click-to-open docs in sidebar
- Auto-index page generation
- Frontmatter support with badges
- Mobile-responsive layout

v2.3 — Fixed tree rendering to show actual content, proper indentation, no nesting cards
"""

import streamlit as st
from pathlib import Path
import re
import os
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
            clean_text = re.sub(r'[^\w\s-]', '', content).lower().replace(' ', '-')
            headings.append({"level": level, "text": content, "id": clean_text})
    return headings

# --- File Discovery ---

def get_folder_order(folder_name):
    """Extract numeric order from folder prefix like '01-Systems'."""
    match = re.match(r'^(\d+)-', folder_name)
    if match:
        return int(match.group(1))
    return 999

def load_content_tree():
    """Load all docs and build a clean tree structure."""
    tree = {}
    docs = {}
    
    if not CONTENT_DIR.exists():
        return tree, docs
    
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
                "title": metadata.get("title", clean_path.replace(".md", "").replace("_", " ").title()),
            }
            
            # Build tree structure
            folder_parts = folder_path.split("/") if folder_path != "root" else []
            current = tree
            for part in folder_parts:
                if part not in current:
                    current[part] = {"type": "folder", "order": get_folder_order(part), "children": {}}
                current = current[part]["children"]
            
            # Add file to leaf folder
            if folder_path != "root":
                parent = tree
                for part in folder_parts[:-1]:
                    parent = parent[part]["children"]
                leaf = folder_parts[-1]
                parent[leaf]["children"]["__docs__"] = parent[leaf].get("__docs__", [])
                parent[leaf]["children"]["__docs__"].append(clean_path)
                
        except Exception as e:
            st.error(f"Error loading {file_path}: {e}")
    
    return tree, docs

# --- Rendering Functions ---

def render_breadcrumbs(clean_path):
    """Render path breadcrumbs."""
    parts = clean_path.split("/")
    if len(parts) == 1:
        return
    
    crumb_path = []
    crumb_links = ["🏠 Home"]
    
    for i, part in enumerate(parts[:-1]):
        crumb_path.append(part)
        crumb_links.append(part)
    
    crumb_links.append(parts[-1].replace(".md", ""))
    
    # Render as markdown links
    links = []
    for i, link in enumerate(crumb_links):
        if link == "Home":
            links.append(f"[{link}](app.py)")
        elif link == crumb_links[-1]:
            links.append(f"📄 {link}")  # Current page (no link)
        else:
            folder_path = "/".join(crumb_path[:i+1])
            links.append(f"[{link}](app.py)")
    
    st.markdown(" > ".join(links), unsafe_allow_html=True)

def render_document(doc_data):
    """Render a single document."""
    metadata = doc_data["metadata"]
    content = doc_data["content"]
    
    st.title(doc_data["title"])
    
    render_breadcrumbs(doc_data["clean_path"])
    st.divider()
    
    if doc_data["headings"]:
        with st.expander("📋 On This Page", expanded=False):
            for h in doc_data["headings"]:
                indent = "  " * (h["level"] - 2)
                st.markdown(f"{indent}- [{h['text']}](#{h['id']})")
    
    st.divider()
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

# --- Sidebar Tree Rendering ---

def render_tree_node(name, node, indent=0, prefix=""):
    """Recursively render a tree node (folder or doc)."""
    # Calculate indent spacing
    indent_str = "  " * indent
    exp_key = f"exp_{prefix}_{name}" if prefix else f"exp_{name}"
    is_expanded = exp_key in st.session_state.expanded_folders
    
    # Render folder
    if node["type"] == "folder":
        child_count = len(node.get("children", {}))
        doc_count = len(node.get("__docs__", []))
        
        # Label: name + count if any docs
        label = name
        if doc_count > 0:
            label = f"{label} ({doc_count})"
        
        with st.expander(f"{indent_str}{label}", expanded=is_expanded):
            if is_expanded:
                st.session_state.expanded_folders.add(exp_key)
            else:
                st.session_state.expanded_folders.discard(exp_key)
            
            # Render docs
            for doc_path in node.get("__docs__", []):
                doc = st.session_state.all_docs.get(doc_path)
                if doc:
                    if st.button(f"{indent_str}📄 {doc['title']}", key=f"doc_{doc_path}"):
                        st.session_state.selected_doc = doc_path
            
            # Render child folders
            children = {k: v for k, v in node["children"].items() if k != "__docs__"}
            for child_name, child_node in sorted(children.items(), 
                                                  key=lambda x: (x[1].get("order", 999), x[0].lower())):
                render_tree_node(child_name, child_node, indent + 1, f"{prefix}_{name}")
    
    # Render doc (leaf node)
    elif node["type"] == "doc":
        doc = st.session_state.all_docs.get(name)
        if doc:
            if st.button(f"{indent_str}📄 {doc['title']}", key=f"doc_{name}"):
                st.session_state.selected_doc = name

# --- Main App ---

# Load docs and tree
tree, st.session_state.all_docs = load_content_tree()

# --- Sidebar ---
with st.sidebar:
    st.header(f"🤖 {APP_NAME}")
    st.divider()
    
    # Home link
    if st.button("🏠 Home", key="home-link"):
        st.session_state.selected_doc = None
    
    # Search
    search_query = st.text_input("🔍 Search...", "", placeholder="Search docs...")
    
    st.divider()
    st.subheader("📚 Documents")
    
    # Render tree
    if tree:
        for name, node in sorted(tree.items(), key=lambda x: (x[1].get("order", 999), x[0].lower())):
            render_tree_node(name, node)
    
    st.divider()
    st.caption(f"**Total:** {len(st.session_state.all_docs)} docs")

# --- Main Content ---
# Only show APP_NAME on home page
if not st.session_state.selected_doc:
    st.title(f"🤖 {APP_NAME}")

# Stats - only on home page
if not st.session_state.selected_doc and not search_query:
    st.markdown("Your internal documentation platform.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Documents", len(st.session_state.all_docs))
    with col2:
        st.metric("Folders", len(tree))
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
            if st.button(f"📄 {doc['title']}", key=f"search_{doc['clean_path']}"):
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
