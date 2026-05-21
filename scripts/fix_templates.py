from pathlib import Path

for p in Path("templates").rglob("*.html"):
    t = p.read_text(encoding="utf-8")
    n = t.replace("<motion", "<div").replace("</motion>", "</div>")
    if n != t:
        p.write_text(n, encoding="utf-8")
        print("fixed", p)
