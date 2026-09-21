"""Actual stdio -> HTTP -> authorization integration, with a temporary live API."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def live_api(tmp_path_factory):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    path=tmp_path_factory.mktemp('live')/'test.sqlite'
    process=subprocess.Popen([sys.executable,'-m','server','--demo','--db',str(path),'--port',str(port)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                if httpx.get(base+'/api/v1/health',timeout=.5).status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.1)
        else:raise RuntimeError('Test API did not start')
        yield base
    finally:
        process.terminate();process.wait(timeout=10)


@pytest.mark.parametrize('persona,is_error',[('member',False),('outsider',True)])
def test_real_mcp_uses_caller_membership(live_api,persona,is_error):
    session=httpx.post(live_api+'/api/v1/auth/demo',json={'persona':persona}).json()
    env={**os.environ,'TONGPING_API_URL':live_api,'TONGPING_TOKEN':session['token']}
    messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
              {'jsonrpc':'2.0','method':'notifications/initialized'},
              {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'get_post','arguments':{'post_id':'forest'}}}]
    process=subprocess.run([sys.executable,'-m','server.mcp'],input='\n'.join(json.dumps(m) for m in messages)+'\n',text=True,capture_output=True,env=env,cwd=ROOT,timeout=20)
    assert process.returncode==0
    response=json.loads(process.stdout.splitlines()[-1])['result']
    assert response['isError'] is is_error
    assert ('森林里的慢镜头' in response['content'][0]['text']) is (not is_error)
