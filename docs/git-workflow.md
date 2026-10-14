# Guía de trabajo con Git (branches, rebase y PRs)

Guía práctica para el flujo de este repo. Nada de teoría de más: el modelo mental, los comandos que se usan de verdad, y qué esperar en cada paso.

## 1. Modelo mental (lo único que hay que retener)

Git es un **grafo de commits**. Una rama es **una etiqueta que apunta a un commit**.

```
        A---B---C        <- feat/mi-rama (etiqueta local)
       /
...---X---Y---Z          <- main (etiqueta)
```

- Cuando `main` crece (se mergean PRs), las otras ramas **no se mueven solas**: siguen colgadas del punto donde fueron creadas. Por eso "se atrasan".
- `origin/main` es la etiqueta **en el remoto**. Tu `main` local y `origin/main` pueden estar en commits distintos; no son la misma cosa.
- `origin/mi-rama` es tu rama subida. Tu rama local puede tener commits que el remoto no tiene (y viceversa).

Analogía: `main` es el edificio, tu rama es un andamio. Cuando el edificio crece en otro lado, el andamio sigue enganchado al piso viejo.

## 2. Los tres comandos para no perderse nunca

| Comando | Qué hace | Cuándo |
|---|---|---|
| `git status` | Dónde estás, qué hay sin commitear, qué falta pushear | Antes de cualquier cosa |
| `git branch -vv` | Tus ramas y **qué upstream rastrea cada una** (crítico) | Antes de cualquier `pull` |
| `git log --oneline --graph -10` | El mapa del grafo: quién cuelga de quién | Cuando algo "no te cierra" |

Regla de oro: **sospechá de todo comando que haga cosas sin que sepas contra qué rama** (primero `git log --graph`).

## 3. Actualizar `main` local (mirror, sin tocar tu trabajo)

El `main` local es un espejo del remoto. Solo debe avanzar por **fast-forward** (avanzar la etiqueta, sin commits propios encima):

```bash
git fetch origin
git fetch origin main:main        # avanza main local hasta origin/main
```

Por qué no `git pull` pelado: `pull` mergea contra el **upstream de la rama actual**. Si tu rama rastrea `origin/otra-cosa`, un `pull` ahí mezcla lo que no querés. Excepción segura: parado en tu rama `main`, `git pull --ff-only` nunca crea commits raros.

## 4. Arrancar una feature desde el main actualizado

```bash
git fetch origin
git switch -c feat/mi-cambio origin/main   # rama nueva desde el main MÁS NUEVO
```

Comparar con `git switch -c feat/mi-cambio` a secas: crea la rama desde **donde estés parado**, que puede estar atrasado. Por eso el `origin/main` explícito.

## 5. El flujo diario de una feature

```bash
# 1. estado actual
git status
git diff                              # qué cambié (sin stage)

# 2. commits por unidad de trabajo (conventional commits)
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): wire decisions, generators and storage"

# 3. subir por primera vez (el -u fija el upstream)
git push -u origin feat/mi-cambio

# 4. abrir PR (base: main; head: feat/mi-cambio)
#    -> GitHub corre el CI (check "test" obligatorio)
```

Cuando abrís el PR, GitHub muestra `mergeable_state`:

- `clean` → listo si tenés los approves.
- `blocked` → falta approve no-autor, o check pendiente.
- `behind` → tu rama está atrasada respecto de main (ver sección 6).
- `dirty` → hay conflicto de merge (resolverlo: cambio con otro cambio).

## 6. La rama "se atrasó": merge vs rebase

Cuando a `main` le entran PRs, tu rama queda `behind`. Hay dos formas de re-sincronizar:

| | `git merge origin/main` | `git rebase origin/main` |
|---|---|---|
| Qué hace | Junta historias con un commit de unión | Re-aplica TUS commits encima del main nuevo |
| Historia | Queda un "nudo" | Lineal, como si nunca hubieras salido |
| Reescribe tus commits? | No | **Sí → SHAs nuevos** |
| Push | Normal (`git push`) | **Force** (`git push --force-with-lease`) |
| Cuándo | Default del equipo: re-sincronizar sin pisar | Cuando querés historia limpia en la rama |
| Mantenés el approve? | No | No |

