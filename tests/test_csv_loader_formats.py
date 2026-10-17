import pytest

from src.ingest.csv_loader import CSVInputLoader

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
