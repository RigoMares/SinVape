#!/bin/bash
# SessionStart hook — CDE PAN BCS / SinVape
# Reinstala la CLI de Bright Data (@brightdata/cli) en cada arranque del
# contenedor efímero de Claude Code on the web. Solo el repo persiste entre
# sesiones, así que la CLI instalada globalmente se pierde y hay que reponerla.
#
# Idempotente y no interactivo. Síncrono (sin modo async) para garantizar que
# la CLI esté lista antes de que la sesión empiece a operar Bright Data.
set -euo pipefail

# Solo tiene sentido en el entorno remoto (Claude Code on the web).
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PKG="@brightdata/cli@0.3.1"

# Si ya está instalada la versión correcta, no hacemos nada (cache del contenedor).
if command -v brightdata >/dev/null 2>&1 && [ "$(brightdata --version 2>/dev/null)" = "0.3.1" ]; then
  echo "brightdata CLI 0.3.1 ya presente; nada que hacer." >&2
  exit 0
fi

echo "Instalando ${PKG}..." >&2
npm install -g "${PKG}" >&2

# Verificación
if command -v brightdata >/dev/null 2>&1; then
  echo "brightdata CLI lista: $(brightdata --version)" >&2
else
  echo "ERROR: la CLI brightdata no quedó disponible tras la instalación." >&2
  exit 1
fi
