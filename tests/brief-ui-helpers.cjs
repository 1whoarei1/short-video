'use strict';
// Navigate through the real optional groups before interacting with a control.
// No force clicks, hidden-value mutation, or bypass of production validation.
async function revealBriefControl(page, selector){
 const dialog=await page.evaluate(s=>{const e=document.querySelector(s);if(!e)return null;return {inside:!!e.closest('#voiceDialog'),open:document.querySelector('#voiceDialog').open};},selector);
 if(dialog?.inside&&!dialog.open){await revealBriefControl(page,'#chooseVoice');await page.locator('#chooseVoice').click();}
 if(dialog&&!dialog.inside&&dialog.open)await page.locator('#closeVoice').click();
 const info=await page.evaluate(s=>{const e=document.querySelector(s);if(!e)return null;const tabs=document.querySelector('#briefTabs');if(!tabs||tabs.hidden)return null;const panel=e.closest('[role="tabpanel"]');return panel?({briefContent:'briefTabContent',briefDirection:'briefTabVisual',briefDelivery:'briefTabDelivery'}[panel.id]||null):null;},selector);
 if(info&&await page.locator('#'+info).getAttribute('aria-selected')!=='true')await page.locator('#'+info).click();
 const details=await page.evaluate(s=>{const e=document.querySelector(s);if(!e)return null;const d=e.closest('details');if(!d||d.open||e.tagName==='SUMMARY')return null;return d.id?'#'+d.id+' > summary':d.classList.contains('image-options')?'.image-options > summary':null;},selector);
 if(details)await page.locator(details).click();
}
module.exports={revealBriefControl};
