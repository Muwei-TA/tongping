const { api } = require('../../lib/http');
const { context, run, decorate, go } = require('../../lib/ui');
Page({
  data: { items:[], busy:false, error:'', clubName:'我的社团', kind:'', q:'', offset:0, owner:false },
  onShow() { this.load(); },
  load() { return run(this, async () => {
    const ctx = await context(); this.club = ctx.club;
    this.setData({clubName:ctx.membership ? ctx.membership.name : '先加入一个社团',owner:ctx.owner});
    if (!ctx.membership || ctx.membership.status !== 'active') { this.setData({items:[]}); return; }
    const query = '?limit=12&offset=' + this.data.offset + '&q=' + encodeURIComponent(this.data.q) + (this.data.kind ? '&kind=' + this.data.kind : '');
    const data = await api('/clubs/' + ctx.club + '/posts' + query);
    this.setData({items:data.items.map(decorate)});
  }); },
  filter(event) { this.setData({kind:event.currentTarget.dataset.kind,offset:0}); this.load(); },
  search(event) { this.setData({q:event.detail.value.q,offset:0}); this.load(); },
  more() { this.setData({offset:this.data.offset+12}); this.load(); },
  previous() { this.setData({offset:Math.max(0,this.data.offset-12)}); this.load(); },
  open(event) { go('/pages/post/index?id=' + event.currentTarget.dataset.id); }
});
