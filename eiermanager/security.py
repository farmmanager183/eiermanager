# eiermanager/security.py
import hashlib
from flask import current_app

def pin_index_from_pin(pin: str) -> str:
    """
    Berechnet einen deterministischen, durchsuchbaren Index für eine PIN.
    Speichert NICHT die PIN im Klartext. Für Lookup + danach Hash-Check.
    """
    pin = (pin or "").strip()
    pepper = current_app.config.get("PIN_PEPPER", "default-pepper")
    return hashlib.sha256((pepper + pin).encode("utf-8")).hexdigest()
