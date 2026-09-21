// Page-level data loading. Presentational helpers remain in views.js.
import { request } from './api.js';
import { h, date, tag, head, empty, pager, postCard, review, eventCard, eventForm, compose, login } from './views.js';
export const membership = state => state.me?.memberships.find(m => m.club_id === state.club);
export const isOwner = state => membership(state)?.role === 'owner' && membership(state)?.status === 'active';

export async function renderPage(route, id, params, state) {
  if (route === 'clubs') return clubsPage(state);
  if (!state.me) return login(state.demo);
  if (route === 'profile') return profilePage(state);
  if (membership(state)?.status !== 'active') {
    return empty('先找到属于你的社团', '当前身份还没有加入这个社团，或入社申请正在审核。', '#clubs', '查看社团与申请');
  }
  if (route === 'compose') return compose();
  if (route === 'new-event') return isOwner(state) ? eventForm() : empty('需要社长权限', '只有当前社长可以发起活动。', '#events', '返回活动');
  if (route === 'post') return postPage(id, state);
  if (route === 'event') return eventPage(id, state);
  if (route === 'events') return eventsPage(params, state);
  if (route === 'manage') return managePage(params, state);
  if (['feed', 'knowledge', 'mine'].includes(route)) return feedPage(route, params, state);
  return empty('页面不存在', '请从导航中选择一个入口。', '#feed', '返回动态');
}

async function feedPage(route, params, state) {
  const query = new URLSearchParams(params);
  query.set('limit', '12');
  if (!query.get('kind')) query.delete('kind');
  if (route === 'knowledge') query.set('kind', 'knowledge');
  if (route === 'mine') query.set('mine', 'true');
  const data = await request(`/clubs/${state.club}/posts?${query}`);
  const title = route === 'knowledge' ? '把走过的路，留下来。' : route === 'mine' ? '我的内容' : '今天，也有新的灵感。';
  const subtitle = route === 'mine' ? '投稿进度和退回理由都在这里。' : '在熟悉的社团里，分享、回应，一起慢慢变好。';
  const hero = route === 'mine' ? '' : `<section class="hero ${route === 'knowledge' ? 'sand' : ''}"><div><span class="eyebrow">${route === 'knowledge' ? 'OUR SHARED NOTES' : 'WORK IN PROGRESS'}</span><h2>${route === 'knowledge' ? '一次分享，少走一点弯路。' : '作品不必完成，交流可以先开始。'}</h2><p>${route === 'knowledge' ? '制作清单、方法笔记、经验总结，都值得留下来。' : '带上你的半成品，让同伴成为第一个观众。'}</p></div><div class="hero-badge">一起创作<br>一起成长</div></section>`;
  const selected = params.get('kind') || '';
  const tabs = route === 'feed' ? `<div class="chips">${[['','全部'],['work','作品'],['question','提问'],['chat','闲聊']].map(([key,label]) => `<a class="chip button ${key === selected ? 'active' : ''}" href="#feed?kind=${key}">${label}</a>`).join('')}</div>` : '<span class="muted compact">仅当前社团 · 按发布时间排序</span>';
  return `${head(title, subtitle, '<a class="button primary" href="#compose">＋ 发布</a>')}${hero}<div class="toolbar">${tabs}<form class="search" data-form="search"><input aria-label="搜索社团内容" name="q" maxlength="100" value="${h(params.get('q') || '')}" placeholder="搜索社团内容"><button>搜索</button></form></div>${data.items.length ? `<div class="grid">${data.items.map(p => postCard(p, state.demo)).join('')}</div>` : empty('这里还没有内容', '试着分享一次尝试，或换一个搜索词。')}${pager(Number(params.get('offset') || 0), data.items.length)}`;
}

