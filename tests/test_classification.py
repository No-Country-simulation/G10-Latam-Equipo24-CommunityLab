from src.ingest.ingest import _contiene, calificar_tipo, oferta_laboral


def test_empleos_no_matchea_empleo():
    assert not _contiene("hay empleos", ["empleo"])


def test_contratado_es_testimonio():
    assert calificar_tipo("Fui contratado ayer") == "testimonio"


def test_certificacion_es_testimonio():
    assert calificar_tipo("Terminé mi certificación") == "testimonio"


def test_como_suelto_no_es_pregunta():
    assert calificar_tipo("tan bueno como python") == "otro"


def test_como_puedo_es_pregunta():
    assert calificar_tipo("¿Cómo puedo instalar esto?") == "pregunta tecnica"


def test_hashtags_no_cuentan():
    assert calificar_tipo("Hola #ayuda") == "otro"


def test_postulate_con_y_sin_tilde():
    assert oferta_laboral({"tags": []}, "Postúlate aquí")
    assert oferta_laboral({"tags": []}, "postulate aqui")