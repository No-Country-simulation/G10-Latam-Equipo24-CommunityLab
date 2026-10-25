# Flujo general del sistema

Este documento describe, en cuatro fases, el recorrido completo de un mensaje
desde que entra a la comunidad hasta que aparece en el tablero web.

## Diagrama general

```mermaid
flowchart TD
    subgraph F1["FASE 1 - INGESTA: recolectar y limpiar"]
        T["Grupo de Telegram"] --> LIM
        AF["Archivos CSV / JSON"] --> VIA{"¿El formato<br/>es correcto?"}
        VIA -- "No" --> ERR["La corrida se corta avisando<br/>en qué fila del archivo falló"]
        VIA -- "Sí" --> LIM["Se prepara cada mensaje:<br/>autor, texto, fecha, enlace.<br/>Los vacíos y los comandos<br/>se descartan"]
    end

    LIM --> ANA

    subgraph F2["FASE 2 - ANÁLISIS Y DECISIÓN: leer y decidir"]
        ANA["El modelo lee cada mensaje<br/>y llena una planilla:<br/>sentimiento, tema,<br/>qué tan interesante es"] --> CHEQ{"¿La respuesta es<br/>correcta y completa?"}
        CHEQ -- "No" --> BLANK["Planilla en blanco:<br/>neutral y no interesante.<br/>El mensaje no se descarta,<br/>sigue con valores seguros"]
        CHEQ -- "Sí" --> DEC
        BLANK --> DEC["Un decisor con reglas<br/>fijas (no usa IA) lee la<br/>planilla y decide:<br/>- testimonio o logro<br/>  positivo → publicar<br/>- negativo con seguridad<br/>  alta → derivar a<br/>  una persona<br/>- pregunta técnica →<br/>  crear una FAQ<br/>- lo demás → descartar"]
    end

    DEC --> GEN

    subgraph F3["FASE 3 - GENERADORES: escribir los productos"]
        GEN{"¿Qué decisión<br/>toca al mensaje?"}
        GEN -- "Publicar" --> LI["El modelo escribe el post<br/>de LinkedIn y el destaque<br/>de la newsletter"]
        GEN -- "Crear FAQ" --> FAQ["El modelo redacta una<br/>sugerencia de contenido<br/>para la FAQ"]
        GEN -- "Derivar o descartar" --> NAD["No se escribe nada:<br/>la decisión solo queda<br/>registrada"]
    end

    LI --> INF
    FAQ --> INF
    NAD --> INF

    subgraph F4["FASE 4 - ENTREGA: juntar y mostrar"]
        INF["Todo se junta en el informe<br/>de la corrida: resumen de la<br/>comunidad más los productos<br/>generados"] --> NUBE["Los productos generados<br/>se guardan en la nube (OCI)<br/>para no perderlos"]
        NUBE --> TAB["El tablero web muestra el<br/>informe: el equipo revisa,<br/>marca lo ya atendido y<br/>elige qué publicar"]
    end
```

## Fase 1: Ingesta (recolectar y limpiar)

Los mensajes llegan por dos puertas:

- **Telegram**: los mensajes del grupo se recogen en vivo (Telegram los empuja
  al sistema apenas llegan, mediante un webhook) o de a ratos (el sistema
  pregunta cada tanto si hay mensajes nuevos).
- **Archivos**: el equipo sube archivos CSV o JSON con mensajes recolectados.

Antes de gastar análisis, se descartan los mensajes vacíos y los comandos
internos del grupo (los que empiezan con barras, como `/start`). Si un archivo
trae errores de formato, la corrida corta en ese punto indicando la fila
exacta, para que el equipo corrija y vuelva a intentar.

## Fase 2: Análisis y decisión (leer y decidir)

El modelo de lenguaje es intercambiable por configuración: puede ser **Gemini**
en la nube (pide una clave) o un **modelo abierto servido por Ollama**, que
corre en la máquina o en la nube. Si no se configura ninguno, el análisis se
hace con reglas fijas, sin inteligencia artificial. Ese modelo **no escribe
nada todavía**: solo lee y clasifica. Por cada mensaje llena una planilla con
tres campos:

1. **Sentimiento**: positivo, negativo o neutro, con un puntaje de seguridad.
2. **Tema**: testimonio, pregunta técnica, feedback, logro o discusión.
3. **Interés**: un puntaje de cero a uno que indica si el mensaje vale la pena
   publicar.

Si el modelo falla, responde mal o devuelve categorías desconocidas, la
planilla queda con valores seguros (neutral, sin tema conocido, sin interés)
y el proceso sigue con el siguiente mensaje: **ninguna falla detiene la
corrida**.

Después de la planilla, un **decisor por reglas fijas** — que no usa
inteligencia artificial, por eso sus decisiones siempre resultan iguales —
aplica las reglas de negocio en este orden:

- Testimonio o logro **positivo** con interés suficiente → **publicar**.
- Mensaje **negativo** con una seguridad mayor al 80% → **derivar** al
  community manager para atención personalizada.
- **Pregunta técnica** → **crear una FAQ**.
- Todo lo demás → **descartar**.

## Fase 3: Generadores (escribir los productos)

Solo los mensajes elegidos en la fase anterior hacen una **segunda** llamada al
modelo, esta vez sí para escribir:

- El **post de LinkedIn** y el **destaque de la newsletter** salen del
  testimonio o logro positivo que se decidió publicar.
- La **sugerencia de FAQ** sale de la pregunta técnica elegida.
- Lo derivado se clasifica de acuerdo a su reelevancia y selecciona los de >0.8 y los deriva para atencion humana (Community Manager).

Si la escritura de un producto falla, ese producto simplemente no se incluye y
la corrida sigue: nunca se bloquea todo por un solo intento.

## Fase 4: Entrega (juntar y mostrar)

La corrida junta todo en un informe único: el resumen de la comunidad y los
productos generados.

- Los **productos generados** (post de LinkedIn, newsletter, FAQ) se **guardan
  en la nube** (almacenamiento OCI) para no perderlos y poder consultarlos
  después.
- El informe se **muestra en el tablero web**, donde el equipo revisa los
  productos, marca qué derivados ya fueron atendidos y elige qué publicar.

El tablero también puede cargar una corrida ya guardada (como la muestra de
ejemplo del proyecto) sin volver a analizar nada.

## Cómo ver el diagrama

El diagrama de arriba se dibuja automáticamente en GitHub al pegar este
archivo (GitHub interpreta los bloques `mermaid` sin configurar nada). También
puede previsualizarse en [mermaid.live](https://mermaid.live) o en VS Code con
la extensión "Markdown Preview Mermaid Support".
