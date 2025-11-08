# eiermanager/modules_seed.py
SEED_MODULES = [
    # key, label, endpoint, admin_only
    ("huehner",          "Hühner",           "huehner.index",            False),
    ("verkauf",          "Verkauf",          "verkauf.index",            False),
    ("abonnenten",       "Abonnenten",       "abonnenten.index",         False),
    ("aufgaben",         "Aufgaben",         "aufgaben.index",           False),
    ("ackerschlag",      "Schlagkartei",     "ackerschlag.index",        False),
    ("ferienwohnungen",  "Ferienwohnungen",  "ferienwohnungen.index",    False),
    ("werkstatt",        "Werkstatt",        "werkstatt.index",          False),
    ("lager",            "Lager",            "lager.index",              False),
    ("rinder",           "Rinder",           "rinder.index",             False),
    ("pferde",           "Pferde",           "pferde.index",             False),
    ("events",           "Events",           "events.index",             False),

    # Admin
    ("benutzer",         "Benutzer",         "benutzer.index",           True),
    ("finanzen",         "Finanzen",         "finanzen.index",           True),
    ("reports",          "Reports",          "reports.index",            True),
    ("marketing",        "Marketing",        "marketing.index",          True),
]