async function postPage(id, state) {
  const [post, comments] = await Promise.all([request(`/posts/${id}`), request(`/posts/${id}/comments?limit=100`)]);
  const image = post.media_id ? `<img class="cover detail-cover" data-media="${h(post.media_id)}" alt="${h(post.title)}的作品图片">` : state.demo && post.id === 'forest' ? '<img class="cover detail-cover" src="/forest.svg" alt="几何森林演示作品">' : '';
  return `<div class="detail"><a class="back" href="#feed">← 返回社团动态</a><article class="card"><div class="meta"><span class="avatar">${h(post.author_name[0])}</span>${h(post.author_name)} · ${h(date(post.created_at))}${tag(post.kind)}${tag(post.status)}</div><h1>${h(post.title)}</h1><div class="body-text">${h(post.body)}</div>${image}${post.feedback ? `<div class="feedback"><strong>作者希望听到的反馈</strong>${h(post.feedback)}</div>` : ''}${post.reason ? `<div class="feedback"><strong>审核说明</strong>${h(post.reason)}</div>` : ''}${isOwner(state) && post.status === 'pending' ? review('posts', post.id) : ''}</article><h2 class="section-title">认真回应，比一句“好看”更有用。</h2><div class="stack">${comments.items.map(c => `<article class="card"><div class="meta">${h(c.author_name)} · ${tag(c.status)}</div><p class="body-text">${h(c.body)}</p>${c.reason ? `<p>${h(c.reason)}</p>` : ''}${isOwner(state) && c.status === 'pending' ? review('comments',c.id) : ''}</article>`).join('') || '<p class="muted">还没有可展示的反馈，来做第一个认真回应的人。</p>'}</div><p class="muted compact">最多展示前 100 条反馈；待审核内容仅作者与社长可见。</p>${post.status === 'approved' ? `<form class="form card card-pad section-title" data-form="comment" data-id="${h(post.id)}"><label>写下你的建议<textarea name="body" required minlength="2" maxlength="2000" placeholder="具体哪里有效？有什么可尝试的改进？"></textarea></label><button class="primary">提交反馈审核</button></form>` : ''}</div>`;
}

async function clubsPage(state) {
  const data = await request('/clubs?limit=100');
  return `${head('找到同频的人','公开页面只展示社团介绍，不包含内部作品和成员名单。')}<div class="grid">${data.items.map(club => {
    const member = state.me?.memberships.find(m => m.club_id === club.id);
    return `<article class="card card-pad"><span class="eyebrow">CLUB / INVITATION</span><h2>${h(club.name)}</h2><p>${h(club.summary)}</p><div class="feedback"><strong>共同约定</strong>${h(club.rules)}</div><div class="badge-line">${member ? tag(member.status) : '<span class="tag">待加入</span>'}</div>${!state.me ? '<a class="button primary section-title" href="#profile">登录后申请</a>' : member?.status === 'active' ? `<button class="primary section-title" data-action="switch-club" data-id="${h(club.id)}">进入社团</button>` : member?.status === 'pending' ? '<p class="section-title">入社申请正在等待社长审核。</p>' : `<form class="form section-title" data-form="join" data-id="${h(club.id)}"><label>为什么想加入？<input name="reason" required minlength="2" maxlength="500"></label><label class="check"><input name="accept_rules" type="checkbox" required><span>我已阅读并同意上面的社团约定。</span></label><button class="primary">提交入社申请</button></form>`}</article>`;
  }).join('')}</div><p class="muted compact section-title">首版展示前 100 个社团；新增社团由运营人员核验后开通。</p>`;
}

async function eventsPage(params, state) {
  const offset = Number(params.get('offset') || 0);
  const data = await request(`/clubs/${state.club}/events?limit=12&offset=${offset}`);
  return `${head('一起做点有意思的。','从线上交流，到共同经历。', isOwner(state) ? '<a class="button primary" href="#new-event">＋ 发起活动</a>' : '')}<section class="hero lavender"><div><span class="eyebrow">MEET · MAKE · SHARE</span><h2>带上你的半成品。</h2><p>小放映、共创局、经验分享。没有完美的门槛。</p></div></section><div class="grid">${data.items.map(eventCard).join('') || empty('暂时没有活动','下一次聚会正在酝酿。','#feed','回到动态')}</div>${pager(offset,data.items.length)}`;
}

async function eventPage(id, state) {
  const event = await request(`/events/${id}`);
  const closed = event.status !== 'open' || new Date(event.starts_at) <= new Date();
  const registered = ['confirmed','waiting'].includes(event.my_registration);
  return `<div class="detail"><a class="back" href="#events">← 返回社团活动</a><article class="card"><div class="event-date">${h(date(event.starts_at))}</div><h1>${h(event.title)}</h1><p class="muted">${h(event.location)}</p><p class="body-text">${h(event.description)}</p><p>结束于 ${h(date(event.ends_at))}</p><div class="event-stats"><div><strong>${event.confirmed} / ${event.capacity}</strong><span>已报名</span></div><div><strong>${event.waiting}</strong><span>候补队列</span></div></div><div class="badge-line">${tag(event.status)}${event.my_registration ? tag(event.my_registration) : ''}</div><div class="actions section-title">${closed ? '<span class="muted">活动已开始或取消，报名通道关闭。</span>' : `<button class="primary" data-action="${registered ? 'unregister' : 'register'}" data-id="${h(id)}">${registered ? '取消我的报名' : event.confirmed >= event.capacity ? '加入候补' : '报名参加'}</button>`}${isOwner(state) && event.status === 'open' ? `<button class="danger" data-action="cancel-event" data-id="${h(id)}">取消整个活动</button>` : ''}</div><div class="feedback">候补按申请先后自动递补。首版报名凭证不是签到凭证，也不关联学分。</div></article></div>`;
}

