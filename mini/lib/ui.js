const { host, api } = require('./http');
const labels = {work:'作品',knowledge:'知识',question:'提问',chat:'闲聊',pending:'待审核',approved:'已发布',rejected:'已退回',active:'已加入',confirmed:'报名成功',waiting:'候补中',cancelled:'已取消',open:'报名开放',completed:'交接完成',expired:'已过期'};
function date(value) { return value ? new Date(value).toLocaleString() : ''; }
function decorate(item) { return { ...item, statusLabel: labels[item.status] || item.status, kindLabel: labels[item.kind] || '', dateLabel: date(item.starts_at || item.created_at), registrationLabel: labels[item.my_registration] || '尚未报名' }; }
async function context() {
  const profile = await api('/me');
  const app = getApp(); app.globalData.profile = profile;
  if (!app.globalData.club) app.globalData.club = (profile.memberships.find(m => m.status === 'active') || {}).club_id || '';
  const membership = profile.memberships.find(m => m.club_id === app.globalData.club);
  return { profile, club: app.globalData.club, membership, owner: Boolean(membership && membership.status === 'active' && membership.role === 'owner') };
}
async function run(page, job) {
  if (page.data.busy) return;
  page.setData({ busy:true, error:'' });
  try { await job(); return true; }
  catch (error) { page.setData({ error:error.message }); return false; }
  finally { page.setData({ busy:false }); }
}
function confirm(content) { return new Promise(resolve => host.showModal({title:'请确认',content,success:r=>resolve(r.confirm),fail:()=>resolve(false)})); }
function toast(title) { host.showToast({title,icon:'none'}); }
function go(url) { host.navigateTo({ url }); }
module.exports = { labels, date, decorate, context, run, confirm, toast, go };
