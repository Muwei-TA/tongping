const { api, host, platformLogin, clearSession } = require('../../lib/http');
const { context, run, decorate, date, confirm, go } = require('../../lib/ui');
Page({
  data:{busy:false,error:'',demo:false,profile:null,handovers:[],posts:[],owner:false,offset:0,persona:0,personas:['林杳 · 成员','陈序 · 社长','周周 · 成员','新同学 · 申请者','夏禾 · 外社成员']},
  onShow(){this.load();},
  load(){return run(this,async()=>{
    this.setData({profile:null,handovers:[],posts:[]});
    const health=await api('/health');this.setData({demo:health.demo});
    if(!host.getStorageSync('tp_session')) return;
    const ctx=await context(),list=await api('/me/handovers?limit=100');
    let posts=[];
    if(ctx.membership&&ctx.membership.status==='active') posts=(await api('/clubs/'+ctx.club+'/posts?mine=true&limit=12&offset='+this.data.offset)).items;
    this.setData({profile:ctx.profile,owner:ctx.owner,posts:posts.map(decorate),handovers:list.items.map(h=>({...decorate(h),expires:date(h.expires_at),canAccept:h.to_user_id===ctx.profile.id&&h.status==='pending'&&new Date(h.expires_at)>new Date()}))});
  });},
  choose(event){this.setData({persona:Number(event.detail.value)});},
  login(){return run(this,async()=>{
    const session=this.data.demo?await api('/auth/demo','POST',{persona:['member','owner','next','applicant','outsider'][this.data.persona]}):await platformLogin();
    clearSession();host.setStorageSync('tp_session',session);getApp().globalData={club:'',profile:null};
    host.reLaunch({url:'/pages/home/index'});
  });},
  logout(){return run(this,async()=>{
    try{await api('/auth/session','DELETE');}finally{clearSession();getApp().globalData={club:'',profile:null};host.reLaunch({url:'/pages/profile/index'});}
  });},
  accept(event){return run(this,async()=>{if(await confirm('确认接任社长并承担审核责任？原社长将失去管理权限。')){await api('/handovers/'+event.currentTarget.dataset.id+'/accept','POST');host.reLaunch({url:'/pages/profile/index'});}});},
  open(event){go('/pages/post/index?id='+event.currentTarget.dataset.id);},
  more(){this.setData({offset:this.data.offset+12});this.load();},
  previous(){this.setData({offset:Math.max(0,this.data.offset-12)});this.load();}
});
