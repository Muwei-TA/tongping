import { request, setToken, hasToken } from './api.js';
import { h, empty } from './views.js';
import { renderPage, isOwner } from './pages.js';

const state = { me: null, club: '', clubs: [], demo: false };
const main = document.querySelector('#main');
let generation = 0;
let accountRevision = 0;
let lastRoute = '';
let intent = '';
let imageURLs = [];
let noticeTimer;

function newIntent() {
  return Array.from(crypto.getRandomValues(new Uint32Array(4)), value => value.toString(16).padStart(8, '0')).join('');
}
function routeInfo() {
  const [path, query = ''] = (location.hash.slice(1) || 'feed').split('?');
  const [route, id = ''] = path.split('/');
  return { route, id, params: new URLSearchParams(query) };
}
function notify(message) {
  const node = document.querySelector('#notice');
  node.textContent = message;
  node.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { node.hidden = true; }, 7000);
}
function releaseImages() { imageURLs.forEach(URL.revokeObjectURL); imageURLs = []; }
async function refreshProfile() {
  if (!hasToken()) { state.me = null; return; }
  const revision = accountRevision;
  const profile = await request('/me');
  if (revision !== accountRevision) return;
  state.me = profile;
  const active = state.me.memberships.find(m => m.status === 'active');
  if (!state.club || !state.clubs.some(c => c.id === state.club)) state.club = active?.club_id || state.clubs[0]?.id || '';
}
function shell() {
  const select = document.querySelector('#club-select');
  select.innerHTML = state.clubs.map(club => `<option value="${h(club.id)}">${h(club.name)}</option>`).join('');
  select.value = state.club;
  document.querySelector('#account').textContent = state.me?.name || '登录';
  document.querySelector('#manage-link').hidden = !isOwner(state);
  document.querySelector('#demo-banner').hidden = !state.demo;
  const { route } = routeInfo();
  document.querySelectorAll('nav a').forEach(a => a.classList.toggle('active', a.hash === '#' + route));
}
async function hydrateImages(ticket) {
  for (const image of main.querySelectorAll('[data-media]')) {
    try {
      const blob = await request(`/media/${encodeURIComponent(image.dataset.media)}`, { binary: true });
      if (ticket !== generation) return;
      const url = URL.createObjectURL(blob);
      imageURLs.push(url);
      image.src = url;
    } catch {
      if (ticket === generation) image.alt = '图片加载失败，或访问权限已变更。请刷新页面。';
    }
  }
}
async function render() {
  const ticket = ++generation;
  releaseImages();
  const { route, id, params } = routeInfo();
  if (route === 'compose' && lastRoute !== 'compose') intent = newIntent();
  lastRoute = route;
  main.innerHTML = '<div class="state loading" role="status" aria-busy="true">正在读取社团空间…</div>';
  try {
    await refreshProfile();
    if (ticket !== generation) return;
    shell();
    const html = await renderPage(route, id, params, state);
    if (ticket !== generation) return;
    main.innerHTML = html;
    main.focus({ preventScroll: true });
    await hydrateImages(ticket);
  } catch (error) {
    if (ticket !== generation) return;
    if (error.status === 401) {
      setToken(''); state.me = null; accountRevision++;
      notify('会话已过期，请重新登录。');
      return render();
    }
    main.innerHTML = `<div class="state error-state" role="alert"><h2>暂时无法打开这个页面</h2><p>${h(error.message)}</p><button data-action="refresh">重新读取</button><a class="button" href="#clubs">查看我的社团</a></div>`;
  }
}
function navigate(hash) {
  if (location.hash === hash) return render();
  history.pushState(null, "", hash);
  return render();
}
async function loginWithToken(token) {
  generation++; accountRevision++; releaseImages();
  setToken(token); state.me = null; state.club = '';
  await refreshProfile();
  navigate('#feed');
}
async function logout() {
  try { await request('/auth/session', { method: 'DELETE' }); }
  finally {
    setToken(''); state.me = null; generation++; accountRevision++; releaseImages();
    main.innerHTML = ''; navigate('#profile');
  }
}

const actions = {
  refresh: () => render(),
  logout,
  'switch-club': async id => { state.club = id; navigate('#feed'); },
  register: async id => { await request(`/events/${id}/registration`, { method: 'PUT' }); notify('报名状态已更新。'); await render(); },
  unregister: async id => {
    if (!confirm('确认取消自己的报名？已候补的成员可能立即递补。')) return;
    await request(`/events/${id}/registration`, { method: 'DELETE' }); await render();
  },
  'cancel-event': async id => {
    if (!confirm('确认取消整个活动？所有成员的报名都会失效。')) return;
    await request(`/events/${id}`, { method: 'PATCH', body: { status: 'cancelled' } }); await render();
  },
  'member-active': id => reviewMember(id, 'active'),
  'member-rejected': id => reviewMember(id, 'rejected'),
  'accept-handover': async id => {
    if (!confirm('确认接任？你将承担社团审核和管理责任，原社长将失去管理权限。')) return;
    await request(`/handovers/${id}/accept`, { method: 'POST' }); notify('交接完成，权限已更新。'); await render();
  }
};
async function reviewMember(id, status) {
  await request(`/clubs/${state.club}/members/${id}`, { method: 'PATCH', body: { status } });
  await render();
}

