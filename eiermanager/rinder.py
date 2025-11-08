from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from flask_login import login_required, current_user
from eiermanager import db, admin_required
from eiermanager.models import Rind, Impfung, Medikament, Besamung

rinder_bp = Blueprint('rinder', __name__)

@rinder_bp.route('/rinder')
@login_required
def rinder_startseite():
    # Übersicht aller Rinder (Herdentabelle)
    alle_rinder = Rind.query.all()
    return render_template('rinder_startseite.html', rinder=alle_rinder)

@rinder_bp.route('/rind/neu', methods=['GET', 'POST'], endpoint='rind_zugang')
@login_required
def rind_zugang():
    # Zugang: neues Rind hinzufügen
    if request.method == 'POST':
        name = request.form['name']
        ohrmarke = request.form['ohrmarke']
        geburtsdatum = request.form['geburtsdatum']
        rasse = request.form.get('rasse')
        rind = Rind(name=name, ohrmarkennummer=ohrmarke, geburtsdatum=geburtsdatum, rasse=rasse)
        db.session.add(rind)
        db.session.commit()
        flash('Neues Rind hinzugefügt.', 'success')
        return redirect(url_for('rinder_startseite'))
    return render_template('rind_zugang.html')

@rinder_bp.route('/rind/<int:rind_id>/bearbeiten', methods=['POST'], endpoint='rind_bearbeiten')
@login_required
def rind_bearbeiten(rind_id):
    # Rind-Stammdaten bearbeiten
    rind = Rind.query.get_or_404(rind_id)
    rind.name = request.form.get('name', rind.name)
    rind.ohrmarkennummer = request.form.get('ohrmarke', rind.ohrmarkennummer)
    rind.rasse = request.form.get('rasse', rind.rasse)
    # ... weitere Felder aktualisieren ...
    db.session.commit()
    flash('Rind-Daten aktualisiert.', 'info')
    return redirect(url_for('rind_detail', rind_id=rind.id))

@rinder_bp.route('/rind/<int:rind_id>/abgang', methods=['POST'], endpoint='rind_abgang')
@login_required
def rind_abgang(rind_id):
    # Rind austragen (Abgang)
    rind = Rind.query.get_or_404(rind_id)
    db.session.delete(rind)
    db.session.commit()
    flash('Rind aus Herde entfernt (Abgang).', 'info')
    return redirect(url_for('rinder_startseite'))

@rinder_bp.route('/rind/<int:rind_id>')
@login_required
def rind_detail(rind_id):
    # Detailansicht eines einzelnen Rinds mit Historie
    rind = Rind.query.get_or_404(rind_id)
    impfungen = Impfung.query.filter_by(rind_id=rind.id).all()
    medikamente = Medikament.query.filter_by(rind_id=rind.id).all()
    besamungen = Besamung.query.filter_by(rind_id=rind.id).all()
    return render_template('rind_detail.html', rind=rind, impfungen=impfungen, medikamente=medikamente, besamungen=besamungen)

@rinder_bp.route('/rind/<int:rind_id>/ereignisse')
@login_required
def rind_ereignis_übersicht(rind_id):
    # Übersicht aller Ereignisse (Impfungen, Medikamente, Besamungen) für ein Rind
    rind = Rind.query.get_or_404(rind_id)
    impfungen = Impfung.query.filter_by(rind_id=rind.id).all()
    medikamente = Medikament.query.filter_by(rind_id=rind.id).all()
    besamungen = Besamung.query.filter_by(rind_id=rind.id).all()
    return render_template('rind_ereignisse.html', rind=rind, impfungen=impfungen, medikamente=medikamente, besamungen=besamungen)

@rinder_bp.route('/rind/<int:rind_id>/impfung', methods=['POST'], endpoint='impfung_hinzufuegen')
@login_required
def impfung_hinzufuegen(rind_id):
    rind = Rind.query.get_or_404(rind_id)
    datum = request.form['datum']
    art = request.form['art']
    impfung = Impfung(rind_id=rind.id, datum=datum, art=art)
    db.session.add(impfung)
    db.session.commit()
    flash('Impfung hinzugefügt.', 'success')
    return redirect(url_for('rind_ereignis_übersicht', rind_id=rind.id))

@rinder_bp.route('/rind/<int:rind_id>/impfung/<int:impfung_id>/loeschen', methods=['POST'], endpoint='impfung_loeschen')
@login_required
def impfung_loeschen(rind_id, impfung_id):
    impfung = Impfung.query.get_or_404(impfung_id)
    db.session.delete(impfung)
    db.session.commit()
    flash('Impfung gelöscht.', 'info')
    return redirect(url_for('rind_ereignis_übersicht', rind_id=rind_id))

@rinder_bp.route('/rind/<int:rind_id>/medikament', methods=['POST'], endpoint='medikament_hinzufuegen')
@login_required
def medikament_hinzufuegen(rind_id):
    rind = Rind.query.get_or_404(rind_id)
    datum = request.form['datum']
    name = request.form['name']
    dosis = request.form.get('dosis')
    med = Medikament(rind_id=rind.id, datum=datum, name=name, dosis=dosis)
    db.session.add(med)
    db.session.commit()
    flash('Medikamenteneingabe hinzugefügt.', 'success')
    return redirect(url_for('rind_ereignis_übersicht', rind_id=rind.id))

@rinder_bp.route('/rind/<int:rind_id>/medikament/<int:med_id>/loeschen', methods=['POST'], endpoint='medikament_loeschen')
@login_required
def medikament_loeschen(rind_id, med_id):
    med = Medikament.query.get_or_404(med_id)
    db.session.delete(med)
    db.session.commit()
    flash('Medikamenteneintrag gelöscht.', 'info')
    return redirect(url_for('rind_ereignis_übersicht', rind_id=rind_id))

@rinder_bp.route('/rind/<int:rind_id>/besamung', methods=['POST'], endpoint='besamung_hinzufuegen')
@login_required
def besamung_hinzufuegen(rind_id):
    rind = Rind.query.get_or_404(rind_id)
    datum = request.form['datum']
    bullensperma = request.form.get('bullensperma')
    bes = Besamung(rind_id=rind.id, datum=datum, bullensperma=bullensperma)
    db.session.add(bes)
    db.session.commit()
    flash('Besamung eingetragen.', 'success')
    return redirect(url_for('rind_ereignis_übersicht', rind_id=rind.id))

@rinder_bp.route('/rind/<int:rind_id>/besamung/<int:bes_id>/loeschen', methods=['POST'], endpoint='besamung_loeschen')
@login_required
def besamung_loeschen(rind_id, bes_id):
    bes = Besamung.query.get_or_404(bes_id)
    db.session.delete(bes)
    db.session.commit()
    flash('Besamungseintrag gelöscht.', 'info')
    return redirect(url_for('rind_ereignis_übersicht', rind_id=rind_id))

@rinder_bp.route('/herdenbuch')
@login_required
def herdenbuch():
    # Gesamte Herdenübersicht mit allen Tieren und Ereignissen
    rinder = Rind.query.all()
    return render_template('herdenbuch.html', rinder=rinder)
