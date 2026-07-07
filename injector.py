"""
Takes extracted business data + logo path and populates the website template.
Outputs a ready-to-use index.html + logo file in the output directory.
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path


ICONS = ["🎯", "📈", "🗺️", "🏗️", "🌐", "🔍"]


def _phone_display(phone: str) -> str:
    """Convert +1-XXX-XXX-XXXX to (XXX) XXX-XXXX for display."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone


def _phone_tel(phone: str) -> str:
    """Convert to tel: href format +1XXXXXXXXXX."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11:
        return f"+{digits}"
    return phone


def _service_cards(services: list[str]) -> str:
    """Build HTML service cards, padding to 6 with placeholders if needed."""
    cards = []
    for i in range(6):
        name = services[i] if i < len(services) else f"Service {i + 1}"
        icon = ICONS[i]
        cards.append(
            f'        <div class="service-card">\n'
            f'          <div class="service-icon">{icon}</div>\n'
            f'          <h3>{name}</h3>\n'
            f'          <p>Contact us to learn more about this service.</p>\n'
            f'        </div>'
        )
    return "\n\n".join(cards)


def _service_ld_json(services: list[str]) -> str:
    items = []
    for s in services[:6]:
        items.append(
            f'            {{ "@type": "Offer", "itemOffered": {{ "@type": "Service", "name": "{s}" }} }}'
        )
    return ",\n".join(items)


_SECTION_COMMENTS = {
    "stats":    "STATS BAR",
    "about":    "ABOUT",
    "services": "SERVICES",
    "team":     "TEAM",
    "contact":  "CONTACT",
}

_NAV_LINKS = {
    "about":    '      <li><a href="#about">About</a></li>',
    "services": '      <li><a href="#services">Services</a></li>',
    "team":     '      <li><a href="#team">Team</a></li>',
    "contact":  '      <li><a href="#contact" class="nav-cta">Contact Us</a></li>',
}

_ALL_SECTIONS = list(_SECTION_COMMENTS.keys())


def _strip_sections(html: str, enabled: set) -> str:
    for i, key in enumerate(_ALL_SECTIONS):
        if key in enabled:
            continue
        tag = _SECTION_COMMENTS[key]
        is_last = (key == "contact")
        if is_last:
            stop = r'\n\n  <div class="gradient-divider" role="presentation"></div>\n\n  </main>'
        else:
            next_tag = _SECTION_COMMENTS[_ALL_SECTIONS[i + 1]]
            stop = rf'\n\n  <!-- {re.escape(next_tag)}'
        pattern = rf'\n\n  <!-- {re.escape(tag)}.+?(?={stop})'
        html = re.sub(pattern, "", html, flags=re.DOTALL)
        if key in _NAV_LINKS:
            html = html.replace("\n" + _NAV_LINKS[key], "")
    return html


def populate_template(data: dict, logo_src: str, template_dir: str, output_dir: str, sections: set | None = None) -> str:
    """
    Reads index.html from template_dir, substitutes all placeholders,
    copies the logo, and writes the result to output_dir.
    Returns the output directory path.
    """
    template_path = Path(template_dir) / "index.html"
    html = template_path.read_text(encoding="utf-8")

    year = str(datetime.now().year)
    domain = data.get("domain", "yourdomain.com")
    email = data.get("email", f"contact@{domain}")
    phone_raw = data.get("phone", "+1-000-000-0000")
    phone_display = _phone_display(phone_raw)
    phone_tel = _phone_tel(phone_raw)
    company = data["company_name"]
    tagline = data.get("tagline", "")
    city = data.get("city", "")
    state = data.get("state", "")
    state_abbr = data.get("state_abbr", "")
    services = data.get("services", ["Service 1", "Service 2", "Service 3"])
    industry = services[0] if services else "Professional Services"

    # ── CSS colors (regex replace so whitespace differences don't break it) ──
    html = re.sub(
        r'--color-primary\s*:[^;]+;',
        f"--color-primary: {data.get('color_primary', '#4B2882')};",
        html, count=1
    )
    html = re.sub(
        r'--color-accent\s*:[^;]+;',
        f"--color-accent:  {data.get('color_accent', '#C0245A')};",
        html, count=1
    )
    html = re.sub(
        r'--color-action\s*:[^;]+;',
        f"--color-action:  {data.get('color_action', '#3A6FC4')};",
        html, count=1
    )

    # ── Hero badge (must happen BEFORE CITY/STATE replacement) ───────────────
    html = html.replace(
        '<div class="hero-badge">INDUSTRY &mdash; CITY, STATE</div>',
        f'<div class="hero-badge">{industry} &mdash; {city}, {state}</div>'
    )

    # ── Domain / URL ─────────────────────────────────────────────────────────
    html = html.replace("YOURDOMAIN.com", domain)

    # ── Meta & head ──────────────────────────────────────────────────────────
    html = html.replace("COMPANY NAME | TAGLINE | CITY, STATE", f"{company} | {tagline} | {city}, {state}")
    html = html.replace("COMPANY NAME | TAGLINE", f"{company} | {tagline}")
    html = html.replace("COMPANY NAME", company)
    html = html.replace("TAGLINE OR INC.", tagline)
    html = html.replace("TAGLINE", tagline)
    html = html.replace("DESCRIPTION", data.get("description", ""))
    html = html.replace("BRIEF VALUE PROPOSITION.", data.get("value_proposition", ""))
    html = html.replace("BRIEF VALUE PROPOSITION", data.get("value_proposition", ""))
    html = html.replace("FULL BUSINESS DESCRIPTION", data.get("full_description", data.get("description", "")))

    # Keywords
    kw_str = ", ".join(data.get("keywords", [city, state]))
    html = html.replace("KEYWORD1, KEYWORD2, KEYWORD3, CITY, STATE", kw_str)

    # Geo
    html = html.replace("CITY, STATE", f"{city}, {state}")
    html = html.replace("LAT;LNG", f"{data.get('lat', '0')};{data.get('lng', '0')}")
    html = html.replace("LAT, LNG", f"{data.get('lat', '0')}, {data.get('lng', '0')}")
    html = html.replace("US-XX", f"US-{state_abbr}")
    html = html.replace("CITY", city)
    html = html.replace("STATE_ABBR", state_abbr)
    html = html.replace("STATE", state)

    # Email / phone
    html = html.replace("EMAIL@YOURDOMAIN.com", email)
    html = html.replace("tel:+1XXXXXXXXXX", f"tel:{phone_tel}")
    html = html.replace("(XXX) XXX-XXXX", phone_display)
    html = html.replace("+1-XXX-XXX-XXXX", phone_raw)

    # Year
    html = html.replace("YEAR ", f"{year} ")

    # ── JSON-LD service offers ───────────────────────────────────────────────
    old_offers = (
        '            { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "SERVICE 1" } },\n'
        '            { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "SERVICE 2" } },\n'
        '            { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "SERVICE 3" } }'
    )
    html = html.replace(old_offers, _service_ld_json(services))

    # ── Hero section ─────────────────────────────────────────────────────────
    headline = data.get("hero_headline", f"Welcome to {company}")
    html = html.replace(
        '<h1>MAIN HEADLINE WITH <span>HIGHLIGHTED KEY PHRASE</span></h1>',
        f'<h1>{headline}</h1>'
    )
    html = html.replace(
        'HERO SUBHEADING — one or two sentences describing your value proposition and who you serve.',
        data.get("hero_subtext", data.get("value_proposition", ""))
    )

    # ── About section ────────────────────────────────────────────────────────
    full_desc = data.get("full_description", data.get("description", ""))
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_desc) if s.strip()]
    para1 = sentences[0] if len(sentences) > 0 else full_desc
    para2 = sentences[1] if len(sentences) > 1 else ""
    para3 = sentences[2] if len(sentences) > 2 else ""

    html = html.replace("ABOUT SECTION HEADING", f"About {company}")
    html = html.replace("PARAGRAPH ONE — overview of the company, what you do and who you serve.", para1)
    html = html.replace("PARAGRAPH TWO — your approach or philosophy.", para2)
    html = html.replace("PARAGRAPH THREE — mission statement or differentiator.", para3)

    # Highlight cards
    html = html.replace("HIGHLIGHT 1 TITLE", services[0] if len(services) > 0 else "Our Expertise")
    html = html.replace("HIGHLIGHT 2 TITLE", services[1] if len(services) > 1 else "Our Approach")
    html = html.replace("HIGHLIGHT 3 TITLE", services[2] if len(services) > 2 else "Our Commitment")
    html = html.replace(
        "Brief description of this key differentiator or value.",
        f"A core part of how {company} delivers value to every client.",
        1
    )

    # ── Services section ─────────────────────────────────────────────────────
    html = html.replace("SERVICES SECTION HEADING", f"Our Services")
    html = html.replace(
        "SERVICES SECTION SUBTITLE — brief description of your service offerings.",
        f"Everything {company} offers to help your business succeed."
    )

    old_cards = (
        '        <div class="service-card">\n'
        '          <div class="service-icon">🎯</div>\n'
        '          <h3>SERVICE 1 NAME</h3>\n'
        '          <p>Description of this service and the value it delivers to clients.</p>\n'
        '        </div>\n\n'
        '        <div class="service-card">\n'
        '          <div class="service-icon">📈</div>\n'
        '          <h3>SERVICE 2 NAME</h3>\n'
        '          <p>Description of this service and the value it delivers to clients.</p>\n'
        '        </div>\n\n'
        '        <div class="service-card">\n'
        '          <div class="service-icon">🗺️</div>\n'
        '          <h3>SERVICE 3 NAME</h3>\n'
        '          <p>Description of this service and the value it delivers to clients.</p>\n'
        '        </div>\n\n'
        '        <div class="service-card">\n'
        '          <div class="service-icon">🏗️</div>\n'
        '          <h3>SERVICE 4 NAME</h3>\n'
        '          <p>Description of this service and the value it delivers to clients.</p>\n'
        '        </div>\n\n'
        '        <div class="service-card">\n'
        '          <div class="service-icon">🌐</div>\n'
        '          <h3>SERVICE 5 NAME</h3>\n'
        '          <p>Description of this service and the value it delivers to clients.</p>\n'
        '        </div>\n\n'
        '        <div class="service-card">\n'
        '          <div class="service-icon">🔍</div>\n'
        '          <h3>SERVICE 6 NAME</h3>\n'
        '          <p>Description of this service and the value it delivers to clients.</p>\n'
        '        </div>'
    )
    html = html.replace(old_cards, _service_cards(services))

    # ── Team section (leave generic until we have team data) ─────────────────
    html = html.replace("TEAM SECTION HEADING", f"The {company} Team")
    html = html.replace("TEAM SECTION SUBTITLE — brief intro to your leadership team.", f"The people behind {company}.")

    # ── Contact section ───────────────────────────────────────────────────────
    html = html.replace("CONTACT SECTION HEADING", "Get in Touch")
    html = html.replace(
        "CONTACT SECTION SUBTITLE — brief call to action encouraging visitors to reach out.",
        f"Ready to work with {company}? Reach out and we'll get back to you promptly."
    )

    # ── Form hidden fields ────────────────────────────────────────────────────
    html = html.replace(f"New Consultation Request — COMPANY NAME", f"New Consultation Request — {company}")
    html = html.replace(f"COMPANY NAME Website", f"{company} Website")

    # ── Strip unselected sections ─────────────────────────────────────────────
    if sections is not None:
        html = _strip_sections(html, sections)

    # ── Write output ──────────────────────────────────────────────────────────
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    logo_ext = Path(logo_src).suffix.lower()
    logo_filename = f"logo{logo_ext}"

    # Use SVG natively; for raster formats keep as-is and reference by actual extension
    favicon_type = "image/svg+xml" if logo_ext == ".svg" else f"image/{logo_ext.lstrip('.')}"
    html = html.replace('type="image/png" href="logo.png"', f'type="{favicon_type}" href="{logo_filename}"')
    html = html.replace("logo.png", logo_filename)

    (out / "index.html").write_text(html, encoding="utf-8")

    # Copy logo
    shutil.copy2(logo_src, out / logo_filename)

    # Copy other static files from template
    for fname in ["sitemap.xml", "robots.txt", "CNAME"]:
        src = Path(template_dir) / fname
        if src.exists():
            shutil.copy2(src, out / fname)

    return str(out)
