import csv, json

OVERRIDE_CSV = 'manual_mappings.csv'
OVERRIDE_JSON = 'manual_mappings.json'

mapping = {}
with open(OVERRIDE_CSV, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        db_id = row['db_id'].strip()
        spotify_id  = row['spotify_id'].strip()
        if spotify_id and db_id:
            mapping[db_id] = spotify_id

with open(OVERRIDE_JSON, 'w') as f:
    json.dump(mapping, f, indent=2)

print(f"Wrote {len(mapping)} overrides to {OVERRIDE_JSON}")
