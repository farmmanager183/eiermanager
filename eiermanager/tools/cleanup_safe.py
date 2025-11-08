# eiermanager/tools/cleanup_safe.py
import os, re, shutil, sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]   # .../eiermanager
ROOT = BASE.parent
TEMPLATES = BASE / "templates"
STATIC    = BASE / "static"
INIT_FILE = BASE / "__init__.py"

ARCHIVE   = BASE / "archiv"
ARCH_TPL  = ARCHIVE / "unused_templates"
ARCH_PY   = ARCHIVE / "unused_python"

DRY_RUN = "--dry-run" in sys.argv

# === Platzhalter-Module, die wir NICHT anfassen (auch wenn derzeit unregistriert) ===
PLACEHOLDER_MODULES = {
    "ackerschlag","events","ferienwohnungen","finanzen","kommunikation",
    "lager","marketing","mobil","personal","pferde","qualitaet",
    "reports","rinder","tickets","werkstatt"
}

# === Python-Dateien, die grundsätzlich erhalten bleiben ===
PY_KEEP = {
    "__init__.py","models.py","extensions.py","bootstrap.py",
    # aktiv genutzt:
    "auth.py","core.py","benutzer.py","eier.py","huehner.py","verkauf.py","abonnenten.py","aufgaben.py",
    # benötigt von bootstrap:
    "modules_seed.py",
}

# === Templates, die grundsätzlich erhalten bleiben (Kern + Platzhalter-Einstiege) ===
TPL_KEEP_BASENAMES = {"base.html","menu.html","login2.html","index.html"}
# Zusätzlich: pro (Unter-)Modul behalten wir menu.html/index.html als Platzhalter
# sowie *alle* aktuellen eier/huehner-Templates.
TPL_KEEP_PREFIXES = {
    "eier/","huehner/"   # komplette Unterordner behalten (wir räumen dort separat innerhalb auf Wunsch)
}

def ensure_dirs():
    (ARCH_TPL).mkdir(parents=True, exist_ok=True)
    (ARCH_PY).mkdir(parents=True, exist_ok=True)

def list_files():
    py_files = [p for p in BASE.rglob("*.py") if "archiv" not in p.parts and "tools" not in p.parts]
    tpl_files = [p for p in TEMPLATES.rglob("*.html") if "archiv" not in p.parts]
    return py_files, tpl_files

def parse_template_refs(py_files, tpl_files):
    render_pat  = re.compile(r'render_template\(\s*[\'"]([^\'"]+)[\'"]')
    extends_pat = re.compile(r'\{\%\s*extends\s*[\'"]([^\'"]+)[\'"]\s*\%\}')
    include_pat = re.compile(r'\{\%\s*include\s*[\'"]([^\'"]+)[\'"]\s*\%\}')
    import_pat  = re.compile(r'\{\%\s*import\s*[\'"]([^\'"]+)[\'"]\s+as')

    py_refs = set()
    for py in py_files:
        try:
            txt = py.read_text(encoding="utf-8")
            for m in render_pat.finditer(txt):
                py_refs.add(m.group(1))
        except: pass

    t2t_refs = set()
    for tf in tpl_files:
        try:
            ttxt = tf.read_text(encoding="utf-8")
            for pat in (extends_pat, include_pat, import_pat):
                for m in pat.finditer(ttxt):
                    t2t_refs.add(m.group(1))
        except: pass
    return py_refs, t2t_refs

def parse_registered_modules():
    """Welche Module werden in __init__.py importiert/registriert?"""
    try:
        txt = INIT_FILE.read_text(encoding="utf-8")
    except:
        return set(), set()
    imported = set()
    for m in re.finditer(r'from\s+eiermanager\s+import\s+\((.*?)\)', txt, flags=re.S):
        block = m.group(1)
        for name in re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)', block):
            imported.add(name)
    # Zusätzlich grob prüfen, welche Blueprints registriert werden (rein informativ)
    regs = set(re.findall(r'app\.register_blueprint\(([^)]+)\)', txt))
    return imported, regs

def is_placeholder_module_file(py_path: Path) -> bool:
    name = py_path.stem
    return name in PLACEHOLDER_MODULES

def should_keep_template(rel: str) -> bool:
    # Hard keep by basename
    if Path(rel).name in TPL_KEEP_BASENAMES:
        return True
    # Keep whole subtrees by prefix (eier/, huehner/)
    for prefix in TPL_KEEP_PREFIXES:
        if rel.startswith(prefix):
            # innerhalb dieser Subtrees behalten wir ALLES; alternativ hier filtern
            return True
    # Keep Platzhalter-Einstiege je Modul: */menu.html, */index.html
    parts = rel.split("/")
    if len(parts) >= 2 and parts[-1] in ("menu.html","index.html"):
        return True
    return False

def compute_unused_templates(tpl_files, py_refs, t2t_refs):
    all_rel = {p.relative_to(TEMPLATES).as_posix() for p in tpl_files}
    reachable = set(py_refs) | set(t2t_refs)
    candidates = sorted(all_rel - reachable)
    # Filter: alles behalten, was explizit als Platzhalter/Kern markiert ist
    return [c for c in candidates if not should_keep_template(c)]

def compute_unused_python(py_files, imported_modules):
    unused = []
    for p in py_files:
        if p.name in PY_KEEP:
            continue
        # Platzhalter-Module niemals verschieben, auch wenn unregistriert
        if is_placeholder_module_file(p):
            continue
        # Wenn Modulname NICHT in importliste auftaucht UND eine Blueprint-Definition enthält -> Kandidat
        try:
            txt = p.read_text(encoding="utf-8")
        except:
            continue
        defines_bp = "Blueprint(" in txt
        module_name = p.stem
        if defines_bp and module_name not in imported_modules:
            unused.append(p)
    return unused

def move(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if DRY_RUN:
        print(f"[DRY] move {src} -> {dst}")
    else:
        print(f"[MOVE] {src} -> {dst}")
        shutil.move(str(src), str(dst))

def main():
    ensure_dirs()
    py_files, tpl_files = list_files()
    py_refs, t2t_refs = parse_template_refs(py_files, tpl_files)
    imported_modules, _ = parse_registered_modules()

    unused_tpl = compute_unused_templates(tpl_files, py_refs, t2t_refs)
    unused_py  = compute_unused_python(py_files, imported_modules)

    print(f"Unused templates (candidates): {len(unused_tpl)}")
    print(f"Unused python modules (candidates): {len(unused_py)}")

    # Verschieben
    for rel in unused_tpl:
        src = TEMPLATES / rel
        dst = ARCH_TPL / rel
        if src.exists():
            move(src, dst)

    for p in unused_py:
        rel = p.relative_to(BASE)
        dst = ARCH_PY / rel
        move(p, dst)

    print("Fertig. App neu starten & Smoke-Test (Login → Menü → Eier/Hühner/Verkauf/Abos/Aufgaben).")

if __name__ == "__main__":
    main()
