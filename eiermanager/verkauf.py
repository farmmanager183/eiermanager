from flask import Blueprint, render_template
from flask_login import login_required

verkauf_bp = Blueprint('verkauf', __name__, url_prefix='/verkauf')

@verkauf_bp.route('/')
@login_required
def index():
    return render_template('verkauf/index.html')
