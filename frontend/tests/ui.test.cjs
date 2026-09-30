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
test('expanded history hides popular queries; collapsed suggestions have at most ten rows',()=>{
  const suggestions={innerHTML:'',style:{},classList:{add(){},contains(){return true}}};
  const ctx={suggestions,suggestionsArmed:true,activeSuggestionIndex:-1,showAllHistory:false,
    history:Array.from({length:12},(_,i)=>'query '+i),q:{value:''},remoteSuggestions:[],
    frequentQueries:()=>['popular','another popular','third popular'],escapeHtml:s=>s,DEFAULT_FREQUENT:[],
    window:{innerHeight:800,addEventListener(){}},form:{getBoundingClientRect:()=>({left:20,width:400,top:300,bottom:350})}};
  vm.createContext(ctx);vm.runInContext(html.slice(html.indexOf('function suggestionButton('),html.indexOf('function hideSuggestions(){')),ctx);
  ctx.showSuggestions(true);assert.equal((suggestions.innerHTML.match(/data-delete-query=/g)||[]).length,10);
  assert.doesNotMatch(suggestions.innerHTML,/data-query="popular"/);
  ctx.showAllHistory=true;ctx.showSuggestions(true);
  assert.equal((suggestions.innerHTML.match(/data-delete-query=/g)||[]).length,12);
  assert.match(suggestions.innerHTML,/showLessHistory/);
  assert.doesNotMatch(suggestions.innerHTML,/Популярное у вас|Подсказки из веба/);
  ctx.showAllHistory=false;ctx.history=ctx.history.slice(0,8);ctx.showSuggestions(true);
  assert.equal((suggestions.innerHTML.match(/class="suggestion-row"/g)||[]).length,10);
  assert.match(suggestions.innerHTML,/data-query="popular"/);
  ctx.remoteSuggestions=['web one','web two','web three'];ctx.showSuggestions(true);
  assert.equal((suggestions.innerHTML.match(/class="suggestion-row"/g)||[]).length,10);
  ctx.showAllHistory=true;ctx.showSuggestions(true);
  assert.doesNotMatch(suggestions.innerHTML,/Популярное у вас|Подсказки из веба/);
});

test('dropdown stays inside the viewport, including an on-screen keyboard',()=>{
  const ctx={suggestions:{style:{},classList:{contains:()=>true}},
    form:{getBoundingClientRect:()=>({left:14,width:347,top:400,bottom:454})},
    window:{innerHeight:700,addEventListener(){}}};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function positionSuggestions(){'),html.indexOf('function hideSuggestions(){')),ctx);
  ctx.positionSuggestions();
  assert.equal(ctx.suggestions.style.maxHeight,'230px');
  assert.equal(ctx.suggestions.style.top,'460px');
  ctx.window.visualViewport={offsetTop:0,height:470};
  ctx.positionSuggestions();
  assert.equal(ctx.suggestions.style.maxHeight,'320px');
  assert.equal(ctx.suggestions.style.top,'74px');
});

test('expanding and collapsing history keeps focus inside and stops outside-click dismissal',()=>{
  let listener,focusCount=0,renderCount=0;
  const ctx={suggestions:{addEventListener:(type,fn)=>listener=fn,querySelector:()=>({focus:()=>focusCount++})},
    showAllHistory:false,suggestionsArmed:true,showSuggestions:()=>renderCount++};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf("suggestions.addEventListener('click'"),html.indexOf('function statusMarkup')),ctx);
  for(const id of ['showMoreHistory','showLessHistory']){
    let stopped=false,prevented=false;
    listener({stopPropagation(){stopped=true},preventDefault(){prevented=true},
      target:{closest:selector=>selector==='#showMoreHistory,#showLessHistory'?{id}:null}});
    assert.equal(stopped,true);assert.equal(prevented,true);
    assert.equal(ctx.showAllHistory,id==='showMoreHistory');
  }
  assert.equal(focusCount,2);assert.equal(renderCount,2);
});

