"""Detect whether tiles carry a coordinate grid (graticule) and find image
margins. Purely numeric output (no image viewing). Safe to delete later."""
import numpy as np
from PIL import Image

TILES = ['tile1', 'tile2', 'tile3', 'tile4']


def analyze(name):
    im = Image.open(f'_tile_images/{name}.png').convert('RGB')
    a = np.asarray(im).astype(np.int16)
    h, w, _ = a.shape
    gray = a.mean(axis=2)

    # "dark" pixels (grid lines / text are dark on light topo background)
    dark = gray < 90
    row_dark = dark.mean(axis=1)   # fraction dark per row (full width)
    col_dark = dark.mean(axis=0)   # fraction dark per col (full height)

    # Candidate grid lines = rows/cols with unusually high full-span darkness
    r_thr = row_dark.mean() + 4 * row_dark.std()
    c_thr = col_dark.mean() + 4 * col_dark.std()
    grid_rows = np.where(row_dark > max(r_thr, 0.30))[0]
    grid_cols = np.where(col_dark > max(c_thr, 0.30))[0]

    # Detect near-black border margins (the tile PNG padding)
    # column is "mostly black" if mean brightness very low
    col_bright = gray.mean(axis=0)
    row_bright = gray.mean(axis=1)
    black_cols = np.where(col_bright < 25)[0]
    black_rows = np.where(row_bright < 25)[0]

    def span(idxs, n):
        if len(idxs) == 0:
            return None
        left = idxs[idxs < n * 0.15]
        right = idxs[idxs > n * 0.85]
        return (int(left.max()) + 1 if len(left) else 0,
                int(right.min()) if len(right) else n)

    print(f'\n=== {name} ({w}x{h}) ===')
    print(f'  mean row-dark={row_dark.mean():.4f} std={row_dark.std():.4f}')
    print(f'  candidate grid ROWS (>{max(r_thr,0.30):.2f}): {len(grid_rows)} -> '
          f'{grid_rows[:25].tolist()}')
    print(f'  candidate grid COLS (>{max(c_thr,0.30):.2f}): {len(grid_cols)} -> '
          f'{grid_cols[:25].tolist()}')
    # regular spacing check
    for label, g in (('rows', grid_rows), ('cols', grid_cols)):
        if len(g) >= 3:
            d = np.diff(g)
            d = d[d > 20]  # ignore line-thickness duplicates
            if len(d):
                print(f'  {label} spacing: median={np.median(d):.0f} '
                      f'min={d.min()} max={d.max()} count={len(d)}')
    print(f'  black border cols: span={span(black_cols, w)} (count={len(black_cols)})')
    print(f'  black border rows: span={span(black_rows, h)} (count={len(black_rows)})')

    # blue (water) fraction - sanity that these are topo maps
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    blue = ((b - r > 15) & (b - g > 5) & (b > 120)).mean()
    print(f'  blue/water fraction: {blue:.3f}')


if __name__ == '__main__':
    for t in TILES:
        analyze(t)
