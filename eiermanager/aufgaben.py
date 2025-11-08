from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from flask_login import login_required, current_user
from eiermanager import db, admin_required
from eiermanager.models import Aufgabe, Arbeitszeit, User

aufgaben_bp = Blueprint('aufgaben', __name__)

@aufgaben_bp.route('/aufgaben')
@login_required
def aufgaben_verwalten():
    # Zeigt alle offenen Aufgaben (für Admin: evtl. gefiltert nach Benutzer)
    if current_user.is_admin:
        tasks = Aufgabe.query.filter_by(erledigt=False).all()
    else:
        tasks = Aufgabe.query.filter_by(erledigt=False, benutzer_id=current_user.id).all()
    return render_template('aufgaben_verwalten.html', aufgaben=tasks)

@aufgaben_bp.route('/aufgabe/neu', methods=['GET', 'POST'], endpoint='aufgabe_erstellen')
@login_required
def aufgabe_erstellen():
    if request.method == 'POST':
        titel = request.form['titel']
        beschreibung = request.form.get('beschreibung')
        benutzer_id = request.form.get('benutzer_id')
        aufgabe = Aufgabe(titel=titel, beschreibung=beschreibung)
        if benutzer_id:
            aufgabe.benutzer_id = int(benutzer_id)
        db.session.add(aufgabe)
        db.session.commit()
        flash('Neue Aufgabe erstellt.', 'success')
        return redirect(url_for('aufgaben_verwalten'))
    mitarbeiter = User.query.all()
    return render_template('aufgabe_erstellen.html', mitarbeiter=mitarbeiter)

@aufgaben_bp.route('/aufgabe/<int:aufgabe_id>/bearbeiten', methods=['POST'], endpoint='aufgabe_bearbeiten')
@login_required
def aufgabe_bearbeiten(aufgabe_id):
    # Markiert Aufgabe als erledigt oder bearbeitet Felder
    aufgabe = Aufgabe.query.get_or_404(aufgabe_id)
    if 'erledigt' in request.form:
        aufgabe.erledigt = True
    else:
        aufgabe.titel = request.form.get('titel', aufgabe.titel)
        aufgabe.beschreibung = request.form.get('beschreibung', aufgabe.beschreibung)
        aufgabe.benutzer_id = int(request.form.get('benutzer_id', aufgabe.benutzer_id or 0)) or None
    db.session.commit()
    flash('Aufgabe aktualisiert.', 'info')
    return redirect(url_for('aufgaben_verwalten'))

@aufgaben_bp.route('/aufgabe/<int:aufgabe_id>/loeschen', methods=['POST'], endpoint='aufgabe_loeschen')
@login_required
def aufgabe_loeschen(aufgabe_id):
    aufgabe = Aufgabe.query.get_or_404(aufgabe_id)
    db.session.delete(aufgabe)
    db.session.commit()
    flash('Aufgabe gelöscht.', 'info')
    return redirect(url_for('aufgaben_verwalten'))

@aufgaben_bp.route('/aufgaben/wiederkehrend')
@login_required
def wiederkehrende_aufgaben_verwalten():
    # Übersicht der wiederkehrenden Aufgaben
    tasks = Aufgabe.query.filter(Aufgabe.intervall.isnot(None)).all()
    return render_template('wiederkehrende_aufgaben_verwalten.html', aufgaben=tasks)

@aufgaben_bp.route('/aufgabe/wiederkehrend/neu', methods=['GET', 'POST'], endpoint='wiederkehrende_aufgabe_hinzufuegen')
@login_required
def wiederkehrende_aufgabe_hinzufuegen():
    if request.method == 'POST':
        titel = request.form['titel']
        intervall = request.form.get('intervall')  # z.B. "Wöchentlich", "Monatlich"
        aufgabe = Aufgabe(titel=titel, intervall=intervall)
        db.session.add(aufgabe)
        db.session.commit()
        flash('Wiederkehrende Aufgabe hinzugefügt.', 'success')
        return redirect(url_for('wiederkehrende_aufgaben_verwalten'))
    return render_template('wiederkehrende_aufgabe_hinzufuegen.html')

