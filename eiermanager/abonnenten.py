# eiermanager/abonnenten.py
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from eiermanager.extensions import db
from eiermanager.models import Abonnement, LogEntry

abonnenten_bp = Blueprint("abonnenten", __name__, url_prefix="/abonnenten")


# ----------------- Menü -----------------
@abonnenten_bp.route("/", endpoint="index")
@login_required
def index():
    return render_template("abonnenten/menu.html")


# ----------------- Liste -----------------
@abonnenten_bp.route("/liste", endpoint="liste")
@login_required
def liste():
    abos = Abonnement.query.order_by(Abonnement.aktiv.desc(), Abonnement.name.asc()).all()
    return render_template("abonnenten/liste.html", abos=abos)


# ----------------- Neu -----------------
@abonnenten_bp.route("/neu", methods=["GET", "POST"], endpoint="neu")
@login_required
def neu():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        menge = request.form.get("menge")
        abholtag = request.form.get("abholtag")
        aktiv = request.form.get("aktiv") == "on"
        notizen = (request.form.get("notizen") or "").strip()

        try:
            menge = int(menge or 0)
        except ValueError:
            menge = 0
        try:
            abholtag = int(abholtag or 0)
        except ValueError:
            abholtag = 0

        if not name or menge <= 0 or not (0 <= abholtag <= 6):
            flash("Bitte gültige Daten eingeben (Name, Menge > 0, Abholtag 0-6).", "warning")
            return redirect(url_for("abonnenten.neu"))

        a = Abonnement(name=name, menge=menge, abholtag=abholtag, aktiv=aktiv, notizen=notizen)
        db.session.add(a)
        db.session.commit()
        flash("Abo angelegt.", "success")
        return redirect(url_for("abonnenten.liste"))

    return render_template("abonnenten/edit.html", abo=None)


# ----------------- Bearbeiten -----------------
@abonnenten_bp.route("/<int:abo_id>/edit", methods=["GET", "POST"], endpoint="edit")
@login_required
def edit(abo_id: int):
    a = Abonnement.query.get_or_404(abo_id)
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        menge = request.form.get("menge")
        abholtag = request.form.get("abholtag")
        aktiv = request.form.get("aktiv") == "on"
        notizen = (request.form.get("notizen") or "").strip()

        try:
            menge = int(menge or 0)
        except ValueError:
            menge = a.menge
        try:
            abholtag = int(abholtag or 0)
        except ValueError:
            abholtag = a.abholtag

        if not name or menge <= 0 or not (0 <= abholtag <= 6):
            flash("Bitte gültige Daten eingeben (Name, Menge > 0, Abholtag 0-6).", "warning")
            return redirect(url_for("abonnenten.edit", abo_id=abo_id))

        a.name = name
        a.menge = menge
        a.abholtag = abholtag
        a.aktiv = aktiv
        a.notizen = notizen
        db.session.commit()
        flash("Abo gespeichert.", "success")
        return redirect(url_for("abonnenten.liste"))

    return render_template("abonnenten/edit.html", abo=a)


# ----------------- Löschen -----------------
@abonnenten_bp.route("/<int:abo_id>/delete", methods=["POST"], endpoint="delete")
@login_required
def delete(abo_id: int):
    a = Abonnement.query.get_or_404(abo_id)
    db.session.delete(a)
    db.session.commit()
    flash("Abo gelöscht.", "success")
    return redirect(url_for("abonnenten.liste"))


# ----------------- HEUTE BUCHEN -----------------
@abonnenten_bp.route("/heute", methods=["GET", "POST"], endpoint="heute")
@login_required
def heute():
    today = date.today()
    weekday = today.weekday()  # Mo=0 ... So=6
    if request.method == "POST":
        # Es kommen mehrere Felder: selected_<id>=on und menge_<id>=value
        count = 0
        total = 0
        for key, val in request.form.items():
            if not key.startswith("selected_"):
                continue
            try:
                abo_id = int(key.split("_", 1)[1])
            except Exception:
                continue
            a = Abonnement.query.get(abo_id)
            if not a or not a.aktiv:
                continue

            # Menge lesen (override oder default)
            menge_str = request.form.get(f"menge_{abo_id}", "")
            try:
                menge = int(menge_str or a.menge or 0)
            except ValueError:
                menge = a.menge or 0

            if menge <= 0:
                continue

            # LogEntry anlegen (Abgang)
            db.session.add(LogEntry(
                datum=today,
                zeitpunkt=datetime.now().strftime("%H:%M"),
                typ="abgang",
                menge=menge,
                benutzer=getattr(current_user, "username", None),
                name=f"Abo {a.name}"
            ))
            count += 1
            total += menge

        db.session.commit()
        if count == 0:
            flash("Keine Abgänge gebucht.", "warning")
        else:
            flash(f"{count} Abo-Buchungen erfasst (gesamt {total} Eier).", "success")
        return redirect(url_for("abonnenten.heute"))

    # GET: aktive Abos für heutigen Wochentag
    abos = Abonnement.query.filter_by(aktiv=True, abholtag=weekday).order_by(Abonnement.name.asc()).all()
    return render_template("abonnenten/heute.html", abos=abos, weekday=weekday, today=today)
