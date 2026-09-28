import pytest
import requests

from src.ingest import ingest
from src.ingest.ingest import limpiar_html, obtener_posts, oferta_laboral


class FakeResp:
    def __init__(self, status=200, data=None, headers=None):
        self.status_code = status
        self._data = data if data is not None else []
        self.headers = headers or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


def post(i, content="<p>hola mundo</p>"):
    return {"id": str(i), "content": content, "tags": [],
            "account": {"acct": "u", "bot": False}}


@pytest.fixture
def mock_get(monkeypatch):
    """Devuelve una función que instala respuestas en orden y registra las llamadas."""
    def instalar(respuestas):
        it = iter(respuestas)
        llamadas = []

        def fake_get(url, params=None, timeout=None):
            llamadas.append(dict(params))
            return next(it)

        monkeypatch.setattr(ingest.requests, "get", fake_get)
        return llamadas
    return instalar


@pytest.fixture
def sleeps(monkeypatch):
    registro = []
    monkeypatch.setattr(ingest.time, "sleep", registro.append)
    return registro


# --- 429 ---

def test_429_respeta_retry_after(mock_get, sleeps):
    mock_get([FakeResp(429, headers={"Retry-After": "2"}),
              FakeResp(200, [post(1)])])
    assert len(obtener_posts("x", "python", 1)) == 1
    assert sleeps == [2]


def test_429_retry_after_fecha_http_usa_default(mock_get, sleeps):
    mock_get([FakeResp(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}),
              FakeResp(200, [post(1)])])
    assert len(obtener_posts("x", "python", 1)) == 1
    assert sleeps == [5]


def test_429_tope_de_60s(mock_get, sleeps):
    mock_get([FakeResp(429, headers={"Retry-After": "999"}),
              FakeResp(200, [post(1)])])
    obtener_posts("x", "python", 1)
    assert sleeps == [60]


def test_429_no_consume_paginas(mock_get, sleeps):
    mock_get([FakeResp(429), FakeResp(200, [post(1)])])
    assert len(obtener_posts("x", "python", 1, max_paginas=1)) == 1


def test_429_exceso_de_reintentos_lanza_error(mock_get, sleeps):
    mock_get([FakeResp(429)] * 4)
    with pytest.raises(requests.HTTPError):
        obtener_posts("x", "python", 1)
    assert len(sleeps) == 3


# --- paginación ---

def test_paginacion_limit_mayor_a_40(mock_get):
    p1 = [post(i) for i in range(200, 160, -1)]
    p2 = [post(i) for i in range(160, 120, -1)]
    p3 = [post(i) for i in range(120, 100, -1)]
    llamadas = mock_get([FakeResp(200, p1), FakeResp(200, p2), FakeResp(200, p3)])

    resultado = obtener_posts("x", "python", 100)

    assert len(resultado) == 100
    assert [c["limit"] for c in llamadas] == [40, 40, 20]
    assert "max_id" not in llamadas[0]
    assert llamadas[1]["max_id"] == "161"   # id del último post del lote anterior


def test_log_cuando_se_agotan_paginas(mock_get, capsys):
    ruido = [post(i, "<p>Acme is hiring devs</p>") for i in range(40)]
    mock_get([FakeResp(200, ruido), FakeResp(200, ruido)])

    assert obtener_posts("x", "python", 100, max_paginas=2) == []
    assert "Se agotaron las 2 páginas" in capsys.readouterr().err


def test_sin_log_si_se_acaban_los_resultados(mock_get, capsys):
    mock_get([FakeResp(200, [post(1), post(2)])])
    assert len(obtener_posts("x", "python", 100)) == 2
    assert "Se agotaron" not in capsys.readouterr().err


# --- oferta_laboral ---

def test_oferta_por_hashtag():
    p = {"tags": [{"name": "Hiring"}]}
    assert oferta_laboral(p, "cualquier cosa")


def test_oferta_por_frase_con_y_sin_tilde():
    assert oferta_laboral({}, "Estamos contratando programadores")
    assert oferta_laboral({}, "Postúlate ya")


def test_postulates_no_es_oferta():
    assert not oferta_laboral({}, "the paper postulates a new theory")


def test_texto_normal_no_es_oferta():
    assert not oferta_laboral({}, "Aprendí Python este mes")


# --- limpiar_html ---

def test_limpiar_html_parrafos_y_br():
    assert limpiar_html("<p>Hola</p><p>mundo</p>") == "Hola\nmundo"
    assert limpiar_html("a<br />b") == "a\nb"


def test_limpiar_html_quita_tags_y_entidades():
    assert limpiar_html('<a href="x">link</a> &amp; más') == "link & más"


def test_limpiar_html_colapsa_saltos():
    assert limpiar_html("a<br /><br /><br /><br />b") == "a\n\nb"


def test_limpiar_html_vacio():
    assert limpiar_html("") == ""
    assert limpiar_html(None) == ""


def test_sin_log_si_alcanza_el_limite(mock_get, capsys):
    p1 = [post(i) for i in range(200, 160, -1)]
    p2 = [post(i) for i in range(160, 120, -1)]
    p3 = [post(i) for i in range(120, 100, -1)]
    mock_get([FakeResp(200, p1), FakeResp(200, p2), FakeResp(200, p3)])

    assert len(obtener_posts("x", "python", 100)) == 100
    assert "Se agotaron" not in capsys.readouterr().err