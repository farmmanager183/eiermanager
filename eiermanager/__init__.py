# eiermanager/__init__.py
import os
from datetime import timedelta
from flask import Flask, abort
from flask_login import current_user
from eiermanager.extensions import db, login_manager

# Login-Endpoint für Flask-Login
login_manager.login_view = 'benutzer.login'


def admin_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            abort(403)
        return func(*args, **kwargs)
    return wrapper


def create_app():
    # App + instance/ (DB/Secrets)
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # ------------------------------------------------------------------
    # Konfiguration
    # ------------------------------------------------------------------
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-insecure')

    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'eiermanager.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Sessions / Login-Cookies: kein "Remember me"
    app.config['SESSION_PERMANENT'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(0)
    app.config['REMEMBER_COOKIE_REFRESH_EACH_REQUEST'] = False

    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)

    # 1) Models laden
    from eiermanager import models  # noqa: F401

    # 2) Tabellen anlegen
    with app.app_context():
        db.create_all()

    # 3) Bootstrap/Seeding
    from eiermanager.bootstrap import bootstrap_data
    bootstrap_data(app)

    # 4) Stabile Blueprints registrieren (+ NEU: abonnenten)
    from eiermanager import benutzer, core, eier, huehner, einstellungen, abonnenten

    app.register_blueprint(benutzer.benutzer_bp)            # Login/Logout
    app.register_blueprint(core.core_bp)                    # Start / Dashboard
    app.register_blueprint(eier.eier_bp)                    # Eier (Bestand/Bewegungen)
    app.register_blueprint(huehner.huehner_bp)              # Hühner
    app.register_blueprint(einstellungen.einstellungen_bp)  # Einstellungen
    app.register_blueprint(abonnenten.abonnenten_bp)        # Abonnenten (NEU)

    # 4a) Safety-Upserts: Module in DB sicherstellen + Admin zuweisen
    with app.app_context():
        from eiermanager.models import Module, User
        try:
            def ensure_module(key: str, label: str, endpoint: str,
                              admin_only: bool = False, active: bool = True) -> Module:
                m = Module.query.filter_by(key=key).first()
                if not m:
                    m = Module(key=key, label=label, endpoint=endpoint,
                               admin_only=admin_only, active=active)
                    db.session.add(m)
                    db.session.commit()
                else:
                    changed = False
                    if m.endpoint != endpoint:
                        m.endpoint = endpoint; changed = True
                    if m.admin_only != admin_only:
                        m.admin_only = admin_only; changed = True
                    if m.active != active:
                        m.active = active; changed = True
                    if changed:
                        db.session.commit()
                return m

            mod_eier       = ensure_module("eier",        "Eier",        "eier.index",        admin_only=False, active=True)
            mod_huehner    = ensure_module("huehner",     "Hühner",      "huehner.index",     admin_only=False, active=True)
            mod_settings   = ensure_module("einstellungen","Einstellungen","einstellungen.index", admin_only=True,  active=True)
            mod_abos       = ensure_module("abonnenten",  "Abonnenten",  "abonnenten.index",  admin_only=False, active=True)

            admin = User.query.filter_by(is_admin=True).first()
            if admin:
                for m in (mod_eier, mod_huehner, mod_settings, mod_abos):
                    if all(mm.id != m.id for mm in admin.modules):
                        admin.modules.append(m)
                db.session.commit()
        except Exception as e:
            app.logger.warning("[safety-upsert] Module konnten nicht sichergestellt werden: %r", e)

    # Login-User-Loader
    @login_manager.user_loader
    def load_user(user_id):
        from eiermanager.models import User
        return User.query.get(int(user_id))

    # Menü-Utilities (für Templates)
    @app.context_processor
    def utility_processor():
        from flask import current_app
        from eiermanager.models import Module

        def has_endpoint(name: str) -> bool:
            return name in current_app.view_functions

        def can_access_module(m: "Module") -> bool:
            if not getattr(m, "active", True):
                return False
            if getattr(current_user, "is_admin", False):
                return True
            if getattr(m, "admin_only", False):
                return False
            if hasattr(current_user, "modules") and current_user.modules:
                return any(um.id == m.id for um in current_user.modules)
            return True

        return dict(has_endpoint=has_endpoint, can_access_module=can_access_module, Module=Module)

    # Debug-Infos beim Start
    with app.app_context():
        try:
            from eiermanager.models import Module, User
            app.logger.info("Registered endpoints: %s", list(app.view_functions.keys()))
            app.logger.info("Modules in DB: %s", [(m.key, m.endpoint, m.active) for m in Module.query.all()])
            app.logger.info("Users in DB: %s", [(u.username, u.is_admin) for u in User.query.all()])
        except Exception as e:
            app.logger.warning("Startup debug-info failed: %r", e)

    return app