test('language changes are reversible and retain dynamic counts',()=>{
  const start=html.indexOf('  const messages=');
  const end=html.indexOf('  function visit(root)',start);
  const ctx={localStorage:{getItem:()=>null}};vm.createContext(ctx);
  vm.runInContext(html.slice(start,end)+"\nthis.setLanguage=value=>{language=value};this.update=update;this.translate=translate;",ctx);
  const node={nodeValue:'Найти'};
  ctx.setLanguage('en');ctx.update(node);assert.equal(node.nodeValue,'Search');
  ctx.setLanguage('ru');ctx.update(node);assert.equal(node.nodeValue,'Найти');
  ctx.setLanguage('en');
  assert.equal(ctx.translate('10 результатов · Web · 6083 мс'),'10 results · Web · 6083 ms');
  assert.equal(ctx.translate('Search with an independent verification layer'),'Search with independent verification');
  ctx.setLanguage('ru');assert.equal(ctx.translate('Verified'),'Проверенные');
});

test('all inline scripts parse',()=>{
  for(const match of html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g))new vm.Script(match[1]);
});

function companyHarness(){
  const panel={hidden:false,innerHTML:'old company',style:{setProperty(){}},classList:{toggle(){}},querySelector:()=>({})};
  const ctx={companyPanel:panel,companyPanelRequest:0,currentResults:[],sort:{value:'nova'},q:{value:''},
    hasProfilePlus:()=>false,profileSearchMarkup:()=>'',bindProfileSearch(){},
    applyDomainPreferences:rows=>rows.filter(x=>!x.blocked),
    isOfficialStatus:s=>s==='CONFIRMED',domainOf:url=>new URL(url).hostname.replace(/^www\./,''),
    loadOrganizationProfile:async domain=>({domain,url:'https://'+domain,organization:domain}),loadBillingStatus:async()=>null,
    safeAccent:()=>'',profileLinksMarkup:()=>'',escapeHtml:String,faviconOf:()=>'',profileVisualBadge:()=>''};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function displayedResults(){'),html.indexOf('function renderResults(){')),ctx);
  vm.runInContext(html.slice(html.indexOf('async function updateCompanyPanel('),html.indexOf('async function openOrganizationProfile(')),ctx);
  return ctx;
}
const companyResult=(domain,official=true)=>({url:'https://'+domain,title:domain,verification:{officiality:{status:official?'CONFIRMED':'UNKNOWN'}}});
test('a later registered company never substitutes for an unregistered first result',async()=>{
  const h=companyHarness();let calls=0;h.loadOrganizationProfile=async()=>{calls++;};
  h.currentResults=[companyResult('auto.ru',false),companyResult('avito.ru')];
  await h.updateCompanyPanel();assert.equal(calls,0);assert.equal(h.companyPanel.hidden,true);
  assert.equal(h.companyPanel.innerHTML,'');
});
test('profile follows the first visible result after sorting and hiding domains',async()=>{
  const h=companyHarness();h.currentResults=[companyResult('avito.ru'),companyResult('auto.ru')];
  h.sort.value='title';await h.updateCompanyPanel();assert.match(h.companyPanel.innerHTML,/auto\.ru/);
  h.currentResults[1].blocked=true;await h.updateCompanyPanel();assert.match(h.companyPanel.innerHTML,/avito\.ru/);
});
test('late profile responses cannot revive a panel after its first result changed',async()=>{
  const h=companyHarness();let release;h.currentResults=[companyResult('avito.ru')];
  h.loadOrganizationProfile=()=>new Promise(resolve=>{release=resolve});
  const pending=h.updateCompanyPanel();h.currentResults=[companyResult('auto.ru',false)];
  await h.updateCompanyPanel();release({domain:'avito.ru',url:'https://avito.ru',organization:'Avito'});await pending;
  assert.equal(h.companyPanel.hidden,true);assert.equal(h.companyPanel.innerHTML,'');
});
test('a profile for a different domain is rejected',async()=>{
  const h=companyHarness();h.currentResults=[companyResult('auto.ru')];
  h.loadOrganizationProfile=async()=>({domain:'avito.ru',url:'https://avito.ru'});
  await h.updateCompanyPanel();assert.equal(h.companyPanel.hidden,true);
});

test('a slow earlier search cannot overwrite a newer search and its company selection',async()=>{
  const waiting=[],applied=[],retry={};
  const element=()=>({classList:{add(){},remove(){}},textContent:'',innerHTML:''});
  const ctx={form:{},q:{value:'avito'},searchGeneration:0,companyPanelRequest:0,
    handleBang:()=>false,saveHistory(){},clearTimeout(){},suggestTimer:null,suggestionsArmed:false,hideSuggestions(){},
    document:{body:element(),querySelector:()=>retry},needsVerification:()=>false,status:element(),activeMode:'web',summary:element(),toolbar:element(),companyPanel:element(),
    briefCard:element(),metricCount:element(),metricTime:element(),metricVerified:element(),metricOfficial:element(),
    showSkeletons(){},pollTimer:null,performance:{now:()=>0},searchRequestUrl:x=>x,
    fetch:()=>new Promise(resolve=>waiting.push(resolve)),showCorrection(){},currentResults:[],
    applyResponse:(data,query)=>applied.push(query),results:element(),escapeHtml:String};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('form.onsubmit=async'),html.indexOf("document.addEventListener('keydown',e=>")),ctx);
  const old=ctx.form.onsubmit({preventDefault(){}});ctx.q.value='авто ру';
  const recent=ctx.form.onsubmit({preventDefault(){}});
  waiting[1]({ok:true,json:async()=>({})});await recent;
  waiting[0]({ok:true,json:async()=>({})});await old;
  assert.deepEqual(applied,['авто ру']);
  const failed=ctx.form.onsubmit({preventDefault(){}});
  waiting[2]({ok:false,json:async()=>{throw Error('Unexpected token <')}});await failed;
  assert.match(ctx.results.innerHTML,/Сервис временно недоступен/);
  assert.doesNotMatch(ctx.results.innerHTML,/Unexpected token/);
  let retried=false;ctx.form.requestSubmit=()=>{retried=true};retry.onclick();assert.equal(retried,true);
});

