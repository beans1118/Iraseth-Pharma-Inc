"""Complete, reviewable CSV; staff cells are never inferred from source facts."""
import csv
from io import StringIO
import json

from modules.brochure.assessment import assess, inspect_images

STAFF_FIELDS = ('include_in_batch','staff_approved_sku','staff_approved_selling_unit',
    'model_decision','staff_verified_model','model_evidence','image_decision',
    'images_approved','staff_review_notes','staff_approved','duplicate_reviewed')
SOURCE_FIELDS = ('candidate_id','source_pdf','source_pdf_page','name','category','documented_brand',
    'documented_manufacturer','description','key_features','specifications','source_image_paths',
    'image_review_status','image_validation','documented_models','missing_fields','source_status','approval_status')


def mapping_rows(manifest, folder, previous=None):
    previous=previous or {}
    images={i['path']:i for i in inspect_images(manifest,folder)}
    rows=[]
    for candidate in manifest['candidates']:
        review=assess(candidate)
        if not review['source_ready']:continue
        row={field:candidate.get(field) or '' for field in ('candidate_id','name','category','description','source_pdf_page','documented_brand','documented_manufacturer')}
        row.update(source_pdf=manifest['source_pdf'],source_status=review['source_status'],
            key_features=json.dumps(candidate['key_features'],ensure_ascii=False),
            specifications=json.dumps(candidate['specifications'],ensure_ascii=False),
            source_image_paths=json.dumps(candidate['image_paths'],ensure_ascii=False),
            image_review_status=candidate['image_review_status'],
            image_validation=json.dumps([{k:images[path][k] for k in ('path','upload_valid','low_resolution')} for path in candidate['image_paths']],ensure_ascii=False),
            documented_models=json.dumps(review['documented_models'],ensure_ascii=False),
            missing_fields=json.dumps(review['missing_identity']+review['missing_optional_content'],ensure_ascii=False))
        row.update({field:'' for field in STAFF_FIELDS})
        row.update(include_in_batch='false',model_decision='pending',image_decision='pending',images_approved='false',staff_approved='false',duplicate_reviewed='false')
        old=previous.get(candidate['candidate_id'],{})
        for field in STAFF_FIELDS:
            if field in old:row[field]=old[field]
        if 'image_decision' not in old and old.get('approve_source_images','').strip().lower()=='true':
            row['image_decision']='include'
        row['approval_status']='Staff review recorded; dry run required' if row['staff_approved'].strip().lower()=='true' else 'Pending staff review'
        rows.append(row)
    if set(previous)-{r['candidate_id'] for r in rows}:
        raise ValueError('Existing mapping has unknown or newly blocked candidates. Review it without dropping staff work.')
    return rows


def mapping_csv(manifest, folder, previous=None):
    output=StringIO(newline='');writer=csv.DictWriter(output,fieldnames=SOURCE_FIELDS+STAFF_FIELDS)
    writer.writeheader();writer.writerows(mapping_rows(manifest,folder,previous))
    return '\ufeff'+output.getvalue()


def refresh_mapping_file(path,manifest,folder):
    previous={}
    if path.exists():
        with path.open(encoding='utf-8-sig',newline='') as source:
            for row in csv.DictReader(source):
                key=row.get('candidate_id')
                if not key or key in previous:raise ValueError('Existing mapping contains missing/duplicate candidate keys. It was not overwritten.')
                previous[key]=row
    content=mapping_csv(manifest,folder,previous)
    path.write_text(content,encoding='utf-8',newline='')
