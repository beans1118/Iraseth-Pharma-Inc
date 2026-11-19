"""No anonymous access. Dry runs never write. Import requires a signed fresh
dry-run token, explicit item approvals, live RBAC, and a MongoDB transaction.
"""
import base64
import re
from uuid import uuid4

from flask import Blueprint, g, jsonify, request, send_file, Response
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pymongo.errors import DuplicateKeyError

from config import Config
from extensions import db
from modules.brochure.service import FOLDER, load_manifest, preview, classify, digest, identity, provisional_product_id
from modules.brochure.assessment import assess
from modules.brochure.review_sheet import mapping_csv
from modules.product_metadata import valid_image, canonical_sku, identifier_keys, PENDING_UNIT
from routes.products import prepare_product, insert_product_document, ProductProblem
from utils.security import require_role

bp=Blueprint('brochure_review', __name__, url_prefix='/api/v2/brochure')


class ReviewProblem(ValueError):
    def __init__(self,message,status=400):
        super().__init__(message); self.status=status


@bp.errorhandler(ValueError)
def invalid(exc):
    return jsonify(error=str(exc)), getattr(exc,'status',400)


@bp.after_request
def no_store(response):
    response.headers['Cache-Control']='no-store'
    return response


def catalog(session=None):
    return list(db.products.find({}, {'_id':0,'id':1,'name':1,'brand':1,'manufacturer':1,'sku':1},session=session).sort('id',1))


def signer():
    return URLSafeTimedSerializer(Config.JWT_SECRET,salt='brochure-dry-run-v1')


def payload():
    if request.content_length and request.content_length>128000:raise ReviewProblem('Request too large.',413)
    body=request.get_json(silent=True)
    if not isinstance(body,dict):raise ReviewProblem('A JSON object is required.')
    return body


