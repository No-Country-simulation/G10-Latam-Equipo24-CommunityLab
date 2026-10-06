import argparse, json, sys
import unicodedata
from collections import defaultdict
from pathlib import Path


TEMAS = {
    "LangGraph": ["langgraph"],
    "OCI SDK": ["oci sdk", "oci"],
}
TEMA_DEFECTO = "otros"
TIPO_PROGUNTA =  "Pregunta_tecnica"


def quitar_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def cargar_interacciones(ruta):
    with Path(ruta).open(encoding="utf-8") as f:
        data = json.load(f)
    return data["interacciones"] if isinstance(data, dict) else data


def detectar_tema(texto: str) -> str:
    t = quitar_tildes(texto.lower())
    for tema, claves in TEMAS.items():
        if any(c in t for c in claves):
            return tema
    return TEMA_DEFECTO


def main():
    parser = argparse.ArgumentParser(description="Generador de FAQ")
    parser.add_argument("--input", default="data/sample/demo_fixed.json")
    parser.add_argument("--out", default="data/raw/faq.md")
    args = parser.parse_args()

    interacciones = cargar_interacciones(args.input)


if __name__ == "__main__":
    main()