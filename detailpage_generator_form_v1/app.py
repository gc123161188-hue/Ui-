
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import os, json, uuid
from pathlib import Path
from renderer import render

app = Flask(__name__)
app.secret_key = "dev"

BASE = Path(__file__).resolve().parent
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

DEFAULT_THEME = str(BASE / "theme_classic_v1.json")

@app.get("/")
def index():
    return render_template("form.html")

@app.get("/legacy")
def legacy():
    return render_template("index.html")

@app.post("/render")
def do_render():
    # theme json (optional)
    theme_file = request.files.get("theme")
    theme_path = DEFAULT_THEME
    if theme_file and theme_file.filename:
        tid = uuid.uuid4().hex
        theme_path = str(UPLOADS / f"theme_{tid}.json")
        theme_file.save(theme_path)

    # product json
    prod_file = request.files.get("product")
    if not prod_file or not prod_file.filename:
        flash("请上传 product.json")
        return redirect(url_for("index"))
    pid = uuid.uuid4().hex
    product_path = str(UPLOADS / f"product_{pid}.json")
    prod_file.save(product_path)

    # package image (optional override)
    pkg_file = request.files.get("package_image")
    if pkg_file and pkg_file.filename:
        pkg_name = f"package_{pid}_{pkg_file.filename}"
        pkg_path = UPLOADS / pkg_name
        pkg_file.save(pkg_path)
        # patch product.json to point to uploaded image
        prod = json.loads(Path(product_path).read_text(encoding="utf-8"))
        prod["package_image"] = str(pkg_path.relative_to(BASE)).replace("\\","/")
        Path(product_path).write_text(json.dumps(prod, ensure_ascii=False, indent=2), encoding="utf-8")

    out_path = str(OUTPUTS / f"detail_{pid}.png")
    render(theme_path, product_path, out_path)
    return send_file(out_path, mimetype="image/png", as_attachment=True, download_name="detail.png")

@app.post("/api/render_from_form")
def api_render_from_form():
    product_json = request.form.get("product_json", "")
    if not product_json:
        return "missing product_json", 400
    try:
        prod = json.loads(product_json)
    except Exception as e:
        return f"invalid product_json: {e}", 400

    pid = uuid.uuid4().hex
    product_path = str(UPLOADS / f"product_{pid}.json")
    Path(product_path).write_text(json.dumps(prod, ensure_ascii=False, indent=2), encoding="utf-8")

    pkg_file = request.files.get("package_image")
    if pkg_file and pkg_file.filename:
        pkg_name = f"package_{pid}_{pkg_file.filename}"
        pkg_path = UPLOADS / pkg_name
        pkg_file.save(pkg_path)
        prod["package_image"] = str(pkg_path.relative_to(BASE)).replace("\\","/")
        Path(product_path).write_text(json.dumps(prod, ensure_ascii=False, indent=2), encoding="utf-8")

    out_path = str(OUTPUTS / f"detail_{pid}.png")
    render(DEFAULT_THEME, product_path, out_path)
    return send_file(out_path, mimetype="image/png")

@app.get("/sample")
def sample():
    out_path = str(OUTPUTS / "sample_out.png")
    render(str(BASE/"theme_classic_v1.json"), str(BASE/"sample_product.json"), out_path)
    return send_file(out_path, mimetype="image/png", as_attachment=True, download_name="sample_detail.png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=True)
