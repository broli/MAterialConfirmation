"""Print a compact summary of the PDF analysis JSON for inspection."""
import json

with open('scratch/pdf_analysis_results.json', encoding='utf-8') as f:
    data = json.load(f)

for doc in data:
    print('=' * 80)
    print('FILE:', doc['file'])
    print('PAGES:', len(doc['pages']))
    for pg in doc['pages']:
        print(f'\n  -- Page {pg["page"]} --')
        print(f'  Tables found: {len(pg["tables"])}')
        for t in pg['tables']:
            print(f'    Table {t["table_index"]}: {len(t["rows"])} rows')
            for row in t['rows'][:8]:
                print('      ROW:', row)
        lines = pg['text_lines']
        if lines:
            print(f'  Text lines ({len(lines)}):')
            for l in lines[:40]:
                print('    |', l)
        print()
    print()
