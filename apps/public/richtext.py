import re
from html.parser import HTMLParser
from urllib.parse import urlparse

from django.utils.html import escape

HTML_TAG_RE = re.compile(r"<[a-zA-Z/][^>]*>")
ALLOWED_TAGS = {"p", "br", "strong", "em", "ul", "ol", "li", "a", "h2", "h3", "blockquote"}
VOID_TAGS = {"br"}
ALLOWED_REL = {"noopener", "noreferrer", "nofollow"}
ALLOWED_SCHEMES = {"http", "https", "mailto"}


def looks_like_html(value):
    return bool(HTML_TAG_RE.search(value or ""))


def sanitize_url(value):
    candidate = (value or "").strip()
    if not candidate:
        return ""

    if candidate.startswith("/") or candidate.startswith("#"):
        return candidate

    parsed = urlparse(candidate)
    if parsed.scheme in ALLOWED_SCHEMES:
        return candidate

    return ""


def plain_text_to_html(value):
    text = (value or "").replace("\r\n", "\n").strip()
    if not text:
        return ""

    paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    html_parts = []
    for paragraph in paragraphs:
        html_parts.append(f"<p>{escape(paragraph).replace(chr(10), '<br>')}</p>")
    return "".join(html_parts)


class LimitedHTMLSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag not in ALLOWED_TAGS:
            return

        if tag in VOID_TAGS:
            self.parts.append("<br>")
            return

        attr_text = ""
        if tag == "a":
            cleaned = {}
            for name, value in attrs:
                name = (name or "").lower()
                value = (value or "").strip()
                if not value:
                    continue

                if name == "href":
                    safe_value = sanitize_url(value)
                    if safe_value:
                        cleaned["href"] = safe_value
                elif name == "target" and value == "_blank":
                    cleaned["target"] = "_blank"
                elif name == "rel":
                    rel_tokens = [token for token in value.split() if token in ALLOWED_REL]
                    if rel_tokens:
                        cleaned["rel"] = " ".join(rel_tokens)

            if "target" in cleaned and "rel" not in cleaned:
                cleaned["rel"] = "noopener noreferrer"

            attr_text = "".join(f' {name}="{escape(value)}"' for name, value in cleaned.items())

        self.parts.append(f"<{tag}{attr_text}>")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag not in ALLOWED_TAGS or tag in VOID_TAGS or tag not in self.stack:
            return

        while self.stack:
            current = self.stack.pop()
            self.parts.append(f"</{current}>")
            if current == tag:
                break

    def handle_startendtag(self, tag, attrs):
        if tag.lower() in VOID_TAGS:
            self.parts.append("<br>")

    def handle_data(self, data):
        self.parts.append(escape(data))

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def get_html(self):
        while self.stack:
            self.parts.append(f"</{self.stack.pop()}>")
        return "".join(self.parts)


def sanitize_rich_text_html(value):
    sanitizer = LimitedHTMLSanitizer()
    sanitizer.feed(value or "")
    sanitizer.close()
    return sanitizer.get_html().strip()


def normalize_rich_text(value):
    text = (value or "").strip()
    if not text:
        return ""

    if looks_like_html(text):
        return sanitize_rich_text_html(text)

    return plain_text_to_html(text)
