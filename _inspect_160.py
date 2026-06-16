import json

with open('TS_Save_160.json', encoding='utf-8') as f:
    d = json.load(f)
objs = d.get('ObjectStates', [])
print('SaveName:', d.get('SaveName'))
print('Top-level objects:', len(objs))

print('\n=== The four big tiles (1-4) ===')
for o in objs:
    if o.get('Name') == 'Custom_Tile' and o.get('Nickname') in ('1', '2', '3', '4'):
        t = o.get('Transform') or {}
        ci = o.get('CustomImage') or {}
        url = (ci.get('ImageURL') or '')[:95]
        print('Tile {}: posX={:.2f} posZ={:.2f} rotY={:.1f} sX={} sZ={}'.format(
            o.get('Nickname'), t.get('posX', 0), t.get('posZ', 0),
            t.get('rotY', 0), t.get('scaleX'), t.get('scaleZ')))
        print('   img =', url)
        print('   tags =', o.get('Tags'))

# Build a quick set of all nicknames to look for city markers
print('\n=== All distinct nicknames (non-empty) with counts ===')
from collections import Counter
nicks = Counter()
def walk(lst):
    for o in lst:
        if not isinstance(o, dict):
            continue
        n = o.get('Nickname')
        if isinstance(n, str) and n.strip():
            nicks[n.strip()] += 1
        walk(o.get('ContainedObjects') or [])
walk(objs)
for n, c in sorted(nicks.items()):
    print('  {!r}: {}'.format(n, c))
