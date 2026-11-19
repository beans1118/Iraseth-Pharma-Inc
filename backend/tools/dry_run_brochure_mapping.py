"""Read-only mapping validation BEFORE Flask startup or index creation.

No app import, writes, index creation, approval token or automatic import.
This command never switches environment files or imports active products.
"""
import argparse
import csv
import json
from pathlib import Path
import sys

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from modules.brochure.service import load_manifest, digest
from modules.product_metadata import canonical_sku


def flag(value):
    value=(value or 'false').strip().lower()
    if value not in ('true','false'):raise ValueError('Batch/approval flags must be true or false.')
    return value=='true'


def selections_from_csv(path,manifest):
    allowed={c['candidate_id'] for c in manifest['candidates']};seen=set();skus=set();selections=[]
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        required={'candidate_id','include_in_batch','staff_approved_sku','staff_approved_selling_unit','model_decision','image_decision','staff_approved'}
        if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames) or not required<=set(reader.fieldnames):raise ValueError('Use the current mapping template with unique headers.')
        for row in reader:
            key=row['candidate_id']
            if key not in allowed or key in seen:raise ValueError('Unknown or duplicate candidate key in mapping.')
            seen.add(key)
            if not flag(row.get('include_in_batch')):continue
            sku=(row.get('staff_approved_sku') or '').strip()
            if canonical_sku(sku) in skus:raise ValueError('Duplicate SKU among selected rows.')
            skus.add(canonical_sku(sku))
            selections.append({'candidate_id':key,'id':sku,'unit':(row.get('staff_approved_selling_unit') or '').strip(),
                'model_decision':row.get('model_decision'),'model':row.get('staff_verified_model') or '',
                'model_evidence':row.get('model_evidence') or '', 'image_decision':row.get('image_decision'),
                'include_images':row.get('image_decision')=='include','images_reviewed':flag(row.get('images_approved')),
                'review_confirmed':flag(row.get('staff_approved')),'review_notes':row.get('staff_review_notes') or '',
                'duplicate_reviewed':flag(row.get('duplicate_reviewed'))})
    if not 1<=len(selections)<=30:raise ValueError('Mark 1 to 30 rows include_in_batch=true; obtain genuine mappings and review decisions first.')
    return selections


def validate_read_only(selections,manifest,products):
    # Blueprint/product-validator imports do not create an application or call
    # ensure_indexes. The selected_documents helper consumes supplied data/files.
    from modules.brochure.routes import selected_documents
    docs=selected_documents(selections,manifest,products)
    return [{'id':d['id'],'name':d['name'],'category':d['category'],'unit':d['unit'],
        'brand':d['brand'],'manufacturer':d['manufacturer'],'model':d['model'],
        'candidate_id':d['brochure_source']['candidate_id'],'source_pdf_page':d['brochure_source']['page'],
        'description':d['description'],'key_features':d['key_features'],'specifications':d['specifications'],
        'image_count':len(d['images']),'image_decision':d['brochure_source']['image_review']['decision'],
        'quantity':0,'publicPrice':None,'inStock':False} for d in docs]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping',type=Path,required=True)
    parser.add_argument('--database',choices=['iraseth_dev'],required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    try:
        if args.report and args.report.exists():raise ValueError('Report already exists. Choose a new filename to preserve previous review evidence.')
        manifest,manifest_hash=load_manifest()
        selections=selections_from_csv(args.mapping,manifest)
        from dotenv import dotenv_values
        from pymongo import MongoClient
        settings=dotenv_values(BACKEND/'.env')
        if settings.get('MONGO_DB_NAME')!=args.database or not settings.get('MONGO_URI'):raise ValueError('Configured database must already be iraseth_dev; no environment change is permitted.')
        with MongoClient(settings['MONGO_URI'],serverSelectionTimeoutMS=5000) as client:
            products=list(client[args.database].products.find({}, {'_id':0,'id':1,'name':1,'brand':1,'manufacturer':1}).sort('id',1))
        result=validate_read_only(selections,manifest,products)
        if 'app' in sys.modules:raise RuntimeError('Unexpected Flask application import; do not use this process for an active dry run.')
        report={'database':args.database,'read_only':True,'dry_run':True,'approval_token_created':False,
            'manifest_hash':manifest_hash,'catalog_hash':digest(products),'selection_hash':digest(selections),
            'products':result,'message':'No database writes or indexes created. This is review evidence only; active import remains unauthorized.'}
        if args.report:args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=2))
    except (ValueError,OSError) as exc:
        print('Dry run blocked: '+str(exc),file=sys.stderr);return 2
    return 0


if __name__=='__main__':sys.exit(main())
