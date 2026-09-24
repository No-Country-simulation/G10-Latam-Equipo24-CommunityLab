# Checklist de Revisión — CommunityLab

> Para quien revisa un PR **antes del merge a `main`**.
> Hay dos pasadas: la **Pasada 1** es obligatoria para TODOS los PRs.
> La **Pasada 2** se suma solo cuando el PR toca análisis / IA / decisiones.

---

## Pasada 1 — Obligatoria para todos los PRs

### 1. ¿Pasa el CI?
- [ ] El check `test` está en verde (pytest + flake8).
- [ ] No "en mi máquina anda" — el CI es la verdad.

### 2. ¿No rompe el contrato de datos?
- [ ] El modelo conserva `tipo` y valida los valores permitidos.
- [ ] La entrada usa `autor` / `canal` / `tipo` / `texto` + `origen_comunidad` / `periodo_referencia`.
- [ ] La salida reproduce `status` / `resumen_comunidad` / `activos_distribucion_generados` / `almacenamiento_oci`.
- [ ] Hay un test con el ejemplo literal del PDF (Mariana / Lucas).

### 3. ¿No hay secretos?
- [ ] Buscá en el diff: `key`, `secret`, `token`, `password`, `.env`.
- [ ] Las credenciales van por variables de entorno, nunca hardcodeadas.

### 4. ¿No rompe lo que ya estaba?
- [ ] El branch está rebaseado con `main` (diff limpio, sin conflictos raros).
- [ ] El PR no toca módulos que no le corresponden.

---

## Pasada 2 — Solo si toca análisis / IA / decisiones

### 5. ¿El LLM devuelve algo usable?
- [ ] El output del LLM se parsea y se valida (schema) **antes** de usarse.
- [ ] Hay fallback si la API falla (timeout / rate limit).

### 6. ¿El ruteo es correcto?
- [ ] La decisión usa `tipo` (`testimonio` → LinkedIn, `pregunta_tecnica` → FAQ), no solo sentimiento.

---

## Veredicto

- ✅ **Aprobar**: Pasada 1 completa y verde (+ Pasada 2 si aplica).
- 🔁 **Pedir cambios**: algo de la Pasada 1 o 2 falla.
- 💬 **Comentario**: no bloquea, pero dejás una mejora sugerida.

> Regla de oro: "no rompe el pipeline" NO es lo mismo que "cumple el contrato de datos".
> Para código de infra/UI/OCI alcanza la pasada ligera (CI + contrato + secretos);
> la revisión profunda del módulo la hace su autor.
