#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte la materia prima de intel/captures/<fecha>/ en un DIGEST ruteado,
deduplicado y filtrado, listo para el workflow fan-out-and-synthesize.

Por qué existe: Bright Data trae mucho volumen crudo (cientos de titulares +
posts). Meter eso directo a la síntesis quema cupo de Opus y diluye el análisis.
Este digest enruta por corriente, recorta a lo accionable y deja el material en
markdown lean para que el FAN-OUT (Sonnet) lo procese y solo escale 🔴 a Opus.

NO hace análisis: solo transforma y enruta. (El análisis lo hace el workflow.)

Uso:
  python3 intel/build_digest.py                         # toma la captura más reciente
  python3 intel/build_digest.py --captures-dir <dir>    # una captura específica
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO / "intel" / "workflow_config_bright_data.yaml"
CAPTURES_ROOT = REPO / "intel" / "captures"

ENRICH_QUOTE_CHARS = 400   # cuánto texto real del post se cita (regla: solo texto real)
DISCOVERY_TOP_PER_ENTITY = 3


def latest_captures_dir() -> Path | None:
    if not CAPTURES_ROOT.exists():
        return None
    dirs = sorted([p for p in CAPTURES_ROOT.iterdir() if p.is_dir()])
    return dirs[-1] if dirs else None


def bloque_map(cfg: dict) -> dict[str, str]:
    """entity (persona/marca/tema/variante) -> lente (adversario|aliado|tema)."""
    fa = cfg["frente_a_redes"]
    m: dict[str, str] = {}
    for e in fa["bloque_adversario"]["personas"] + fa["bloque_adversario"]["marcas"]:
        m[e] = "adversario"
    for e in fa["bloque_aliado"]["personas"] + fa["bloque_aliado"]["marcas"]:
        m[e] = "aliado"
    for e in fa.get("variantes_busqueda", []):
        m[e] = "aliado"   # las variantes actuales son del bloque aliado
    for e in fa["temas_calientes"]:
        m[e] = "tema"
    return m


def load(d: Path, name: str) -> dict | None:
    p = d / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def fmt_frente_b(res_b: dict) -> list[str]:
    lines = ["## Corriente #1 (gobierno en turno) + prensa transversal — MEDIOS\n"]
    total = sum(len(r["titulares"]) for r in res_b["resultados"] if r["ok"])
    ok = sum(1 for r in res_b["resultados"] if r["ok"])
    lines.append(f"_Frente B · {ok} medios OK · {total} titulares._\n")
    for r in res_b["resultados"]:
        if not r["ok"] or not r["titulares"]:
            continue
        seen_l, seen_t, dedup = set(), set(), []
        for t in r["titulares"]:
            tk = (t.get("titulo") or "").lower()
            lk = t.get("link")
            if (lk and lk in seen_l) or tk in seen_t:
                continue
            if lk:
                seen_l.add(lk)
            seen_t.add(tk)
            dedup.append(t)
        lines.append(f"### {r['medio']} ({len(dedup)})")
        for t in dedup:
            ent = f" — {t['entradilla']}" if t.get("entradilla") else ""
            link = f" [{t['link']}]" if t.get("link") else ""
            lines.append(f"- **{t['titulo']}**{ent}{link}")
        lines.append("")
    return lines


