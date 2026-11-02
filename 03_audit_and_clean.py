"""Stage 3: audit and clean the two-stage Vancouver parking enrichment.
Run beside 01_coordinate_lookup.csv, 02_block_annotation_lookup.csv and
parking_tickets_with_coordinates_and_blocks.csv. Requires pandas, numpy.
Keeps only verified-by-rule coordinate matches (ExactStart / InclusiveRange).
Nearest block-number annotation is NOT required for inclusion.
Outputs CSV files; does not modify source files.
"""
from pathlib import Path
import pandas as pd
import numpy as np

from project_paths import ROOT, RAW, INTERMEDIATE, QUALITY, COLLISION, MAPS, ensure_output_dirs
ensure_output_dirs()
ROOT = Path(__file__).resolve().parent
INPUT = INTERMEDIATE / 'parking_tickets_with_coordinates_and_blocks.csv'
OUT = QUALITY
CHUNKSIZE = 100_000
KEEP_METHODS = {'ExactStart', 'InclusiveRange'}


def main():
    OUT.mkdir(exist_ok=True)
    if not INPUT.exists():
        raise FileNotFoundError(f'Missing input: {INPUT}')

    method_counts = {}
    block_counts = {}
    reason_counts = {}
    annotation_counts = {}
    street_counts = {}
    totals = {'InputTickets': 0, 'KeptTickets': 0, 'ExcludedTickets': 0}
    output_paths = {
        'keep': OUT / 'parking_tickets_clean_geocoded.csv',
        'exclude': OUT / 'parking_tickets_excluded_review.csv',
    }
    for path in output_paths.values():
        if path.exists():
            path.unlink()
    first = {'keep': True, 'exclude': True}
    required = {'Block', 'Street', 'Latitude', 'Longitude', 'CoordinateMatchMethod'}

    for chunk in pd.read_csv(INPUT, dtype='string', chunksize=CHUNKSIZE, low_memory=False):
        if not required.issubset(chunk.columns):
            raise ValueError(f'Missing required columns: {sorted(required-set(chunk.columns))}')
        totals['InputTickets'] += len(chunk)
        method = chunk['CoordinateMatchMethod'].fillna('MissingMethod').str.strip()
        lat = pd.to_numeric(chunk['Latitude'], errors='coerce')
        lon = pd.to_numeric(chunk['Longitude'], errors='coerce')
        valid_coord = lat.between(49.0, 49.5) & lon.between(-123.4, -122.9)
        # Vancouver-area bounds are a gross-error check, not proof of correct street placement.
        keep = method.isin(KEEP_METHODS) & valid_coord
        
                
        # Determine why each record is kept or excluded
        is_matched = method.isin(KEEP_METHODS).fillna(False)
        has_valid_coord = pd.Series(
            valid_coord, index=method.index
        ).fillna(False).astype(bool)

        why = pd.Series("Kept", index=method.index)

        why.loc[~has_valid_coord] = "InvalidCoordinates"
        why.loc[~is_matched] = "UnmatchedStreetBlock"


        chunk['CleaningDecision'] = np.where(keep, 'Keep', 'ExcludeFromGeographicDataset')
        chunk['CleaningReason'] = why
        # Record-level status counts, NOT unique block counts.
        for col, store in [('CoordinateMatchMethod', method_counts), ('CleaningReason', reason_counts),
                           ('BlockNumberMatchStatus', annotation_counts)]:
            vals = chunk[col].fillna('Missing') if col in chunk else pd.Series('NotAvailable', index=chunk.index)
            for k, n in vals.value_counts(dropna=False).items():
                store[str(k)] = store.get(str(k), 0) + int(n)
        for tag, mask in [('keep', keep), ('exclude', ~keep)]:
            part = chunk.loc[mask]
            totals['KeptTickets' if tag == 'keep' else 'ExcludedTickets'] += len(part)
            if len(part):
                part.to_csv(output_paths[tag], index=False, sep=';', encoding='utf-8-sig' if first[tag] else 'utf-8',
                            mode='w' if first[tag] else 'a', header=first[tag])
                first[tag] = False
        # Aggregate by unique Block + Street to avoid counting the same location many times.
        location_cols = ['Block', 'Street', 'CoordinateMatchMethod', 'CleaningDecision', 'CleaningReason']
        group = chunk.groupby(location_cols, dropna=False).size()
        for key, n in group.items():
            block_counts[key] = block_counts.get(key, 0) + int(n)

    block_rows = [dict(zip(['Block','Street','CoordinateMatchMethod','CleaningDecision','CleaningReason'], key), TicketCount=n)
                  for key, n in block_counts.items()]
    blocks = pd.DataFrame(block_rows)
    blocks.to_csv(OUT/'location_audit.csv', index=False, encoding='utf-8-sig')
    methods = blocks.groupby('CoordinateMatchMethod', dropna=False).agg(
        Blocks=('Block','size'), Tickets=('TicketCount','sum')).reset_index()
    methods['BlockPercent'] = (methods.Blocks / len(blocks) * 100).round(3)
    methods['TicketPercent'] = (methods.Tickets / totals['InputTickets'] * 100).round(3)
    methods.to_csv(OUT/'matching_summary.csv', index=False, encoding='utf-8-sig')
    exclusions = blocks.loc[blocks.CleaningDecision != 'Keep'].sort_values('TicketCount', ascending=False)
    exclusions.to_csv(OUT/'unmatched_locations_ranked.csv', index=False, encoding='utf-8-sig')
    ann = pd.DataFrame([{'BlockNumberMatchStatus': k, 'Tickets': n} for k,n in annotation_counts.items()])
    ann.sort_values('Tickets', ascending=False).to_csv(OUT/'block_annotation_summary.csv', index=False, encoding='utf-8-sig')
    decision = blocks.groupby(['CleaningDecision','CleaningReason'],dropna=False).agg(
        Blocks=('Block','size'),Tickets=('TicketCount','sum')).reset_index()
    decision.to_csv(OUT/'cleaning_summary.csv', index=False, encoding='utf-8-sig')
    assert totals['InputTickets'] == totals['KeptTickets'] + totals['ExcludedTickets']
    assert len(blocks) == int(methods.Blocks.sum())
    print('\n=== FINAL DATA QUALITY AUDIT ===')
    print('Input tickets:', f"{totals['InputTickets']:,}")
    print('Unique street-blocks:', f'{len(blocks):,}')
    print(methods.to_string(index=False))
    print('\nCleaning decisions:')
    print(decision.to_string(index=False))
    print('\nBlock-number annotation (ticket counts; proximity candidates only):')
    print(ann.to_string(index=False))
    print('\nSaved to:', OUT)
    print('Kept:', output_paths['keep'].name, '| Excluded review:', output_paths['exclude'].name)
    print('\nCONCLUSION: The cleaned file includes only ExactStart/InclusiveRange rows with plausible coordinates.')
    print('Unmatched records are excluded from this copy, not deleted from source. Block-number labels are unverified proximity annotations.')

if __name__ == '__main__':
    main()
