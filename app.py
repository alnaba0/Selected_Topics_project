"""
app.py
------
Flask web UI for the Image Recognition + Blockchain prototype.

Routes:
    GET  /            Upload form
    POST /upload       Runs recognition, hashes the image, writes a block,
                        redirects to the result page
    GET  /result/<idx> Shows one block's details
    GET  /chain        Shows the full ledger and a "Verify Chain" action
    GET  /verify        Re-checks chain integrity and reports pass/fail
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash

from blockchain import Blockchain
from image_recognition import recognize, hash_image_bytes

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(APP_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(APP_ROOT, "data"), exist_ok=True)

app = Flask(__name__)
app.secret_key = "dev-only-secret-change-before-any-real-deployment"

chain = Blockchain(storage_path=os.path.join(APP_ROOT, "data", "chain.json"))

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/")
def index():
    return render_template("index.html", block_count=len(chain.chain))


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("image")
    if not file or file.filename == "":
        flash("No file selected.")
        return redirect(url_for("index"))
    if not allowed_file(file.filename):
        flash("Unsupported file type. Use PNG, JPG, or WEBP.")
        return redirect(url_for("index"))

    image_bytes = file.read()
    image_hash = hash_image_bytes(image_bytes)

    # Save the raw file under its hash so duplicate uploads are traceable
    # back to the same record.
    save_path = os.path.join(UPLOAD_DIR, f"{image_hash}_{file.filename}")
    with open(save_path, "wb") as f:
        f.write(image_bytes)

    existing = chain.find_by_image_hash(image_hash)
    if existing:
        flash("This exact image is already on the ledger -- showing the existing record.")
        return redirect(url_for("result", idx=existing.index))

    prediction, confidence, used_real_model = recognize(image_bytes)
    block = chain.add_block(
        image_hash=image_hash,
        filename=file.filename,
        prediction=prediction,
        confidence=confidence,
    )

    if not used_real_model:
        flash("Recognition ran in OFFLINE FALLBACK mode (no model weights available) -- "
              "see image_recognition.py. Result is a placeholder, not a real classification.")

    return redirect(url_for("result", idx=block.index))


@app.route("/result/<int:idx>")
def result(idx):
    if idx < 0 or idx >= len(chain.chain):
        flash("No such block.")
        return redirect(url_for("index"))
    block = chain.chain[idx]
    return render_template("result.html", block=block)


@app.route("/chain")
def view_chain():
    return render_template("chain.html", blocks=chain.as_list())


@app.route("/verify")
def verify():
    valid, reason = chain.is_valid()
    if valid:
        flash("Chain verified: all blocks are correctly hashed and linked.")
    else:
        flash(f"Chain INVALID: {reason}")
    return redirect(url_for("view_chain"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
