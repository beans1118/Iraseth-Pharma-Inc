"""Ephemeral browser QA fixtures, explicitly locked to iraseth_test.

Scenario configuration arrives on stdin. Cleanup deletes only fixture IDs.
Never use this server for normal operations or connect it to another database.
"""
import atexit
import base64
from datetime import datetime,timezone
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import hmac

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from dotenv import dotenv_values
settings=dotenv_values(BACKEND/'.env.test')
assert settings.get('APP_ENV')=='testing' and settings.get('MONGO_DB_NAME')=='iraseth_test'
assert settings.get('MONGO_URI')=='mongodb://127.0.0.1:27017/?replicaSet=rs0'
for key,value in settings.items():
    if value is not None:os.environ[key]=value
os.environ.update(APP_ENV='testing',MONGO_DB_NAME='iraseth_test',MONGO_URI=settings['MONGO_URI'],BATCH_MODE='false',SMTP_HOST='',EMAIL_ASYNC='false',RATE_LIMIT_LOGIN_PER_MINUTE='10000')
config=json.loads(sys.stdin.readline())
if config.get('uat'):
    # Match the separate dashboard/browser origin for staging-style direct API
    # calls as well as the original same-origin local Vite proxy.
    os.environ['CORS_ORIGINS']='http://127.0.0.1:5174'
from app import app
from extensions import db
from PIL import Image
from utils.security import hash_password
from werkzeug.serving import make_server
assert db.name=='iraseth_test' and db.client.address==('127.0.0.1',27017)
marker=config['marker'];prefix='PYTEST-BROWSER-'+marker
ids=[prefix+f'-{i:03}' for i in range(105)]
pdf_ids=[]
emails=[f'qa-{role}-{marker}@example.invalid' for role in ('superadmin','admin','subadmin')]
refs=[config['reference'],config['decline_reference']]
now=datetime.now(timezone.utc).isoformat()


def own_product(field):
    return {'$or':[{field:{'$regex':'^'+prefix}},{field:{'$in':pdf_ids}}]}


def cleanup():
    assert db.name=='iraseth_test'
    own_refs=[q['id'] for q in db.quotations.find({'$or':[{'id':{'$in':refs}},own_product('items.id')]},{'id':1})]
    linked=[o['id'] for o in db.orders.find({'$or':[{'source_inquiry_id':{'$in':own_refs}},own_product('lines.id')]},{'id':1})]
    invoice_ids=[i['id'] for i in db.invoices.find({'$or':[{'order_id':{'$in':linked}},own_product('lines.id')]},{'id':1})]
    db.sessions.delete_many({'user_email':{'$in':emails}})
    db.users.delete_many({'email':{'$in':emails}})
    db.orders.delete_many({'id':{'$in':linked}})
    db.quotations.delete_many({'id':{'$in':own_refs}})
    db.quotation_events.delete_many({'reference':{'$in':own_refs}})
    db.tracking_challenges.delete_many({'reference':{'$in':own_refs}})
    db.communication_requests.delete_many({'reference':{'$in':own_refs}})
    db.invoice_events.delete_many({'invoice_id':{'$in':invoice_ids}})
    db.invoices.delete_many({'id':{'$in':invoice_ids}})
    db.stock_reservations.delete_many(own_product('product_id'))
    db.stock_movements.delete_many(own_product('product_id'))
    db.inventory_operations.delete_many({'actor_email':{'$in':emails}})
    db.support_messages.delete_many({'order_id':{'$in':linked}})
    db.support_threads.delete_many({'order_id':{'$in':linked}})
    db.support_challenges.delete_many({'order_id':{'$in':linked}})
    db.support_sessions.delete_many({'order_id':{'$in':linked}})
    db.catalog_events.delete_many(own_product('product_id'))
    db.inventory_batches.delete_many(own_product('product_id'))
    db.products.delete_many(own_product('id'))
    db.brochure_imports.delete_many({'product_ids':{'$in':[prefix+'-BROCHURE']}})