def selected_documents(selections,manifest,products):
    if not isinstance(selections,list) or not 1<=len(selections)<=30:raise ReviewProblem('Select 1 to 30 individual records.')
    source={c['candidate_id']:c for c in manifest['candidates']}
    documents=[]; ids=set(); candidates=set(); identities=set()
    for selection in selections:
        if not isinstance(selection,dict) or any(k not in {'candidate_id','id','unit','review_confirmed','review_notes','duplicate_reviewed','include_images','images_reviewed','model_decision','model','model_evidence','image_decision','identity_mode'} for k in selection):raise ReviewProblem('Invalid selection fields.')
        if not isinstance(selection.get('candidate_id'), str):raise ReviewProblem('A candidate review key is required.')
        candidate=source.get(selection['candidate_id'])
        if not candidate or not candidate['importable']:raise ReviewProblem('Select an individually documented product/variant. Families and services require staff identification outside the import.')
        source_review=assess(candidate)
        if not source_review['source_ready']:raise ReviewProblem('Source clarification required: '+' '.join(source_review['source_holds']),409)
        if selection.get('review_confirmed') is not True:raise ReviewProblem('Each selected record needs explicit staff review approval.')
        note=selection.get('review_notes','')
        if not isinstance(note,str) or not 5<=len(note.strip())<=2000:raise ReviewProblem('Record a staff review note (5-2000 characters), including resolution of source warnings.')
        match=classify(candidate,products+documents)
        if match['existing_identity_count']:raise ReviewProblem(f"{candidate['name']} already exists. Edit the existing product instead.",409)
        if match['match_status']=='Ambiguous' and selection.get('duplicate_reviewed') is not True:raise ReviewProblem(f"Resolve possible duplicates for {candidate['name']} before approving.",409)
        proposed_id=selection.get('id','')
        provisional=selection.get('identity_mode')=='provisional'
        if selection.get('identity_mode') not in (None,'provisional'):raise ReviewProblem('Invalid identity mode.')
        if provisional and (proposed_id != provisional_product_id(manifest,candidate) or selection.get('unit') != PENDING_UNIT):
            raise ReviewProblem('Provisional products must use the marked stable internal ID and pending-unit marker.')
        if not isinstance(proposed_id,str) or any(canonical_sku(proposed_id) in identifier_keys(p) for p in products):raise ReviewProblem('The proposed product ID is invalid or already exists.',409)
        key=identity(candidate['name'],candidate.get('documented_brand'))
        if canonical_sku(proposed_id) in ids or candidate['candidate_id'] in candidates or key in identities:raise ReviewProblem('Duplicate selection or product identity.',409)
        ids.add(canonical_sku(proposed_id));candidates.add(candidate['candidate_id']);identities.add(key)
        decision=selection.get('model_decision')
        model=selection.get('model','');evidence=selection.get('model_evidence','')
        if not isinstance(model,str) or len(model.strip())>200 or not isinstance(evidence,str) or len(evidence.strip())>1000:
            raise ReviewProblem('Invalid model or model evidence.')
        if decision=='use_documented':
            documented=source_review['documented_models']
            if not documented:raise ReviewProblem('No model identifier is documented for this candidate.')
            if model.strip() and model.strip() not in documented:raise ReviewProblem('The selected model does not match the source.')
            model=' / '.join(documented)
            evidence=f"Source PDF page {candidate['source_pdf_page']}"
        elif decision=='not_documented':
            if source_review['documented_models']:raise ReviewProblem('A model is documented; approve that model rather than marking it undocumented.')
            if model.strip() or evidence.strip():raise ReviewProblem('Leaving a model undocumented cannot also assign a model or evidence.')
        elif decision=='staff_verified':
            if not model.strip() or len(evidence.strip())<5:raise ReviewProblem('A staff-verified model needs the genuine identifier and supporting document/reference.')
            if source_review['documented_models'] and model.strip() not in source_review['documented_models']:raise ReviewProblem('The verified model conflicts with this documented candidate. Review the source identity separately.')
        else:raise ReviewProblem('Explicitly review the model: use documented, leave undocumented, or staff verified.')
        image_decision=selection.get('image_decision')
        if image_decision not in ('include','omit') or not isinstance(selection.get('include_images',False),bool) or selection.get('include_images',False) != (image_decision=='include'):
            raise ReviewProblem('Explicitly choose to include reviewed source images or omit images.')
        if image_decision=='include' and not candidate['image_paths']:raise ReviewProblem('There is no individually identified source image for this candidate.')
        images=[]
        if selection.get('include_images'):
            if selection.get('images_reviewed') is not True:raise ReviewProblem('Approve image clarity and product association before including source images.')
            for path in candidate['image_paths']:
                image_path=(FOLDER/path).resolve()
                if not image_path.is_relative_to((FOLDER/'images').resolve()):raise ReviewProblem('Invalid source image path.')
                image='data:image/png;base64,'+base64.b64encode(image_path.read_bytes()).decode()
                if not valid_image(image):raise ReviewProblem('A source image exceeds upload controls or is unclear. Import without images and upload a reviewed replacement in Edit metadata.')
                images.append(image)
        doc=prepare_product({'id':proposed_id,'unit':selection.get('unit',''),'name':candidate['name'],
            'category':candidate['category'],'manufacturer':candidate.get('documented_manufacturer') or '',
            'brand':candidate.get('documented_brand') or '',
            'model':model.strip(),
            'description':candidate['description'],'key_features':candidate['key_features'],'specifications':candidate['specifications'],
            'images':images,'quantity':0},provisional=provisional)
        doc['_brochure_identity']=key
        doc['brochure_source']={'sha256':manifest['source_sha256'],'page':candidate['source_pdf_page'],
            'candidate_id':candidate['candidate_id'],'review_notes':note.strip(),
            'model_review':{'decision':decision,'model':model.strip(),'evidence':evidence.strip()},
            'image_review':{'decision':image_decision,'approved':selection.get('images_reviewed') is True}}
        documents.append(doc)
    return documents


def plan(manifest_hash,selections,products):
    return {'actor':g.user['email'],'database':db.name,'manifest':manifest_hash,'selections':digest(selections),'catalog':digest(products)}


@bp.get('/preview')
@require_role()
def review():
    manifest,manifest_hash=load_manifest()
    return jsonify({**preview(manifest,catalog()),'manifest_hash':manifest_hash,'database':db.name})


