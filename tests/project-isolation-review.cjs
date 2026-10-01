// Independent regression: globally selecting a new project must not retarget an old tab.
'use strict';
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const {spawn}=require('child_process'),fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert');
(async()=>{
 const root=path.resolve(__dirname,'..'),workspace=fs.mkdtempSync(path.join(os.tmpdir(),'project-isolation-')),port=18788,base=`http://127.0.0.1:${port}`;
 const server=spawn('python',['-m','app.server','--workspace',workspace,'--port',String(port)],{cwd:root,stdio:'ignore'});let browser;
 try{
  for(let i=0;i<60;i++){try{if((await fetch(base+'/api/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH,args:['--no-sandbox','--disable-dev-shm-usage','--single-process']});
  const context=await browser.newContext(),old=await context.newPage();await old.goto(base+'/?project=default');await old.waitForFunction(()=>document.querySelector('#stageTitle').textContent);
  await old.locator('#editor').fill('Old tab stays pinned');
  const auth=await(await fetch(base+'/api/state?project=default')).json();
  const create=await fetch(base+'/api/projects/create?project=default',{method:'POST',headers:{'Content-Type':'application/json','X-Workspace-Token':auth.token},body:JSON.stringify({title:'Independent new project'})});assert.equal(create.status,200);const key=(await create.json()).created.id;
  const fresh=await context.newPage();await fresh.goto(base);await fresh.waitForFunction(()=>document.querySelector('#stageTitle').textContent);assert.equal(new URL(fresh.url()).searchParams.get('project'),key);
  await fresh.locator('#editor').fill('New project data');await fresh.locator('#save').click();await fresh.waitForFunction(()=>document.querySelector('#notice').textContent.includes('已保存'));
  await old.locator('#save').click();await old.waitForFunction(()=>document.querySelector('#notice').textContent.includes('已保存'));
  const oldState=await(await fetch(base+'/api/state?project=default')).json(),newState=await(await fetch(base+'/api/state?project='+key)).json();
  assert.equal(oldState.project.stages.requirements.text,'Old tab stays pinned');assert.equal(newState.project.stages.requirements.text,'New project data');
  for(const value of ['../escape','unknown','sample/../../'])assert([400,404].includes((await fetch(base+'/api/state?project='+encodeURIComponent(value))).status));
  assert.equal((await fetch(base+'/api/projects/create',{method:'POST',body:JSON.stringify({title:'Unauthorized'})})).status,403);
  console.log('PASS independent project isolation: old/new concurrent tabs retain their own edits; root reopen active; invalid project and unauthenticated create rejected');
 }finally{await browser?.close();server.kill();await new Promise(r=>server.once('exit',r));fs.rmSync(workspace,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
