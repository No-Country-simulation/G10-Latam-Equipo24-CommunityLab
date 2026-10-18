import pytest

from src.ingest.csv_loader import CSVInputLoader, _count_outside_quotes

TIPO = "feedback"


def _write(tmp_path, content, encoding="utf-8", name="datos.csv"):
    """Escribe `content` en un CSV con la codificación indicada."""
    path = tmp_path / name
    path.write_bytes(content.encode(encoding))
    return path


def test_utf8_bom_is_tolerated(tmp_path):
    content = (
        "autor;canal;tipo;texto\n"
        f"ana;general;{TIPO};hola\n"
        f"luis;general;{TIPO};que tal\n"
    )
    path = _write(tmp_path, content, encoding="utf-8-sig")

    batch = CSVInputLoader().load_batch(str(path))

    assert len(batch.interacciones) == 2


def test_cp1252_falls_back_when_utf8_fails(tmp_path):
    content = (
        "autor;canal;tipo;texto\n"
        f"ana;general;{TIPO};canción con ñ\n"
        f"luis;general;{TIPO};ñandú\n"
    )
    path = _write(tmp_path, content, encoding="cp1252")

    batch = CSVInputLoader().load_batch(str(path))

    assert len(batch.interacciones) == 2


def test_undecodable_file_raises_clear_error(tmp_path):
    # 0x81 no es válido ni en utf-8 ni en cp1252.
    path = tmp_path / "roto.csv"
    path.write_bytes(
        b"autor;canal;tipo;texto\n"
        b"ana;general;" + TIPO.encode() + b";\x81\n"
    )

    with pytest.raises(ValueError, match="No se pudo decodificar"):
        CSVInputLoader().load_batch(str(path))


@pytest.mark.parametrize("sep", [";", "\t", ","])
def test_delimiter_is_autodetected(tmp_path, sep):
    rows = [
        ["autor", "canal", "tipo", "texto"],
        ["ana", "general", TIPO, "hola"],
        ["luis", "general", TIPO, "que tal"],
    ]
    content = "\n".join(sep.join(r) for r in rows) + "\n"
    path = _write(tmp_path, content)

    batch = CSVInputLoader().load_batch(str(path))

    assert len(batch.interacciones) == 2


@pytest.mark.parametrize(
    "header, sep",
    [
        # CSV de Excel con ";": el encabezado trae 4 comas citadas y solo4
        # punto y coma reales, así que empatan en cantidad. Contando a
        # ciegas, el desempate por orden de `_DELIMITERS` elegiría la coma.
        ('"nota, a, b, c, d";autor;canal;tipo;texto', ";"),
        # Caso simétrico: CSV de comas con un ";" citado de más.
        ('"nota; a; b; c; d; e",autor,canal,tipo,texto', ","),
    ],
)
def test_quoted_header_cells_do_not_confuse_delimiter(tmp_path, header, sep):
    # La primera columna es un descartable a propósito: pone el encabezado y
    # las filas en el mismo orden de modo que el mapeo por nombre quede
    # alineado y se pueda assertar. Assertar solo `len(...)` no detectaría
    # un desplazamiento de columnas.
    rows = [
        header,
        sep.join(["x", "ana", "general", TIPO, "hola"]),
        sep.join(["y", "luis", "general", TIPO, "que tal"]),
    ]
    path = _write(tmp_path, "\n".join(rows) + "\n")

    batch = CSVInputLoader().load_batch(str(path))

    assert len(batch.interacciones) == 2
    assert [i.autor for i in batch.interacciones] == ["ana", "luis"]
    assert [i.canal for i in batch.interacciones] == ["general", "general"]
    assert [i.tipo for i in batch.interacciones] == [TIPO, TIPO]
    assert [i.texto for i in batch.interacciones] == ["hola", "que tal"]


# ---------------------------------------------------------------------------
# Unidades del detector de delimitador
#
# Pasan por `load_batch` son pruebas de extremo a extremo: si el delimitador
# sale mal, el error aparece lejos de su causa. Estas prueban la función
# directamente, así el fallo nombra al culpable y se cubren los casos que la
# ruta completa no alcanza (tab y comillas escapadas).
# ---------------------------------------------------------------------------


def test_count_outside_quotes_ignores_quoted_separators():
    assert _count_outside_quotes("a,b;c;d", ",") == 1
    assert _count_outside_quotes('"a,b";c;d', ",") == 0
    assert _count_outside_quotes('"a,b";c,d', ",") == 1


def test_count_outside_quotes_tolerates_escaped_quotes():
    # Una comilla escapada (`""`) alterna dos veces y deja el estado igual.
    assert _count_outside_quotes('"a""b,c";d,e', ",") == 1
    assert _count_outside_quotes('"a""b,c"', ",") == 0


@pytest.mark.parametrize(
    "sample, expected",
    [
        # Un solo separador presente: ese gana.
        ("autor,canal,tipo,texto", ","),
        ("autor;canal;tipo;texto", ";"),
        ("autor\tcanal\ttipo\ttexto", "\t"),
        # Empate en cantidad: desempata el orden de `_DELIMITERS`
        # (la coma va primero), igual que hacía el `max` anterior.
        ("a,b;c", ","),
        # Sin ningún separador, o muestra vacía: fallback a la coma.
        ("autortexto", ","),
        ("", ","),
    ],
)
def test_detect_delimiter_picks_the_unquoted_winner(sample, expected):
    assert CSVInputLoader._detect_delimiter(sample) == expected


