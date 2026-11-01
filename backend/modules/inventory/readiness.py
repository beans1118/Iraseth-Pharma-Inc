"""Fail-closed readiness checks before activating batch inventory writes."""
from datetime import date


def check_ready(database, require_marker=True):
    if require_marker and not database.system_metadata.find_one({'_id': 'batch_mode_ready', 'approved': True}):
        raise RuntimeError('Batch mode not approved: run reconciliation and explicit activation first.')
    if database.inventory_batches.count_documents({'unverified': True}):
        raise RuntimeError('Unverified legacy batches remain. Reconcile lot identity and expiration first.')
    today = date.today().isoformat()
    for batch in database.inventory_batches.find({}, {'id': 1, 'on_hand': 1, 'reserved': 1,
                                                       'condition': 1, 'expires_on': 1}):
        stock = batch.get('on_hand')
        reserved = batch.get('reserved')
        if type(stock) is not int or type(reserved) is not int or stock < 0 or reserved < 0 or reserved > stock:
            raise RuntimeError(f'Invalid batch balance: {batch.get("id")}')
        if reserved and (batch.get('condition') != 'available' or batch.get('expires_on', '') < today):
            raise RuntimeError(f'Restricted batch has active reserved units: {batch.get("id")}')
    for product in database.products.find({}, {'id': 1, 'quantity': 1}):
        amount = sum(b['on_hand'] for b in database.inventory_batches.find({'product_id': product['id']}, {'on_hand': 1}))
        if amount != product.get('quantity', 0):
            raise RuntimeError(f'Product/batch physical inventory mismatch: {product["id"]}')
    return True
