"""Shared product metadata validation; never reads or writes inventory."""
import base64
import binascii
from io import BytesIO
import warnings
import unicodedata

from PIL import Image, UnidentifiedImageError

MAX_IMAGES = 8
MAX_IMAGE_BYTES = 200000
MAX_PIXELS = 16_000_000
PENDING_UNIT = 'PENDING UNIT CONFIRMATION'
TEMP_ID_PREFIX = 'TMP-PDF-'
IDENTITY_REQUIRED = 'Confirm the genuine SKU and selling unit in Edit metadata before stock or order operations.'


def identity_pending(product):
    status = product.get('identity_status')
    return status not in (None, 'confirmed') or canonical_sku(str(product.get('unit') or '')) == canonical_sku(PENDING_UNIT) or (status == 'confirmed' and (
        not str(product.get('sku') or '').strip() or not str(product.get('unit') or '').strip() or
        canonical_sku(str(product.get('sku') or '')).startswith(TEMP_ID_PREFIX.lower()) or
        canonical_sku(str(product.get('unit') or '')) == canonical_sku(PENDING_UNIT)))


def identifier_keys(product):
    return {canonical_sku(str(value)) for value in (product.get('id'), product.get('sku')) if value}


def canonical_sku(value):
    """Comparison only: retain the genuine identifier exactly as staff entered it."""
    return unicodedata.normalize('NFKC', value).strip().casefold()


def valid_image(value):
    if value in (None, ''):
        return True
    if not isinstance(value, str) or len(value) > 275000:
        return False
    mime_formats = {'data:image/png;base64': 'PNG', 'data:image/jpeg;base64': 'JPEG', 'data:image/webp;base64': 'WEBP'}
    try:
        prefix, encoded = value.split(',', 1)
        if prefix not in mime_formats:
            return False
        payload = base64.b64decode(encoded, validate=True)
        if not payload or len(payload) > MAX_IMAGE_BYTES:
            return False
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as image:
                if image.format != mime_formats[prefix] or image.width * image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
                    return False
                image.verify()
            # Verify headers and actual decodability, with bounded dimensions.
            with Image.open(BytesIO(payload)) as image:
                image.load()
        return True
    except (ValueError, binascii.Error, UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return False


def metadata(data, existing=None):
    """Return only validated metadata updates; canonical first gallery image is primary."""
    if not isinstance(data, dict):
        raise ValueError('Product data must be a JSON object.')
    result = {}
    for key, maximum in [('id', 80), ('name', 200), ('description', 12000), ('category', 160), ('unit', 80), ('manufacturer', 200), ('brand', 200), ('model', 200)]:
        if key in data:
            value = data[key]
            if not isinstance(value, str) or len(value.strip()) > maximum or (key in ('id','name','category','unit') and not value.strip()):
                raise ValueError(f'Invalid {key}: text of at most {maximum} characters required.')
            if key == 'id' and any(character in value for character in '/\\?#'):
                raise ValueError('Product ID cannot contain /, \\, ? or #.')
            result[key] = value.strip()
    if 'key_features' in data:
        features = data['key_features']
        if not isinstance(features, list) or len(features) > 40 or any(not isinstance(f, str) or not f.strip() or len(f.strip()) > 1000 for f in features):
            raise ValueError('Key features must contain at most 40 non-empty text entries, up to 1000 characters each.')
        result['key_features'] = [f.strip() for f in features]
    if 'specifications' in data:
        specs = data['specifications']
        if not isinstance(specs, list) or len(specs) > 60:
            raise ValueError('Specifications must contain at most 60 label/value entries.')
        for spec in specs:
            if not isinstance(spec, dict) or set(spec) != {'label','value'} or any(not isinstance(spec[k], str) or not spec[k].strip() or len(spec[k].strip()) > maximum for k, maximum in [('label',160),('value',2000)]):
                raise ValueError('Each specification needs a label (max 160 characters) and value (max 2000 characters).')
        result['specifications'] = [{'label': s['label'].strip(), 'value': s['value'].strip()} for s in specs]
    if 'images' in data:
        images = data['images']
        if not isinstance(images, list) or len(images) > MAX_IMAGES or any(not isinstance(i, str) or not i or not valid_image(i) for i in images):
            raise ValueError('Use up to 8 valid, static PNG, JPEG or WebP images, at most 200 KB and 16 megapixels each.')
        if len(set(images)) != len(images):
            raise ValueError('Remove duplicate gallery images.')
        result['images'] = images
        result['image'] = images[0] if images else ''
    elif 'image' in data:
        image = data['image']
        if not valid_image(image):
            raise ValueError('Product image must be a valid static PNG, JPEG or WebP under 200 KB and 16 megapixels.')
        old = (existing or {}).get('images') or []
        result['image'] = image or ''
        result['images'] = ([image] + [i for i in old[1:] if i != image]) if image else []
    return result


def public_metadata(product):
    """Allowlist the structured public fields; malformed legacy metadata stays private."""
    result = {'keyFeatures': [], 'specifications': [], 'imageUrls': []}
    for internal, public in [('key_features','keyFeatures'), ('specifications','specifications')]:
        try:
            result[public] = metadata({internal: product.get(internal, [])})[internal]
        except ValueError:
            pass
    images = product.get('images')
    if not isinstance(images, list):
        images = []
    images = [i for i in images[:MAX_IMAGES] if i and valid_image(i)]
    legacy = product.get('image')
    if not images and legacy and valid_image(legacy):
        images = [legacy]
    result['imageUrls'] = list(dict.fromkeys(images))
    return result
