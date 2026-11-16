from copy import deepcopy
import runpy
from pathlib import Path
import pytest
from config import Config
from tools.initialize_staging import assert_empty, validate_accounts, initialize
from utils.deployment import validate_staging_target


@pytest.mark.parametrize('env,name,uri', [
    ('development','iraseth_staging','mongodb+srv://sample.mongodb.net/'),
    ('production','iraseth_dev','mongodb+srv://sample.mongodb.net/'),
    ('production','iraseth_test','mongodb+srv://sample.mongodb.net/'),
    ('production','iraseth_staging','mongodb://127.0.0.1:27017/?replicaSet=rs0'),
    ('production','iraseth_staging','mongodb+srv://sample.mongodb.net.evil.invalid/'),
])
def test_staging_refuses_local_or_wrong_targets(env,name,uri):
    with pytest.raises(ValueError):validate_staging_target(env,name,uri)


def test_staging_accepts_isolated_atlas_target():
    validate_staging_target('production','iraseth_staging','mongodb+srv://sample.mongodb.net/iraseth_staging?retryWrites=true&w=majority')


def test_staging_guard_runs_before_production_bypass(monkeypatch):
    monkeypatch.setattr(Config,'DEPLOYMENT_ENVIRONMENT','staging')
    with pytest.raises(ValueError,match='Staging requires'):Config.validate_production()


def test_bootstrap_refuses_placeholder_or_reused_passwords():
    rows=[{'email':f'{role}@example.invalid','name':role,'role':role,'password':'Distinct fixture '+role+' 123!'} for role in ('superadmin','admin','subadmin')]
    validate_accounts(rows)
    bad=deepcopy(rows);bad[0]['password']='REPLACE_WITH_A_REAL_PASSWORD'
    with pytest.raises(ValueError,match='genuine staff passwords'):validate_accounts(bad)
    bad=deepcopy(rows);bad[1]['password']=bad[0]['password']
    with pytest.raises(ValueError,match='own password'):validate_accounts(bad)


def test_bootstrap_emptiness_guard_is_read_only_and_refuses_existing(test_db,product_factory):
    pid=product_factory();before=test_db.products.find_one({'id':pid})
    with pytest.raises(ValueError,match='already contains'):assert_empty(test_db,['products'])
    assert test_db.products.find_one({'id':pid})==before


def test_initializer_function_also_refuses_actual_local_test_database(test_db):
    with pytest.raises(ValueError,match='restricted to iraseth_staging'):initialize(test_db,[])


def test_initializer_default_performs_only_reads():
    from contextlib import nullcontext
    from types import SimpleNamespace
    class ReadOnlyDatabase:
        name='iraseth_staging'
        client=SimpleNamespace(admin=SimpleNamespace(command=lambda _: {'setName':'atlas-fixture','logicalSessionTimeoutMinutes':30}),
            start_session=lambda: nullcontext(SimpleNamespace(start_transaction=lambda: nullcontext())))
        def list_collection_names(self):return []
        def __getitem__(self,name):return SimpleNamespace(count_documents=lambda *args,**kwargs:0)
    rows=[{'email':f'{role}@example.invalid','name':role,'role':role,'password':'Distinct fixture '+role+' 123!'} for role in ('superadmin','admin','subadmin')]
    assert 'No indexes, accounts or readiness marker written' in initialize(ReadOnlyDatabase(),rows)


def test_production_guards_accept_real_settings_and_reject_bypasses(monkeypatch):
    settings={'APP_ENV':'production','IS_PRODUCTION':True,'DEPLOYMENT_ENVIRONMENT':'staging',
        'MONGO_DB_NAME':'iraseth_staging','MONGO_URI':'mongodb+srv://fixture.mongodb.net/',
        'JWT_SECRET':'strong-unique-fixture-secret-for-configuration-tests',
        'CORS_ORIGINS':['https://staff.example.invalid'],'SOCKET_AUTH_REQUIRED':True,'FLASK_DEBUG':False,
        'SEED_USERS':[{'password':'Unique fixture password '+role} for role in ('superadmin','admin','subadmin')]}
    for name,value in settings.items():monkeypatch.setattr(Config,name,value)
    Config.validate_production()
    monkeypatch.setattr(Config,'SOCKET_AUTH_REQUIRED',False)
    with pytest.raises(RuntimeError,match='SOCKET_AUTH_REQUIRED'):Config.validate_production()
    monkeypatch.setattr(Config,'SOCKET_AUTH_REQUIRED',True)
    monkeypatch.setattr(Config,'JWT_SECRET','REPLACE_WITH_UNIQUE_RANDOM_64_HEX_SECRET')
    with pytest.raises(RuntimeError,match='JWT_SECRET'):Config.validate_production()


def test_gunicorn_config_has_threading_single_worker_and_render_port(monkeypatch):
    monkeypatch.setenv('PORT','10555')
    config=runpy.run_path(str(Path(__file__).resolve().parents[1]/'gunicorn.conf.py'))
    assert config['bind']=='0.0.0.0:10555'
    assert config['worker_class']=='gthread' and config['workers']==1
    assert config['threads']>=2 and config['preload_app'] is False
    assert Path(config['chdir']).name=='backend'


def test_dashboard_preflight_and_disallowed_origin(client):
    origin=next((o for o in Config.CORS_ORIGINS if o!='*'),'https://staff.example.invalid')
    response=client.options('/api/products',headers={'Origin':origin,'Access-Control-Request-Method':'POST',
        'Access-Control-Request-Headers':'authorization,content-type,idempotency-key,x-support-token'})
    assert response.status_code==200
    assert response.headers['Access-Control-Allow-Origin']==origin
    allowed=response.headers['Access-Control-Allow-Headers'].lower()
    assert all(key in allowed for key in ('authorization','content-type','idempotency-key','x-support-token'))
    if '*' not in Config.CORS_ORIGINS:
        denied=client.options('/api/products',headers={'Origin':'https://untrusted.example.invalid','Access-Control-Request-Method':'POST'})
        assert 'Access-Control-Allow-Origin' not in denied.headers