async function submit(form, submitter) {
  const data = Object.fromEntries(new FormData(form));
  const type = form.dataset.form;
  if (type === 'login') {
    const session = await request('/auth/demo', { method: 'POST', body: { persona: data.persona } });
    return loginWithToken(session.token);
  }
  if (type === 'session') return loginWithToken(data.token.trim());
  if (type === 'search') {
    const { route, params } = routeInfo();
    params.set('q', data.q); params.delete('offset');
    return navigate(`#${route}?${params}`);
  }
  if (type === 'compose') {
    if (!intent) intent = newIntent();
    const file = form.elements.image.files[0];
    if (file && !form.dataset.media) {
      if (file.size > 5 * 1024 * 1024) throw new Error('请选择小于 5 MB 的图片。');
      const multipart = new FormData(); multipart.append('file', file);
      form.dataset.media = (await request(`/clubs/${state.club}/media`, { method: 'POST', body: multipart })).id;
    }
    const post = await request(`/clubs/${state.club}/posts`, { method: 'POST', body: {
      client_id: intent, kind: data.kind, title: data.title, body: data.body, feedback: data.feedback,
      media_id: form.dataset.media || null
    }});
    notify('投稿已保存，等待社长审核。'); return navigate(`#post/${post.id}`);
  }
  if (type === 'comment') {
    await request(`/posts/${form.dataset.id}/comments`, { method: 'POST', body: { body: data.body } });
    notify('反馈已提交审核。'); return render();
  }
  if (type === 'review') {
    const status = submitter?.value;
    if (status === 'rejected' && !data.reason.trim()) throw new Error('请填写退回理由，帮助作者改进。');
    await request(`/${form.dataset.type}/${form.dataset.id}/review`, { method: 'PATCH', body: { status, reason: data.reason } });
    notify('审核结果已保存。'); return render();
  }
  if (type === 'join') {
    await request(`/clubs/${form.dataset.id}/membership`, { method: 'POST', body: { reason: data.reason, accept_rules: true } });
    notify('申请已提交，登录不会自动获得入社权限。'); return render();
  }
  if (type === 'event') {
    const event = await request(`/clubs/${state.club}/events`, { method: 'POST', body: {
      title: data.title, description: data.description, location: data.location, capacity: Number(data.capacity),
      starts_at: new Date(data.starts_at).toISOString(), ends_at: new Date(data.ends_at).toISOString()
    }});
    return navigate(`#event/${event.id}`);
  }
  if (type === 'handover') {
    await request(`/clubs/${state.club}/handovers`, { method: 'POST', body: { to_user_id: data.to_user_id } });
    notify('已发出交接，请由继任者本人确认。'); return navigate('#profile');
  }
}

async function run(button, operation) {
  if (button?.disabled) return;
  if (button) button.disabled = true;
  try { await operation(); }
  catch (error) { notify(error.message); }
  finally { if (button) button.disabled = false; }
}
document.addEventListener('click', event => {
  const anchor = event.target.closest('a[href^="#"]');
  if (anchor && !event.ctrlKey && !event.metaKey && !event.shiftKey && event.button === 0) {
    if (anchor.hash !== '#main') { event.preventDefault(); navigate(anchor.hash); }
  }
  const button = event.target.closest('[data-action]');
  if (button && actions[button.dataset.action]) run(button, () => actions[button.dataset.action](button.dataset.id));
  const pageButton = event.target.closest('[data-page]');
  if (pageButton) {
    const { route, params } = routeInfo(); params.set('offset', pageButton.dataset.page);
    navigate(`#${route}?${params}`);
  }
});
document.addEventListener('submit', event => {
  const form = event.target.closest('[data-form]');
  if (!form) return;
  event.preventDefault();
  run(event.submitter, () => submit(form, event.submitter));
});
document.addEventListener('change', event => {
  if (event.target.name === 'image') delete event.target.form.dataset.media;
});
document.querySelector('#club-select').addEventListener('change', event => {
  state.club = event.target.value; navigate('#feed');
});
window.addEventListener('hashchange', render);
window.addEventListener('popstate', render);
try {
  const [health, clubs] = await Promise.all([request('/health'), request('/clubs?limit=100')]);
  state.demo = health.demo; state.clubs = clubs.items; state.club = clubs.items[0]?.id || '';
  await render();
} catch (error) {
  main.innerHTML = empty('服务未连接',error.message,'#profile','重新打开');
}