atexit.register(cleanup)
try:
    pictures=[]
    for color in ('white','red','blue'):
        output=BytesIO();Image.new('RGB',(200,200),color).save(output,format='PNG')
        pictures.append('data:image/png;base64,'+base64.b64encode(output.getvalue()).decode())
    for i,pid in enumerate(ids):
        db.products.insert_one({'id':pid,'name':f'Browser QA {marker} Product {i:03}',
            'description':'Documented browser QA description.','category':'Browser QA '+marker,
            'manufacturer':'QA test brand','unit':'Box','quantity':5 if i==0 and not config.get('uat') else 0,'baseline_qty':5 if i==0 and not config.get('uat') else 0,
            'price':12.5,'storefront_visible':True,'storefront_price':None,'created_at':now,
            'image':pictures[0] if i==0 else '', 'images':pictures if i==0 else [],
            'key_features':['Documented feature'] if i==0 else [],'specifications':[{'label':'Documented specification','value':'Source value'}] if i==0 else []})
    for role,email in zip(('superadmin','admin','subadmin'),emails):
        db.users.insert_one({'email':email,'name':'QA '+role,'role':role,'password_hash':hash_password(config['password'])})
    for ref in refs:
        db.quotations.insert_one({'id':ref,'idempotency_key':ref,'status':'New','created_at':now,'updated_at':now,
            'fullName':'Private Browser Customer','email':'qa-customer@example.invalid','phone':'Private phone','company':'Private organization','notes':'Private staff note',
            'items':[{'id':ids[0],'name':'Test medical product','quantity':1,'public_price_at_inquiry':None}]})
    if config.get('uat'):
        from config import Config
        from datetime import timedelta
        from modules.inventory import service as inventory
        from flask import request, jsonify
        # Isolated fixture injection follows the batch API integration tests:
        # leave production startup/migration guards unchanged, then enable the
        # actual batch services for this explicitly test-only process.
        Config.BATCH_MODE=True
        if config.get('pdf_products'):
            from modules.brochure.service import load_manifest,FOLDER,provisional_product_id
            from tools.add_pdf_products import build_plan,apply_plan
            manifest,_=load_manifest()
            image_review=json.loads((FOLDER/'pdf-product-image-review.json').read_text(encoding='utf-8'))
            candidate=next(c for c in manifest['candidates'] if c['name']=='Microfusion Set')
            pdf_id=provisional_product_id(manifest,candidate)
            # Refuse to claim/clean a record belonging to another local session.
            assert not db.products.find_one({'id':pdf_id}), 'PDF browser fixture already exists; stop and inspect.'
            pdf_ids.append(pdf_id)
            plan,_=build_plan(manifest,[candidate['candidate_id']],image_review)
            apply_plan(manifest,[candidate['candidate_id']],image_review,plan,emails[2])
        if config.get('image_candidates'):
            from modules.brochure.service import load_manifest,FOLDER,provisional_product_id
            from tools.add_pdf_products import build_plan,apply_plan
            manifest,_=load_manifest()
            image_review=json.loads((FOLDER/'pdf-product-image-review.json').read_text(encoding='utf-8'))
            proposal=json.loads((BACKEND.parent/'docs/product-ui-cleanup/image-mapping-proposal.json').read_text(encoding='utf-8'))
            selected=[next(c for c in manifest['candidates'] if c['name']==item['name']) for item in proposal['products']]
            claimed=[provisional_product_id(manifest,c) for c in selected]
            assert not db.products.count_documents({'id':{'$in':claimed}}), 'Image fixtures already exist; stop and inspect.'
            pdf_ids.extend(claimed)
            keys=[c['candidate_id'] for c in selected]
            plan,_=build_plan(manifest,keys,image_review)
            apply_plan(manifest,keys,image_review,plan,emails[2])
        # Give each synthetic browser run its own client-rate-limit namespace.
        # Keep real limiter behavior and existing test counters intact.
        original_wsgi=app.wsgi_app
        fixture_address='127.'+'.'.join(str(int(marker[i:i+2],16)) for i in (0,2,4))
        def isolated_client(environ,start_response):
            environ['REMOTE_ADDR']=fixture_address
            return original_wsgi(environ,start_response)
        app.wsgi_app=isolated_client
        for lot,days,qty in [('UAT-EARLY',30,2),('UAT-LATER',90,3)]:
            inventory.receive(ids[0],lot,(datetime.now(timezone.utc).date()+timedelta(days=days)).isoformat(),qty,emails[2],prefix+'-'+lot)
        mailbox=[]
        def capture_mail(to,subject,body):
            mailbox.append({'to':to,'subject':subject,'body':body})
            return True
        def qa_authorized():
            return bool(config.get('qa_token')) and hmac.compare_digest(request.headers.get('X-QA-Token',''),config['qa_token'])
        @app.get('/__qa/state')
        def qa_state():
            if not qa_authorized():return jsonify(error='Test token required.'),403
            inquiry_rows=list(db.quotations.find(own_product('items.id'),{'_id':0}))
            order_rows=list(db.orders.find(own_product('lines.id'),{'_id':0}))
            return jsonify(pdf_product_ids=pdf_ids,products=list(db.products.find(own_product('id'),{'_id':0,'id':1,'name':1,'quantity':1,'images':1,'key_features':1,'sku':1,'identity_status':1,'unit':1,'price':1,'model':1,'description':1,'category':1,'brand':1,'manufacturer':1,'specifications':1})),
                batches=list(db.inventory_batches.find(own_product('product_id'),{'_id':0})),
                reservations=list(db.stock_reservations.find(own_product('product_id'),{'_id':0})),
                inquiries=inquiry_rows,orders=order_rows,
                invoices=list(db.invoices.find(own_product('lines.id'),{'_id':0})),mail=mailbox)
        @app.post('/__qa/enable-memory-mail')
        def enable_memory_mail():
            if not qa_authorized():return jsonify(error='Test token required.'),403
            from modules.tracking import routes as tracking
            from modules.support import routes as support
            from utils import email as email_service
            Config.SMTP_HOST='isolated-memory-mailer'
            tracking.send_email=capture_mail;support.send_email=capture_mail;email_service.send_email=capture_mail
            return jsonify(mode='Isolated in-memory test double; no external email delivery')
    server=make_server('127.0.0.1',5011,app,threaded=True)
    @app.post('/__qa/shutdown')
    def shutdown():
        from threading import Thread
        Thread(target=server.shutdown,daemon=True).start()
        return {'ok':True}
    print('Browser QA ready; isolated database iraseth_test',flush=True)
    server.serve_forever()
finally:
    cleanup()
    atexit.unregister(cleanup)
