"""Browser workflows against a real temporary API/database.

Default: native browser HTTP. --bridge: render the same local UI source offline
and bridge fetch through Python HTTP, for environments forbidding browser URL
navigation. This never changes browser policy and is not mini-program testing.
"""
import argparse
import base64
from io import BytesIO
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import httpx
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def bridge_page(page, base):
    def exchange(url, options):
        if not url.startswith('/api/v1/'):
            raise ValueError('Test bridge is restricted to the local application API')
        kwargs = {"headers": options.get("headers", {}), "timeout": 15}
        if options.get("multipart"):
            kwargs["files"] = [(v["name"], (v["filename"], base64.b64decode(v["data"]), v["type"])) for v in options["multipart"]]
        elif options.get("body") is not None:
            kwargs["content"] = options["body"]
        response = httpx.request(options.get('method', 'GET'), base + url, **kwargs)
        return {"status": response.status_code, "headers": dict(response.headers), "body": base64.b64encode(response.content).decode()}
    page.expose_function('_testApiBridge', exchange)
    bridge = r'''window.fetch = async (url, options={}) => {
      const value = {...options};
      if (options.body instanceof FormData) {
        value.multipart = [];
        for (const [name,file] of options.body.entries()) {
          const bytes = new Uint8Array(await file.arrayBuffer());
          let raw=''; for (const byte of bytes) raw += String.fromCharCode(byte);
          value.multipart.push({name,filename:file.name,type:file.type,data:btoa(raw)});
        }
        delete value.body;
      }
      const response = await window._testApiBridge(url,value);
      const bytes = Uint8Array.from(atob(response.body),c=>c.charCodeAt(0));
      return new Response(response.status===204 ? null : bytes,{status:response.status,headers:response.headers});
    };'''
    sources = []
    for name in ('api.js', 'views.js', 'pages.js', 'app.js'):
        source = (ROOT / 'web' / name).read_text()
        source = re.sub(r'^import .*?;\n', '', source, flags=re.M)
        source = re.sub(r'^export ', '', source, flags=re.M)
        sources.append(source)
    script = '\n'.join(sources)
    art = (ROOT / 'web/forest.svg').read_text().strip().replace('<svg ', '<svg class="cover" role="img" aria-label="几何森林演示作品" ')
    script = re.sub(r'<img[^>]*src="/forest.svg"[^>]*>', lambda _: art, script)
    html = (ROOT / 'web/index.html').read_text()
    html = re.sub(r'<script[^>]*src="/app.js"[^>]*></script>', '', html)
    html = html.replace('<link rel="stylesheet" href="/style.css">', '<style>' + (ROOT / 'web/style.css').read_text() + '</style>')
    html = html.replace('</body>', '<script>' + bridge + '\n(async()=>{' + script + '\n})().catch(console.error);</script></body>')
    page.set_content(html)


