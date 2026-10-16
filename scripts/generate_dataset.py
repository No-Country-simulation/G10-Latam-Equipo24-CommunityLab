#!/usr/bin/env python3
"""Generador de dataset sintético determinista para CommunityLab.

Uso:
    python scripts/generate_dataset.py [--salida data/sample/sintetico_120.csv]
                                       [--filas 120] [--semilla 42]

Genera un CSV con los encabezados autor,canal,tipo,texto: mensajes realistas
en español neutro de una comunidad tech (empleo, portafolio, migración de
servidores, tutoriales, dudas tipo FAQ y errores). Incluye mensajes negativos
de feedback con queja para que la regla R4/DERIVAR tenga material.

Determinismo: se usa random.Random(semilla), nunca el random global; la misma
semilla produce siempre el mismo dataset. Sin dependencias externas.
"""

import argparse
import csv
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SALIDA = REPO_ROOT / "data" / "sample" / "sintetico_120.csv"
DEFAULT_FILAS = 120
DEFAULT_SEMILLA = 42

AUTORES = [
    "Mariana",
    "Carlos",
    "Luciana",
    "Jorge",
    "Ana",
    "Diego",
    "Valentina",
    "Ramiro",
    "Elena",
    "Federico",
]

# Pools de mensajes: (peso, canal, tipo, [textos]). El peso controla la
# frecuencia relativa de cada tema; los autores y los textos se eligen con
# random.Random(semilla).
_POOLS = [
    # Testimonios y logros (canal general)
    (4, "general", "testimonio", [
        "Conseguí mi primer empleo como desarrolladora después de seis meses de estudio.",
        "Quedé seleccionado para el puesto junior que recomendaron en la comunidad.",
        "El proyecto del curso fue clave en la entrevista técnica que tuve esta semana.",
        "Terminé el bootcamp y ya estoy aplicando a vacantes con mi portafolio.",
    ]),
    (2, "general", "logro", [
        "Migré mi aplicación de pruebas a OCI y quedó funcionando de entrada.",
        "Aprobé la certificación de la nube y lo festejo con el grupo.",
        "Publicaron mi proyecto en el newsletter de la comunidad.",
    ]),
    # Dudas técnicas tipo FAQ (canal ayuda)
    (3, "ayuda", "pregunta_tecnica", [
        "¿Cómo valido un token JWT en una API con FastAPI?",
        "¿Cuál es la diferencia entre una clase y una función en Python?",
        "¿Cómo conecto el backend con una base de datos en la nube?",
        "¿Qué pasos sigo para desplegar un contenedor en OCI?",
        "¿Cuál es la mejor forma de estructurar un proyecto grande en Python?",
        "¿Cómo manejo variables de entorno sin exponer las claves?",
    ]),
    # Migración y servidores (canal ayuda)
    (2, "ayuda", "pregunta_tecnica", [
        "¿Alguien migró una base local a Autonomous Database? ¿Qué cuidados hay que tener?",
        "El balanceador de OCI me devuelve error 502 con la app nueva, ¿por dónde empiezo?",
        "¿Conviene migrar el servidor o empezar de cero en la nube?",
    ]),
    # Errores (canal ayuda)
    (2, "ayuda", "pregunta_tecnica", [
        "Me da error 500 al subir el modelo entrenado, alguien sabe por qué puede ser.",
        "El certificado TLS venció y el sitio cae, ¿cómo lo renuevan en OCI?",
        "El pipeline de CI falla por un error de dependencias y no entiendo el log.",
    ]),
    # Tutoriales (canal general)
    (2, "general", "discusion", [
        "El tutorial de despliegue con Docker me ahorró un día entero, muy claro.",
        "Gracias por el tutorial de CI/CD: pude automatizar las pruebas del proyecto.",
        "¿Hacen un tutorial de autenticación con OAuth para el próximo encuentro?",
    ]),
    # Feedback positivo (canal feedback)
    (1, "feedback", "feedback", [
        "El taller de portafolios estuvo muy bueno, me llevé ideas concretas.",
        "La mentoría individual me sirvió muchísimo para ordenar el proyecto.",
    ]),
    # Feedback negativo con queja (canal feedback): material para R4/DERIVAR.
    (3, "feedback", "feedback", [
        "La demo de la semana pasada terminó apurada y no hubo espacio para preguntas.",
        "Las correcciones de los proyectos tardan demasiado: perdí dos semanas esperando.",
        "El canal de ayuda quedó sin respuestas varias horas y no hay un plan B.",
        "El encuentro del sábado fue confuso, no se explicaron los objetivos de las actividades.",
    ]),
]

_HEADERS = ("autor", "canal", "tipo", "texto")


def generar(filas: int = DEFAULT_FILAS, semilla: int = DEFAULT_SEMILLA):
    """Devuelve las filas (dicts) del dataset para la semilla dada."""
    rng = random.Random(semilla)
    pesos = [pool[0] for pool in _POOLS]
    generadas = []
    for _ in range(filas):
        _, canal, tipo, textos = rng.choices(_POOLS, weights=pesos)[0]
        generadas.append(
            {
                "autor": rng.choice(AUTORES),
                "canal": canal,
                "tipo": tipo,
                "texto": rng.choice(textos),
            }
        )
    return generadas


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera un dataset sintético determinista para CommunityLab."
    )
    parser.add_argument(
        "--salida",
        default=str(DEFAULT_SALIDA),
        help=f"Ruta del CSV generado (default: {DEFAULT_SALIDA})",
    )
    parser.add_argument(
        "--filas",
        type=int,
        default=DEFAULT_FILAS,
        help=f"Cantidad de mensajes a generar (default: {DEFAULT_FILAS})",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=DEFAULT_SEMILLA,
        help=f"Semilla para random.Random (default: {DEFAULT_SEMILLA})",
    )
    args = parser.parse_args()

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_HEADERS)
        writer.writeheader()
        writer.writerows(generar(args.filas, args.semilla))

    print(
        f"Dataset generado: {salida} "
        f"({args.filas} mensajes, semilla {args.semilla})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
