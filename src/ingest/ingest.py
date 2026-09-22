import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

lista_palabras_testmonio = [
    "logré", "logre", "conseguí", "contratad", "empleo", "trabajo nuevo",
    "gracias a", "aprendí", "aprendi", "termine", "certificaci",
]

lista_palabras_preguntas = [
    "?", "cómo", "como puedo", "duda", "alguien sabe", "error", "no funciona",
    "ayuda", "como puedo",
]

def limpiarHTML(textoHtml: str) -> str:

    if not textoHtml:
        return ""
    texto = re.sub(r"</p>|<br\s*/>", "\n", textoHtml)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    return texto