def test_detect_delimiter_ignores_separators_inside_quoted_header():
    # El caso del fix: 4 comas citadas empatan con 4 punto y coma reales.
    header = '"nota, a, b, c, d";autor;canal;tipo;texto'
    assert CSVInputLoader._detect_delimiter(header) == ";"


def test_detect_delimiter_waits_for_a_newline_outside_quotes():
    # Un salto de línea DENTRO de una celda citada no termina el encabezado:
    # los punto y coma reales están DESPUÉS del salto, así que un corte a la
    # primera línea (`splitlines()[0]`) los pierde y cae al fallback ",".
    sample = (
        '"nota\nnota2,nota3,nota4";autor;canal;tipo;texto\n'
        "global,general,feedback,hola\n"
    )
    assert CSVInputLoader._detect_delimiter(sample) == ";"


def test_english_aliases_with_comma(tmp_path):
    content = (
        "author,channel,tipo,content\n"
        f"ana,general,{TIPO},hola\n"
        f"luis,general,{TIPO},que tal\n"
    )
    path = _write(tmp_path, content)

    batch = CSVInputLoader().load_batch(str(path))

    assert len(batch.interacciones) == 2


def test_headers_are_normalized(tmp_path):
    content = (
        " Autor ;CANAL;Tipo;TEXTO \n"
        f"ana;general;{TIPO};hola\n"
        f"luis;general;{TIPO};que tal\n"
    )
    path = _write(tmp_path, content)

    batch = CSVInputLoader().load_batch(str(path))

    assert len(batch.interacciones) == 2


def test_duplicate_headers_raise(tmp_path):
    content = (
        "autor;canal;tipo;texto;autor\n"
        f"ana;general;{TIPO};hola;luis\n"
    )
    path = _write(tmp_path, content)

    with pytest.raises(ValueError, match="duplicados"):
        CSVInputLoader().load_batch(str(path))


def test_missing_required_header_raises(tmp_path):
    content = (
        "autor;canal;texto\n"
        "ana;general;hola\n"
    )
    path = _write(tmp_path, content)

    with pytest.raises(ValueError, match="tipo"):
        CSVInputLoader().load_batch(str(path))


def test_short_row_does_not_crash(tmp_path):
    content = (
        "autor;canal;tipo;texto\n"
        f"ana;general;{TIPO}\n"
        f"luis;general;{TIPO};que tal\n"
    )
    path = _write(tmp_path, content)

    batch = CSVInputLoader().load_batch(str(path))

    assert len(batch.interacciones) == 2


def test_extra_cells_are_ignored(tmp_path):
    content = (
        "autor;canal;tipo;texto\n"
        f"ana;general;{TIPO};hola;sobrante\n"
        f"luis;general;{TIPO};que tal\n"
    )
    path = _write(tmp_path, content)

    batch = CSVInputLoader().load_batch(str(path))

    assert len(batch.interacciones) == 2


def test_normalization_error_reports_row_number(tmp_path, monkeypatch):
    content = (
        "autor;canal;tipo;texto\n"
        f"ana;general;{TIPO};bien\n"
        f"luis;general;{TIPO};malo\n"
    )
    path = _write(tmp_path, content)
    loader = CSVInputLoader()
    original = loader.normalizer.normalize

    def fake_normalize(stem, row):
        if row.get("texto") == "malo":
            raise ValueError("boom")
        return original(stem, row)

    monkeypatch.setattr(loader.normalizer, "normalize", fake_normalize)

    # Encabezado = fila 1, así que "luis" es la fila 3 del archivo.
    with pytest.raises(ValueError, match=r"datos\.csv, fila 3: boom"):
        loader.load_batch(str(path))


def test_envelope_default_uses_file_stem(tmp_path):
    content = (
        "autor;canal;tipo;texto\n"
        f"ana;general;{TIPO};hola\n"
    )
    path = _write(tmp_path, content, name="mi_comunidad.csv")

    batch = CSVInputLoader().load_batch(str(path))

    assert batch.origen_comunidad == "CSV-mi_comunidad"
    assert batch.periodo_referencia == "CSV-mi_comunidad"


def test_envelope_column_beats_default(tmp_path):
    content = (
        "autor;canal;tipo;texto;origen_comunidad;periodo_referencia\n"
        f"ana;general;{TIPO};hola;Mastodon;2026-10\n"
    )
    path = _write(tmp_path, content)

    batch = CSVInputLoader().load_batch(str(path))

    assert batch.origen_comunidad == "Mastodon"
    assert batch.periodo_referencia == "2026-10"


def test_envelope_argument_beats_column(tmp_path):
    content = (
        "autor;canal;tipo;texto;origen_comunidad;periodo_referencia\n"
        f"ana;general;{TIPO};hola;Mastodon;2026-10\n"
    )
    path = _write(tmp_path, content)

    loader = CSVInputLoader(
        origen_comunidad="Discord", periodo_referencia="2026-09"
    )
    batch = loader.load_batch(str(path))

    assert batch.origen_comunidad == "Discord"
    assert batch.periodo_referencia == "2026-09"
