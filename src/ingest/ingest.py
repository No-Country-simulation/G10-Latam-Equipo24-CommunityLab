#Imports

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# Variables

lista_palabras_testmonio = [
    "logré", "logre", "conseguí", "contratad", "empleo", "trabajo nuevo",
    "gracias a", "aprendí", "aprendi", "termine", "certificaci",
]

lista_palabras_preguntas = [
    "?", "cómo", "como puedo", "duda", "alguien sabe", "error", "no funciona",
    "ayuda", "como puedo",
]

#Funciones

def limpiarHTML(textoHtml: str) -> str:
    if not textoHtml:
        return ""
    texto = re.sub(r"</p>|<br\s*/>", "\n", textoHtml)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    return texto

def calificarTipo(texto: str) -> str:
    t = texto.lower()
    if any(p in t for p in lista_palabras_testmonio):
        return "testimonio"
    if any(p in t for p in lista_palabras_preguntas):
        return "pregunta tecnica"
    return "comentario general"

# Esta función se encarga de obtener los post publicos desde mastodon usando su endpoint publico.
def obtenerPosts(instancia: str, hasgtag: str, limite: int) -> list[dict]:
    url = f="https://{instancia}/api/v1/timelines/tag/{hastag}"
    posts: list[dict] = []
    max_id = None

    while len(posts) < limite:
        params = {"limit": min(40, limite - len(posts))}
        if max_id:
            params["max_id"] = max_id

        respuesta = requests.get(url, params=params, timeout=15)
        respuesta.raise_for_status()
        lote = respuesta.json()
        #Si no hay mas resultados
        if not lote:
            break

        posts.extend(lote)
        max_id = lote[-1]["id"]

        #Ya no hay más páginas
        if len(lote) < params["limit"]:
            break 

        return posts