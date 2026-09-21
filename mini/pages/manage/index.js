const { api, image } = require('../../lib/http');
const { context, run, decorate, toast } = require('../../lib/ui');
Page({
  data:{busy:false,error:'',members:[],posts:[],comments:[],candidates:[],candidateNames:[],candidate:0,offset:0},
  onShow(){this.load();},
  async refresh(){
    const [members,posts,comments]=await Promise.all([api('/clubs/'+this.club+'/members?limit=100'),api('/clubs/'+this.club+'/posts?status=pending&limit=12&offset='+this.data.offset),api('/clubs/'+this.club+'/review-comments?limit=100')]);
    const candidates=members.items.filter(m=>m.status==='active'&&m.user_id!==this.userId);
    const previews=[];
    for(const item of posts.items){
      const value=decorate(item);
      if(item.media_id){try{value.imagePath=await image(item.media_id);}catch(error){value.imageError=error.message;}}
      previews.push(value);
    }
    this.setData({members:members.items.filter(m=>m.status==='pending'),posts:previews,comments:comments.items.map(decorate),candidates,candidateNames:candidates.map(m=>m.name),candidate:0});
  },
  load(){return run(this,async()=>{
    this.setData({members:[],posts:[],comments:[],candidates:[]});
    const ctx=await context();if(!ctx.owner) throw new Error('只有当前社长可以访问工作台');
    this.club=ctx.club;this.userId=ctx.profile.id;await this.refresh();
  });},
  reviewMember(event){return run(this,async()=>{const d=event.currentTarget.dataset;await api('/clubs/'+this.club+'/members/'+d.id,'PATCH',{status:d.status});await this.refresh();});},
  review(event){return run(this,async()=>{const d=event.currentTarget.dataset,value=event.detail.value;if(value.status==='rejected'&&!value.reason.trim()) throw new Error('请填写退回理由');await api('/'+d.type+'/'+d.id+'/review','PATCH',{status:value.status,reason:value.reason});await this.refresh();});},
  chooseCandidate(event){this.setData({candidate:Number(event.detail.value)});},
  handover(event){return run(this,async()=>{
    if(!event.detail.value.confirm.length) throw new Error('请先确认资料与职责交接');
    const member=this.data.candidates[this.data.candidate];if(!member) throw new Error('没有可交接的成员');
    await api('/clubs/'+this.club+'/handovers','POST',{to_user_id:member.user_id});toast('已发出交接，等待本人确认');
  });},
  more(){this.setData({offset:this.data.offset+12});this.load();},
  previous(){this.setData({offset:Math.max(0,this.data.offset-12)});this.load();}
});
