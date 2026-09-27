#Imports

import argparse
import html
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

#Descarta el ruido
MAX_CHARS = 1000

hashstag_oferta = {
    "hiring", "nowhiring", "jobs", "jobalert", "jobopening",
    "remotejobs", "vacante", "oferta_laboral", "ofertadeempleo", 
}

palabra_oferta = [
    "is hiring", "are hiring", "we're hiring", "job details",
    "apply now", "estamos contratando", "oferta laboral", "oferta de empleo",
    "vacante", "postúlante", "postulate",
]

#Funciones

def limpiar_html(textoHtml: str) -> str:
    if not textoHtml:
        return ""
    texto = re.sub(r"</p>|<br\s*/>", "\n", textoHtml)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = html.unescape(texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    return texto

def _contiene(texto: str, palabras: list[str]) -> bool:
    for p in palabras:
        if p == "?":
            if "?" in texto:
                return True
        elif re.search(r"\b" + re.escape(p), texto):
                return True
    return False

def calificar_tipo(texto: str) -> str:
    t = re.sub(r"https?://\S+", "", texto.lower())
    if _contiene(t, lista_palabras_testmonio):
        return "testimonio"
    if _contiene(t,lista_palabras_preguntas):
        return "pregunta tecnica"
    return "comentario general"

def oferta_Laboral(p: dict, texto: str) -> bool:
    tags = {t["name"].lower() for t in p.get("tags", [])}
    if tags & hashstag_oferta:
        return True
    t = texto.lower()
    return any(f in t for f in palabra_oferta)

def relevante(p: dict, tipo: str | None) -> bool:
    if p.get("account", {}).get("bot"):
        return False
    texto = limpiar_html(p.get("content", ""))
    if not texto or len(texto) > MAX_CHARS:
        return False
    if oferta_Laboral(p, texto):
        return False
    if tipo and calificar_tipo(texto) != tipo:
        return False
    return True

# Esta función se encarga de obtener los post publicos desde mastodon usando su endpoint publico.
def obtener_posts(instancia: str, hashtag: str, limite: int, tipo: str | None = None, max_paginas: int = 10) -> list[dict]:
    url = f"https://{instancia}/api/v1/timelines/tag/{hashtag}"
    posts: list[dict] = []
    max_id = None

    for _ in range(max_paginas):
        if len(posts) >= limite:
            break

        params = {"limit": min(40, limite - len(posts))}
        if max_id:
            params["max_id"] = max_id

        respuesta = requests.get(url, params=params, timeout=15)
        respuesta.raise_for_status()
        lote = respuesta.json()
        #Si no hay mas resultados
        if not lote:
            break

        max_id = lote[-1]["id"]
        posts.extend(p for p in lote if relevante(p, tipo))

        #Ya no hay más páginas
        if len(lote) < params["limit"]:
            break 

    return posts

def mapear_posts(posts: list[dict], canal: str) -> list[dict]:
    interaccion = []
    for p in posts:
        texto = limpiar_html(p.get("content", ""))
        interaccion.append({
            "id": p["id"],
            "canal": canal,
            "autor": p["account"]["acct"],
            "fecha": p["created_at"],
            "texto": texto,
            "tipo": calificar_tipo(texto),
            "url": p.get("url"),
        })
    return interaccion

def main():
    parser = argparse.ArgumentParser(description="Ingesta de Mastodon para CommunityLab")
    parser.add_argument("--hashtag", required=True, help="Hashtag a consultar sin '#' (ej: ia, python)")
    parser.add_argument("--instance", default="mastodon.social", help="instancia de Mastodon (default: mastodon.social)")
    parser.add_argument("--limit", type=int, default=40, help='Cantidad máxima de post a traer (default: 40)')
    parser.add_argument("--tipo", choices=["testimonio", "pregunta tecnica", "comentario general"], default=None,
                        help="Conservar unicamente este tipo de interacción")
    parser.add_argument("--origen", default=None, help="Valor de 'origen_comunidad' en el JSON de salida")
    parser.add_argument("--out", default="data/sample/mastodon_interacciones.json", help="Ruta del archivo de salida")
    args = parser.parse_args()

    canal_label = f"#{args.hashtag}@{args.instance}"
    origen = args.origen or f"Mastodon_{args.instance}_{args.hashtag}"

    print(f"Consulta a https://{args.instance}/api/v1/timelines/tag/{args.hashtag}", file=sys.stderr)

    try:
        posts = obtener_posts(args.instance, args.hashtag, args.limit, args.tipo)
    except requests.RequestException as err: #err => Error
        print(f"Error consultando Mastodon: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"{len(posts)} posts recibidos, mapeando al formato de CommunityLab", file=sys.stderr)

    interactuar = mapear_posts(posts, canal_label)

    payload = {
        "origen_comunidad": origen,
        "periodo_referencia": datetime.now(timezone.utc).strftime("Semana_%V_%Y"),
        "interacciones": interactuar
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    tipos = {}
    for i in interactuar:
        tipos[i["tipo"]] = tipos.get(i["tipo"], 0) + 1

    print(f"Guardado: {out_path} ({len(interactuar)} interaciones)", file=sys.stderr)
    print(f"Los tipos de distribuyen como: {tipos}", file=sys.stderr)

if __name__ == "__main__":
    main()