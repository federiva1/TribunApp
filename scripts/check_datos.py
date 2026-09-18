"""Red de seguridad ANTES de commitear datos: compara el working tree contra un
commit de git y falla si algo se perdió.

Con el deploy por GitHub (push a master → Vercel publica solo) ya no hay un paso
intermedio donde frenar: lo que se pushea, sale. Este chequeo es ese freno.

    python scripts/check_datos.py            # contra HEAD
    python scripts/check_datos.py origin/master

Falla (exit 1) si, respecto de la base:
  - un archivo de data/fixtures tiene MENOS partidos, o menos partidos jugados;
  - liga.json tiene menos partidos finalizados;
  - data/partidos/index.json perdió entradas;
  - se borró una ficha de data/partidos/ o un plantel;
  - algún .json tocado dejó de ser JSON válido.

Casos reales que ataja: un agregado de api-sports que devuelve el partido como
NS y "des-termina" un resultado, un refresco de copas que reescribe fichas
viejas, o un script que corta a la mitad y deja un JSON truncado.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8')


def en_base(base: str, rel: str):
    """JSON del archivo en el commit base, o None si no existía ahí."""
    try:
        return json.loads(git('show', f'{base}:{rel}'))
    except Exception:
        return None


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else 'HEAD'
    problemas: list[str] = []
    avisos: list[str] = []

    # 1) Borrados: fichas de partidos, planteles y fixtures nunca deberían desaparecer.
    borrados = [l[3:].strip().strip('"') for l in git('status', '--porcelain').splitlines() if l[:2].strip() == 'D']
    borrados += git('diff', '--name-only', '--diff-filter=D', base).split()
    for rel in sorted(set(borrados)):
        if rel.startswith(('data/partidos/', 'data/planteles/', 'data/fixtures/')):
            problemas.append(f'BORRADO  {rel}')

    # 2) JSON válido en todo lo tocado bajo data/.
    tocados = set(git('diff', '--name-only', base).split())
    tocados |= {l[3:].strip().strip('"') for l in git('status', '--porcelain').splitlines()}
    for rel in sorted(t for t in tocados if t.startswith('data/') and t.endswith('.json')):
        p = ROOT / rel
        if not p.exists():
            continue
        try:
            json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            problemas.append(f'JSON ROTO  {rel}: {e}')

    # 3) Fixtures: ni menos partidos ni menos jugados.
    comparados = 0
    for p in sorted((ROOT / 'data' / 'fixtures').glob('*.json')):
        rel = p.relative_to(ROOT).as_posix()
        viejo = en_base(base, rel)
        if viejo is None:
            continue
        try:
            nuevo = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue                      # ya reportado arriba
        comparados += 1
        if isinstance(viejo, list) and isinstance(nuevo, list):
            if len(nuevo) < len(viejo):
                problemas.append(f'ACHICÓ  {rel}: {len(viejo)} → {len(nuevo)} partidos')
            if rel.endswith('/liga.json'):
                ft = lambda d: sum(1 for x in d if (x.get('status') or {}).get('finished'))
                if ft(nuevo) < ft(viejo):
                    problemas.append(f'DES-TERMINÓ  {rel}: finalizados {ft(viejo)} → {ft(nuevo)}')
                else:
                    avisos.append(f'liga.json: {len(nuevo)} partidos, finalizados {ft(viejo)} → {ft(nuevo)}')
            else:
                jug = lambda d: sum(1 for x in d if isinstance(x, dict) and x.get('goles') is not None)
                if jug(nuevo) < jug(viejo):
                    problemas.append(f'PERDIÓ RESULTADOS  {rel}: jugados {jug(viejo)} → {jug(nuevo)}')
        elif isinstance(viejo, dict) and isinstance(nuevo, dict):
            for k in viejo:
                if k not in nuevo:
                    problemas.append(f'CLAVE PERDIDA  {rel}: {k}')
                    continue
                pv, pn = (viejo[k] or {}).get('partidos'), (nuevo[k] or {}).get('partidos')
                # copas.json solo trae la ronda en curso: al avanzar de ronda la lista
                # cambia entera, así que acá solo se avisa, no se bloquea.
                if isinstance(pv, list) and isinstance(pn, list) and len(pn) < len(pv):
                    avisos.append(f'{rel} [{k}]: {len(pv)} → {len(pn)} partidos (¿cambio de ronda?)')

    # 4) Índice de fichas: no pierde entradas.
    rel = 'data/partidos/index.json'
    viejo = en_base(base, rel)
    if viejo is not None and (ROOT / rel).exists():
        try:
            nuevo = json.loads((ROOT / rel).read_text(encoding='utf-8'))
            ids_n = {e.get('id') for e in nuevo}
            perdidos = [e.get('id') for e in viejo if e.get('id') not in ids_n]
            if perdidos:
                problemas.append(f'ÍNDICE PERDIÓ  {len(perdidos)} fichas: {", ".join(map(str, perdidos[:5]))}')
            else:
                avisos.append(f'index.json: {len(viejo)} → {len(nuevo)} fichas')
        except Exception:
            pass

    for a in avisos:
        print('  ·', a)
    print(f'{comparados} fixtures comparados contra {base}')
    if problemas:
        print('\nNO COMMITEAR — se perderían datos:')
        for x in problemas:
            print('  ✗', x)
        return 1
    print('OK: no se pierde nada.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
