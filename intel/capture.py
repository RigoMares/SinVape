#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Captura de materia prima para el workflow de inteligencia — CDE PAN BCS.

Cablea los dos frentes definidos en intel/workflow_config_bright_data.yaml
contra las corrientes del workflow fan-out-and-synthesize:

  Frente B (Web Unlocker)  -> corriente #1 (gobierno en turno) + prensa transversal
  Frente A (SERP + Pipeline) -> corriente #3 (conversacion y ataques en redes)

Patron Frente A: SERP DESCUBRE menciones -> pipeline facebook_posts ENRIQUECE.
(`facebook_posts` es por URL, no por keyword; la SERP API es la que descubre.)

Conexion: CLI de Bright Data por subprocess (decision de sesion 2026-06-03).
Auth: la CLI lee BRIGHTDATA_API_KEY del entorno; se puede sobreescribir con --api-key.

Reglas (del config):
  - Solo contenido publico.
  - Bright Data solo trae materia prima; el analisis lo hace el workflow.
  - Respetar tope_registros_por_corrida aunque el costo sea bajo.

Caps aplicados:
  - --max-records  : tope blando por corrida (default 20 en sweep test).
  - tope duro       : tope_registros_por_corrida del config (default 2000).
  - --hours         : ventana temporal para registros enriquecidos (default 48h).

Uso tipico:
  python3 intel/capture.py --sweep test --frente all --zone web_unlocker1 --enrich 2
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO / "intel" / "workflow_config_bright_data.yaml"

# Entidades acotadas para el PRIMER BARRIDO de prueba (Frente A).
TEST_ENTITIES = ["Rigo Mares", "Morena BCS"]
# En sweep test tambien limitamos cuantos medios tocamos (Frente B) para ir barato.
TEST_MEDIA_LIMIT = 3


# --------------------------------------------------------------------------- #
# Helpers de CLI
# --------------------------------------------------------------------------- #
def run_cli(args: list[str], api_key: str | None, timeout: int = 120) -> tuple[int, str, str]:
    """Corre `brightdata <args>` y devuelve (rc, stdout, stderr)."""
    cmd = ["brightdata"]
    if api_key:
        cmd += ["-k", api_key]
    cmd += args
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout tras {timeout}s"
    except FileNotFoundError:
        sys.exit("ERROR: no se encontro la CLI 'brightdata' en el PATH.")


# --------------------------------------------------------------------------- #
# FRENTE A — Redes (SERP descubre -> pipeline enriquece)
# --------------------------------------------------------------------------- #
def serp_discover(entity: str, zone: str, api_key: str | None) -> list[dict]:
    """Descubre posts publicos de FB que mencionan `entity` via SERP API."""
    query = f'"{entity}" site:facebook.com'
    rc, out, err = run_cli(
        ["search", query, "--zone", zone, "--country", "mx",
         "--language", "es", "--json"],
        api_key, timeout=90,
    )
    if rc != 0:
        print(f"  ! SERP fallo para '{entity}': {err.strip().splitlines()[-1] if err.strip() else rc}",
              file=sys.stderr)
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        print(f"  ! SERP devolvio JSON invalido para '{entity}'", file=sys.stderr)
        return []
    hits = []
    for r in data.get("organic", []):
        link = r.get("link")
        if not link or "facebook.com" not in link:
            continue
        hits.append({
            "entity": entity,
            "title": r.get("title"),
            "link": link,
            "description": r.get("description"),
            "source": r.get("source"),
        })
    return hits


def enrich_post(url: str, api_key: str | None, timeout: int) -> dict | None:
    """Enriquece UNA URL de post FB con el pipeline facebook_posts."""
    rc, out, err = run_cli(["pipelines", "facebook_posts", url, "--json"],
                           api_key, timeout=timeout)
    if rc != 0:
        print(f"  ! enrich fallo: {err.strip().splitlines()[-1] if err.strip() else rc}",
              file=sys.stderr)
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    rec = data[0] if isinstance(data, list) and data else data
    return rec if isinstance(rec, dict) else None


