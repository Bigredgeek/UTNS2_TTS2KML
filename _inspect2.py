import json

with open('TS_Save_160.json', encoding='utf-8') as f:
    d = json.load(f)
objs = d.get('ObjectStates', [])

# 1) Tile grid layout
print('=== Tile grid (Custom_Tile nick 1-4) ===')
tiles = [o for o in objs if o.get('Name') == 'Custom_Tile' and o.get('Nickname') in ('1', '2', '3', '4')]
for o in sorted(tiles, key=lambda x: x.get('Nickname')):
    t = o['Transform']
    print('Tile {}: X={:7.2f} Z={:7.2f} rotY={:5.1f} sX={} sY={} sZ={}'.format(
        o['Nickname'], t['posX'], t['posZ'], t['rotY'],
        t['scaleX'], t.get('scaleY'), t['scaleZ']))

# 2) How are units stored? Top-level vs contained
print('\n=== Top-level object Names (counts) ===')
from collections import Counter
names = Counter(o.get('Name') for o in objs)
for n, c in names.most_common():
    print('  {}: {}'.format(n, c))

# 3) Count units with NATO / WP / Marker tags at top level and nested
print('\n=== Tag distribution (recursive) ===')
tagc = Counter()
def walk(lst, depth=0):
    for o in lst:
        if not isinstance(o, dict):
            continue
        for t in (o.get('Tags') or []):
            tagc[t] += 1
        walk(o.get('ContainedObjects') or [], depth + 1)
walk(objs)
for t, c in tagc.most_common():
    print('  {}: {}'.format(t, c))

# 4) Sample tagged units
print('\n=== Sample tagged unit objects (first 5 top-level) ===')
shown = 0
for o in objs:
    if (o.get('Tags') and o.get('Name') in ('Custom_Tile', 'Custom_Token')
            and o.get('Nickname') not in ('1', '2', '3', '4')):
        t = o.get('Transform', {})
        print('  Nick={!r} Name={} Tags={} X={:.2f} Z={:.2f}'.format(
            o.get('Nickname'), o.get('Name'), o.get('Tags'),
            t.get('posX', 0), t.get('posZ', 0)))
        shown += 1
        if shown >= 5:
            break

# 5) X/Z extent of all tagged units
xs, zs = [], []
def collect(lst):
    for o in lst:
        if not isinstance(o, dict):
            continue
        if o.get('Tags') and o.get('Nickname') not in ('1', '2', '3', '4'):
            t = o.get('Transform') or {}
            if 'posX' in t:
                xs.append(t['posX'])
                zs.append(t['posZ'])
        collect(o.get('ContainedObjects') or [])
collect(objs)
if xs:
    print('\n=== Tagged-unit coordinate span ===')
    print('  X: {:.2f} .. {:.2f}'.format(min(xs), max(xs)))
    print('  Z: {:.2f} .. {:.2f}'.format(min(zs), max(zs)))
    print('  count:', len(xs))
