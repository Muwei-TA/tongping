import sqlite3
import time
import httpx
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import identity
from server.db import closing_connection
from server.manage import create_club
from test_api import API, login, new_post


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'test.sqlite',demo=True)) as value:
        yield value


def test_public_responses_do_not_expose_owner_ids_or_internal_intents(client):
    assert 'owner_id' not in client.get(API+'/clubs/animation').json()
    post=new_post(client)
    assert 'client_id' not in post


def test_production_refuses_an_existing_demo_database(tmp_path):
    path=tmp_path/'demo.sqlite'
    create_app(path,demo=True)
    with pytest.raises(ValueError):create_app(path,demo=False,production=True)


def test_demo_refuses_an_existing_real_database(tmp_path,monkeypatch):
    path=tmp_path/'real.sqlite'
    monkeypatch.setattr(identity,'exchange_code',lambda provider,code:'real-subject')
    with TestClient(create_app(path)) as client:
        assert client.post(API+'/auth/code',json={'provider':'wechat','code':'code'}).status_code==200
    with pytest.raises(ValueError):create_app(path,demo=True)


def test_provider_identity_is_scoped_and_sessions_are_hashed(tmp_path,monkeypatch):
    monkeypatch.setattr(identity,'exchange_code',lambda provider,code:'same-subject')
    app=create_app(tmp_path/'real.sqlite')
    with TestClient(app) as client:
        first=client.post(API+'/auth/code',json={'provider':'wechat','code':'one'}).json()
        again=client.post(API+'/auth/code',json={'provider':'wechat','code':'two'}).json()
        qq=client.post(API+'/auth/code',json={'provider':'qq','code':'three'}).json()
        assert first['user']['id']==again['user']['id']
        assert first['user']['id']!=qq['user']['id']
        with closing_connection(app.state.db_path) as db:
            assert not db.execute('SELECT 1 FROM sessions WHERE token_hash=?',(first['token'],)).fetchone()
            assert db.execute('SELECT 1 FROM sessions WHERE token_hash=?',(identity.token_hash(first['token']),)).fetchone()
            cid=create_club(db,first['user']['id'],'真实试点社团','管理员核验后开通','遵守原创与隐私规则')
        profile=client.get(API+'/me',headers={'Authorization':'Bearer '+first['token']}).json()
        assert profile['memberships'][0]['club_id']==cid
        assert profile['memberships'][0]['role']=='owner'


@pytest.mark.parametrize('payload',[[],{'session_key':'must-not-leak'},{'openid':3},{'openid':'x','errcode':40029}])
def test_malformed_provider_response_fails_closed(monkeypatch,payload):
    monkeypatch.setenv('WECHAT_APP_ID','fixture-id');monkeypatch.setenv('WECHAT_APP_SECRET','fixture-secret')
    monkeypatch.setattr(httpx,'get',lambda *a,**k:httpx.Response(200,json=payload,request=httpx.Request('GET','https://provider.test')))
    with pytest.raises(identity.DomainError) as exc:identity.exchange_code('wechat','fixture-code')
    assert exc.value.status==401
    assert 'fixture-secret' not in str(exc.value)


def test_expired_session_is_rejected(client):
    headers=login(client)
    with sqlite3.connect(client.app.state.db_path) as db:db.execute('UPDATE sessions SET expires_at=?',(time.time()-1,))
    assert client.get(API+'/me',headers=headers).status_code==401


def test_media_cannot_be_stolen_from_another_author(client):
    from test_api import image_bytes,post_input
    mid=client.post(API+'/clubs/animation/media',headers=login(client),files={'file':('a.png',image_bytes(),'image/png')}).json()['id']
    response=client.post(API+'/clubs/animation/posts',headers=login(client,'next'),json=post_input(media_id=mid))
    assert response.status_code==422


def test_mcp_surfaces_api_authorization_errors(client,monkeypatch):
    from server import mcp
    monkeypatch.setattr(mcp,'read_api',lambda name,args: (_ for _ in ()).throw(ValueError('API 返回 HTTP 403')))
    result=mcp.handle({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_post','arguments':{'post_id':'forest'}}})
    assert result['result']['isError'] is True
