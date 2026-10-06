'use strict';
// Local artifact editor and Codex task bridge. No model endpoint is called here.
window.PublishingWorkspace=(()=>{
  const $=id=>document.getElementById(id),orientations=['landscape','portrait'];
  let bridge=null,dirty=false,project=null,lastText='',requestKey=null;
  const fields={title:'publishTitle',description:'publishDescription',topics:'publishTopics'};
  const requestNames={text:'发布文案',landscape:'横版封面',portrait:'竖版封面'};
  function draft(){return{title:$('publishTitle').value,description:$('publishDescription').value,topics:$('publishTopics').value.split(/[\s,，]+/).map(s=>s.replace(/^#+/, '')).filter(Boolean)};}
  function textSnapshot(value){return JSON.stringify({title:value?.title||'',description:value?.description||'',topics:value?.topics||[]});}
  function hasDirty(){return dirty;}
  function changed(){dirty=true;$('publishingSaved').textContent='文案有未保存修改';}
  function publication(){return bridge.getState()?.publishing||{};}
  function feedback(message,error=false){$('publishingSaved').textContent=message;bridge.notice(message,error);}
  async function mutate(action,data={}){bridge.assertMutable();const key=bridge.projectKey;await bridge.api('publishing/'+action,data);if(key!==bridge.projectKey)throw Error('项目已切换，请在原项目查看操作结果');}
  async function save(){await mutate('save',draft());dirty=false;lastText=textSnapshot(publication().text);render();feedback('发布文案已保存');}
  function run(fn,button){return bridge.operation(async()=>{try{await fn();}catch(error){feedback(error.message,true);throw error;}},button).finally(()=>render());}
  function printable(){const d=draft();return `视频标题\n${d.title}\n\n简介\n${d.description}\n\n话题\n${d.topics.map(t=>'#'+t).join(' ')}`;}
  async function copy(value){try{await navigator.clipboard.writeText(value);feedback('已复制');}catch{throw Error('浏览器无法自动复制，请选中对应文案复制');}}
  async function request(targets){
    if(dirty)await save();
    const active=publication().request;
    if(['queued','running'].includes(active?.status)){feedback('已有生成请求，请等待 Codex 完成或先取消');return;}
    await mutate('request',{targets,direction:$('publishingDirection').value.trim()});render();feedback('请求已保存，等待当前 Codex 会话领取');
  }
  function renderCover(orientation,cover){
    const preview=$(orientation+'CoverPreview'),download=$(orientation+'CoverDownload'),meta=$(orientation+'CoverMeta');
    // Backend read-state validation is authoritative; old paths are not completion proof.
    const valid=Boolean(cover?.path&&cover?.width&&cover?.height&&cover?.sha256&&cover?.valid!==false);
    const url=valid?bridge.assetURL(cover.path):'';
    if(preview.dataset.asset!==url){
      preview.replaceChildren();preview.dataset.asset=url;
      if(valid){const image=document.createElement('img');image.src=url;image.alt=(orientation==='landscape'?'横版':'竖版')+'封面';preview.append(image);}else{const span=document.createElement('span');span.textContent=cover?.path?'图片缺失或验证未通过':'等待真实'+(orientation==='landscape'?'横版':'竖版')+'封面';preview.append(span);}
    }
    preview.disabled=!valid;download.hidden=!valid;
    if(valid){download.href=url;download.download=cover.path.split('/').pop();preview.onclick=()=>bridge.openAsset({path:cover.path,label:(orientation==='landscape'?'横版4:3':'竖版3:4')+'封面',version:bridge.getState().stages.export.version},cover.path.split('.').pop().toLowerCase());}
    meta.textContent=valid?`${cover.width} × ${cover.height} · ${cover.source==='code-generated'?'HTML/CSS / 代码图形':cover.source==='ai-generated'?'AI 生成图片':cover.source==='user-supplied'?'用户图片':cover.source==='licensed-reference'?'授权素材':'已登记'}`:cover?.path?'验证未通过':'尚未登记';
  }
  function render(current,stage){
    if(!bridge)return;
    const key=bridge.projectKey,p=current?.publishing||publication();
    if(project!==key){project=key;dirty=false;lastText='';requestKey=null;$('publishingDirection').value='';}
    $('publishingPanel').hidden=(stage||bridge.getStage())!=='export';
    const snapshot=textSnapshot(p.text);
    if(!dirty&&snapshot!==lastText){$('publishTitle').value=p.text?.title||'';$('publishDescription').value=p.text?.description||'';$('publishTopics').value=(p.text?.topics||[]).map(t=>'#'+t.replace(/^#+/, '')).join(' ');lastText=snapshot;}
    if(!dirty)$('publishingSaved').textContent=p.text?.title?'文案已保存':'文案待准备';
    $('publishingStale').hidden=!p.stale;$('reviewPublishing').hidden=!p.stale;
    const complete=Boolean(p.enabled!==false&&p.ready&&p.text?.title&&p.text?.description&&p.text?.topics?.length&&orientations.every(o=>p.covers?.[o]?.path));
    $('publishingStatus').textContent=p.stale?'需要核对':complete?'发布包已验证':p.enabled===false?'旧项目 · 可补充':'发布材料待完成';
    $('publishingStatus').className='badge '+(p.stale?'stale':complete?'approved':'draft');
    for(const orientation of orientations){renderCover(orientation,p.covers?.[orientation]);$('request'+orientation[0].toUpperCase()+orientation.slice(1)+'Cover').textContent='请 Codex '+(p.covers?.[orientation]?.path?'重新生成':'生成')+(orientation==='landscape'?'横版':'竖版');}
    $('requestPublishingAll').textContent=p.text?.title?'请 Codex 重新生成完整发布包':'请 Codex 准备完整发布包';
    const pending=['queued','running'].includes(p.request?.status),request=p.request;
    $('cancelPublishing').hidden=!pending;
    for(const id of ['requestPublishingAll','requestPublishingText','requestLandscapeCover','requestPortraitCover'])$(id).disabled=pending;
    const status=request?.status,targets=(request?.targets||[]).map(t=>requestNames[t]||t).join('、');
    $('publishingRequestStatus').textContent=status==='queued'?`等待 Codex 接手：${targets}`:status==='running'?`Codex 已领取：${targets}`:status==='cancelled'?'上次生成请求已取消':status==='completed'?'上次生成请求已完成':'';
    if(request?.id!==requestKey){requestKey=request?.id;if(request?.direction)$('publishingDirection').value=request.direction;}
    const ready=complete&&!p.stale&&!dirty;
    for(const format of ['Txt','Json','Zip']){const link=$('downloadPublishing'+format);link.href='/api/publishing/export'+bridge.suffix+'&format='+format.toLowerCase();link.setAttribute('aria-disabled',String(!ready));}
    $('publishingDownloadHelp').textContent=ready?'包含文案、双封面及来源清单':dirty?'先保存文案再下载':p.stale?'先核对内容变化再下载':'文案与两张合规封面完成后可下载';
  }
  async function upload(orientation){
    const input=$(orientation+'CoverFile'),file=input.files[0];
    if(!file)throw Error('请先选择封面图片');
    if(!/\.(png|jpe?g|webp)$/i.test(file.name)||!file.size||file.size>8_000_000)throw Error('请使用8 MB以内的 PNG、JPEG 或 WebP 图片');
    if(dirty)await save();
    const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('无法读取封面文件'));reader.readAsDataURL(file);});
    await mutate('upload',{orientation,name:file.name,data});input.value='';render();feedback('封面已验证并替换；另一张封面保持原样');
  }
  async function download(format){
    if(dirty)throw Error('请先保存发布文案');
    const p=publication();if(p.enabled===false||!p.ready||p.stale)throw Error('请先完成文案、双封面并核对内容变化');
    await mutate('export');render();
    const link=document.createElement('a');link.href='/api/publishing/export'+bridge.suffix+'&format='+format;link.download='publishing.'+format;document.body.append(link);link.click();link.remove();feedback('发布包已更新，下载已开始');
  }
  function init(value){
    bridge=value;
    for(const id of Object.values(fields))$(id).addEventListener('input',()=>{changed();render();});
    $('savePublishing').onclick=()=>run(save,$('savePublishing'));
    for(const [id,value]of [['copyPublishTitle',()=>draft().title],['copyPublishDescription',()=>draft().description],['copyPublishTopics',()=>draft().topics.map(t=>'#'+t).join(' ')],['copyPublishing',printable]])$(id).onclick=()=>run(()=>copy(value()),$(id));
    for(const [id,targets]of [['requestPublishingText',['text']],['requestLandscapeCover',['landscape']],['requestPortraitCover',['portrait']],['requestPublishingAll',['text','landscape','portrait']]])$(id).onclick=()=>run(()=>request(targets),$(id));
    $('cancelPublishing').onclick=()=>run(async()=>{await mutate('cancel',{id:publication().request?.id});render();feedback('已取消生成请求，已有文案与封面保留');},$('cancelPublishing'));
    $('reviewPublishing').onclick=()=>run(async()=>{if(dirty)await save();await mutate('review-current',{note:'用户在导出页核对了发布文案与双封面'});render();feedback('已登记核对当前内容');},$('reviewPublishing'));
    for(const orientation of orientations){const id='replace'+orientation[0].toUpperCase()+orientation.slice(1)+'Cover';$(id).onclick=()=>run(()=>upload(orientation),$(id));}
    for(const format of ['txt','json','zip'])$('downloadPublishing'+format[0].toUpperCase()+format.slice(1)).onclick=e=>{e.preventDefault();run(()=>download(format));};
  }
  return{init,render,hasDirty,discard:()=>{dirty=false;}};
})();
