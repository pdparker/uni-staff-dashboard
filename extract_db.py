import zipfile, xml.etree.ElementTree as ET, sqlite3, re, os

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'

def tag(name): return f'{{{NS}}}{name}'

xlsx = '2025 Staff Pivot table.xlsx'

with zipfile.ZipFile(xlsx) as z:
    defn_xml  = z.read('xl/pivotCache/pivotCacheDefinition1.xml')
    recs_xml  = z.read('xl/pivotCache/pivotCacheRecords1.xml')

# ── Parse field lookup tables ─────────────────────────────
root_def = ET.fromstring(defn_xml)
fields = []
for cf in root_def.findall(f'.//{tag("cacheField")}'):
    name = cf.attrib['name']
    items = []
    si = cf.find(tag('sharedItems'))
    if si is not None:
        for child in si:
            local = child.tag.split('}')[1]
            if local == 's':
                items.append(child.attrib['v'])
            elif local == 'n':
                items.append(int(float(child.attrib['v'])))
    fields.append({'name': name, 'items': items})

print("Fields:")
for i, f in enumerate(fields):
    print(f"  {i}: {f['name']} → {f['items'][:6]}{'...' if len(f['items'])>6 else ''}")

# ── Parse records ─────────────────────────────────────────
root_recs = ET.fromstring(recs_xml)
records = []
for r in root_recs.findall(tag('r')):
    row = []
    for child in r:
        local = child.tag.split('}')[1]
        if local == 'x':
            row.append(int(child.attrib['v']))   # shared-item index
        elif local == 'n':
            row.append(float(child.attrib['v']))  # numeric value
        elif local == 's':
            row.append(child.attrib['v'])
    records.append(row)

print(f"\nTotal records: {len(records)}")
print("Sample record (indices):", records[0])

# Decode first few records for sanity check
for rec in records[:3]:
    decoded = {}
    for fi, val in enumerate(rec):
        f = fields[fi]
        if f['items']:  # categorical – val is index
            decoded[f['name']] = f['items'][int(val)]
        else:           # numeric
            decoded[f['name']] = val
    print("  Decoded:", decoded)

# ── Build SQLite DB ───────────────────────────────────────
db_path = 'staff_data.db'
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute('''CREATE TABLE staff (
    year INTEGER,
    institution TEXT,
    state TEXT,
    gender TEXT,
    classification TEXT,
    function TEXT,
    org_unit TEXT,
    work_contract TEXT,
    staff_count INTEGER,
    staff_fte REAL
)''')

cur.execute('CREATE INDEX idx_year ON staff(year)')
cur.execute('CREATE INDEX idx_inst ON staff(institution)')
cur.execute('CREATE INDEX idx_state ON staff(state)')
cur.execute('CREATE INDEX idx_function ON staff(function)')
cur.execute('CREATE INDEX idx_gender ON staff(gender)')
cur.execute('CREATE INDEX idx_classification ON staff(classification)')

rows_inserted = 0
for rec in records:
    vals = []
    for fi, val in enumerate(rec):
        f = fields[fi]
        if f['items']:
            vals.append(f['items'][int(val)])
        else:
            vals.append(val)

    year, institution, state, gender, classification, function_, org_unit, work_contract, staff_count, staff_fte = vals
    cur.execute('INSERT INTO staff VALUES (?,?,?,?,?,?,?,?,?,?)',
        (year, institution, state, gender, classification, function_, org_unit, work_contract,
         int(staff_count) if staff_count is not None else 0, staff_fte))
    rows_inserted += 1

conn.commit()

# Quick verification
print(f"\nInserted {rows_inserted} rows")
print("\nFunction breakdown (2025, FT&FF only, all institutions):")
for row in cur.execute('''
    SELECT function, SUM(staff_count), ROUND(SUM(staff_fte),1)
    FROM staff
    WHERE year=2025 AND work_contract="Full-Time and Fractional Full-Time"
    GROUP BY function ORDER BY SUM(staff_fte) DESC
'''):
    print(f"  {row[0]}: count={row[1]:,}  FTE={row[2]:,.1f}")

print("\nGender breakdown (2025, FT&FF):")
for row in cur.execute('''
    SELECT gender, SUM(staff_count), ROUND(SUM(staff_fte),1)
    FROM staff
    WHERE year=2025 AND work_contract="Full-Time and Fractional Full-Time"
    GROUP BY gender ORDER BY SUM(staff_count) DESC
'''):
    print(f"  {row[0]}: count={row[1]:,}  FTE={row[2]:,.1f}")

print("\nClassification breakdown (2025, FT&FF):")
for row in cur.execute('''
    SELECT classification, SUM(staff_count), ROUND(SUM(staff_fte),1)
    FROM staff
    WHERE year=2025 AND work_contract="Full-Time and Fractional Full-Time"
    GROUP BY classification ORDER BY SUM(staff_fte) DESC
'''):
    print(f"  {row[0]}: count={row[1]:,}  FTE={row[2]:,.1f}")

print("\nWork Contract breakdown (2025):")
for row in cur.execute('''
    SELECT work_contract, SUM(staff_count), ROUND(SUM(staff_fte),1)
    FROM staff WHERE year=2025
    GROUP BY work_contract
'''):
    print(f"  {row[0]}: count={row[1]:,}  FTE={row[2]:,.1f}")

print("\nOrg Unit breakdown (2025, FT&FF):")
for row in cur.execute('''
    SELECT org_unit, SUM(staff_count), ROUND(SUM(staff_fte),1)
    FROM staff
    WHERE year=2025 AND work_contract="Full-Time and Fractional Full-Time"
    GROUP BY org_unit ORDER BY SUM(staff_fte) DESC
'''):
    print(f"  {row[0]}: count={row[1]:,}  FTE={row[2]:,.1f}")

conn.close()
print(f"\nDatabase saved to {db_path}")
