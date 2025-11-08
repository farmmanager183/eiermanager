# eiermanager/eier.py
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func, case
from eiermanager.extensions import db
from eiermanager.models import LogEntry, Mobilstall, Abonnement, AboException  # <-- korrekt!

# --- Blueprint: MUSS existieren, damit __init__.py es registrieren kann ---
eier_bp = Blueprint("eier", __name__, url_prefix="/eier")


# -----------------------------
# Hilfsfunktion: Eierbestand
# -----------------------------
def _bestand() -> int:
    zugang = db.session.query(
        func.coalesce(func.sum(case((LogEntry.typ == 'zugang', LogEntry.menge), else_=0)), 0)
    ).scalar() or 0
    abgang = db.session.query(
        func.coalesce(func.sum(case((LogEntry.typ == 'abgang', LogEntry.menge), else_=0)), 0)
    ).scalar() or 0
    return int(zugang - abgang)


# -----------------------------
# Menü
# -----------------------------
@eier_bp.route("/", endpoint="index")
@login_required
def index():
    return redirect(url_for("eier.menu"))


@eier_bp.route("/menu")
@login_required
def menu():
    return render_template("eier/menu.html")


# -----------------------------
# Übersicht (Bestand, Statistiken)
# -----------------------------
@eier_bp.route("/uebersicht")
@login_required
def uebersicht():
    today = date.today()
    start_7 = today - timedelta(days=6)      # 7 Tage inkl. heute
    start_14 = today - timedelta(days=13)    # 14 Tage inkl. heute

    # Heutige Summen
    zugang_heute = db.session.query(
        func.coalesce(func.sum(case((LogEntry.typ == 'zugang', LogEntry.menge), else_=0)), 0)
    ).filter(LogEntry.datum == today).scalar() or 0

    abgang_heute = db.session.query(
        func.coalesce(func.sum(case((LogEntry.typ == 'abgang', LogEntry.menge), else_=0)), 0)
    ).filter(LogEntry.datum == today).scalar() or 0

    sum_heute = {
        "zugang": int(zugang_heute),
        "abgang": int(abgang_heute),
        "netto": int(zugang_heute) - int(abgang_heute),
    }

    # 7-Tage Summen (inkl. heute)
    zugang_woche = db.session.query(
        func.coalesce(func.sum(case((LogEntry.typ == 'zugang', LogEntry.menge), else_=0)), 0)
    ).filter(LogEntry.datum >= start_7).scalar() or 0

    abgang_woche = db.session.query(
        func.coalesce(func.sum(case((LogEntry.typ == 'abgang', LogEntry.menge), else_=0)), 0)
    ).filter(LogEntry.datum >= start_7).scalar() or 0

    sum_woche = {
        "zugang": int(zugang_woche),
        "abgang": int(abgang_woche),
        "netto": int(zugang_woche) - int(abgang_woche),
    }

    # Tageswerte der letzten 14 Tage (lückenlos)
    agg_rows = db.session.query(
        LogEntry.datum.label("d"),
        func.coalesce(func.sum(case((LogEntry.typ == 'zugang', LogEntry.menge), else_=0)), 0).label("zugang"),
        func.coalesce(func.sum(case((LogEntry.typ == 'abgang', LogEntry.menge), else_=0)), 0).label("abgang"),
    ).filter(
        LogEntry.datum >= start_14
    ).group_by(
        LogEntry.datum
    ).all()

    by_day = {row.d: {"zugang": int(row.zugang or 0), "abgang": int(row.abgang or 0)} for row in agg_rows}

    daily = []
    for i in range(14):
        d = start_14 + timedelta(days=i)
        z = by_day.get(d, {"zugang": 0, "abgang": 0})
        daily.append({"datum": d, "zugang": z["zugang"], "abgang": z["abgang"]})

    bestand = _bestand()

    # Letzte Buchungen (neueste zuerst)
    buchungen = (LogEntry.query
                 .filter(LogEntry.typ.in_(["zugang", "abgang"]))
                 .order_by(LogEntry.datum.desc(), LogEntry.zeitpunkt.desc())
                 .limit(25)
                 .all())

    return render_template(
        "eier/uebersicht.html",
        bestand=bestand,
        sum_heute=sum_heute,
        sum_woche=sum_woche,
        daily=daily,
        buchungen=buchungen,
    )


# -----------------------------
# Zugang buchen
# -----------------------------
@eier_bp.route("/zugang", methods=["GET", "POST"])
@login_required
def zugang():
    stalls = Mobilstall.query.filter_by(aktiv=True).order_by(Mobilstall.name.asc()).all()

    if request.method == "POST":
        stall_id = request.form.get("stall_id")
        try:
            menge = int(request.form.get("menge", "0"))
        except ValueError:
            menge = 0

        if not stall_id:
            flash("Bitte einen Stall wählen.", "warning")
            return redirect(url_for("eier.zugang"))
        if menge <= 0:
            flash("Bitte eine positive Menge eingeben.", "warning")
            return redirect(url_for("eier.zugang"))

        stall = Mobilstall.query.get(stall_id)
        if not stall:
            flash("Ausgewählter Stall existiert nicht.", "danger")
            return redirect(url_for("eier.zugang"))

        db.session.add(LogEntry(
            datum=date.today(),
            zeitpunkt=datetime.now().strftime("%H:%M"),
            typ="zugang",
            menge=menge,
            benutzer=current_user.username,
            name=f"Produktion {stall.name}"
        ))
        db.session.commit()
        flash(f"Zugang für {stall.name} gebucht (+{menge}).", "success")
        return redirect(url_for("eier.menu"))

    return render_template("eier/zugang.html", stalls=stalls)


# -----------------------------
# Abgang buchen (eine Seite)
# -----------------------------
@eier_bp.route("/abgang", methods=["GET", "POST"], endpoint="abgang_menu")
@login_required
def abgang_menu():
    valid_types = {
        "verkauf": "Verkauf",
        "verlust": "Verlust",
        "restaurant": "Restaurant",
        "eigenbedarf": "Eigenbedarf",
    }

    if request.method == "POST":
        typ = (request.form.get("typ") or "").lower().strip()
        try:
            menge = int(request.form.get("menge", "0"))
        except ValueError:
            menge = 0

        if typ not in valid_types:
            flash("Bitte eine Abgangsart wählen.", "warning")
            return redirect(url_for("eier.abgang_menu"))
        if menge <= 0:
            flash("Bitte eine gültige Menge eingeben.", "warning")
            return redirect(url_for("eier.abgang_menu"))
        if menge > _bestand():
            flash("Menge übersteigt aktuellen Bestand.", "danger")
            return redirect(url_for("eier.abgang_menu"))

        db.session.add(LogEntry(
            datum=date.today(),
            zeitpunkt=datetime.now().strftime("%H:%M"),
            typ="abgang",
            menge=menge,
            benutzer=current_user.username,
            name=f"Abgang {valid_types[typ]}"
        ))
        db.session.commit()
        flash(f"Abgang „{valid_types[typ]}“ gebucht (-{menge}).", "success")
        return redirect(url_for("eier.menu"))

    # GET
    return render_template("eier/abgang.html", valid_types=valid_types)
