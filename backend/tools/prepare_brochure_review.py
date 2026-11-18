"""Create a source-reviewed staff packet using READ-ONLY catalog queries.

No Flask application import, inserts, indexes, stock changes or staff approval.
Run from the repository root; the configured database must be iraseth_dev.
"""
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from dotenv import dotenv_values
from pymongo import MongoClient
from modules.brochure.service import FOLDER, load_manifest, preview, normalized
from modules.brochure.assessment import inspect_images
from modules.brochure.review_sheet import refresh_mapping_file
from modules.product_metadata import canonical_sku


def main():
    settings = dotenv_values(BACKEND / '.env')
    if settings.get('MONGO_DB_NAME') != 'iraseth_dev' or not settings.get('MONGO_URI'):
        raise RuntimeError('Read-only review expects the existing iraseth_dev configuration. No environment file will be changed.')
    manifest, manifest_hash = load_manifest()
    with MongoClient(settings['MONGO_URI'], serverSelectionTimeoutMS=5000) as client:
        products = list(client['iraseth_dev'].products.find({}, {'_id':0,'id':1,'name':1,'brand':1,'manufacturer':1}).sort('id',1))
    report = preview(manifest, products)
    report.update(manifest_hash=manifest_hash, database='iraseth_dev', read_only=True,
        catalog_records_read=len(products), review_kind='Technical source review only; no staff identity or import approval',
        reviewed_images=inspect_images(manifest, FOLDER))
    groups = defaultdict(list)
    for row in report['candidates']:
        groups[normalized(row['name'])].append(row['candidate_id'])
    report['duplicate_source_names'] = [ids for ids in groups.values() if len(ids)>1]
    sku_groups=defaultdict(list)
    for product in products:sku_groups[canonical_sku(product['id'])].append(product['id'])
    report['existing_sku_collision_groups']=[ids for ids in sku_groups.values() if len(ids)>1]
    report['merged_source_duplicates'] = [{'name':c['name'],'occurrences':c['source_occurrences'],'page':c['source_pdf_page']}
        for c in report['candidates'] if c.get('source_occurrences',1)>1]
    report['missing_counts'] = {key:sum(not c.get(key) for c in report['candidates'])
        for key in ('sku','unit','documented_manufacturer','description','key_features','specifications','image_paths')}
    report['missing_counts']['documented_model'] = sum(not c['documented_models'] for c in report['candidates'])
    (FOLDER / 'reviewed-candidates.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    refresh_mapping_file(FOLDER/'staff-mapping-template.csv',manifest,FOLDER)
    lines=[
        'Core products: technical source review and staff preparation','',
        f"Source: {report['source_pdf']}; manifest SHA-256 `{manifest_hash}`.",'',
        f"{report['total']} records reviewed. {report['source_ready_count']} have clear source identities; "
        f"{report['source_counts'].get('Source clarification required',0)} require source clarification; "
        f"{report['source_counts'].get('Family / offering',0)} are families/offerings.",'',
        f"Fully ready for iraseth_dev insert: {report['ready_to_import_count']}. All 266 still lack staff-approved SKU and selling unit. "
        'The user confirmed that no mapping is available. The CSV leaves these fields blank. This review is not a staff approval.','',
        f"Read-only matching against {len(products)} iraseth_dev products: {json.dumps(report['match_counts'])}. "
        'No inserts or active inventory changes were performed.','',
        'Documented brands and manufacturers are kept separate. The brochure documents no manufacturer for any of the 266 records; '
        'a brand logo is not treated as manufacturer evidence. Optional missing descriptions, features and specifications stay empty.','',
        'Only four ENT entries have explicit model identifiers (VL3D, VL3R, VLDM, VLRM). The other 262 records do not supply a separate model identifier. '
        'Named products and documented needle/gauge variants are preserved; no unlisted model is invented. Broad equipment families need a verified specific model before import.','',
        f"{len(report['reviewed_images'])} source images checked: "
        f"{sum(i['upload_valid'] for i in report['reviewed_images'])} pass upload controls, "
        f"{sum(not i['upload_valid'] for i in report['reviewed_images'])} fail; "
        f"{sum(i['low_resolution'] for i in report['reviewed_images'])} are low resolution. "
        'Passing validation does not approve an image for active use. Images are optional.','',
        'The repeated High Quality Ductless Fume Hood entry is already merged (two source occurrences). '
        'Overlapping radiography family names remain separate review records. No broad family is imported.','',
        '| Candidate | Page | Source review | SKU | Selling unit | Source holds |','|---|---:|---|---|---|---|']
    for row in report['candidates']:
        lines.append('| '+' | '.join([row['name'].replace('|','/'),str(row['source_pdf_page']),row['source_status'],
            'Missing','Missing',' '.join(row['source_holds']).replace('|','/')])+' |')
    (FOLDER / 'SOURCE_REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ['total','catalog_records_read','source_counts','source_ready_count','ready_to_import_count','match_counts','missing_counts']},indent=2))


if __name__=='__main__': main()