@aufgaben_bp.route('/arbeitszeit', methods=['GET', 'POST'])
@login_required
def arbeitszeit():
    # Mitarbeiter stempeln sich ein oder aus
    if request.method == 'POST':
        if 'start' in request.form:
            # Einstempeln
            eintrag = Arbeitszeit(user_id=current_user.id)
            db.session.add(eintrag)
            db.session.commit()
            flash('Arbeitszeit gestartet.', 'success')
        elif 'stop' in request.form:
            # Ausstempeln – zuletzt offener Arbeitszeiteintrag schließen
            eintrag = Arbeitszeit.query.filter_by(user_id=current_user.id).order_by(Arbeitszeit.id.desc()).first()
            if eintrag and eintrag.ausschlag_zeit is None:
                eintrag.ausschlag_zeit = datetime.now()
                db.session.commit()
                flash('Arbeitszeit gestoppt.', 'success')
    # Aktueller Status (eingestempelt oder nicht) und Liste der heutigen Zeiten
    heute = datetime.now().date()
    zeiten_heute = Arbeitszeit.query.filter(
        Arbeitszeit.user_id == current_user.id,
        db.func.date(Arbeitszeit.einstempel_zeit) == heute
    ).all()
    return render_template('arbeitszeit.html', zeiten=zeiten_heute)

@aufgaben_bp.route('/arbeitszeit/uebersicht')
@login_required
def arbeitszeit_uebersicht():
    # Gesamtübersicht der Arbeitszeiten (für Admin oder Nutzer)
    if current_user.is_admin:
        alle_zeiten = Arbeitszeit.query.all()
    else:
        alle_zeiten = Arbeitszeit.query.filter_by(user_id=current_user.id).all()
    return render_template('arbeitszeit_uebersicht.html', zeiten=alle_zeiten)

@aufgaben_bp.route('/arbeitszeit/admin/<int:zeit_id>/bearbeiten', methods=['POST'], endpoint='arbeitszeit_bearbeiten_admin')
@login_required
@admin_required
def arbeitszeit_bearbeiten_admin(zeit_id):
    # Admin korrigiert einen Arbeitszeiteintrag (z.B. Zeit nachtragen)
    eintrag = Arbeitszeit.query.get_or_404(zeit_id)
    if 'delete' in request.form:
        db.session.delete(eintrag)
        flash('Arbeitszeit-Eintrag gelöscht.', 'info')
    else:
        # z.B. Start- oder Endzeit anpassen
        neue_start = request.form.get('start')
        neue_ende = request.form.get('ende')
        if neue_start:
            eintrag.einstempel_zeit = datetime.fromisoformat(neue_start)
        if neue_ende:
            eintrag.ausschlag_zeit = datetime.fromisoformat(neue_ende)
        flash('Arbeitszeit-Eintrag bearbeitet.', 'info')
    db.session.commit()
    return redirect(url_for('arbeitszeit_uebersicht'))

@aufgaben_bp.route('/arbeitszeit/admin/<int:zeit_id>/loeschen', methods=['POST'], endpoint='arbeitszeit_loeschen_admin')
@login_required
@admin_required
def arbeitszeit_loeschen_admin(zeit_id):
    eintrag = Arbeitszeit.query.get_or_404(zeit_id)
    db.session.delete(eintrag)
    db.session.commit()
    flash('Arbeitszeit-Eintrag gelöscht.', 'info')
    return redirect(url_for('arbeitszeit_uebersicht'))

@aufgaben_bp.route('/arbeitszeit/gesamt')
@login_required
def arbeitszeit_gesamt():
    # Gesamtstundenzahl pro Mitarbeiter
    nutzer = User.query.all()
    statistik = {}
    for user in nutzer:
        zeiten = Arbeitszeit.query.filter_by(user_id=user.id).all()
        gesamt = sum([(z.ausschlag_zeit - z.einstempel_zeit).total_seconds() / 3600
                      for z in zeiten if z.ausschlag_zeit], 0.0)
        statistik[user.username] = round(gesamt, 2)
    return render_template('arbeitszeit_gesamt.html', statistik=statistik)

@aufgaben_bp.route('/benutzer/aufgaben')
@login_required
def benutzer_aufgaben():
    # Zeigt aktuelle Nutzer-Aufgaben (für eingeloggten Benutzer)
    tasks = Aufgabe.query.filter_by(erledigt=False, benutzer_id=current_user.id).all()
    return render_template('benutzer_aufgaben.html', aufgaben=tasks)
