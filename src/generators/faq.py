import argparse, json
from pathlib import Path


def cargar_interacciones(ruta):
    with Path(ruta).open(encoding="utf-8") as f:
        return json.load(f)["interacciones"]


def main():
    parser = argparse.ArgumentParser(description="Generador de FAQ")
    parser.add_argument("--input", default="data/sample/demo_fixed.json")
    parser.add_argument("--out", default="data/raw/faq.md")
    args = parser.parse_args()

    interacciones = cargar_interacciones(args.input)


if __name__ == "__main__":
    main()