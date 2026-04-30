import yaml, os
from schema.contract_item import ContractItem
from matching_engine import MatchService

cat_dir = 'database/categories'
catalog = {}
for fname in os.listdir(cat_dir):
    if not fname.endswith('.yaml'): continue
    with open(os.path.join(cat_dir, fname), encoding='utf-8') as f:
        items = yaml.safe_load(f) or []
        for it in items:
            catalog[it['id']] = it

service = MatchService(catalog, debug_mode=True)

test_items = [
    {
        'raw_description': 'Bath Bathroom Labor One Piece Demo/Install Demolition, Disposal, and haul away of existing wet space. Replace P-Trap, replace necessary wet space plumbing. Includes installation of moisture resistant backerboard and selected shower base or tub, walls, fixtures, and accessories. Adjust height of showerhead.',
        'category': 'Bathroom',
        'section': 'Bath'
    },
    {
        'raw_description': 'Bath Accessories Grab Bars Traditional 12" Traditional Grab Bar Chrome',
        'category': 'Grab Bars',
        'section': 'Bath'
    },
    {
        'raw_description': 'Bath Fixtures Tub Bundles Arcade Bundle (NEW) Brushed Nickel (BN)',
        'category': 'Fixtures Tub',
        'section': 'Bath'
    }
]

print('Running tests...')
for i, item in enumerate(test_items):
    print(f'\n--- TEST {i+1} ---')
    print(f'Raw: {item["raw_description"][:80]}...')
    res = service.resolve_match(item)
    print(f'Match ID : {res["match_id"]}')
    print(f'Color    : {res["color_code"]}')
    print(f'Score    : {res["confidence"]}')
    
print('\nTests complete. Check the logs folder for the debug output to verify fast path.')
