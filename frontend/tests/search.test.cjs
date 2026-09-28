const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const html=readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const source=html.slice(html.indexOf('async function refreshVerification('),html.indexOf("document.addEventListener('keydown',e=>{"));
function setup(){
  const element=()=>({classList:{add(){},remove(){}},textContent:'',innerHTML:'',hidden:false});
  const requests=[],applied=[],intervals=[];
  const ctx={AbortController,performance,form:{},q:{value:'nova'},activeMode:'web',pollTimer:null,searchController:null,searchGeneration:0,
    suggestTimer:null,suggestionsArmed:false,currentResults:[],lastElapsed:0,document:{body:element()},
    status:element(),summary:element(),toolbar:element(),companyPanel:element(),briefCard:element(),
    metricCount:element(),metricTime:element(),metricVerified:element(),metricOfficial:element(),results:element(),
    handleBang:()=>false,saveHistory(){},hideSuggestions(){},showSkeletons(){},showCorrection(){},escapeHtml:x=>x,
    clearTimeout(){},clearInterval(){},setInterval(fn){intervals.push(fn);return intervals.length},
    needsVerification:r=>r.pending,
    searchRequestUrl:q=>q+':'+ctx.activeMode,
    applyResponse(data){applied.push(data);ctx.currentResults=data.results||[]},
    fetch(url,options){return new Promise((resolve,reject)=>requests.push({url,options,resolve:data=>resolve({ok:true,json:async()=>data}),reject}))}
  };
  vm.runInNewContext(source,ctx);
  return {ctx,requests,applied,intervals,submit:()=>ctx.form.onsubmit({preventDefault(){}})};
}
test('old response cannot replace results after a mode change for the same query',async()=>{
  const h=setup();const old=h.submit();h.ctx.activeMode='verified';const latest=h.submit();
  assert.equal(h.requests[0].options.signal.aborted,true);
  h.requests[1].resolve({results:[{title:'new'}]});await latest;
  h.requests[0].resolve({results:[{title:'old'}]});await old;
  assert.equal(h.applied.length,1);assert.equal(h.applied[0].results[0].title,'new');
});
test('old network failure cannot replace the current screen with an error',async()=>{
  const h=setup();const old=h.submit();const latest=h.submit();
  h.requests[1].resolve({results:[]});await latest;
  h.requests[0].reject(new Error('old error'));await old;
  assert.equal(h.ctx.results.innerHTML,'');
});
test('corrected queries refresh the original request and never overlap polling',async()=>{
  const h=setup();const first=h.submit();
  h.requests[0].resolve({corrected_query:'NOVA corrected',results:[{pending:true}]});await first;
  const poll=h.intervals[0]();await h.intervals[0]();
  assert.equal(h.requests.length,2);assert.equal(h.requests[1].url,h.requests[0].url);
  h.requests[1].resolve({results:[{pending:false}]});await poll;
  assert.equal(h.applied.length,2);
});
