from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from eiermanager.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        return render_template('menu2.html')
    if request.method == 'POST':
        pin = request.form['pin']
        user = User.query.filter_by(pin=pin).first()
        if user:
            login_user(user)
            session['username'] = user.username
            return redirect(url_for('auth.index'))
        else:
            flash("Falsche PIN!", "danger")
    return render_template('login2.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth.index'))

@auth_bp.route('/menu')
def menu():
    if current_user.is_authenticated:
        return render_template('menu2.html')
    return redirect(url_for('auth.index'))