Consejo para este repo: como `main` solo acepta **squash** (aplasta todo el PR en 1 commit al mergear), el "nudo" del merge en tu rama desaparece igual. Usar `merge origin/main` evita el force-push y es más difícil romper algo. Rebasa solo si querés que los commits intermedios queden lindos en el PR.

**Lo importante: en AMBOS casos el approve anterior se desestima** si `dismiss_stale_reviews` está activo. No es un error: el reviewer aprobó un contenido que ya no es el que se mergea.

```bash
# re-sincronizar con merge (sin reescribir nada)
git fetch origin
git merge origin/main
# resolver conflictos si hay, luego:
git push origin feat/mi-cambio

# re-sincronizar con rebase (historia lineal, reescribe)
git fetch origin
git rebase origin/main
git push --force-with-lease origin feat/mi-cambio
```

El `--force-with-lease` es el force-push seguro: solo pisa si nadie pusheó algo nuevo que no viste.

## 7. Qué significan las reglas de protección de `main`

| Regla | Significado |
|---|---|
| `required_reviews=1` | Necesita 1 approve que **no sea del autor** del PR |
| `up_to_date` (strict) | La rama del PR debe incluir el main más nuevo ANTES de mergear |
| `dismiss_stale=true` | Si la rama cambia tras un approve, el approve se invalida |
| `required_linear_history` + squash | main avanza SOLO con commits aplastados, nunca merge commits |

Consecuencias prácticas:

- Un PR "aprobado" puede no ser mergeable si quedó `behind` → hay que re-sincronizar.
- Re-sincronizar → el approve se resetea → hay que pedir re-aprobación. Ciclo normal, no un bug.

## 8. Errores comunes y cómo salir

| Error | Síntoma | Salida |
|---|---|---|
| `git pull` en la rama equivocada | Trae commits raros / rechaza por cambios locales | `git status`, `git branch -vv`, `git log --graph`: ubicarse. `git merge --abort` si lo cancelás |
| Force-push que pisó commits ajenos | El otro pierde commits | No force-pushear ramas compartidas; `--force-with-lease` solo si es tuya |
| Conflicto de merge | `CONFLICT` en `git merge`/`rebase` | Editar los archivos marcados, `git add`, y terminar (`git merge --continue` / `git rebase --continue`) |
| Push rechazado (`non-fast-forward`) | El remoto tiene commits que no tenés | `git fetch` + `git merge origin/main` (o rebase) y reintentar |
| Commit que no debía ir | Ya pusheaste | Nunca reescribir compartido: revert con commit nuevo (`git revert`) |

## 9. Glosario mínimo

- **Upstream**: la rama remota que tu rama local rastrea (`git branch -vv` la muestra).
- **Fast-forward**: avanzar una etiqueta sin crear commits nuevos (solo es posible si no te alejaste).
- **Squash**: aplastar N commits de un PR en 1 al mergear (lo hace GitHub al hacer "Squash and merge").
- **SHA**: el identificador único de un commit (`d266282`). Si cambia un rebase, es OTRO commit aunque el contenido sea igual.
- **`fetch`**: baja info del remoto SIN tocar tu trabajo. Es la operación inofensiva; usala primero siempre.

## 10. Ejemplo real: lo que pasó con #89 y #90

1. `#86` se mergeó → `main` avanzó (`5cd9872`).
2. `#89` había sido aprobado ANTES, sobre un main viejo → quedó `behind` (strict lo bloqueaba).
3. Se re-sincronizó con `git merge origin/main`, 149 tests verdes, push.
4. El push **desestimó el approve de Itan** (`dismiss_stale`) → se pidió re-aprobación.
5. `#90` (cableado) nació AL DÍA con main (`git switch -c feat/pipeline-wiring origin/main`) → `mergeable_state=blocked` solo por falta de approve.

Moraleja: crear la rama desde `origin/main` al día evita el ciclo "aprobado pero atrasado". Y cuando una rama se atrasa, re-sincronizarla es rutina, no drama.