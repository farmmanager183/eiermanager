from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from flask_login import login_required, current_user
from eiermanager import db, admin_required
from eiermanager.models import Pferd, Reitstunde, User

pferde_bp = Blueprint('pferde', __name__)

@pferde_bp.route('/reitstunden')
@login_required
def reitstunden():
    # Übersicht geplanter Reitstunden
    stunden = Reitstunde.query.all()
    return render_template('reitstunden.html', reitstunden=stunden)

@pferde_bp.route('/reitstunden/neu', methods=['GET', 'POST'], endpoint='add_reitstunde')
@login_required
def add_reitstunde():
    # Neue Reitstunde planen
    pferde = Pferd.query.all()
    mitarbeiter = User.query.all()
    if request.method == 'POST':
        art = request.form['art_der_stunde']
        datum = request.form['datum']
        dauer = int(request.form['dauer'])
        pferd_id = request.form.get('pferd_id')
        mitarbeiter_id = request.form.get('mitarbeiter_id')
        stunde = Reitstunde(art_der_stunde=art, datum=datum, dauer=dauer)
        if pferd_id:
            stunde.pferd = Pferd.query.get(pferd_id)
        if mitarbeiter_id:
            stunde.mitarbeiter = User.query.get(mitarbeiter_id)
        db.session.add(stunde)
        db.session.commit()
        flash('Reitstunde geplant.', 'success')
        return redirect(url_for('reitstunden'))
    return render_template('reitstunden_verwaltung.html', pferde=pferde, mitarbeiter=mitarbeiter)

@pferde_bp.route('/reitstunden/<int:stunde_id>/delete', methods=['POST'], endpoint='get_reitstunden')
@login_required
def get_reitstunden(stunde_id):
    # Entfernt eine geplante Reitstunde
    stunde = Reitstunde.query.get_or_404(stunde_id)
    db.session.delete(stunde)
    db.session.commit()
    flash('Reitstunde gelöscht.', 'info')
    return redirect(url_for('reitstunden'))