def fmt_frente_a(res_a: dict, bmap: dict[str, str]) -> list[str]:
    lines = ["## Corriente #3 (conversación y ataques en redes) — FACEBOOK\n"]
    lines.append(f"_Frente A · método: {res_a.get('method')} · recencia: {res_a.get('recency')} "
                 f"· {res_a.get('discovered_count')} descubiertos · "
                 f"{res_a.get('enriched_count')} enriquecidos._\n")

    # 1) Enriquecidos dentro de ventana = lo más accionable (texto real + engagement).
    within = [r for r in res_a.get("enriched", []) if r.get("_within_window")]
    lines.append(f"### Posts enriquecidos en ventana 48h ({len(within)}) — texto real")
    if not within:
        lines.append("_(ninguno en ventana; revisar --recency/--enrich en la corrida)_")
    for r in within:
        autor = r.get("user_username_raw") or "?"
        fecha = (r.get("date_posted") or "?")[:16]
        likes = sum(x.get("num", 0) for x in (r.get("num_likes_type") or []))
        eng = f"❤{likes} 💬{r.get('num_comments') or 0} ↗{r.get('num_shares') or 0}"
        texto = (r.get("content") or "").replace("\n", " ").strip()[:ENRICH_QUOTE_CHARS]
        link = r.get("url") or ""
        lines.append(f'- **{autor}** ({fecha}, {eng}): "{texto}" [{link}]')
    lines.append("")

    # 2) Descubrimiento (sin enriquecer), agrupado por entidad y lente.
    by_entity: dict[str, list[dict]] = {}
    for h in res_a.get("discovered", []):
        by_entity.setdefault(h.get("entity", "?"), []).append(h)
    lines.append("### Descubrimiento por entidad (sin enriquecer)")
    # Adversario y aliado primero, temas después.
    orden = {"adversario": 0, "aliado": 1, "tema": 2}
    for ent in sorted(by_entity, key=lambda e: (orden.get(bmap.get(e, "tema"), 3), e.lower())):
        hits = by_entity[ent]
        lente = bmap.get(ent, "otro")
        lines.append(f"- **{ent}** [{lente}] — {len(hits)} menciones:")
        for h in hits[:DISCOVERY_TOP_PER_ENTITY]:
            lines.append(f"    - {(h.get('title') or '').strip()[:80]} [{h.get('link')}]")
    lines.append("")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description="Construye el digest de inteligencia desde captures/.")
    ap.add_argument("--captures-dir", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cap_dir = Path(args.captures_dir) if args.captures_dir else latest_captures_dir()
    if not cap_dir or not cap_dir.exists():
        raise SystemExit("No hay captura que procesar. Corre primero intel/capture.py.")

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    bmap = bloque_map(cfg)
    citas = cfg["frente_b_medios"]["regla_citas"]
    routing = cfg["meta"]["presupuesto"]["routing_modelo"]

    res_b = load(cap_dir, "frente_b_medios.json")
    res_a = load(cap_dir, "frente_a_redes.json")

    out: list[str] = []
    out.append(f"# Digest de inteligencia — CDE PAN BCS · captura {cap_dir.name}\n")
    out.append("> **Esto es MATERIA PRIMA ruteada, no análisis.** La síntesis la hace el workflow.")
    out.append(f"> **Regla de citas:** {citas}")
    out.append("> **Bloque aliado:** solo defender y medir, jamás generar ataques.")
    out.append(f"> **Routing de modelo:** fan-out/triage → `{routing['fan_out_subagentes']}`; "
               f"síntesis + verificación 🔴 → `{routing['sintesis_y_verificacion_roja']}`.")
    out.append(f"> _Generado {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} "
               f"desde `{cap_dir}`._\n")

    if res_b:
        out += fmt_frente_b(res_b)
    if res_a:
        out += fmt_frente_a(res_a, bmap)

    out.append("---")
    out.append("## Siguiente paso del workflow")
    out.append(f"1. **Fan-out ({routing['fan_out_subagentes']})**: un subagente por corriente; "
               "clasifica por urgencia (🔴/🟡/🟢) y descarta ruido/duplicados/cuentas falsas.")
    out.append(f"2. **Verificación + síntesis ({routing['sintesis_y_verificacion_roja']})**: "
               "confirma cada 🔴 contra el texto real antes de redactar; aplica kit de defensa "
               "si hay ataque al bloque aliado (p.ej. etiqueta 'misógino + Mares' → hallazgo R-1).")

    text = "\n".join(out)
    out_path = Path(args.out) if args.out else (cap_dir / "digest.md")
    out_path.write_text(text, encoding="utf-8")

    approx_tokens = len(text) // 4
    print(f"Digest escrito: {out_path}")
    print(f"  medios: {'sí' if res_b else 'no'} | redes: {'sí' if res_a else 'no'}")
    print(f"  tamaño: {len(text)} chars (~{approx_tokens} tokens aprox)")
    if approx_tokens > cfg['meta']['presupuesto']['tope_tokens_por_ciclo']:
        print(f"  ⚠️ supera tope_tokens_por_ciclo ({cfg['meta']['presupuesto']['tope_tokens_por_ciclo']}); "
              "considera recortar discovery o subir el cap de triage a Sonnet.")


if __name__ == "__main__":
    main()
