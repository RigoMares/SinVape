# Inteligencia política CDE PAN BCS — pipeline de captura

Materia prima vía **Bright Data** → **digest ruteado** → **workflow fan-out-and-synthesize**.
Bright Data solo trae datos crudos; **el análisis lo hace el workflow**, no estos scripts.

## Arquitectura

```
   FRENTE A (redes)                          FRENTE B (medios)
   SERP+recencia → facebook_posts            Web Unlocker (+reintento)
        │  corriente #3                           │  corriente #1 + prensa
        └───────────────┬─────────────────────────┘
                        ▼
            intel/captures/<fecha>/*.json   (materia prima cruda, gitignored)
                        ▼
            intel/build_digest.py
                        ▼
            intel/captures/<fecha>/digest.md   (ruteado, deduplicado, en ventana, lean)
                        ▼
   FAN-OUT (Sonnet): 1 subagente por corriente → clasifica 🔴/🟡/🟢, descarta ruido
                        ▼
   SÍNTESIS + VERIFICACIÓN 🔴 (Opus): confirma contra texto real → brief
```

## Comandos

```bash
# 1) Capturar (corrida diaria recomendada — ver workflow_config_bright_data.yaml)
python3 intel/capture.py --sweep full --frente all --recency d --enrich 20 --hours 48 --zone web_unlocker1

# 2) Construir el digest desde la captura más reciente
python3 intel/build_digest.py

# Variantes útiles
python3 intel/capture.py --sweep test --frente a --recency w --enrich 0   # solo discovery, barato
python3 intel/capture.py --frente b --zone web_unlocker1                   # solo medios
```

Requiere `BRIGHTDATA_API_KEY` en el entorno (o `--api-key`) y la zona Web Unlocker
(`web_unlocker1`). La CLI `brightdata` se reinstala sola vía el SessionStart hook.

## Por qué `--recency` es obligatorio en monitoreo

Sin filtro temporal, Google prioriza posts *evergreen* con alto engagement: medido
2026-06-03, **~89% de lo enriquecido caía FUERA de la ventana de 48h**. Con `--recency d`:
**100% en ventana**. Siempre usar `--recency d` (o `w`) para el monitor.

## Caps (del config)

| Cap | Valor | Dónde |
|---|---|---|
| Registros enriquecidos / corrida | 20 (sweep test) | `--max-records` / `--enrich` |
| Tope duro de captura | 2000 | `tope_registros_por_corrida` |
| Ventana temporal | 48h | `--hours` |
| Calidad de síntesis | ~60k tokens | `tope_tokens_por_ciclo` (referencia, no costo) |

El costo en dólares es trivial (Bright Data ~centavos/corrida; análisis bajo Claude Max).
La restricción real es el **cupo de Opus por ventana** → fan-out en Sonnet, Opus solo en
síntesis y verificación de 🔴.

## Reglas (no negociables)

- Solo contenido **público**.
- Citar **textual solo desde el texto real** de la nota/post (nunca desde resumen reconstruido).
- **Bloque aliado**: solo defender y medir; jamás generar ataques.
- No publicar nada sin pasar el filtro de verificación (redes traen cuentas falsas; portadas traen ruido).

## Pendientes conocidos

- **discover-by-profile** (Dataset API, `num_of_posts`+fechas) para completitud total de
  páginas oficiales. `facebook_posts <perfil>` da `crawl_error`; la vía SERP+recencia ya
  surfacea los posts propios recientes, así que es opcional.
- Parsers de medios afinados a 4 plantillas; sitios nuevos pueden requerir ajuste.
