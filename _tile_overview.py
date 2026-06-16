"""Ad-hoc helper: downscale tiles for overview + crop regions at native res
to check for a coordinate graticule / grid labels. Safe to delete later."""
import sys
from PIL import Image

TILES = ['tile1', 'tile2', 'tile3', 'tile4']


def overview(name, size=1200):
    im = Image.open(f'_tile_images/{name}.png').convert('RGB')
    im.thumbnail((size, size))
    out = f'_tile_images/{name}_overview.png'
    im.save(out)
    print(f'{name}: saved {out} at {im.size}')


def crop(name, box, tag):
    im = Image.open(f'_tile_images/{name}.png').convert('RGB')
    region = im.crop(box)
    out = f'_tile_images/{name}_{tag}.png'
    region.save(out)
    print(f'{name}: saved {out} {region.size} from {box}')


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'overview'
    if what == 'overview':
        for t in TILES:
            overview(t)
    elif what == 'corners':
        # native-res corner + edge crops of tile1 to look for grid coordinate labels
        name = 'tile1'
        crop(name, (0, 0, 700, 700), 'TL')
        crop(name, (2300, 0, 3000, 700), 'TR')
        crop(name, (0, 2300, 700, 3000), 'BL')
        crop(name, (2300, 2300, 3000, 3000), 'BR')
        # center-edge strips where grid labels often sit
        crop(name, (1150, 0, 1850, 400), 'Ttop')
        crop(name, (0, 1150, 400, 1850), 'Lside')
