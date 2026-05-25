import csv
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_JS_DIR = PROJECT_ROOT / "static" / "js"

def get_html_files():
    html_files = []
    if TEMPLATES_DIR.exists():
        for root, _, files in os.walk(TEMPLATES_DIR):
            for f in files:
                if f.endswith(".html"):
                    html_files.append(Path(root) / f)
    return html_files

def get_js_files():
    js_files = []
    if STATIC_JS_DIR.exists():
        for root, _, files in os.walk(STATIC_JS_DIR):
            for f in files:
                if f.endswith(".js"):
                    js_files.append(Path(root) / f)
    return js_files

def parse_html_files(html_files):
    gui_features = []
    # Regex to find elements with hx-get, hx-post, or action
    # This is a naive regex for extraction
    attr_re = re.compile(r'\b(hx-get|hx-post|action)\s*=\s*["\']([^"\']+)["\']')
    id_class_re = re.compile(r'\b(id|class)\s*=\s*["\']([^"\']+)["\']')
    
    for hf in html_files:
        content = hf.read_text(encoding="utf-8")
        # Split by < to roughly get tags
        tags = content.split('<')
        for tag in tags:
            tag = tag.strip()
            if not tag: continue
            
            # Find the tag name
            tag_name = tag.split()[0] if tag else "unknown"
            
            # Extract relevant attributes
            attrs = attr_re.findall(tag)
            if not attrs:
                continue
                
            # Find id or class for context
            id_classes = id_class_re.findall(tag)
            element_context = ""
            for k, v in id_classes:
                element_context += f"[{k}: {v}]"
                
            for attr, value in attrs:
                gui_features.append({
                    "template": hf.relative_to(PROJECT_ROOT).as_posix(),
                    "element": tag_name,
                    "context": element_context,
                    "action_type": attr,
                    "endpoint": value,
                    "status": "CONNECTED" # Default, will be cross-referenced later
                })
    return gui_features

def parse_js_files(js_files, html_files):
    js_events = []
    
    # Check JS files
    event_re = re.compile(r'\.addEventListener\s*\(\s*["\']([^"\']+)["\']')
    fetch_re = re.compile(r'\bfetch\s*\(\s*["\']([^"\']+)["\']')
    htmx_re = re.compile(r'htmx\.on\s*\(\s*["\']([^"\']+)["\']')
    
    for jf in js_files:
        content = jf.read_text(encoding="utf-8")
        rel_path = jf.relative_to(PROJECT_ROOT).as_posix()
        
        for match in event_re.finditer(content):
            js_events.append({
                "source": rel_path,
                "event_type": "addEventListener",
                "event_name": match.group(1),
                "target_endpoint": "N/A"
            })
            
        for match in fetch_re.finditer(content):
            js_events.append({
                "source": rel_path,
                "event_type": "fetch",
                "event_name": "API Call",
                "target_endpoint": match.group(1)
            })
            
        for match in htmx_re.finditer(content):
            js_events.append({
                "source": rel_path,
                "event_type": "htmx.on",
                "event_name": match.group(1),
                "target_endpoint": "N/A"
            })
            
    # Also check inline script tags in HTML
    for hf in html_files:
        content = hf.read_text(encoding="utf-8")
        rel_path = hf.relative_to(PROJECT_ROOT).as_posix()
        
        # very basic inline script extraction
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, flags=re.DOTALL | re.IGNORECASE)
        for script_content in scripts:
            for match in event_re.finditer(script_content):
                js_events.append({
                    "source": rel_path + " (inline)",
                    "event_type": "addEventListener",
                    "event_name": match.group(1),
                    "target_endpoint": "N/A"
                })
            for match in fetch_re.finditer(script_content):
                js_events.append({
                    "source": rel_path + " (inline)",
                    "event_type": "fetch",
                    "event_name": "API Call",
                    "target_endpoint": match.group(1)
                })
            for match in htmx_re.finditer(script_content):
                js_events.append({
                    "source": rel_path + " (inline)",
                    "event_type": "htmx.on",
                    "event_name": match.group(1),
                    "target_endpoint": "N/A"
                })

    return js_events

def main():
    html_files = get_html_files()
    js_files = get_js_files()
    
    gui_features = parse_html_files(html_files)
    js_events = parse_js_files(js_files, html_files)
    
    # Write gui_feature_matrix.csv
    with open(PROJECT_ROOT / "gui_feature_matrix.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["template", "element", "context", "action_type", "endpoint", "status"])
        writer.writeheader()
        writer.writerows(gui_features)
        
    # Write frontend_event_matrix.csv
    with open(PROJECT_ROOT / "frontend_event_matrix.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "event_type", "event_name", "target_endpoint"])
        writer.writeheader()
        writer.writerows(js_events)

if __name__ == "__main__":
    main()
