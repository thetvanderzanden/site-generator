"""
Reads a .docx business plan and uses Claude to extract structured site data.
"""

import json
import os
import re
import urllib.request
import anthropic
from docx import Document


def extract_text_from_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


EXTRACTION_PROMPT = """You are extracting information from a business plan document to populate a website template.

Read the document carefully and return a JSON object with exactly these fields.
If a field cannot be determined from the document, use a sensible placeholder.

Return ONLY valid JSON — no markdown, no explanation.

{
  "company_name": "Full legal or trade name of the business",
  "tagline": "Short punchy slogan or value proposition (max 8 words)",
  "description": "One sentence describing what the business does and who it serves",
  "full_description": "Two to three sentences for the About section",
  "city": "City where the business is located",
  "state": "Full state name",
  "state_abbr": "Two-letter state abbreviation e.g. TX",
  "domain": "yourdomain.com (guess from company name if not stated, no www)",
  "email": "contact email address",
  "phone": "+1-XXX-XXX-XXXX formatted phone number",
  "services": ["Service 1", "Service 2", "Service 3"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "color_primary": "#hex — dominant brand color (guess from industry if not stated)",
  "color_accent": "#hex — secondary brand color",
  "color_action": "#hex — CTA / link color",
  "hero_headline": "Compelling hero headline (max 10 words, may use line breaks with \\n)",
  "hero_subtext": "Supporting paragraph under the headline (2-3 sentences)",
  "value_proposition": "Brief value proposition for meta description (1-2 sentences)",
  "lat": "Latitude as decimal string e.g. 30.2672",
  "lng": "Longitude as decimal string e.g. -97.7431"
}

Business plan document:
"""


def _fetch_url(url: str, timeout: int = 8) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(120_000).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_colors(css: str) -> list:
    hex_colors = re.findall(r'#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', css)
    rgb_colors = re.findall(r'rgb\([^)]+\)', css)
    return list(dict.fromkeys(hex_colors + rgb_colors))[:40]


def _fetch_style_hints(url: str) -> str:
    """Fetch a page and its linked stylesheets; return colors + tone signals."""
    from urllib.parse import urljoin
    html = _fetch_url(url)
    if not html:
        return ""

    parts = []

    # Inline <style> blocks
    inline_styles = re.findall(r"<style[^>]*>(.*?)</style>", html, re.DOTALL | re.IGNORECASE)
    inline_css = "\n".join(inline_styles[:5])

    # Linked external stylesheets (up to 3)
    sheet_hrefs = re.findall(r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)["\']', html, re.IGNORECASE)
    external_css = ""
    for href in sheet_hrefs[:3]:
        css = _fetch_url(urljoin(url, href), timeout=6)
        external_css += css[:30_000]

    all_css = inline_css + "\n" + external_css

    # CSS custom properties (brand tokens)
    css_vars = re.findall(r'--[\w-]+\s*:\s*[^;]+;', all_css)
    if css_vars:
        parts.append("CSS custom properties (brand tokens):\n" + "\n".join(css_vars[:60]))

    # All color values
    colors = _extract_colors(all_css)
    if colors:
        parts.append("Colors found in CSS:\n" + ", ".join(colors))

    # Font families
    fonts = re.findall(r'font-family\s*:[^;]+;', all_css)
    if fonts:
        parts.append("Fonts: " + " | ".join(dict.fromkeys(fonts[:6])))

    # Page title and meta for tone
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title:
        parts.append("Page title: " + title.group(1).strip())

    metas = re.findall(r'<meta[^>]+content=["\']([^"\']{15,})["\']', html, re.IGNORECASE)
    if metas:
        parts.append("Meta content (tone/descriptions):\n" + "\n".join(metas[:6]))

    return "\n\n".join(parts)[:8000]


def extract_business_data(docx_path: str, reference_url: str | None = None) -> dict:
    text = extract_text_from_docx(docx_path)

    prompt = EXTRACTION_PROMPT + text

    if reference_url:
        style_hints = _fetch_style_hints(reference_url)
        if style_hints:
            prompt += (
                f"\n\n--- REFERENCE SITE DESIGN ({reference_url}) ---\n"
                "IMPORTANT: You MUST derive color_primary, color_accent, and color_action directly from "
                "the CSS colors and custom properties listed below. Pick the 3 most prominent brand colors. "
                "Also match the tone and style of the copy (tagline, headlines, descriptions) to this site.\n\n"
                + style_hints
                + "\n--- END REFERENCE SITE ---"
            )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if Claude wrapped the JSON
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw.strip())
