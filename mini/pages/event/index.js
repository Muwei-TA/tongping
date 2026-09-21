const { api } = require('../../lib/http');
const { context, run, decorate, confirm } = require('../../lib/ui');
Page({
  data:{event:null,busy:false,error:'',owner:false,closed:false,registered:false},
  onLoad(options){this.id=options.id;this.load();},
  async refresh(){const item=await api('/events/'+this.id);this.setData({event:decorate(item),closed:item.status!=='open'||new Date(item.starts_at)<=new Date(),registered:['confirmed','waiting'].includes(item.my_registration)});},
  load(){return run(this,async()=>{const ctx=await context();this.setData({owner:ctx.owner});await this.refresh();});},
  register(){return run(this,async()=>{await api('/events/'+this.id+'/registration','PUT');await this.refresh();});},
  cancel(){return run(this,async()=>{if(await confirm('取消自己的报名？候补成员可能立即递补。')){await api('/events/'+this.id+'/registration','DELETE');await this.refresh();}});},
  cancelEvent(){return run(this,async()=>{if(await confirm('取消整个活动？所有成员的报名都会失效。')){await api('/events/'+this.id,'PATCH',{status:'cancelled'});await this.refresh();}});}
});
