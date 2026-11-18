"""Technical source review, kept separate from staff identity/approval decisions.

Clear source means the existing sanitized transcription identifies an item;
it does not assign a SKU/unit, certify claims, approve images or authorize an
active-database insert. Missing content is never filled with invented values.
"""
from pathlib import Path
import base64

from modules.product_metadata import valid_image


def assess(candidate):
    name = candidate['name']
    models = [s['value'] for s in candidate.get('specifications', []) if s.get('label') == 'Model as printed']
    holds = []
    if not candidate.get('importable') or candidate.get('candidate_type') in ('product_family', 'equipment_family', 'service_or_offering'):
        holds.append('Identify a specific sellable product/model; this record is a family or offering.')
    if name == 'Glucoseth':
        holds.append('Resolve the conflicting power information and verify the exact glucose-meter model against the supplier source.')
    if name.endswith('PUR Catheter Option'):
        holds.append('The exact gauge for the PUR option is not documented; do not infer a gauge/material combination.')
    if any(word in name for word in ('Trachomatics', 'Hepatits', 'Chikugunya', '(Variety)')):
        holds.append('Confirm the ambiguous printed name or unspecified variant; do not silently correct medical identity.')
    if candidate.get('documented_diagnostic_category') == 'Hepatitis Markers' and any(word in name for word in ('HIV', 'Syphilis')):
        holds.append('Confirm the customer-facing diagnostic category; preserve the original source grouping as provenance.')
    missing = []
    if not candidate.get('sku'): missing.append('Staff-approved SKU / product ID')
    if not candidate.get('unit'): missing.append('Staff-approved selling unit')
    return {
        'source_status': 'Source clarification required' if holds and candidate.get('importable') else 'Family / offering' if holds else 'Source clear',
        'source_ready': not holds,
        'source_holds': holds,
        'missing_identity': missing,
        'identity_ready': not missing,
        # This field deliberately does not infer staff approval from source review.
        'ready_to_import': not holds and not missing and candidate.get('approved') is True,
        'staff_approval_required': candidate.get('approved') is not True,
        'documented_models': models,
        'model_status': 'Documented model identifier' if models else 'Model identifier not documented',
        'missing_optional_content': [label for key, label in (
            ('description', 'Description'), ('documented_manufacturer', 'Manufacturer'),
            ('key_features', 'Key features'), ('specifications', 'Specifications'),
            ('image_paths', 'Individually identified image')) if not candidate.get(key)] + ([] if models else ['Model identifier']),
    }


def inspect_images(manifest, folder):
    """Technical eligibility only; staff still approve clarity and association."""
    result = []
    for item in manifest.get('images', []):
        path = (folder / item['path']).resolve()
        if not path.is_relative_to((folder / 'images').resolve()):
            raise ValueError('Invalid image evidence path.')
        payload = path.read_bytes()
        valid = valid_image('data:image/png;base64,' + base64.b64encode(payload).decode())
        result.append({**item, 'upload_valid': valid,
            'low_resolution': min(item['width'], item['height']) < 150,
            'approved_for_active_catalog': False})
    return result