def frente_a(cfg: dict, entities: list[str], zone: str, api_key: str | None,
             max_records: int, hard_cap: int, enrich: int, hours: int) -> dict:
    print(f"== FRENTE A (redes) :: {len(entities)} entidades -> SERP descubre ==")
    discovered: list[dict] = []
    seen: set[str] = set()
    for ent in entities:
        hits = serp_discover(ent, zone, api_key)
        for h in hits:
            if h["link"] in seen:
                continue
            seen.add(h["link"])
            discovered.append(h)
        print(f"  - {ent!r}: {len(hits)} hits (acumulado unico {len(discovered)})")
        if len(discovered) >= hard_cap:
            print(f"  ! tope duro {hard_cap} alcanzado; corto descubrimiento.", file=sys.stderr)
            break

    # Caps: el tope de registros aplica al ENRIQUECIMIENTO (los "registros" reales).
    to_enrich = [d for d in discovered if "/posts/" in d["link"] or "/videos/" in d["link"]]
    n_enrich = min(enrich, max_records, len(to_enrich))
    enriched: list[dict] = []
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    if n_enrich:
        print(f"  enriqueciendo {n_enrich} posts (cap registros={max_records}, ventana {hours}h)...")
    for d in to_enrich[:n_enrich]:
        rec = enrich_post(d["link"], api_key, timeout=300)
        if not rec:
            continue
        # Filtro de ventana temporal sobre date_posted (si viene).
        dp = rec.get("date_posted")
        within = True
        if dp:
            try:
                ts = dt.datetime.fromisoformat(dp.replace("Z", "+00:00"))
                within = ts >= cutoff
            except ValueError:
                within = True
        rec["_within_window"] = within
        enriched.append(rec)

    return {
        "routing": cfg["frente_a_redes"]["routing"],
        "method": "serp_discover + facebook_posts_enrich",
        "entities": entities,
        "discovered_count": len(discovered),
        "discovered": discovered,
        "enriched_count": len(enriched),
        "enriched": enriched,
        "caps": {"max_records": max_records, "hard_cap": hard_cap, "window_hours": hours},
    }


# --------------------------------------------------------------------------- #
# FRENTE B — Medios (Web Unlocker + reintento)
# --------------------------------------------------------------------------- #
# h2/h3 que sea (a) titular con link `[titulo](link)` o (b) titular plano.
# Los sitios varian de plantilla: BCS Noticias/El Independiente usan link inline;
# El Sudcaliforniano usa `### Titulo` plano.
HEADLINE_LINKED_RE = re.compile(r"^#{2,3}\s+\[(.+?)\]\((https?://[^)]+)\)\s*$")
HEADLINE_PLAIN_RE = re.compile(r"^#{2,3}\s+(?!\[)(.+?)\s*$")
MIN_PLAIN_TITLE_LEN = 25  # descarta etiquetas de seccion ("Agenda azul", "Deportes")


def _domain(url: str) -> str:
    """Dominio normalizado: sin esquema, sin path, sin 'www.'."""
    d = url.split("//")[-1].split("/")[0].lower()
    return d[4:] if d.startswith("www.") else d


def parse_headlines(md: str, base_url: str) -> list[dict]:
    """Extrae titulares (h2/h3, con o sin link) + entradilla (parrafo siguiente)."""
    base_dom = _domain(base_url)
    lines = md.splitlines()
    out, seen = [], set()
    for i, line in enumerate(lines):
        s = line.strip()
        title, link = None, None
        m = HEADLINE_LINKED_RE.match(s)
        if m:
            title, link = m.group(1).strip(), m.group(2).strip()
            if title.startswith("!"):  # heading que es solo logo/imagen
                continue
            # mismo dominio registrable (tolera www / subdominios); filtra externos
            link_dom = _domain(link)
            if base_dom not in link_dom and link_dom not in base_dom:
                continue
        else:
            m = HEADLINE_PLAIN_RE.match(s)
            if not m:
                continue
            title = m.group(1).strip()
            if len(title) < MIN_PLAIN_TITLE_LEN:  # probablemente etiqueta de seccion
                continue
        key = link or title.lower()
        if key in seen:
            continue
        seen.add(key)
        # entradilla = primer parrafo de texto plano tras el titular
        entradilla = ""
        for nxt in lines[i + 1:i + 6]:
            t = nxt.strip()
            if t and not t.startswith(("#", "*", "[", "!", "-")):
                entradilla = t
                break
        out.append({"titulo": title, "link": link, "entradilla": entradilla})
    return out


# Fallback: enlaces de nota (texto largo, slug con guiones) para sitios cuyos
# titulares NO viven en headings (p.ej. Peninsular Digital, listas de enlaces).
# (?<!!) evita capturar imagenes ![alt](img).
ARTICLE_LINK_RE = re.compile(r"(?<!!)\[([^\]]{30,}?)\]\((https?://[^)]+)\)")
NAV_HINTS = ("contacto", "privacy", "aviso", "anunciate", "codigo-etico", "/tag/",
             "/category", "/categorias", "/author", "suscrib", "unete", "/page/", "wp-content")


def harvest_article_links(md: str, base_dom: str) -> list[dict]:
    """Cosecha enlaces que parezcan notas (mismo dominio, slug con guiones)."""
    out, seen = [], set()
    for m in ARTICLE_LINK_RE.finditer(md):
        text, link = m.group(1).strip(), m.group(2).strip()
        ld = _domain(link)
        if base_dom not in ld and ld not in base_dom:
            continue
        last = link.split("//")[-1].rstrip("/").split("/")[-1]
        if "-" not in last:                       # los slugs de nota llevan guiones
            continue
        if any(h in link.lower() for h in NAV_HINTS) or text.startswith("!"):
            continue
        if link in seen:
            continue
        seen.add(link)
        out.append({"titulo": text, "link": link, "entradilla": ""})
    return out


