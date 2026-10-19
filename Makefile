# Atajos del panel de curaduría (CommunityLab).
#
#   make run      cierra cualquier instancia previa y abre el panel
#   make stop     cierra las instancias del panel
#   make status   dice si el panel está arriba y en qué puerto
#
# El panel corre en el puerto 8502. El puerto se pasa por línea de comandos a
# propósito: fijarlo en .streamlit/config.toml también lo fija en Streamlit
# Community Cloud, que verifica la salud de la app en el 8501 y falla el deploy
# con "Error running app".

# Raíz del repo, resuelta desde la ubicación de este Makefile: así `make run`
# funciona aunque lo invoques desde otro directorio.
ROOT := $(patsubst %/,%,$(dir $(realpath $(lastword $(MAKEFILE_LIST)))))

STREAMLIT ?= $(shell test -x "$(ROOT)/venv/bin/streamlit" && echo "$(ROOT)/venv/bin/streamlit" || echo streamlit)
APP := src/interface/app.py
PORT := 8502

# El patrón de pkill usa [.] en lugar de "." a propósito: el proceso que corre
# esta receta tiene el texto "app[.]py" en su propia línea de comando, que NO
# matchea la regex (la regex pide un "." literal). Sin ese truco, pkill mataría
# también a la shell que lo invoca.
APP_PATTERN := streamlit run src/interface/app[.]py

.PHONY: run stop status

# PYTHONPATH es imprescindible: `streamlit run src/interface/app.py` agrega solo
# src/interface/ al sys.path, y app.py importa `src.domain.models`, `src.pipeline`,
# etc. Sin esto la app arranca pero muestra ModuleNotFoundError: No module named 'src'
# en el navegador (el servidor responde 200 igual, así que el fallo pasa inadvertido).
run: stop
	@echo "▶ Arrancando el panel en http://localhost:$(PORT) ..."
	@cd "$(ROOT)" && PYTHONPATH="$(ROOT)" $(STREAMLIT) run $(APP) --server.port $(PORT)

stop:
	@-pkill -f "$(APP_PATTERN)" 2>/dev/null || true
	@sleep 1
	@if ss -ltn 2>/dev/null | grep -q ":$(PORT) "; then \
		echo "⚠  el puerto $(PORT) sigue ocupado: quedó una instancia que no cerró"; \
	else \
		echo "✓  puerto $(PORT) libre"; \
	fi

status:
	@if ss -ltn 2>/dev/null | grep -q ":$(PORT) "; then \
		echo "✓  el panel está escuchando en http://localhost:$(PORT)"; \
	else \
		echo "✗  el panel no está corriendo (puerto $(PORT) libre)"; \
	fi
	@-pgrep -af "$(APP_PATTERN)" 2>/dev/null | grep -v "bin/sh -c" || echo "   (ninguna instancia del panel corriendo)"
