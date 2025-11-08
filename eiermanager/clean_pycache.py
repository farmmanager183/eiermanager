# clean_pycache.py
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def clean_pycache(root_dir):
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for d in dirnames:
            if d == "__pycache__":
                full_path = os.path.join(dirpath, d)
                print(f"🗑️ Entferne: {full_path}")
                shutil.rmtree(full_path, ignore_errors=True)
                removed += 1
    return removed

if __name__ == "__main__":
    count = clean_pycache(BASE_DIR)
    if count:
        print(f"\n✅ {count} '__pycache__'-Ordner erfolgreich gelöscht.")
    else:
        print("\nℹ️ Keine '__pycache__'-Ordner gefunden.")
