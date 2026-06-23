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
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, sans-serif;
      background: #0f0f1a;
      color: #e0e0f0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }
    .card {
      background: #1a1a2e;
      border: 1px solid #2a2a4a;
      border-radius: 16px;
      padding: 2.5rem;
      width: 100%;
      max-width: 520px;
    }
    h1 { font-size: 1.6rem; margin-bottom: 0.4rem; }
    .sub { color: #888; font-size: 0.9rem; margin-bottom: 2rem; }
    label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.4rem; color: #a0a0c0; }
    .field { margin-bottom: 1.4rem; }
    input[type="file"] {
      width: 100%;
      background: #0f0f1a;
      border: 1px solid #333;
      border-radius: 8px;
      padding: 0.7rem 1rem;
      color: #e0e0f0;
      font-size: 0.9rem;
    }
    button {
      width: 100%;
      padding: 0.9rem;
      background: linear-gradient(135deg, #4B2882, #3A6FC4);
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 700;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    button:hover { opacity: 0.88; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    #status {
      margin-top: 1.2rem;
      font-size: 0.9rem;
      color: #6B9FE4;
      min-height: 1.4rem;
    }
    .error { color: #E06090; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Site Generator</h1>
    <p class="sub">Upload a logo and business plan to generate a ready-to-deploy website.</p>

    <form id="form" enctype="multipart/form-data">
      <div class="field">
        <label for="logo">Company Logo (PNG, JPG, SVG)</label>
        <input type="file" id="logo" name="logo" accept=".png,.jpg,.jpeg,.svg,.webp,.gif,.bmp,.tiff,.tif,.ico,.avif,.heic,.heif" required />
      </div>
      <div class="field">
        <label for="doc">Business Plan (.docx)</label>
        <input type="file" id="doc" name="doc" accept=".docx" required />
      </div>
      <button type="submit" id="btn">Generate Site</button>
    </form>
    <div id="status"></div>
  </div>

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

        try:
            data = extract_business_data(str(doc_path))
        except Exception as e:
            return jsonify(error=f"Claude extraction failed: {e}"), 500

        company_slug = slugify(data.get("company_name", "site"))
        out_dir = tmp / company_slug

        try:
            populate_template(data, str(logo_path), TEMPLATE_DIR, str(out_dir))
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
