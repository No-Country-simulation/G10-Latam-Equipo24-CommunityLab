<!--
  ⚠️ Esto es una PLANTILLA: GitHub la muestra sola cada vez que alguien abre un PR.
  Completá las secciones y NO borres los checklists.
  Borrá los comentarios (las líneas que empiezan con <!--) antes de publicar.
-->

## Qué hice
Conecté el panel de curaduría de Streamlit con `run_pipeline`, agregué una prueba básica de `process_json_input` y moví el mockup visual a `docs/`.

## Por qué
Permite cargar un lote JSON, revisar/editar los activos generados y avanzar al paso de confirmación con datos reales del pipeline.

## Cómo probarlo
1. Ejecutar `pytest tests/test_interface_app.py`.
2. Ejecutar `streamlit run src/interface/app.py`, cargar un JSON de interacciones y verificar el análisis y la edición de activos.

## Contrato de datos
No aplica: no se modificó el contrato de entrada ni de salida.

## Checklist del autor (marcá TODO antes de pedir review)
- [x] Corrí los tests en local (`pytest`) y pasan
- [ ] El CI (check `test`) está en verde
- [x] No dejé `print`s ni código de debug
- [ ] No commitié API keys, tokens ni credenciales
- [x] Agregué tests si es funcionalidad nueva
- [ ] Mi branch está al día con `main` (rebase hecho)
