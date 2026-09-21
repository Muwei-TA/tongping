const { api } = require('../../lib/http');
const { context, run, decorate, go } = require('../../lib/ui');
Page({
  data:{items:[],busy:false,error:'',owner:false,showForm:false,offset:0},
  onShow(){this.load();},
  load(){return run(this,async()=>{
    const ctx=await context();this.club=ctx.club;
    const result=await api('/clubs/'+this.club+'/events?limit=12&offset='+this.data.offset);
    this.setData({items:result.items.map(decorate),owner:ctx.owner});
  });},
  toggle(){this.setData({showForm:!this.data.showForm});},
  open(event){go('/pages/event/index?id='+event.currentTarget.dataset.id);},
  more(){this.setData({offset:this.data.offset+12});this.load();},
  previous(){this.setData({offset:Math.max(0,this.data.offset-12)});this.load();},
  create(event){return run(this,async()=>{
    const d=event.detail.value;
    const start=new Date(d.start),end=new Date(d.end);
    if(!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime())) throw new Error('请按示例填写带时区的 ISO 日期');
    const item=await api('/clubs/'+this.club+'/events','POST',{title:d.title,description:d.description,location:d.location,capacity:Number(d.capacity),starts_at:start.toISOString(),ends_at:end.toISOString()});
    this.setData({showForm:false});go('/pages/event/index?id='+item.id);
  });}
});
