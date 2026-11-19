"""Pure matching and source loading; no writes or import-time database actions."""
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from modules.brochure.assessment import assess
from modules.product_metadata import TEMP_ID_PREFIX, PENDING_UNIT

FOLDER = Path(__file__).resolve().parents[3] / 'docs' / 'brochure'


def provisional_product_id(manifest, candidate):
    return TEMP_ID_PREFIX + manifest['source_sha256'][:10].upper() + '-' + candidate['candidate_id'].upper()


def provisional_selections(manifest, candidate_ids, image_review, duplicate_reviews=None):
    """One-time source preparation, not a second product model/catalog."""
    if not 1<=len(candidate_ids)<=30 or len(candidate_ids)!=len(set(candidate_ids)):
        raise ValueError('Select 1–30 distinct source products; start with 1–5.')
    if image_review.get('source_sha256') != manifest['source_sha256']:
        raise ValueError('Image review does not match this source PDF.')
    by_id={c['candidate_id']:c for c in manifest['candidates']}
    duplicate_reviews=duplicate_reviews or {}
    if set(duplicate_reviews)-set(candidate_ids) or any(not isinstance(note,str) or not 5<=len(note.strip())<=1000 for note in duplicate_reviews.values()):
        raise ValueError('Duplicate reviews must name selected candidates and document the exact distinction.')
    result=[]
    for key in candidate_ids:
        candidate=by_id.get(key)
        if not candidate or not assess(candidate)['source_ready']:
            raise ValueError('Source is ambiguous, a family/offering, or unknown; no automatic product creation is permitted.')
        reviewed=image_review.get('include_images_for',{}).get(key)
        if reviewed and (reviewed.get('name')!=candidate['name'] or reviewed.get('paths')!=candidate['image_paths'] or reviewed.get('page')!=candidate['source_pdf_page']):
            raise ValueError('Image association changed; review the exact product panel again.')
        include=bool(reviewed)
        result.append({'candidate_id':key,'id':provisional_product_id(manifest,candidate),'unit':PENDING_UNIT,
            'identity_mode':'provisional','review_confirmed':True,'duplicate_reviewed':key in duplicate_reviews,
            'review_notes':'Source-clear PDF product prepared for the existing products collection under the current integration request. Genuine SKU and selling unit remain unconfirmed; inventory/order operations must stay blocked.'+(' Duplicate review: '+duplicate_reviews[key].strip() if key in duplicate_reviews else ''),
            'model_decision':'use_documented' if assess(candidate)['documented_models'] else 'not_documented',
            'image_decision':'include' if include else 'omit','include_images':include,'images_reviewed':include})
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',',':'), ensure_ascii=True).encode()).hexdigest()


def normalized(value):
    value = unicodedata.normalize('NFKD', str(value or '')).casefold()
    return ' '.join(re.findall(r'[a-z0-9]+', value))


def identity(name, brand):
    return normalized(name) + '|' + normalized(brand)


def load_manifest():
    raw = (FOLDER/'import-manifest.json').read_bytes()
    manifest = json.loads(raw)
    pdf = FOLDER / manifest['source_pdf']
    if pdf.parent.resolve() != FOLDER.resolve() or hashlib.sha256(pdf.read_bytes()).hexdigest() != manifest['source_sha256']:
        raise ValueError('Brochure source hash mismatch. Staff must review the source before importing.')
    return manifest, hashlib.sha256(raw).hexdigest()


def classify(candidate, products):
    name, brand = normalized(candidate['name']), normalized(candidate.get('documented_brand'))
    exact, possible = [], []
    for product in products:
        pname, pbrand = normalized(product.get('name')), normalized(product.get('brand') or product.get('manufacturer'))
        if candidate.get('sku') and normalized(candidate['sku']) == normalized(product['id']):
            exact.append(product)
        elif name == pname:
            (exact if not brand or not pbrand or brand == pbrand else possible).append(product)
        elif pname and (SequenceMatcher(None,name,pname).ratio() >= .84 or name.startswith(pname+' ') or pname.startswith(name+' ')):
            possible.append(product)
    matches = exact or possible
    match_status = 'Existing' if len(exact) == 1 else 'Ambiguous' if matches else 'New'
    return {'match_status': match_status, 'existing_identity_count': len(exact),
            'status': match_status if matches else 'Needs Review' if candidate.get('gaps') or candidate.get('review_notes') else 'New',
            'matches': [{'id':p['id'],'name':p.get('name',''),'brand':p.get('brand',''),'manufacturer':p.get('manufacturer','')} for p in matches]}


def preview(manifest, products):
    candidates=[{**item, **classify(item, products), **assess(item)} for item in manifest['candidates']]
    return {'source_pdf':manifest['source_pdf'],'source_sha256':manifest['source_sha256'],
        'page_count':manifest['page_count'],'total':len(candidates),'type_counts':dict(Counter(c['candidate_type'] for c in candidates)),
        'status_counts':dict(Counter(c['status'] for c in candidates)),
        'match_counts':dict(Counter(c['match_status'] for c in candidates)),
        'source_counts':dict(Counter(c['source_status'] for c in candidates)),
        'source_ready_count':sum(c['source_ready'] for c in candidates),
        'ready_to_import_count':sum(c['ready_to_import'] for c in candidates),
        'candidates':candidates}
