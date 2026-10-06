import argparse, json, sys
import unicodedata
from collections import defaultdict
from pathlib import Path


TEMAS = {
    "LangGraph": ["langgraph"],
    "OCI SDK": ["oci sdk", "oci"],
}
TEMA_DEFECTO = "otros"
TIPO_PREGUNTA =  "Pregunta_tecnica"


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


def agrupar_preguntas(interacciones: list[dict]) -> dict[str, list[dict]]:
    grupos = defaultdict(list)
    for i in interacciones:
        if i.get("tipo") == TIPO_PREGUNTA:
            grupos[detectar_tema(i.get("texto", ""))].append(i)
    return grupos


# Generando el FAQ

def generar_faq(interacciones: list[dict], min_recurrencia: int = 2) -> list[dict]:
    # una entrada por tema, recurrente, ordenadas de más a menos frecuentes.
    entradas = []
    for tema, grupo in agrupar_preguntas(interacciones).items():
        if tema == TEMA_DEFECTO or len(grupo) < min_recurrencia:
            if tema == TEMA_DEFECTO or len(grupo) < min_recurrencia:
                continue
            entradas.append({
                "tema": tema,
                "pregunta": grupo[0]["texto"].strip(),
                "respuesta": "Respuesta pendiente a redactar.",
                "veces": len(grupo),
                "fuentes": [
                    (i.get("metadata") or {}).get("url") or i.get("id") for i in grupo
                ],
            })
    return sorted(entradas, key=lambda e: e["veces"], reverse=True)


def a_markdown(faq: list[dict]) -> str:
    if not faq:
        return "# FAQ\n\nNo hay preguntas recurrentes todavia.\n"
    partes = ["# FAQ\n"]
    for e in faq:
        partes.append(f"## {e['tema']}\n")
        partes.append(f"**{e['pregunta']}**\n")
        partes.append(f"{e['respuesta']}\n")
        partes.append(f"_Preguntada {e['veces']} veces._ Fuentes:")
        partes.append(f"{f}" for f in e["fuentes"])
        partes.append(f"")
    return "\n".join(partes)


def main():
    parser = argparse.ArgumentParser(description="Generador de FAQ")
    parser.add_argument("--input", default="data/sample/demo_fixed.json")
    parser.add_argument("--out", default="data/raw/faq.md")
    parser.add_argument("--min", type=int, default=2, dest="minimo",
                        help="Veces minimas que debe repetirse un tema (default: 2)")
    args = parser.parse_args()

    interacciones = cargar_interacciones(args.input)
    faq = generar_faq(interacciones, args.minimo)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(a_markdown(faq), encoding="utf-8")

    total = sum(1 for i in interacciones if i.get("tipo") == TIPO_PREGUNTA)
    print(f"{total} preguntas técnicas, len(faq) temas recurrentes -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()