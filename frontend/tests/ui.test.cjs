const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
function setup(){
  const document={body:{style:{}},activeElement:null};
  const shell={};
  function modal(id){
    const classes=new Set(),attrs={};
    const dialog={scrollTop:100};
    const close={isConnected:true,focus(){document.activeElement=this}};
    return {id,attrs,dialog,close,inert:false,style:{removeProperty(key){delete this[key]}},
      classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x)},
      setAttribute(k,v){attrs[k]=v},removeAttribute(k){delete attrs[k]},
      querySelector:s=>s==='.dialog'?dialog:close,contains:e=>e===close};
  }
  const org=modal('org'),verify=modal('verify'),claim=modal('claim');
  document.querySelector=()=>shell;document.querySelectorAll=()=>[org,verify,claim];
  const ctx={document};vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('const modalStack=[];'),html.indexOf('function openVerification(x){')),ctx);
  return {ctx,document,shell,org,verify,claim};
}
test('verification opens above profile; closing restores profile focus and scroll lock',()=>{
  const h=setup();const opener={isConnected:true,focus(){h.document.activeElement=this}};h.document.activeElement=opener;
  h.ctx.openModal(h.org);h.ctx.openModal(h.verify);
  assert.ok(+h.verify.style.zIndex>+h.org.style.zIndex);
  assert.equal(h.org.inert,true);assert.equal(h.verify.inert,false);assert.equal(h.shell.inert,true);
  assert.equal(h.verify.dialog.scrollTop,0);
  h.ctx.closeModal(h.verify);
  assert.equal(h.document.activeElement,h.org.close);assert.equal(h.org.inert,false);
  assert.equal(h.document.body.style.overflow,'hidden');
  h.ctx.closeModal(h.org);
  assert.equal(h.document.activeElement,opener);assert.equal(h.document.body.style.overflow,'');assert.equal(h.shell.inert,false);
});
test('three nested dialogs close in reverse order without activating background',()=>{
  const h=setup();h.ctx.openModal(h.org);h.ctx.openModal(h.verify);h.ctx.openModal(h.claim);
  assert.ok(+h.claim.style.zIndex>+h.verify.style.zIndex);
  h.ctx.closeModal(h.claim);assert.equal(h.verify.attrs['aria-modal'],'true');assert.equal(h.org.inert,true);
  h.ctx.closeModal(h.verify);assert.equal(h.org.attrs['aria-modal'],'true');
});
test('show all history renders more than eight entries and preserves popular queries',()=>{
  const suggestions={innerHTML:'',classList:{add(){}}};
  const ctx={suggestions,suggestionsArmed:true,activeSuggestionIndex:-1,showAllHistory:false,
    history:Array.from({length:12},(_,i)=>'query '+i),q:{value:''},remoteSuggestions:[],
    frequentQueries:()=>['popular'],escapeHtml:s=>s,DEFAULT_FREQUENT:[]};
  vm.createContext(ctx);vm.runInContext(html.slice(html.indexOf('function suggestionButton('),html.indexOf('function hideSuggestions(){')),ctx);
  ctx.showSuggestions(true);assert.equal((suggestions.innerHTML.match(/data-delete-query=/g)||[]).length,8);
  assert.match(suggestions.innerHTML,/data-query="popular"/);
  ctx.showAllHistory=true;ctx.showSuggestions(true);
  assert.equal((suggestions.innerHTML.match(/data-delete-query=/g)||[]).length,12);
  assert.match(suggestions.innerHTML,/showLessHistory/);
});
