# eiermanager/models.py
from datetime import datetime, date
from flask_login import UserMixin
from eiermanager.extensions import db

# -------------------------------------------------
# M2M: User <-> Module
# -------------------------------------------------
user_modules = db.Table(
    'user_modules',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('module_id', db.Integer, db.ForeignKey('module.id'), primary_key=True),
)


# -------------------------------------------------
# User / Module
# -------------------------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    pin = db.Column(db.String(10), nullable=False)      # 4-stellig (als Text)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # UserMixin liefert is_active=True -> kein extra Feld nötig
    modules = db.relationship('Module', secondary=user_modules, lazy='joined',
                              backref=db.backref('users', lazy=True))

    def __repr__(self) -> str:
        return f"<User {self.username} admin={self.is_admin}>"


class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)     # 'eier', 'huehner', ...
    label = db.Column(db.String(120), nullable=False)                # Anzeigename
    endpoint = db.Column(db.String(120), nullable=False)             # z.B. 'eier.index'
    active = db.Column(db.Boolean, default=True, nullable=False)
    admin_only = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Module {self.key} -> {self.endpoint}>"


# -------------------------------------------------
# Hühner / Ställe / Ereignisse
# -------------------------------------------------
class Mobilstall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    aktiv = db.Column(db.Boolean, default=True, nullable=False)
    hens_start = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Mobilstall {self.name} aktiv={self.aktiv} hens_start={self.hens_start}>"


class HuehnerEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stall_id = db.Column(db.Integer, db.ForeignKey('mobilstall.id'), nullable=False, index=True)
    datum = db.Column(db.Date, default=date.today, nullable=False)
    typ = db.Column(db.String(50), nullable=False)       # 'fuettern','wasser','reinigen','umsetzen','verlust',...
    menge = db.Column(db.Integer, nullable=True)         # optional (z.B. Verluste)
    notiz = db.Column(db.String(255), nullable=True)

    stall = db.relationship('Mobilstall', backref=db.backref('events', lazy=True))

    def __repr__(self) -> str:
        return f"<HuehnerEvent stall={self.stall_id} {self.typ} {self.datum}>"


# -------------------------------------------------
# Eier-Log (Zugang/Abgang)
# -------------------------------------------------
class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datum = db.Column(db.Date, default=date.today, nullable=False)
    zeitpunkt = db.Column(db.String(10), nullable=True)  # "HH:MM"
    typ = db.Column(db.String(20), nullable=False)       # 'zugang' | 'abgang'
    menge = db.Column(db.Integer, nullable=False)
    benutzer = db.Column(db.String(120), nullable=True)  # username
    name = db.Column(db.String(200), nullable=True)      # Beschreibung
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<LogEntry {self.typ} {self.menge} {self.datum}>"


# -------------------------------------------------
# Abonnenten (Eier-Abos) + Ausnahmen (skip/shift)
# -------------------------------------------------
class Abonnement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)                 # Kunde/Haushalt
    menge = db.Column(db.Integer, nullable=False, default=10)        # Eier pro Abholung
    abholtag = db.Column(db.Integer, nullable=False, default=5)      # 0=Mo .. 6=So (Python weekday)
    aktiv = db.Column(db.Boolean, nullable=False, default=True)
    notizen = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Abo {self.name} {self.menge}@{self.abholtag} aktiv={self.aktiv}>"


class AboException(db.Model):
    """
    Ausnahme/Vormerkung zu einem Abo:
      - action = 'skip'  -> heutige Woche aussetzen
      - action = 'shift' -> auf new_datum verschieben (z.B. morgen)
    """
    id = db.Column(db.Integer, primary_key=True)
    abo_id = db.Column(db.Integer, db.ForeignKey('abonnement.id'), nullable=False, index=True)
    datum = db.Column(db.Date, nullable=False)                       # ursprünglicher Abholtag
    action = db.Column(db.String(20), nullable=False)                # 'skip' | 'shift'
    new_datum = db.Column(db.Date)                                   # nur bei 'shift' belegt
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    abo = db.relationship('Abonnement', backref=db.backref('exceptions', lazy=True))

    def __repr__(self) -> str:
        return f"<AboEx abo={self.abo_id} {self.action} {self.datum} -> {self.new_datum}>"
