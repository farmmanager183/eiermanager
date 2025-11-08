# eiermanager/benutzer.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from eiermanager.models import User

benutzer_bp = Blueprint("benutzer", __name__)


@benutzer_bp.route("/login", methods=["GET", "POST"])
def login():
    # Bereits eingeloggt? Ab ins Dashboard.
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    if request.method == "POST":
        pin = (request.form.get("pin") or "").strip()
        if not pin:
            flash("Bitte PIN eingeben.", "warning")
            return redirect(url_for("benutzer.login"))

        # Kein Filter auf "active" o.ä. – minimal & robust
        u = User.query.filter_by(pin=pin).first()
        if not u:
            flash("Falsche PIN.", "danger")
            return redirect(url_for("benutzer.login"))

        login_user(u, remember=False)  # Session-Cookie wird beim Browser-Schließen gelöscht
        return redirect(url_for("core.dashboard"))

    # GET → nutze DEIN bestehendes Template
    return render_template("login2.html")


@benutzer_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Abgemeldet.", "success")
    return redirect(url_for("benutzer.login"))
