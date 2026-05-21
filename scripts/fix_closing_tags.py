from pathlib import Path

wrong = "</" + "m" + "o" + "t" + "i" + "o" + "n>"
right = "</" + "d" + "i" + "v>"

for p in Path("templates").rglob("*.html"):
    t = p.read_text(encoding="utf-8")
    if wrong in t:
        p.write_text(t.replace(wrong, right), encoding="utf-8")
        print("fixed", p)