@bp.get('/source')
@require_role()
def source_pdf():
    manifest,_=load_manifest()
    return send_file(FOLDER/manifest['source_pdf'],as_attachment=True,download_name=manifest['source_pdf'])


@bp.get('/mapping-template')
@require_role()
def mapping_template():
    manifest,_=load_manifest()
    return Response(mapping_csv(manifest,FOLDER),mimetype='text/csv',headers={
        'Content-Disposition':'attachment; filename="staff-mapping-template.csv"'})


@bp.get('/images/<filename>')
@require_role()
def source_image(filename):
    manifest,_=load_manifest()
    paths={image['path'] for image in manifest['images']}
    if 'images/'+filename not in paths:raise ReviewProblem('Source image not found.',404)
    return jsonify(image='data:image/png;base64,'+base64.b64encode((FOLDER/'images'/filename).read_bytes()).decode())


@bp.post('/dry-run')
@require_role('superadmin','subadmin')
def dry_run():
    body=payload();manifest,manifest_hash=load_manifest();products=catalog()
    selections=body.get('selections')
    documents=selected_documents(selections,manifest,products)
    return jsonify(dry_run=True,database=db.name,approval_token=signer().dumps(plan(manifest_hash,selections,products)),
        products=[{'id':d['id'],'name':d['name'],'unit':d['unit'],'brand':d['brand'],'manufacturer':d['manufacturer'],
            'model':d['model'],'model_review':d['brochure_source']['model_review'],
            'image_decision':d['brochure_source']['image_review']['decision'],
            'description':d['description'],'key_features':d['key_features'],'specifications':d['specifications'],
            'quantity':0,'publicPrice':None,'inStock':False,'images':len(d['images'])} for d in documents],
        message='No records written. Review this dry run, then explicitly approve the selected records. New products use the existing catalog visibility default and have no physical stock or public price.')


@bp.post('/approve')
@require_role('superadmin','subadmin')
def approve():
    body=payload()
    if body.get('approved') is not True:raise ReviewProblem('Explicit approval of the selected records is required.')
    key=request.headers.get('Idempotency-Key','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,120}',key):raise ReviewProblem('A valid Idempotency-Key is required.')
    try:token=signer().loads(body.get('approval_token',''),max_age=900)
    except (BadSignature,SignatureExpired,TypeError):raise ReviewProblem('Dry run missing, invalid or expired. Run it again.',409) from None
    manifest,manifest_hash=load_manifest();selections=body.get('selections')
    if token.get('database')!=db.name or token.get('actor')!=g.user['email'] or token.get('manifest')!=manifest_hash or token.get('selections')!=digest(selections):raise ReviewProblem('Target database, selections or source changed. Run a new dry run.',409)
    def run(session):
        old=db.brochure_imports.find_one({'key':key},session=session)
        if old:
            if old['actor_email']!=g.user['email'] or old['selection_hash']!=digest(selections):raise ReviewProblem('Import key already used.',409)
            return old['product_ids']
        products=catalog(session)
        if digest(products)!=token['catalog']:raise ReviewProblem('Catalog changed since the dry run. Review duplicates again.',409)
        documents=selected_documents(selections,manifest,products)
        product_ids=[]
        for doc in documents:
            insert_product_document(doc,session=session)
            product_ids.append(doc['id'])
            db.catalog_events.insert_one({'id':uuid4().hex,'product_id':doc['id'],'action':'brochure_import',
                'source':doc['brochure_source'],'actor_email':g.user['email'],'at':doc['created_at']},session=session)
        db.brochure_imports.insert_one({'key':key,'actor_email':g.user['email'],'source_sha256':manifest['source_sha256'],
            'selection_hash':digest(selections),'product_ids':product_ids,'at':documents[0]['created_at']},session=session)
        return product_ids
    try:
        with db.client.start_session() as session:ids=session.with_transaction(run)
    except DuplicateKeyError:raise ReviewProblem('A selected product was imported concurrently. Refresh the preview.',409) from None
    return jsonify(database=db.name,product_ids=ids,message='Approved products created with zero stock. Receive physical stock separately; public prices remain controlled by Storefront Settings.'),201
