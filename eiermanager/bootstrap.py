# eiermanager/bootstrap.py
from eiermanager.extensions import db
from eiermanager.models import User, Mobilstall, Module

def bootstrap_data(app):
    with app.app_context():
        if User.query.count() == 0:
            db.session.add(User(username="admin", pin="0000", is_admin=True))
            app.logger.info("[bootstrap] Admin-User 'admin' (PIN 0000) angelegt.")

        if Mobilstall.query.count() == 0:
            db.session.add_all([
                Mobilstall(name="Mobil 1", aktiv=True, hens_start=0),
                Mobilstall(name="Mobil 2", aktiv=True, hens_start=0),
                Mobilstall(name="Mobil 3", aktiv=True, hens_start=0),
            ])
            app.logger.info("[bootstrap] 3 Mobilställe angelegt.")

        def ensure_module(key, label, endpoint, admin_only=False, active=True):
            m = Module.query.filter_by(key=key).first()
            if not m:
                m = Module(key=key, label=label, endpoint=endpoint,
                           admin_only=admin_only, active=active)
                db.session.add(m)
                app.logger.info(f"[bootstrap] Modul '{key}' -> {endpoint}")
            else:
                changed = False
                if m.endpoint != endpoint:
                    m.endpoint = endpoint; changed = True
                if m.admin_only != admin_only:
                    m.admin_only = admin_only; changed = True
                if m.active != active:
                    m.active = active; changed = True
                if changed:
                    app.logger.info(f"[bootstrap] Modul '{key}' aktualisiert.")
            return m

        ensure_module("eier", "Eier", "eier.index", admin_only=False, active=True)
        ensure_module("huehner", "Hühner", "huehner.index", admin_only=False, active=True)
        ensure_module("einstellungen", "Einstellungen", "einstellungen.index", admin_only=True, active=True)
        # Schnellkachel für Tagesgeschäft:
        ensure_module("abonnenten", "Abonnenten", "eier.abos_heute", admin_only=False, active=True)

        db.session.commit()

        app.logger.info("[bootstrap] Users: %s", [u.username for u in User.query.all()])
        app.logger.info("[bootstrap] Mobilställe: %s", [(s.id, s.name) for s in Mobilstall.query.all()])
        app.logger.info("[bootstrap] Module: %s", [(m.key, m.endpoint) for m in Module.query.all()])
