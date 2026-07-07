"""
Flask backend for the automated site generator.
POST /generate  — accepts logo + .docx, returns populated site as a zip download.
GET  /          — upload form UI
"""

import os
import re
import zipfile
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify, send_file, render_template_string
from dotenv import load_dotenv

from extractor import extract_business_data
from injector import populate_template

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB


TEMPLATE_DIR = os.getenv("TEMPLATE_PATH", str(Path(__file__).parent.parent / "Website Template"))
OUTPUT_BASE  = os.getenv("OUTPUT_PATH",   str(Path(__file__).parent / "output"))

ALLOWED_LOGO = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".ico", ".avif", ".heic", ".heif"}
ALLOWED_DOC  = {".docx"}


UPLOAD_FORM = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Site Generator</title>
  <style>
    :root {
      --purple: #4B2882;
      --magenta: #C0245A;
      --blue: #3A6FC4;
      --dark: #1A1A2E;
      --light-bg: #F7F6FA;
      --white: #FFFFFF;
      --text: #2D2D3A;
      --text-light: #666680;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: var(--light-bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: linear-gradient(135deg, #1A1A2E 0%, #2C1654 50%, #1E3C72 100%);
      padding: 2.5rem 2rem;
      text-align: center;
    }
    .header-badge {
      display: inline-block;
      background: rgba(192,36,90,0.2);
      border: 1px solid rgba(192,36,90,0.4);
      color: #F06090;
      font-size: 0.75rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;
      padding: 0.35rem 0.9rem; border-radius: 20px;
      margin-bottom: 1rem;
    }
    header h1 {
      font-size: 2rem; font-weight: 800; color: var(--white);
      margin-bottom: 0.5rem; line-height: 1.2;
    }
    header h1 span {
      background: linear-gradient(90deg, #E0609A, #6B9FE4);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    header p {
      font-size: 0.95rem; color: rgba(255,255,255,0.65); max-width: 440px; margin: 0 auto;
    }
    .gradient-divider {
      height: 4px;
      background: linear-gradient(90deg, var(--purple), var(--magenta), var(--blue));
    }
    main {
      flex: 1;
      display: flex; align-items: center; justify-content: center;
      padding: 3rem 1.5rem;
    }
    .card {
      background: var(--white);
      border-radius: 18px;
      padding: 2.5rem;
      width: 100%;
      max-width: 520px;
      box-shadow: 0 8px 40px rgba(74,40,130,0.12);
    }
    .card-title { font-size: 1.3rem; font-weight: 800; color: var(--dark); }
    .card-sub { font-size: 0.9rem; color: var(--text-light); margin-top: 0.3rem; }
    .modal-divider {
      height: 3px; border-radius: 2px;
      background: linear-gradient(90deg, var(--purple), var(--magenta), var(--blue));
      margin: 1.25rem 0;
    }
    .field { margin-bottom: 1.2rem; }
    label {
      display: block;
      font-size: 0.82rem; font-weight: 600; color: var(--dark);
      text-transform: uppercase; letter-spacing: 0.05em;
      margin-bottom: 0.4rem;
    }
    input[type="password"],
    input[type="file"] {
      width: 100%;
      background: var(--white);
      border: 1.5px solid #DDD;
      border-radius: 8px;
      padding: 0.7rem 1rem;
      color: var(--text);
      font-size: 0.95rem;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    input[type="password"]:focus {
      border-color: var(--purple);
      box-shadow: 0 0 0 3px rgba(74,40,130,0.12);
    }
    button {
      width: 100%;
      padding: 0.9rem 2rem;
      background: linear-gradient(135deg, var(--purple), var(--blue));
      color: var(--white);
      border: none;
      border-radius: 8px;
      font-size: 1rem; font-weight: 700; font-family: inherit;
      cursor: pointer;
      transition: opacity 0.2s, transform 0.2s;
      box-shadow: 0 4px 18px rgba(74,40,130,0.3);
      margin-top: 0.5rem;
    }
    button:hover { opacity: 0.9; transform: translateY(-1px); }
    button:disabled { opacity: 0.55; cursor: not-allowed; transform: none; }
    #status {
      margin-top: 1.2rem;
      font-size: 0.9rem;
      color: var(--blue);
      min-height: 1.4rem;
      text-align: center;
    }
    .error { color: var(--magenta) !important; }
    .section-label {
      font-size: 0.82rem; font-weight: 600; color: var(--dark);
      text-transform: uppercase; letter-spacing: 0.05em;
      margin-bottom: 0.75rem; display: block;
    }
    .section-toggles {
      display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem;
      margin-bottom: 1.2rem;
    }
    .toggle-item {
      display: flex; align-items: center; gap: 0.6rem;
      background: var(--light-bg); border: 1.5px solid #DDD;
      border-radius: 8px; padding: 0.6rem 0.9rem;
      cursor: pointer; transition: border-color 0.2s, background 0.2s;
      user-select: none;
    }
    .toggle-item:has(input:checked) {
      border-color: var(--purple);
      background: rgba(74,40,130,0.06);
    }
    .toggle-item input[type="checkbox"] {
      width: 16px; height: 16px; accent-color: var(--purple);
      flex-shrink: 0; cursor: pointer;
    }
    .toggle-item span {
      font-size: 0.88rem; font-weight: 600; color: var(--text);
    }
    footer {
      background: var(--dark); color: rgba(255,255,255,0.5);
      padding: 1.25rem 2rem; text-align: center; font-size: 0.82rem;
    }
  </style>
</head>
<body>
  <header>
    <div class="header-badge">Rogue Coding — Internal Tool</div>
    <h1>Site <span>Generator</span></h1>
    <p>Upload a logo and business plan to generate a ready-to-deploy website.</p>
  </header>
  <div class="gradient-divider"></div>

  <main>
  <div class="card">
    <div class="card-title">Generate a New Site</div>
    <div class="card-sub">Provide your credentials and files below to get started.</div>
    <div class="modal-divider"></div>

    <form id="form" enctype="multipart/form-data">
      <div class="field">
        <label for="logo">Company Logo (PNG, JPG, SVG)</label>
        <input type="file" id="logo" name="logo" accept=".png,.jpg,.jpeg,.svg,.webp,.gif,.bmp,.tiff,.tif,.ico,.avif,.heic,.heif" required />
      </div>
      <div class="field">
        <label for="doc">Business Plan (.docx)</label>
        <input type="file" id="doc" name="doc" accept=".docx" required />
      </div>
      <div class="field">
        <label for="ref_url">Reference Site URL <span style="font-weight:400;text-transform:none;letter-spacing:0;color:var(--text-light)">(optional — match color &amp; tone)</span></label>
        <input type="url" id="ref_url" name="ref_url" placeholder="https://example.com" style="width:100%;background:var(--white);border:1.5px solid #DDD;border-radius:8px;padding:0.7rem 1rem;color:var(--text);font-size:0.95rem;font-family:inherit;outline:none;transition:border-color 0.2s,box-shadow 0.2s;" />
      </div>
      <div class="field">
        <span class="section-label">Sections to Include</span>
        <div class="section-toggles">
          <label class="toggle-item">
            <input type="checkbox" name="sections" value="stats" checked />
            <span>Stats Bar</span>
          </label>
          <label class="toggle-item">
            <input type="checkbox" name="sections" value="about" checked />
            <span>About</span>
          </label>
          <label class="toggle-item">
            <input type="checkbox" name="sections" value="services" checked />
            <span>Services</span>
          </label>
          <label class="toggle-item">
            <input type="checkbox" name="sections" value="team" checked />
            <span>Team</span>
          </label>
          <label class="toggle-item">
            <input type="checkbox" name="sections" value="contact" checked />
            <span>Contact</span>
          </label>
        </div>
      </div>
      <button type="submit" id="btn">Generate Site</button>
    </form>
    <div id="status"></div>
  </div>
  </main>

  <footer>&copy; 2026 Rogue Coding &mdash; Internal Use Only</footer>

  <script>
    document.getElementById('form').addEventListener('submit', async e => {
      e.preventDefault();
      const btn = document.getElementById('btn');
      const status = document.getElementById('status');
      btn.disabled = true;
      status.textContent = 'Uploading files…';
      status.className = '';

      const fd = new FormData(e.target);
      try {
        status.textContent = 'Extracting business data with Claude…';
        const res = await fetch('/generate', { method: 'POST', body: fd });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.error || res.statusText);
        }
        status.textContent = 'Building site…';
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'generated-site.zip';
        a.click();
        status.textContent = 'Done! Your site zip has been downloaded.';
      } catch (err) {
        status.textContent = 'Error: ' + err.message;
        status.className = 'error';
      } finally {
        btn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@app.get("/debug-env")
def debug_env():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return jsonify({"set": bool(key), "prefix": key[:10] if key else "", "length": len(key), "all_keys": [k for k in os.environ.keys() if "ANTHROPIC" in k.upper() or "API" in k.upper()]})

@app.get("/")
def index():
    return render_template_string(UPLOAD_FORM)


@app.post("/generate")
def generate():

    if "logo" not in request.files or "doc" not in request.files:
        return jsonify(error="Both 'logo' and 'doc' files are required."), 400

    logo_file = request.files["logo"]
    doc_file  = request.files["doc"]

    logo_ext = Path(logo_file.filename).suffix.lower()
    doc_ext  = Path(doc_file.filename).suffix.lower()

    if logo_ext not in ALLOWED_LOGO:
        return jsonify(error=f"Logo must be one of: {', '.join(ALLOWED_LOGO)}"), 400
    if doc_ext not in ALLOWED_DOC:
        return jsonify(error="Business plan must be a .docx file."), 400

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        logo_path = tmp / f"logo{logo_ext}"
        doc_path  = tmp / "plan.docx"
        logo_file.save(logo_path)
        doc_file.save(doc_path)

        ref_url = request.form.get("ref_url", "").strip() or None

        try:
            data = extract_business_data(str(doc_path), reference_url=ref_url)
        except Exception as e:
            return jsonify(error=f"Claude extraction failed: {e}"), 500

        sections = set(request.form.getlist("sections")) or {"stats", "about", "services", "team", "contact"}
        company_slug = slugify(data.get("company_name", "site"))
        out_dir = tmp / company_slug

        try:
            populate_template(data, str(logo_path), TEMPLATE_DIR, str(out_dir), sections=sections)
        except Exception as e:
            return jsonify(error=f"Template injection failed: {e}"), 500

        zip_path = tmp / f"{company_slug}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in out_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(out_dir))

        return send_file(
            str(zip_path),
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{company_slug}-site.zip"
        )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
