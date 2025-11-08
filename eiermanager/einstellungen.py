# eiermanager/einstellungen.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from eiermanager.extensions import db
from eiermanager.models import Mobilstall, User, Module, Abonnement  # <-- Abonnement statt Abo
from eiermanager.__init__ import admin_required

einstellungen_bp = Blueprint("einstellungen", __name__, url_prefix="/einstellungen")


# ----------------- Menü -----------------
@einstellungen_bp.route("/", endpoint="index")
@login_required
@admin_required
def index():
    # Schlanke Menüseite – Links müssen existieren (siehe Templates)
    return render_template("einstellungen/menu.html")


# ----------------- Mobilställe (Liste/Neu/Bearbeiten) -----------------
@einstellungen_bp.route("/staelle", endpoint="stalle_list")
@login_required
@admin_required
def stalle_list():
    staelle = Mobilstall.query.order_by(Mobilstall.name.asc()).all()
    return render_template("einstellungen/stalle_list.html", staelle=staelle)


@einstellungen_bp.route("/stall/new", methods=["GET", "POST"], endpoint="stall_new")
@login_required
@admin_required
def stall_new():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        aktiv = request.form.get("aktiv") == "on"
        hens_start = request.form.get("hens_start")
        try:
            hens_start = int(hens_start or 0)
        except ValueError:
            hens_start = 0

        if not name:
            flash("Bitte einen Namen eingeben.", "warning")
            return redirect(url_for("einstellungen.stall_new"))

        st = Mobilstall(name=name, aktiv=aktiv, hens_start=hens_start)
        db.session.add(st)
        db.session.commit()
        flash("Stall angelegt.", "success")
        return redirect(url_for("einstellungen.stalle_list"))

    return render_template("einstellungen/stall_edit.html", stall=None)


@einstellungen_bp.route("/stall/<int:stall_id>/edit", methods=["GET", "POST"], endpoint="stall_edit")
@login_required
@admin_required
def stall_edit(stall_id: int):
    st = Mobilstall.query.get_or_404(stall_id)
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        aktiv = request.form.get("aktiv") == "on"
        hens_start = request.form.get("hens_start")
        try:
            hens_start = int(hens_start or 0)
        except ValueError:
            hens_start = st.hens_start or 0

        if not name:
            flash("Bitte einen Namen eingeben.", "warning")
            return redirect(url_for("einstellungen.stall_edit", stall_id=stall_id))

        st.name = name
        st.aktiv = aktiv
        st.hens_start = hens_start
        db.session.commit()
        flash("Stall gespeichert.", "success")
        return redirect(url_for("einstellungen.stalle_list"))

    return render_template("einstellungen/stall_edit.html", stall=st)


# ----------------- Benutzer (Liste/Neu/Löschen) -----------------
@einstellungen_bp.route("/benutzer", endpoint="benutzer_list")
@login_required
@admin_required
def benutzer_list():
    users = User.query.order_by(User.username.asc()).all()
    return render_template("einstellungen/benutzer_list.html", users=users)


@einstellungen_bp.route("/benutzer/new", methods=["GET", "POST"], endpoint="benutzer_new")
@login_required
@admin_required
def benutzer_new():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        pin = (request.form.get("pin") or "").strip()
        is_admin = request.form.get("is_admin") == "on"

        if not username or not pin or len(pin) != 4 or not pin.isdigit():
            flash("Bitte gültigen Namen und 4-stellige PIN angeben.", "warning")
            return redirect(url_for("einstellungen.benutzer_new"))

        # Doppelter Username?
        if User.query.filter_by(username=username).first():
            flash("Benutzername existiert bereits.", "warning")
            return redirect(url_for("einstellungen.benutzer_new"))

        u = User(username=username, pin=pin, is_admin=is_admin)
        db.session.add(u)
        db.session.commit()
        flash("Benutzer angelegt.", "success")
        return redirect(url_for("einstellungen.benutzer_list"))

    return render_template("einstellungen/benutzer_edit.html")


@einstellungen_bp.route("/benutzer/<int:user_id>/delete", methods=["POST"], endpoint="benutzer_delete")
@login_required
@admin_required
def benutzer_delete(user_id: int):
    u = User.query.get_or_404(user_id)
    db.session.delete(u)
    db.session.commit()
    flash("Benutzer gelöscht.", "success")
    return redirect(url_for("einstellungen.benutzer_list"))


# ----------------- Module-Matrix (Platzhalter – verhindert BuildError) -----------------
@einstellungen_bp.route("/module", endpoint="module_matrix")
@login_required
@admin_required
def module_matrix():
    # Hier könntest du später Module pro User aktivieren/deaktivieren.
    modules = Module.query.order_by(Module.label.asc()).all()
    return render_template("einstellungen/module_matrix.html", modules=modules)
