# FASE 0 — Prompt de arranque (prueba de concepto Bright Data)

> Pega este prompt al iniciar una **sesión nueva** en este entorno (para que ya tenga
> `BRIGHTDATA_API_KEY` y el dominio `api.brightdata.com` habilitado en Network access).
> La sesión nueva arranca sin memoria; el prompt es autocontenido.

---

```
Contexto: Trabajo de inteligencia política para el CDE PAN BCS. En la rama
`claude/pan-bcs-political-monitoring-LWAKd` (PR #1) ya está commiteada la config
del workflow en `intel/workflow_config_bright_data.yaml` (Frente A redes / Frente
B medios). La CLI de Bright Data está instalada (`brightdata`, v0.3.1). Acabo de
agregar al entorno la variable BRIGHTDATA_API_KEY y habilité en Network access
(Custom) el dominio api.brightdata.com. Decisiones ya tomadas: arrancamos SOLO
Facebook + medios (X/Twitter en fase posterior); conexión vía CLI por Bash.

Tarea — FASE 0 (prueba de concepto, gastar centavos):

0. Verifica primero que el entorno quedó bien:
   - Confirma que $BRIGHTDATA_API_KEY está presente (NO lo imprimas; solo largo/ok).
   - Confirma que api.brightdata.com es alcanzable (si da "Host not in allowlist",
     detente y avísame: falta el dominio en Allowed domains).

1. Corre `brightdata budget` para ver saldo ANTES de gastar.

2. FRENTE B (Web Unlocker): `brightdata scrape https://www.bcsnoticias.mx`
   — objetivo: validar que rompe el 403 que medimos antes. Muéstrame titulares +
   entradillas + links que devuelva. Si el bloqueo persiste, dímelo en vez de
   inventar contenido.

3. FRENTE A (Facebook): primero confirma contra `brightdata pipelines --help` (o la
   doc viva) el tipo/parámetros correctos para Facebook. Luego haz UNA extracción de
   prueba: posts públicos de FB que mencionen "Rigo Mares" en las últimas 48h, máximo
   20 registros. Devuélveme el JSON crudo para ver el shape. NO analices todavía.

Reglas: solo contenido público; respeta el tope de 2000 registros/corrida del config;
no publiques nada sin verificación; cita textual SOLO desde el texto real de la nota.
Cuando termines, muéstrame los resultados crudos y dime si Fase 0 valida ambos frentes
para pasar a Fase 1 (cablear contra las corrientes #1 y #3 del workflow de inteligencia).
```

---

## Notas para esa sesión

- Si el paso 0 falla con `Host not in allowlist`: el dominio no se guardó o la sesión
  no es realmente nueva. Revisa **Allowed domains** (Network access → Custom) y reinicia.
- **No vuelvas a pegar la key en el chat** — la sesión nueva la lee sola desde la
  variable de entorno `BRIGHTDATA_API_KEY`.
- Si `brightdata pipelines` no fuera el subcomando correcto para Facebook, revisar
  `brightdata scraper` / la doc viva y ajustar **antes** de gastar.

## Estado al cierre de la sesión 2026-06-03

- ✅ CLI Bright Data instalada (v0.3.1).
- ✅ Config del workflow commiteada: `intel/workflow_config_bright_data.yaml`.
- ✅ Mapa de bloqueo 403 medido (8/10 medios bloquean — valida Frente B).
- ✅ `BRIGHTDATA_API_KEY` agregada al entorno (aplica en sesión nueva).
- ✅ `api.brightdata.com` habilitado en Network access (aplica en sesión nueva).
- ⏳ Pendiente: correr Fase 0 en sesión nueva con este prompt.
- 🔐 Recordatorio: rotar la API key (quedó visible en el chat de la sesión anterior).
- 📍 Pendientes menores: URLs reales de Colectivo Pericú y CPS Noticias (dominios no
  resuelven); decidir si n8n orquesta el `/loop` diario o se queda en Claude Code.
