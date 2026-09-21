const { api, host, upload } = require('../../lib/http');
const { context, run, toast } = require('../../lib/ui');
Page({
  data:{busy:false,error:'',kinds:['作品 / 半成品','知识分享','提问','闲聊'],kindIndex:0,imagePath:''},
  onLoad(){this.intent=Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);run(this,async()=>{this.club=(await context()).club;});},
  kind(event){this.setData({kindIndex:Number(event.detail.value)});},
  choose(){host.chooseImage({count:1,sizeType:['compressed'],success:result=>{this.mediaId=null;this.setData({imagePath:result.tempFilePaths[0]});},fail:()=>this.setData({error:'未选择图片；也可以仅发布文字。'})});},
  submit(event){return run(this,async()=>{
    const data=event.detail.value;
    if(!data.consent.length) throw new Error('请确认作品发布权限');
    if(!data.title.trim() || !data.body.trim()) throw new Error('请填写标题和正文');
    if(this.data.imagePath && !this.mediaId) this.mediaId=(await upload(this.club,this.data.imagePath)).id;
    const item=await api('/clubs/'+this.club+'/posts','POST',{client_id:this.intent,kind:['work','knowledge','question','chat'][this.data.kindIndex],title:data.title,body:data.body,feedback:data.feedback,media_id:this.mediaId||null});
    toast('已提交审核');host.redirectTo({url:'/pages/post/index?id='+item.id});
  });}
});
