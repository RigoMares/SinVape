# Prompt de análisis — fan-out-and-synthesize (CDE PAN BCS)

Consume `intel/captures/<fecha>/digest.md` (salida de `build_digest.py`) y produce el
brief del ciclo. **Bright Data ya trajo la materia prima; aquí se hace el análisis.**

## Routing de modelo (del config)
- **Fan-out / triage → Sonnet** (un subagente por corriente; barato en cupo).
- **Síntesis + verificación 🔴 → Opus** (juicio final; reserva el cupo caro para esto).

## Paso 1 — Fan-out (Sonnet, en paralelo)

Lanza un subagente por corriente. Cada uno recibe su sección del digest y devuelve
hallazgos clasificados. **No inventa**: si un dato no está en el texto real, lo marca
como "sin confirmar".

Corrientes y de dónde salen en el digest:
- **#1 Gobierno en turno** + **prensa transversal** ← sección MEDIOS.
- **#2 Morena como partido** ← MEDIOS + REDES (menciones de Morena/adversario).
- **#3 Conversación y ataques en redes** ← sección FACEBOOK.
- **#4 Quejas y demandas ciudadanas** ← MEDIOS + REDES (posts/quejas: agua, salud, etc.).
- **#5 IEEBCS / marco electoral** ← MEDIOS (notas electorales/instituto).

Cada hallazgo: `{urgencia 🔴/🟡/🟢, bloque (adversario|aliado|neutro), tema_caliente?,
titular, cita_textual (solo del texto real), link, por_qué_importa}`.

Reglas de clasificación:
- **🔴 URGENTE**: ataque directo al bloque aliado, crisis que exige respuesta hoy, o
  munición fuerte contra el adversario verificable.
- Dispara **kit de defensa** si hay etiqueta de ataque (p.ej. "misógino + Mares" → hallazgo R-1:
  sentencia revocatoria Sala Regional GDL + caso Polanco).
- **Bloque aliado: solo defender y medir, jamás generar ataques.**

## Paso 2 — Síntesis + verificación (Opus)

1. Fusiona los hallazgos de todos los subagentes; deduplica.
2. **Verifica cada 🔴** contra el texto real. Si el digest solo trae titular+entradilla,
   re-scrapea la nota completa (`capture.py --frente b` o `brightdata scrape <url>`) antes
   de afirmar nada. Descarta cuentas falsas / ruido.
3. Aplica el kit de defensa donde corresponda.
4. Redacta el brief: resumen ejecutivo → hallazgos por urgencia → **Acciones sugeridas**.
5. Cita textual SOLO desde texto real. Marca explícito lo no confirmado.

## Salida
`intel/captures/<fecha>/brief.md` (o donde defina el ciclo). El brief es la entrega;
la materia prima cruda no se versiona.
