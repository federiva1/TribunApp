"""Extrae el color primario (predominante) y uno alternativo de cada escudo de club,
para usar en las barras/fichas (ej. barra de posesión en fixture.html).

Salida: js/club-colors.js con `window.CLUB_COLORS = { slug: { primary, alt }, ... }`.

Método: pondera cada pixel por saturación * valor (así blanco/negro/gris pesan ~0),
agrupa en buckets de color, toma el bucket más pesado como primario y el siguiente
suficientemente distinto como alternativo. Si no hay un segundo color de identidad,
el alternativo es una variante aclarada/oscurecida del primario (sirve para desempatar
colisiones cuando los dos equipos comparten color predominante).

Uso:
    python scripts/extract_club_colors.py            # todos los clubes de js/clubes.js
    python scripts/extract_club_colors.py velez boca  # solo algunos slugs
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ESCUDOS = ROOT / 'escudos'
OUT = ROOT / 'js' / 'club-colors.js'

# Overrides manuales (slug -> (primary, alt)) para casos donde el escudo no refleja
# la identidad del club. Se completan a mano si algún automático queda mal.
# Los 3 de acá son escudos blanco/negro (sin color): se les da una identidad visible.
OVERRIDES: dict[str, tuple[str, str]] = {
    'gimnasiamendoza':          ('#e2e6ea', '#334155'),  # blanquinegro
    'centralcordobadesantiago': ('#cfd6de', '#1f2937'),  # negro y blanco (Ferroviario)
    'deportivoriestra':         ('#e2e6ea', '#d32f2f'),  # blanco/negro + rojo
}


def club_slugs() -> list[str]:
    js = (ROOT / 'js' / 'clubes.js').read_text(encoding='utf-8')
    m = re.search(r'CLUBES_CONFIG\s*=\s*\{(.*?)\n\};', js, re.DOTALL)
    return re.findall(r'^\s{2}([a-z]+):\s*\{', m.group(1), re.MULTILINE)


def _hex(rgb: tuple[int, int, int]) -> str:
    return '#%02x%02x%02x' % rgb


def _dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def extract(path: Path) -> tuple[str, str]:
    img = Image.open(path).convert('RGBA')
    img.thumbnail((140, 140))
    buckets: dict[tuple[int, int, int], list[float]] = {}
    for r, g, b, a in img.getdata():
        if a < 100:
            continue
        mx, mn = max(r, g, b), min(r, g, b)
        sat = 0.0 if mx == 0 else (mx - mn) / mx
        val = mx / 255
        if mx > 235 and sat < 0.15:   # casi blanco
            continue
        if mx < 40:                    # casi negro
            continue
        weight = sat * val
        if weight < 0.12:              # pixel sin color definido (gris)
            continue
        key = (r // 26, g // 26, b // 26)
        e = buckets.setdefault(key, [0.0, 0, 0, 0, 0])
        e[0] += weight
        e[1] += r
        e[2] += g
        e[3] += b
        e[4] += 1
    if not buckets:
        return ('#888888', '#cccccc')

    ranked = sorted(buckets.values(), key=lambda e: -e[0])

    def avg(e):
        return (round(e[1] / e[4]), round(e[2] / e[4]), round(e[3] / e[4]))

    primary = avg(ranked[0])
    alt = None
    for e in ranked[1:]:
        c = avg(e)
        if _dist(c, primary) > 70:     # segundo color de identidad, bien distinto
            alt = c
            break
    if alt is None:
        pr, pg, pb = primary
        lum = (0.299 * pr + 0.587 * pg + 0.114 * pb) / 255
        f = 0.55
        if lum < 0.5:                  # primario oscuro -> alt aclarado
            alt = tuple(round(x + (255 - x) * f) for x in primary)
        else:                          # primario claro -> alt oscurecido
            alt = tuple(round(x * (1 - f)) for x in primary)
    return (_hex(primary), _hex(alt))


def main() -> int:
    slugs = sys.argv[1:] or club_slugs()
    colors: dict[str, dict[str, str]] = {}
    for slug in slugs:
        path = ESCUDOS / f'{slug}.png'
        if slug in OVERRIDES:
            primary, alt = OVERRIDES[slug]
        elif not path.exists():
            print(f'  ! sin escudo: {slug}')
            continue
        else:
            primary, alt = extract(path)
        colors[slug] = {'primary': primary, 'alt': alt}
        print(f'  {slug:24s} primary {primary}  alt {alt}')

    # Merge con el archivo existente si se corrieron solo algunos slugs
    if OUT.exists() and sys.argv[1:]:
        try:
            prev = OUT.read_text(encoding='utf-8')
            mm = re.search(r'CLUB_COLORS\s*=\s*(\{.*\});', prev, re.DOTALL)
            if mm:
                existing = json.loads(mm.group(1))
                existing.update(colors)
                colors = existing
        except Exception:
            pass

    colors = {k: colors[k] for k in sorted(colors)}
    body = json.dumps(colors, ensure_ascii=False, indent=2)
    OUT.write_text(
        '// Colores de identidad por club, extraídos del escudo con '
        'scripts/extract_club_colors.py.\n'
        '// { slug: { primary, alt } }. En colisión (dos equipos con primary parecido)\n'
        '// el frontend usa el alt del visitante. Editá OVERRIDES en el script si alguno queda mal.\n'
        f'window.CLUB_COLORS = {body};\n',
        encoding='utf-8')
    print(f'\nEscrito: js/club-colors.js ({len(colors)} clubes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
