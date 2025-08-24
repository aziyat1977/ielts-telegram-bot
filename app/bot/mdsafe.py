from __future__ import annotations
import re

# Escape Telegram Markdown special characters conservatively.
# Works with both "Markdown" and "MarkdownV2" parse modes for user-supplied text.
_MD_SPECIAL = r'([_*\[\]()~`>#+\-=|{}.!])'

def escape_md(s: str) -> str:
    if not s:
        return s
    return re.sub(_MD_SPECIAL, r'\\\1', s)