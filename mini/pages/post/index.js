const { api, image } = require('../../lib/http');
const { context, run, decorate, toast } = require('../../lib/ui');
Page({
  data:{post:null,comments:[],busy:false,error:'',imagePath:''},
  onLoad(options){this.id=options.id;this.load();},
  load(){return run(this,async()=>{
    await context();
    const [post,comments]=await Promise.all([api('/posts/'+this.id),api('/posts/'+this.id+'/comments?limit=100')]);
    this.setData({post:decorate(post),comments:comments.items.map(decorate),imagePath:''});
    if(post.media_id) this.setData({imagePath:await image(post.media_id)});
  });},
  comment(event){return run(this,async()=>{
    await api('/posts/'+this.id+'/comments','POST',{body:event.detail.value.body});toast('反馈已提交审核');
    const comments=await api('/posts/'+this.id+'/comments?limit=100');this.setData({comments:comments.items.map(decorate)});
  });}
});
