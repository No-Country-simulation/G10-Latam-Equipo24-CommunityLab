<!--
  ⚠️ Esto es una PLANTILLA: GitHub la muestra sola cada vez que alguien abre un PR.
  Completá las secciones y NO borres los checklists.
  Borrá los comentarios (las líneas que empiezan con <!--) antes de publicar.
-->

## Qué hice
<!-- Una línea clara: feature, fix, refactor, docs. Ej: "Agregué el GeminiRelevanceScorer". -->

## Por qué
<!-- Qué problema resuelve o qué agrega. Si cierra un issue: "Closes #28". -->

## Cómo probarlo
<!-- Pasos exactos para que otra persona lo corra y lo verifique. Comandos incluidos. -->

## Contrato de datos
<!-- Obligatorio si tocás src/domain o src/ingest. Si no aplica, poné "No aplica". -->
- ¿Se conserva el campo `tipo` de cada interacción?
- ¿La entrada se parsea con los campos del PDF (`autor`, `canal`, `tipo`, `texto`)?
- ¿La salida reproduce `resumen_comunidad` / `activos_distribucion_generados` / `almacenamiento_oci`?

## Checklist del autor (marcá TODO antes de pedir review)
- [ ] Corrí los tests en local (`pytest`) y pasan
- [ ] El CI (check `test`) está en verde
- [ ] No dejé `print`s ni código de debug
- [ ] No commitié API keys, tokens ni credenciales
- [ ] Agregué tests si es funcionalidad nueva
- [ ] Mi branch está al día con `main` (rebase hecho)
