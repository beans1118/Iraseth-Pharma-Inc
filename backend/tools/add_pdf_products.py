"""Selected PDF products -> EXISTING product validator/service/collection.

Read-only by default, with no Flask startup/index creation. --apply is a later
explicitly authorized operation only; it writes products and catalog audit
events, never stock/batches/orders/prices or a second product collection.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from uuid import uuid4
from urllib.parse import urlsplit

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))


def validate_local_target(name,uri):
    try:parsed=urlsplit(uri)
    except (ValueError,TypeError):raise ValueError('Invalid local MongoDB target.') from None
    if name not in ('iraseth_test','iraseth_dev') or parsed.scheme!='mongodb' or parsed.hostname not in ('127.0.0.1','localhost','::1') or ',' in parsed.netloc:
        raise ValueError('This selected-product operation is local test/development only; Atlas/production targets are refused.')


def build_plan(manifest,candidate_ids,image_review,duplicate_reviews=None):
    from extensions import db
    from config import Config
    from modules.brochure.service import provisional_selections,digest
    from modules.brochure.routes import catalog,selected_documents
    validate_local_target(db.name,Config.MONGO_URI)
    if db.name not in ('iraseth_test','iraseth_dev'):raise ValueError('This one-time operation is restricted to the named test/development databases.')
    selections=provisional_selections(manifest,candidate_ids,image_review,duplicate_reviews)
    products=catalog()
    existing={p['id']:p for p in db.products.find({'id':{'$in':[s['id'] for s in selections]}})}
    skipped=[];pending=[]
    for row in selections:
        old=existing.get(row['id'])
        if old:
            source=old.get('brochure_source',{})
            if source.get('sha256')!=manifest['source_sha256'] or source.get('candidate_id')!=row['candidate_id']:
                raise ValueError('A selected internal identifier already belongs to another product. Stop and review duplicates.')
            skipped.append(old['id'])
        else:pending.append(row)
    documents=selected_documents(pending,manifest,products) if pending else []
    signatures=[{k:v for k,v in d.items() if k!='created_at'} for d in documents]
    plan={'database':db.name,'source_sha256':manifest['source_sha256'],
        'manifest_hash':digest(manifest),'image_review_hash':digest(image_review),
        'candidate_ids':candidate_ids,'catalog_identity_hash':digest(products),
        'duplicate_reviews':duplicate_reviews or {},
        'selection_hash':digest(selections),'document_hash':digest(signatures),
        'already_existing_ids':skipped,'products':[
            {'id':d['id'],'name':d['name'],'category':d['category'],'unit':d['unit'],'sku':None,
             'identity_status':'provisional','source_page':d['brochure_source']['page'],
             'brand':d['brand'],'manufacturer':d['manufacturer'],'model':d['model'],
             'description':d['description'],'key_features':d['key_features'],'specifications':d['specifications'],
             'image_count':len(d['images']),'quantity':0,'price':None,'publicPrice':None,'inStock':False}
            for d in documents],
        'message':'Existing products collection only. No database writes or indexes in this dry run; no stock/batches or approved SKU/unit/price.'}
    return plan,documents


def apply_plan(manifest,candidate_ids,image_review,reviewed_report,actor,duplicate_reviews=None):
    from extensions import db
    from modules.brochure.service import digest
    from routes.products import insert_product_document
    # Dry-run identity/catalog/content hashes bind the exact intended operation.
    plan,docs=build_plan(manifest,candidate_ids,image_review,duplicate_reviews)
    for field in ('database','source_sha256','manifest_hash','image_review_hash','candidate_ids','selection_hash'):
        if plan[field]!=reviewed_report.get(field):raise ValueError('Reviewed report target/source/selection changed; run a new dry run.')
    if not docs:return {'created_ids':[],'already_existing_ids':plan['already_existing_ids']}
    for field in ('catalog_identity_hash','document_hash'):
        if plan[field]!=reviewed_report.get(field):raise ValueError('Catalog or product content changed; run a fresh dry run.')
    user=db.users.find_one({'email':actor})
    if not user or user.get('role') not in ('superadmin','subadmin') or user.get('is_active') is False or user.get('disabled'):
        raise ValueError('An existing active Superadmin or authorized Sub-admin actor is required.')
    # Schema writes occur only behind explicit --apply, never Flask startup.
    db.products.create_index('id',unique=True)
    for field in ('_sku_key','_brochure_identity'):
        db.products.create_index(field,unique=True,partialFilterExpression={field:{'$type':'string'}})
    def create(session):
        from modules.brochure.routes import catalog
        if digest(catalog(session))!=plan['catalog_identity_hash']:
            raise ValueError('Catalog identities changed before commit. No products created; review again.')
        current=db.users.find_one({'email':actor},session=session)
        if not current or current.get('role') not in ('superadmin','subadmin') or current.get('is_active') is False or current.get('disabled'):
            raise ValueError('Actor permissions changed; no products created.')
        for doc in docs:
            insert_product_document(doc,session=session)
            db.catalog_events.insert_one({'id':uuid4().hex,'product_id':doc['id'],'action':'pdf_product_create',
                'source':doc['brochure_source'],'actor_email':actor,'at':doc['created_at'],
                'selection_hash':plan['selection_hash']},session=session)
    with db.client.start_session() as session:session.with_transaction(create)
    return {'created_ids':[d['id'] for d in docs],'already_existing_ids':plan['already_existing_ids']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True,choices=['iraseth_test','iraseth_dev'])
    parser.add_argument('--candidate-id',action='append',required=True)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--reviewed-report',type=Path)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--confirm-database')
    parser.add_argument('--actor')
    parser.add_argument('--duplicate-reviewed-candidate-id',action='append',default=[])
    parser.add_argument('--duplicate-review-note',default='')
    args=parser.parse_args()
    try:
        if args.apply and (args.confirm_database!=args.database or not args.actor or not args.reviewed_report):
            raise ValueError('Applying requires explicit --confirm-database, --actor and --reviewed-report. Current task does not authorize development writes.')
        if args.report and args.report.exists():raise ValueError('Report already exists; choose a new filename to preserve review evidence.')
        from dotenv import dotenv_values
        if args.database=='iraseth_test':
            from utils.test_configuration import local_test_settings
            settings,test_uri,_=local_test_settings(BACKEND)
        else:
            settings=dotenv_values(BACKEND/'.env')
        if settings.get('MONGO_DB_NAME')!=args.database:raise ValueError('Configured target does not match the requested database; no environment switch is allowed.')
        validate_local_target(args.database,settings.get('MONGO_URI',''))
        if args.database=='iraseth_test' and (settings.get('APP_ENV')!='testing' or settings.get('MONGO_URI')!=test_uri):
            raise ValueError('Refusing unsafe test configuration.')
        for key,value in settings.items():
            if value is not None:os.environ[key]=value
        from extensions import db
        if db.name!=args.database:raise ValueError('Actual database does not match requested target.')
        from modules.brochure.service import load_manifest,FOLDER
        manifest,_=load_manifest()
        review=json.loads((FOLDER/'pdf-product-image-review.json').read_text(encoding='utf-8'))
        duplicate_reviews={key:args.duplicate_review_note for key in args.duplicate_reviewed_candidate_id}
        if 'app' in sys.modules:raise RuntimeError('Unexpected Flask startup; stop this operation.')
        if args.apply:
            report=json.loads(args.reviewed_report.read_text(encoding='utf-8'))
            result=apply_plan(manifest,args.candidate_id,review,report,args.actor,duplicate_reviews)
        else:
            result,_=build_plan(manifest,args.candidate_id,review,duplicate_reviews)
        if 'app' in sys.modules:raise RuntimeError('Unexpected Flask startup; stop this operation.')
        if args.report:args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,indent=2));return 0
    except (ValueError,OSError) as exc:
        print('PDF product operation blocked: '+str(exc),file=sys.stderr);return 2
    except Exception as exc:
        print('PDF product operation failed ('+type(exc).__name__+'); no automatic retry, overwrite or target switch.',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
