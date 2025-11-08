# eiermanager/core.py
from flask import Blueprint, render_template, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from eiermanager.models import Module, User

core_bp = Blueprint("core", __name__)

def _user_can_access(module: Module) -> bool:
    if not getattr(module, "active", True):
        return False
    if module.endpoint not in current_app.view_functions:
        return False
    if getattr(current_user, "is_admin", False):
        return True
    if getattr(module, "admin_only", False):
        return False
    if hasattr(current_user, "modules") and current_user.modules:
        return any(m.id == module.id for m in current_user.modules)
    return True

def _visible_modules():
    mods = Module.query.order_by(Module.label.asc()).all()
    return [m for m in mods if _user_can_access(m)]

@core_bp.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("benutzer.login"))
    return render_template("menu.html", modules=_visible_modules())

@core_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("menu.html", modules=_visible_modules())

@core_bp.route("/_debug/modules")
@login_required
def debug_modules():
    endpoints = sorted(list(current_app.view_functions.keys()))
    mods = Module.query.order_by(Module.label.asc()).all()
    u = User.query.get(current_user.id)

    data = {
        "endpoints": endpoints,
        "db_modules": [{"key": m.key, "endpoint": m.endpoint, "active": m.active, "admin_only": m.admin_only} for m in mods],
        "current_user": {
            "username": u.username if u else None,
            "is_admin": bool(u and u.is_admin),
            "modules": [m.key for m in (u.modules if u and hasattr(u, "modules") else [])],
        },
    }
    return jsonify(data), 200
