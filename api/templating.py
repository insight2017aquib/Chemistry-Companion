from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.templating import Jinja2Templates


def create_templates(directory: str | Path) -> Jinja2Templates:
    env = Environment(
        loader=FileSystemLoader(str(directory)),
        autoescape=select_autoescape(["html", "xml"]),
        cache_size=0,
    )
    return Jinja2Templates(env=env)