async function managePage(params, state) {
  if (!isOwner(state)) return empty('需要社长权限','社团管理只对当前社长开放。','#feed','返回社团');
  const offset = Number(params.get('offset') || 0);
  const [members, posts, comments] = await Promise.all([
    request(`/clubs/${state.club}/members?limit=100`), request(`/clubs/${state.club}/posts?status=pending&limit=12&offset=${offset}`),
    request(`/clubs/${state.club}/review-comments?limit=100`)
  ]);
  return `${head('社长工作台','先看内容，再给出明确的通过或退回理由。')}<h2 class="section-title">入社申请</h2><section class="card card-pad">${members.items.filter(m => m.status === 'pending').map(m => `<div class="roster"><div><strong>${h(m.name)}</strong><p>${h(m.reason)}</p></div><div class="actions"><button class="primary" data-action="member-active" data-id="${h(m.user_id)}">同意加入</button><button data-action="member-rejected" data-id="${h(m.user_id)}">拒绝申请</button></div></div>`).join('') || '<p class="muted">没有待处理的入社申请。</p>'}</section><h2 class="section-title">内容审核</h2><div class="stack">${posts.items.map(p => `<article class="card"><span class="meta">${h(p.author_name)} · ${tag(p.kind)}</span><h3><a href="#post/${h(p.id)}">${h(p.title)} ↗</a></h3><p class="body-text">${h(p.body)}</p>${p.media_id ? `<img class="cover" data-media="${h(p.media_id)}" alt="待审核作品图片">` : ''}${review('posts',p.id)}</article>`).join('') || '<p class="muted">所有投稿都已处理。</p>'}</div>${pager(offset,posts.items.length)}<h2 class="section-title">反馈审核</h2><div class="stack">${comments.items.map(c => `<article class="card"><div class="meta">${h(c.author_name)} → ${h(c.post_title)}</div><p class="body-text">${h(c.body)}</p>${review('comments',c.id)}</article>`).join('') || '<p class="muted">没有待处理反馈。</p>'}</div><h2 class="section-title">成员与换届</h2><section class="card card-pad"><p class="muted">名单与反馈队列各展示前 100 条。交接发出后须由继任者本人确认，48 小时有效。</p><form class="form section-title" data-form="handover"><label>指定继任者<select name="to_user_id" required><option value="">选择已加入的成员</option>${members.items.filter(m => m.status === 'active' && m.user_id !== state.me.id).map(m => `<option value="${h(m.user_id)}">${h(m.name)}</option>`).join('')}</select></label><label class="check"><input type="checkbox" required><span>我已核对成员、内容及活动，确认发起社长权限交接。</span></label><button class="primary">发起交接</button></form></section>`;
}

async function profilePage(state) {
  const data = await request('/me/handovers?limit=100');
  return `${head('账号与交接','平台身份与社团权限分开管理。')}<section class="card card-pad"><div class="meta"><span class="avatar">${h(state.me.name[0])}</span><h2>${h(state.me.name)}</h2></div><p class="muted compact">账号 ID：${h(state.me.id)}</p><div class="badge-line">${state.me.memberships.map(m => `<span class="tag">${h(m.name)} · ${h(m.role === 'owner' ? '社长' : '成员')} · ${h(tagText(m.status))}</span>`).join('')}</div><div class="actions section-title"><a class="button" href="#mine">我的投稿</a><a class="button" href="#clubs">社团与申请</a>${isOwner(state) ? '<a class="button primary" href="#manage">社长工作台</a>' : ''}<button data-action="logout">退出登录${state.demo ? ' / 切换演示身份' : ''}</button></div></section><h2 class="section-title">与我有关的交接</h2><div class="stack">${data.items.map(item => `<article class="card"><h3>${h(item.club_name)} → ${h(item.to_name)}</h3><p>有效期至 ${h(date(item.expires_at))}</p>${tag(item.status)}${item.to_user_id === state.me.id && item.status === 'pending' && new Date(item.expires_at) > new Date() ? `<button class="primary" data-action="accept-handover" data-id="${h(item.id)}">确认接任社长</button>` : ''}</article>`).join('') || '<p class="muted">暂时没有交接事项。</p>'}</div><div class="feedback section-title">小程序平台登录接入须完成真实凭据配置与真机验证。当前网页仅作联调，不是已上架服务。</div>`;
}
function tagText(status) { return ({active:'已加入',pending:'待审核',rejected:'未通过'})[status] || status; }
