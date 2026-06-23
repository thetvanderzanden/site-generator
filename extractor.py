"""
Reads a .docx business plan and uses Claude to extract structured site data.
"""

import json
import re
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


def extract_business_data(docx_path: str) -> dict:
    text = extract_text_from_docx(docx_path)

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT + text}
        ]
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if Claude wrapped the JSON
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw.strip())
