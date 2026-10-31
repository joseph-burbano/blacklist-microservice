"""Empaqueta la aplicación para despliegue manual tras aprobar las pruebas."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "blacklist-deploy.zip"
REQUIRED = ("application.py", "version.py", "manage.py", "requirements.txt")
DIRECTORIES = ("app", ".ebextensions")


def main():
    files = [ROOT / name for name in REQUIRED]
    missing_directories = [name for name in DIRECTORIES if not (ROOT / name).is_dir()]
    for directory in DIRECTORIES:
        files.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
    missing = [str(path.relative_to(ROOT)) for path in files if not path.is_file()]
    if missing or missing_directories:
        raise SystemExit("Faltan archivos de despliegue: " + ", ".join(missing + missing_directories))

    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(files):
            if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                continue
            archive.write(path, path.relative_to(ROOT).as_posix())
    print("Artefacto creado:", OUTPUT.name)


if __name__ == "__main__":
    main()
