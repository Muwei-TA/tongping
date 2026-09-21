const { api, host } = require('../../lib/http');
const { run, labels, toast } = require('../../lib/ui');
Page({
  data:{items:[],busy:false,error:''},
  onShow(){this.load();},
  load(){return run(this,async()=>{
    const data=await api('/clubs?limit=100');
    let memberships=[];
    if(host.getStorageSync('tp_session')) memberships=(await api('/me')).memberships;
    this.setData({items:data.items.map(c=>{const m=memberships.find(m=>m.club_id===c.id);return {...c,status:m?m.status:'',statusLabel:m?labels[m.status]:'待加入'};})});
  });},
  join(event){return run(this,async()=>{
    const data=event.detail.value;
    if(!data.accept_rules.length || !data.reason.trim()) throw new Error('请填写申请理由，并同意社团约定');
    await api('/clubs/'+event.currentTarget.dataset.id+'/membership','POST',{reason:data.reason,accept_rules:true});
    toast('申请已提交');
  }).then(ok=>{if(ok)this.load();});},
  enter(event){getApp().globalData.club=event.currentTarget.dataset.id;host.reLaunch({url:'/pages/home/index'});}
});
