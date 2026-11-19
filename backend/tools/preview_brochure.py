"""Read-only matching against the configured catalog. Never imports Flask app,
creates indexes, writes to MongoDB, imports products, or touches inventory.
"""
from pathlib import Path
import json
import sys

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from dotenv import dotenv_values
from pymongo import MongoClient
from modules.brochure.service import FOLDER, load_manifest, preview


def main():
    settings=dotenv_values(BACKEND/'.env')
    name=settings.get('MONGO_DB_NAME') or 'iraseth_pharma'
    client=MongoClient(settings.get('MONGO_URI') or 'mongodb://127.0.0.1:27017',serverSelectionTimeoutMS=5000)
    products=list(client[name].products.find({}, {'_id':0,'id':1,'name':1,'brand':1,'manufacturer':1}).sort('id',1))
    manifest,manifest_hash=load_manifest()
    report=preview(manifest,products)
    report.update(database=name,catalog_records_read=len(products),read_only=True,manifest_hash=manifest_hash)
    (FOLDER/'catalog-match-review.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ['database','catalog_records_read','total','type_counts','status_counts','match_counts','read_only']},indent=2))
    client.close()


if __name__=='__main__':main()