def run_workflows(page, output):
    checks = []
    def record(name):
        checks.append(name)
        print('PASS:', name, flush=True)
    def route(value):
        page.evaluate('(value)=>{history.pushState(null,"",value);dispatchEvent(new PopStateEvent("popstate"))}', value)
    def sign_in(persona):
        if page.locator('[data-action="logout"]').count() == 0 and page.locator('#account').inner_text() != '登录':
            route('#profile')
        if page.locator('#account').inner_text() != '登录':
            page.locator('[data-action="logout"]').click()
        page.locator('[name="persona"]').wait_for()
        page.locator('[name="persona"]').select_option(persona)
        page.get_by_role('button', name='进入演示社团').click()
        page.locator('#main h1').wait_for()
        expect(page.locator('#account')).not_to_have_text('登录')
    def layout(value, label, widths=(320, 390)):
        """Open a route at phone widths and assert the document does not overflow."""
        for width in widths:
            page.set_viewport_size({'width': width, 'height': 900})
            route(value)
            expect(page.locator('#main .state.loading')).to_have_count(0)
            page.locator('#main h1').first.wait_for()
            overflow = page.evaluate('document.documentElement.scrollWidth - innerWidth')
            assert overflow <= 1, f'{label} overflows a {width}px viewport by {overflow}px'
            record(f'{label} has no horizontal overflow at {width}px')
        page.set_viewport_size({'width': 1440, 'height': 1100})
    page.on('dialog', lambda dialog: dialog.accept())
    sign_in('member')
    page.get_by_role('heading', name='今天，也有新的灵感。').wait_for()
    page.get_by_role('link', name='作品', exact=True).click()
    page.get_by_role('heading', name='森林里的慢镜头', exact=False).wait_for()
    page.get_by_role('link', name='全部', exact=True).click()
    page.get_by_role('heading', name='今天，也有新的灵感。').wait_for()
    record('member signs in, switches category and returns to the complete private feed')
    page.screenshot(path=str(output / 'desktop.png'), full_page=True)
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), width
        if width == 390:
            page.screenshot(path=str(output / 'mobile.png'), full_page=True)
        record(f'feed has no horizontal overflow at {width}px')
    route('#compose')
    page.locator('[name="title"]').fill('浏览器验收：森林里的新镜头')
    page.locator('[name="body"]').fill('一次真实的投稿测试；内容包含 <script>标签但不应执行</script>。')
    page.locator('[name="feedback"]').fill('请关注前景的层次。')
    image = BytesIO(); Image.new('RGB', (32, 32), '#90ad71').save(image, format='PNG')
    page.locator('[name="image"]').set_input_files({'name':'work.png','mimeType':'image/png','buffer':image.getvalue()})
    page.locator('[name="consent"]').check()
    page.get_by_role('button', name='提交审核', exact=True).click()
    page.get_by_role('heading', name='浏览器验收：森林里的新镜头').wait_for()
    assert page.locator('main .tag.pending').count() == 1
    expect(page.locator('[data-media]')).to_have_attribute('src', re.compile(r'^blob:'))
    record('image upload and pending post persist through API; untrusted HTML is text')
    post_hash = page.evaluate('location.hash')
    assert post_hash.startswith('#post/'), post_hash
    sign_in('owner'); route('#manage')
    article = page.locator('article').filter(has=page.get_by_role('heading', name='浏览器验收：森林里的新镜头 ↗'))
    article.get_by_role('button', name='通过审核').click()
    expect(page.locator('article .review-box')).to_have_count(0)
    record('owner reviews pending post')
    sign_in('next')
    page.get_by_role('heading', name='浏览器验收：森林里的新镜头', exact=True).click()
    page.locator('form[data-form="comment"] textarea').fill('可以降低前景饱和度来改善景深。')
    page.get_by_role('button', name='提交反馈审核').click()
    page.get_by_text('可以降低前景饱和度来改善景深。', exact=True).wait_for()
    record('peer reads approved post and submits a pending comment')
    sign_in('owner'); route('#manage')
    comment = page.locator('article').filter(has_text='可以降低前景饱和度来改善景深。')
    comment.get_by_role('button', name='通过审核').click()
    expect(page.locator('article .review-box')).to_have_count(0)
    record('owner reviews a comment')
    sign_in('applicant'); route('#clubs')
    club = page.locator('article').filter(has=page.get_by_role('heading', name='动画研习社', exact=True))
    club.locator('input[name="reason"]').fill('想和同学一起学分镜')
    club.locator('input[name="accept_rules"]').check()
    club.get_by_role('button', name='提交入社申请').click()
    club.get_by_text('入社申请正在等待社长审核。', exact=True).wait_for()
    record('applicant accepts rules and applies without obtaining automatic membership')
    sign_in('owner'); route('#manage')
    page.get_by_role('button', name='同意加入').click()
    page.get_by_text('没有待处理的入社申请。', exact=True).wait_for()
    record('owner approves membership')
    sign_in('member'); route('#event/screening')
    page.get_by_role('button', name='报名参加', exact=True).click()
    page.get_by_role('button', name='取消我的报名', exact=True).wait_for()
    page.get_by_role('button', name='取消我的报名', exact=True).click()
    page.get_by_role('button', name='报名参加', exact=True).wait_for()
    record('member registers and cancels an event from the UI')
    for value, label in (
        ('#clubs', 'club directory'),
        ('#compose', 'compose form'),
        ('#events', 'event list'),
        ('#event/screening', 'event detail'),
        ('#mine', 'my submissions'),
        (post_hash, 'post detail'),
        ('#profile', 'account and handover page'),
    ):
        layout(value, label)
    sign_in('owner'); route('#manage')
    for value, label in (('#manage', 'owner dashboard'), ('#new-event', 'event creation form')):
        layout(value, label)
    page.set_viewport_size({'width': 390, 'height': 900})
    route('#manage')
    expect(page.locator('#main .state.loading')).to_have_count(0)
    page.screenshot(path=str(output / 'mobile-manage.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 1100})
    page.locator('select[name="to_user_id"]').select_option('u-next')
    page.locator('form[data-form="handover"] input[type="checkbox"]').check()
    page.get_by_role('button', name='发起交接', exact=True).click()
    page.get_by_role('heading', name='账号与交接', exact=True).wait_for()
    sign_in('next'); route('#profile')
    page.get_by_role('button', name='确认接任社长').click()
    page.get_by_role('link', name='社长工作台', exact=True).last.wait_for()
    record('two accounts complete ownership handover')
    sign_in('owner'); route('#manage')
    page.get_by_role('heading', name='需要社长权限').wait_for()
    record('old owner loses management access without refreshing the session token')
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bridge', action='store_true')
    parser.add_argument('--browser', default=shutil.which('chromium'))
    args = parser.parse_args()
    output = ROOT / 'artifacts'; output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as directory, socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]; sock.close()
        base = f'http://127.0.0.1:{port}'
        log = open(output / 'e2e-server.log', 'w')
        process = subprocess.Popen([sys.executable,'-m','server','--demo','--db',str(Path(directory)/'test.sqlite'),'--port',str(port)],cwd=ROOT,stdout=log,stderr=log)
        try:
            for _ in range(100):
                try:
                    if httpx.get(base+'/api/v1/health',timeout=.5).status_code == 200: break
                except httpx.HTTPError: pass
                time.sleep(.1)
            else: raise RuntimeError('API did not start')
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
                page = browser.new_page(viewport={'width':1440,'height':1100})
                page.set_default_timeout(8000)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                if args.bridge: bridge_page(page,base)
                else: page.goto(base)
                checks = run_workflows(page,output)
                assert not errors, errors
                checks.append('no browser JavaScript runtime errors')
                browser.close()
            report = {'mode':'offline UI source + real HTTP API bridge' if args.bridge else 'native browser HTTP', 'passed':len(checks),'checks':checks,'mini_program_host_tested':False}
            (output/'e2e.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(report,ensure_ascii=False,indent=2))
        finally:
            process.terminate(); process.wait(timeout=10); log.close()


if __name__ == '__main__':
    main()