function profileHelpers(){
  const ctx={URL,escapeHtml:String,q:{value:''},linkLabel:key=>key,linkIcon:()=>'',modalStack:[]};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function linkIntentTerms('),html.indexOf('async function loadBillingStatus(')),ctx);
  return ctx;
}
test('section recommendations match words rather than accidental substrings',()=>{
  const h=profileHelpers();
  assert.equal(h.linkMatchesQuery('app','apple'),false);
  assert.equal(h.linkMatchesQuery('cars','careers'),false);
  assert.equal(h.linkMatchesQuery('app','download app'),true);
  assert.equal(h.linkMatchesQuery('cars','автомобили'),true);
});
test('profile links reject executable URLs and embedded credentials',()=>{
  const h=profileHelpers();
  const markup=h.profileLinksMarkup({shop:'https://example.com/shop',bad:'javascript:alert(1)',other:'https://user:pass@example.com'});
  assert.match(markup,/https:\/\/example.com\/shop/);
  assert.doesNotMatch(markup,/javascript:|user:pass/);
});
test('Plus tools require an active subscription or an explicitly labelled demo',()=>{
  const h=profileHelpers();
  assert.equal(h.profileSearchMarkup({profile_tier:'premium',billing_status:'canceled'}),'');
  assert.match(h.profileSearchMarkup({domain:'puma.com',profile_tier:'premium_demo'}),/data-site-search="puma.com"/);
  assert.match(h.profileSearchMarkup({domain:'example.com',billing_status:'active'}),/data-site-search/);
});
test('site search submits a domain scoped query in web mode',()=>{
  const h=profileHelpers();let submitted=0;
  const search={dataset:{siteSearch:'example.com'},querySelector:()=>({value:' shoes site:other.com '})};
  Object.assign(h,{domainOf:url=>new URL(url).hostname,activeMode:'verified',document:{querySelectorAll:()=>[]},updateClearButton(){},form:{requestSubmit(){submitted++},scrollIntoView(){}}});
  h.bindProfileSearch({querySelectorAll:()=>[search]});search.onsubmit({preventDefault(){}});
  assert.equal(h.q.value,'site:example.com shoes');assert.equal(h.activeMode,'web');assert.equal(submitted,1);
});
test('public company profile remains available without a billing status request',async()=>{
  const h=companyHarness();h.currentResults=[companyResult('auto.ru')];
  h.loadBillingStatus=async()=>{throw Error('unavailable')};
  await h.updateCompanyPanel();assert.equal(h.companyPanel.hidden,false);
});

test('damaged or unavailable browser storage never prevents startup',()=>{
  const ctx={localStorage:{getItem:()=>'{broken',setItem:()=>{throw Error('quota')}}};vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function readStored('),html.indexOf("let history=readStored")),ctx);
  assert.equal(ctx.readStored('history',[]).length,0);
  ctx.localStorage.getItem=()=>'{"unexpected":true}';assert.equal(ctx.readStored('history',[]).length,0);
  ctx.localStorage.getItem=()=>{throw Error('denied')};assert.equal(ctx.readStored('history',[]).length,0);
  assert.doesNotThrow(()=>ctx.storeValue('history','[]'));
});