def scrape_medio(url: str, zone: str, api_key: str | None, retries: int = 2) -> str | None:
    """Scrapea una portada via Web Unlocker, con reintentos ante captcha/proteccion."""
    for attempt in range(1, retries + 2):
        rc, out, err = run_cli(
            ["scrape", url, "--zone", zone, "--country", "mx", "--format", "markdown"],
            api_key, timeout=120,
        )
        if rc == 0 and out.strip():
            return out
        msg = (err.strip().splitlines()[-1] if err.strip() else f"rc={rc}")
        print(f"    intento {attempt}: {msg}", file=sys.stderr)
    return None


def frente_b(cfg: dict, zone: str, api_key: str | None, media_limit: int | None) -> dict:
    fb = cfg["frente_b_medios"]
    activos = [m for m in fb["medios"] if m.get("bloquea_403") and not m.get("pendiente")]
    if media_limit:
        activos = activos[:media_limit]
    print(f"== FRENTE B (medios) :: {len(activos)} medios -> Web Unlocker ==")
    resultados = []
    for m in activos:
        md = scrape_medio(m["url"], zone, api_key)
        if md is None:
            print(f"  - {m['nombre']}: BLOQUEADO (sin contenido tras reintentos)", file=sys.stderr)
            resultados.append({"medio": m["nombre"], "url": m["url"], "ok": False, "titulares": []})
            continue
        titulares = parse_headlines(md, m["url"])
        # Fallback para sitios cuyos titulares no estan en headings.
        if len(titulares) < 5:
            existentes = {t["link"] for t in titulares if t["link"]}
            for h in harvest_article_links(md, _domain(m["url"])):
                if h["link"] not in existentes:
                    titulares.append(h)
                    existentes.add(h["link"])
        print(f"  - {m['nombre']}: OK, {len(titulares)} titulares")
        resultados.append({
            "medio": m["nombre"], "url": m["url"], "ok": True,
            "titulares": titulares, "raw_markdown_chars": len(md),
        })
    return {
        "routing": fb["routing"],
        "regla_citas": fb["regla_citas"],
        "medios_count": len(activos),
        "resultados": resultados,
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Captura Bright Data para inteligencia PAN BCS.")
    ap.add_argument("--frente", choices=["a", "b", "all"], default="all")
    ap.add_argument("--sweep", choices=["test", "full"], default="test")
    ap.add_argument("--zone", default=os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "web_unlocker1"))
    ap.add_argument("--api-key", default=None, help="Override; por defecto usa BRIGHTDATA_API_KEY.")
    ap.add_argument("--enrich", type=int, default=0, help="Cuantos posts FB enriquecer (Frente A).")
    ap.add_argument("--max-records", type=int, default=None, help="Tope blando por corrida.")
    ap.add_argument("--hours", type=int, default=48, help="Ventana temporal (registros enriquecidos).")
    ap.add_argument("--out", default=None, help="Dir de salida (default intel/captures/<fecha>).")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    hard_cap = cfg["meta"]["presupuesto"]["tope_registros_por_corrida"]
    max_records = args.max_records if args.max_records is not None else (20 if args.sweep == "test" else hard_cap)

    # Entidades segun sweep (Frente A).
    if args.sweep == "test":
        entities = TEST_ENTITIES + cfg["frente_a_redes"]["temas_calientes"]
        media_limit = TEST_MEDIA_LIMIT
    else:
        fa = cfg["frente_a_redes"]
        entities = (fa["bloque_adversario"]["personas"] + fa["bloque_adversario"]["marcas"]
                    + fa["bloque_aliado"]["personas"] + fa["bloque_aliado"]["marcas"]
                    + fa["temas_calientes"])
        media_limit = None

    api_key = args.api_key or os.environ.get("BRIGHTDATA_API_KEY")
    fecha = cfg["meta"]["ciclo_base"]
    out_dir = Path(args.out) if args.out else (REPO / "intel" / "captures" / fecha)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Sweep={args.sweep} frente={args.frente} zona={args.zone} "
          f"max_records={max_records} hard_cap={hard_cap} -> {out_dir}")

    manifest = {
        "ciclo": fecha,
        "generado": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sweep": args.sweep,
        "zona": args.zone,
    }

    if args.frente in ("a", "all"):
        res_a = frente_a(cfg, entities, args.zone, api_key, max_records, hard_cap, args.enrich, args.hours)
        (out_dir / "frente_a_redes.json").write_text(
            json.dumps(res_a, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["frente_a"] = {"discovered": res_a["discovered_count"], "enriched": res_a["enriched_count"]}

    if args.frente in ("b", "all"):
        res_b = frente_b(cfg, args.zone, api_key, media_limit)
        (out_dir / "frente_b_medios.json").write_text(
            json.dumps(res_b, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["frente_b"] = {
            "medios": res_b["medios_count"],
            "ok": sum(1 for r in res_b["resultados"] if r["ok"]),
            "titulares": sum(len(r["titulares"]) for r in res_b["resultados"]),
        }

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n== MANIFEST ==")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
