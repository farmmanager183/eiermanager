# eiermanager/huehner.py
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from eiermanager.extensions import db
from eiermanager.models import Mobilstall, HuehnerEvent, LogEntry

huehner_bp = Blueprint("huehner", __name__, url_prefix="/huehner")


@huehner_bp.route("/", endpoint="index")
@login_required
def index():
    return redirect(url_for("huehner.menu"))


@huehner_bp.route("/menu")
@login_required
def menu():
    mobilstaelle = Mobilstall.query.filter_by(aktiv=True).order_by(Mobilstall.name.asc()).all()
    return render_template("huehner/menu.html", mobilstaelle=mobilstaelle)


# ===== Helpers =====

def _stall_losses(stall_id: int, days: int = None) -> int:
    """Summe aller Verluste für einen Stall (optional begrenzt auf X Tage)."""
    q = HuehnerEvent.query.filter_by(stall_id=stall_id, typ="verlust")
    if days:
        since = date.today() - timedelta(days=days - 1)
        q = q.filter(HuehnerEvent.datum >= since)
    return int(sum(e.menge or 0 for e in q.all()))


def _hens_current(stall: Mobilstall) -> int:
    """Aktueller Hühnerbestand: Startbestand minus gebuchte Verluste.
    (Kein hens_adjust im Model – also ggf. 0 als Fallback.)"""
    adjust = getattr(stall, "hens_adjust", 0) or 0  # falls später ergänzt, sonst 0
    return int((stall.hens_start or 0) + adjust - _stall_losses(stall.id))


def _last_event(stall_id: int, typ: str):
    """Letztes Ereignis (Datum als 'dd.mm.'). HuehnerEvent hat keine zeitpunkt-Spalte."""
    e = (
        HuehnerEvent.query
        .filter_by(stall_id=stall_id, typ=typ)
        .order_by(HuehnerEvent.datum.desc(), HuehnerEvent.id.desc())
        .first()
    )
    if not e:
        return (None, None)
    # Zeit gibt es im Model nicht -> leer
    return (e.datum.strftime("%d.%m."), "")


def _eggs_last7_for_stall(stall: Mobilstall) -> int:
    """Heuristik: Eier-Zugänge der letzten 7 Tage, gefiltert über den Stallnamen in LogEntry.name."""
    since = date.today() - timedelta(days=6)
    like_name = f"%{stall.name}%"
    total = (
            db.session.query(func.coalesce(func.sum(LogEntry.menge), 0))
            .filter(
                LogEntry.typ == "zugang",
                LogEntry.datum >= since,
                LogEntry.name.ilike(like_name),
                )
            .scalar()
            or 0
    )
    return int(total)


@huehner_bp.route("/uebersicht")
@login_required
def uebersicht():
    stalls = Mobilstall.query.filter_by(aktiv=True).order_by(Mobilstall.name.asc()).all()

    cards = []
    for s in stalls:
        hens = _hens_current(s)
        eggs7 = _eggs_last7_for_stall(s)
        rate = None
        if hens > 0:
            # grobe Legeleistung (Eier der letzten 7 Tage / (Hennen * 7) * 100)
            rate = round(100.0 * eggs7 / (hens * 7), 1)

        cards.append({
            "stall": s,
            "hens": hens,
            "eggs7": eggs7,
            "rate": rate,
            "last_feed": _last_event(s.id, "fuetterung"),
            "last_water": _last_event(s.id, "wasser"),
            "last_clean": _last_event(s.id, "ausmisten"),
            "last_move": _last_event(s.id, "umstallung"),
        })

    return render_template("huehner/uebersicht.html", cards=cards)


@huehner_bp.route("/stall/<int:stall_id>")
@login_required
def stall(stall_id: int):
    stall = Mobilstall.query.get_or_404(stall_id)

    # letzte 10 Einträge dieses Stalls (nur HuehnerEvent)
    recent = (
        HuehnerEvent.query
        .filter_by(stall_id=stall_id)
        .order_by(HuehnerEvent.id.desc())
        .limit(10)
        .all()
    )

    return render_template("huehner/stall.html", stall=stall, recent=recent)


@huehner_bp.route("/stall/<int:stall_id>/quick_production", methods=["POST"])
@login_required
def quick_production(stall_id: int):
    stall = Mobilstall.query.get_or_404(stall_id)
    try:
        menge = int(request.form.get("menge", "0"))
    except ValueError:
        menge = 0

    if menge <= 0:
        flash("Bitte eine gültige Menge eingeben.", "warning")
        return redirect(url_for("huehner.stall", stall_id=stall_id))

    db.session.add(LogEntry(
        datum=date.today(),
        zeitpunkt=datetime.now().strftime("%H:%M"),
        typ="zugang",
        menge=menge,
        benutzer=current_user.username,
        name=f"Produktion {stall.name}"
    ))
    db.session.commit()
    flash(f"Produktion für {stall.name} gebucht (+{menge}).", "success")
    return redirect(url_for("huehner.stall", stall_id=stall_id))


@huehner_bp.route("/stall/<int:stall_id>/event", methods=["POST"])
@login_required
def event(stall_id: int):
    stall = Mobilstall.query.get_or_404(stall_id)
    typ = (request.form.get("typ") or "").strip().lower()

    try:
        menge = int(request.form.get("menge", "0"))
    except ValueError:
        menge = 0

    note = (request.form.get("note") or "").strip()

    # erlaubte Typen – konsistent mit _last_event und vorhandenen Templates
    if typ not in {"fuetterung", "wasser", "ausmisten", "umstallung", "verlust", "notiz"}:
        flash("Ungültiger Ereignistyp.", "danger")
        return redirect(url_for("huehner.stall", stall_id=stall_id))

    if typ == "verlust" and menge <= 0:
        flash("Bitte Verlust-Menge > 0 eingeben.", "warning")
        return redirect(url_for("huehner.stall", stall_id=stall_id))

    db.session.add(HuehnerEvent(
        stall_id=stall.id,
        typ=typ,
        menge=menge if typ == "verlust" else None,
        notiz=note if note else None,
        datum=date.today(),
    ))
    db.session.commit()

    label = {
        "fuetterung": "Fütterung",
        "wasser": "Wasser",
        "ausmisten": "Ausmisten",
        "umstallung": "Umstallung",
        "verlust": "Verlust",
        "notiz": "Notiz",
    }[typ]

    if typ == "verlust":
        flash(f"{label} gebucht (-{menge}).", "success")
    else:
        flash(f"{label} gebucht.", "success")

    return redirect(url_for("huehner.stall", stall_id=stall_id))
