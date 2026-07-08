#!/usr/bin/env python3
"""
CLI entry point used by GitHub Actions to generate a site.

Usage:
  python generate_cli.py \
    --logo /path/to/logo.png \
    --docx /path/to/plan.docx \
    --output ./sites \
    [--reference https://example.com] \
    [--sections about,services,team,contact]

Prints SLUG=<slug> and OUTPUT=<path> to stdout for the Actions workflow to capture.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from extractor import extract_business_data
from injector import populate_template

TEMPLATE_DIR = str(Path(__file__).parent / "template")


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main():
    parser = argparse.ArgumentParser(description="Generate a site from logo + docx")
    parser.add_argument("--logo",      required=True,  help="Path to logo file")
    parser.add_argument("--docx",      required=True,  help="Path to .docx business plan")
    parser.add_argument("--output",    required=True,  help="Output base directory")
    parser.add_argument("--reference", default="",     help="Reference site URL for design cues")
    parser.add_argument("--sections",  default="about,services,team,contact",
                        help="Comma-separated sections to include")
    args = parser.parse_args()

    print("Extracting business data...", flush=True)
    data = extract_business_data(
        args.docx,
        reference_url=args.reference or None,
    )

    slug = slugify(data["company_name"])
    out_dir = str(Path(args.output) / slug)

    sections = set(s.strip() for s in args.sections.split(",") if s.strip()) if args.sections else None

    print(f"Populating template for: {data['company_name']}", flush=True)
    populate_template(data, args.logo, TEMPLATE_DIR, out_dir, sections)

    # Write metadata sidecar for the Actions summary
    meta = {
        "slug": slug,
        "company": data["company_name"],
        "domain": data.get("domain", ""),
        "colors": {
            "primary": data.get("color_primary"),
            "accent":  data.get("color_accent"),
            "action":  data.get("color_action"),
        },
    }
    (Path(out_dir) / "_meta.json").write_text(json.dumps(meta, indent=2))

    # Print outputs for the Actions workflow to capture with $GITHUB_OUTPUT
    print(f"SLUG={slug}")
    print(f"OUTPUT={out_dir}")
    print(f"COMPANY={data['company_name']}")


if __name__ == "__main__":
    main()
