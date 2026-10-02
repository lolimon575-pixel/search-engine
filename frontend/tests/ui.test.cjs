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
  ctx.history=ctx.history.slice(0,1);ctx.showSuggestions(true);
  assert.match(suggestions.innerHTML,/showLessHistory/);
  assert.doesNotMatch(suggestions.innerHTML,/Популярное у вас|Подсказки из веба/);
  ctx.history=[];ctx.showSuggestions(true);
  assert.match(suggestions.innerHTML,/История пока пуста/);assert.match(suggestions.innerHTML,/showLessHistory/);
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
  assert.equal(ctx.suggestions.style.top,'auto');assert.equal(ctx.suggestions.style.bottom,'306px');
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
  assert.equal(ctx.translate('10 результатов · Verified · Неделя · 6083 мс'),'10 results · Verified · Past week · 6083 ms');
  const summaryNode={nodeValue:'10 результатов · Web · Неделя · 6083 мс'};
  ctx.update(summaryNode);assert.equal(summaryNode.nodeValue,'10 results · Web · Past week · 6083 ms');
  ctx.setLanguage('ru');ctx.update(summaryNode);assert.equal(summaryNode.nodeValue,'10 результатов · Веб · Неделя · 6083 мс');
  ctx.setLanguage('en');
  assert.equal(ctx.translate('Search with an independent verification layer'),'Search with independent verification');
  assert.equal(ctx.translate('Автопоиск'),'Auto');
  assert.equal(ctx.translate('1 результат · Индекс NOVA · 120 мс'),'1 result · NOVA Index · 120 ms');
  assert.equal(ctx.translate('2 результата · Индекс NOVA · 120 мс'),'2 results · NOVA Index · 120 ms');
  assert.equal(ctx.translate('Авто'),'Cars');
  assert.equal(ctx.translate('10 результатов · Web · Индекс NOVA + Веб · 120 мс'),'10 results · Web · NOVA Index + Web · 120 ms');
  ctx.setLanguage('ru');assert.equal(ctx.translate('Verified'),'Проверенные');
});

test('all inline scripts parse',()=>{
  for(const match of html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g))new vm.Script(match[1]);
});

function companyHarness(){
  const panel={hidden:false,dataset:{},innerHTML:'old company',style:{setProperty(){}},classList:{toggle(){}},querySelector:()=>({})};
  const ctx={companyPanel:panel,companyPanelRequest:0,currentResults:[],sort:{value:'nova'},q:{value:''},resultsContext:{query:''},
    hasProfilePlus:()=>false,profileSearchMarkup:()=>'',profileActionMarkup:()=>'',profilePlusValueMarkup:()=>'',placeCompanyPanel(){},bindProfileSearch(){},
    applyDomainPreferences:rows=>rows.filter(x=>!x.blocked),
    isOfficialStatus:s=>s==='CONFIRMED',domainOf:url=>new URL(url).hostname.replace(/^www\./,''),
    loadOrganizationProfile:async domain=>({domain,url:'https://'+domain,organization:domain}),loadBillingStatus:async()=>null,
    safeAccent:()=>'',profileLinksMarkup:()=>'',escapeHtml:String,faviconOf:()=>'',profileVisualBadge:()=>''};
  ctx.resultsQuery=()=>ctx.resultsContext.query||ctx.q.value;
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
  const waiting=[],applied=[],retry={};let blurred=0;
  const element=()=>({classList:{add(){},remove(){}},textContent:'',innerHTML:''});
  const ctx={form:{},q:{value:'avito',blur(){blurred++}},searchGeneration:0,companyPanelRequest:0,resultsContext:{},skipNextCorrection:false,freshnessSelect:{value:''},engineSelect:{value:'auto'},stopVerificationPolling(){},startVerificationPolling(){},hasPendingSearch:()=>false,
    handleBang:()=>false,saveHistory(){},clearTimeout(){},suggestTimer:null,suggestionsArmed:false,hideSuggestions(){},
    document:{body:element(),querySelector:()=>retry},needsVerification:()=>false,status:element(),activeMode:'web',summary:element(),toolbar:element(),companyPanel:element(),
    briefCard:element(),metricCount:element(),metricTime:element(),metricVerified:element(),metricOfficial:element(),
    showSkeletons(){},pollTimer:null,performance:{now:()=>0},searchRequestUrl:x=>x,
    fetch:()=>new Promise(resolve=>waiting.push(resolve)),showCorrection(){},currentResults:[],
    applyResponse:(data,query)=>applied.push(query),results:element(),escapeHtml:String};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function showSearchError('),html.indexOf('function startVerificationPolling(')),ctx);
  vm.runInContext(html.slice(html.indexOf('form.onsubmit=async'),html.indexOf("document.addEventListener('keydown',e=>")),ctx);
  const old=ctx.form.onsubmit({preventDefault(){}});ctx.q.value='авто ру';
  const recent=ctx.form.onsubmit({preventDefault(){}});
  waiting[1]({ok:true,json:async()=>({})});await recent;
  waiting[0]({ok:true,json:async()=>({})});await old;
  assert.deepEqual(applied,['авто ру']);
  assert.equal(blurred,2);
  const failed=ctx.form.onsubmit({preventDefault(){}});
  waiting[2]({ok:false,json:async()=>{throw Error('Unexpected token <')}});await failed;
  assert.match(ctx.results.innerHTML,/Сервис временно недоступен/);
  assert.doesNotMatch(ctx.results.innerHTML,/Unexpected token/);
  let retried=false;ctx.form.requestSubmit=()=>{retried=true};retry.onclick();assert.equal(retried,true);
});

function profileHelpers(){
  const ctx={URL,escapeHtml:String,q:{value:''},resultsContext:{query:''},linkIcon:()=>'',modalStack:[],freshnessSelect:{value:'m'}};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function domainOf('),html.indexOf('function domainPreference(')),ctx);
  vm.runInContext(html.slice(html.indexOf('function resultsQuery('),html.indexOf('async function loadBillingStatus(')),ctx);
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
  const search={dataset:{siteSearch:'example.com'},querySelector:s=>s==='input'?{value:' shoes site:other.com '}:null};
  Object.assign(h,{domainOf:url=>new URL(url).hostname,activeMode:'verified',document:{querySelectorAll:()=>[]},updateClearButton(){},form:{requestSubmit(){submitted++},scrollIntoView(){}}});
  h.bindProfileSearch({querySelectorAll:()=>[search]});search.onsubmit({preventDefault(){}});
  assert.equal(h.q.value,'site:example.com shoes');assert.equal(h.activeMode,'web');assert.equal(submitted,1);
  assert.equal(h.freshnessSelect.value,'');
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

test('company sections stay expanded during mobile result refresh and switch layout on resize',()=>{
  const tools={open:true},panel={dataset:{},parentElement:null,querySelector:()=>tools};
  const target=()=>({prepend(node){node.parentElement=this}}),slot=target(),aside=target();
  let mobile=true;
  const ctx={companyPanel:panel,window:{matchMedia:()=>({matches:mobile})},document:{querySelector:s=>s==='#mobileCompanySlot'?slot:aside}};
  vm.createContext(ctx);vm.runInContext(html.slice(html.indexOf('function placeCompanyPanel('),html.indexOf('let viewportReference=null;')),ctx);
  ctx.placeCompanyPanel();assert.equal(panel.parentElement,slot);assert.equal(tools.open,false);
  tools.open=true;aside.prepend(panel);ctx.placeCompanyPanel();
  assert.equal(panel.parentElement,slot);assert.equal(tools.open,true);
  mobile=false;ctx.placeCompanyPanel();assert.equal(panel.parentElement,aside);assert.equal(tools.open,true);
  mobile=true;ctx.placeCompanyPanel();assert.equal(tools.open,false);
  tools.open=true;ctx.placeCompanyPanel(true);assert.equal(tools.open,false);
});

test('the visual viewport tracks keyboard height without mistaking zoom for a keyboard',()=>{
  const properties={},classes=new Set();let positions=0;
  const ctx={window:{innerHeight:800,innerWidth:390,visualViewport:{height:460,offsetTop:24,scale:1}},
    positionSuggestions(){positions++},document:{activeElement:{matches:()=>true},
      documentElement:{style:{setProperty:(name,value)=>properties[name]=value}},
      body:{classList:{toggle:(name,enabled)=>enabled?classes.add(name):classes.delete(name)}}}};
  vm.createContext(ctx);vm.runInContext(html.slice(html.indexOf('let viewportReference=null;'),html.indexOf('function profileLinksMarkup(')),ctx);
  ctx.updateViewportLayout();assert.equal(classes.has('keyboard-open'),true);
  assert.equal(properties['--visual-height'],'460px');assert.equal(properties['--visual-top'],'24px');
  ctx.window.innerHeight=460;ctx.updateViewportLayout();assert.equal(classes.has('keyboard-open'),true);
  ctx.window.innerHeight=800;
  ctx.window.visualViewport.scale=2;ctx.updateViewportLayout();assert.equal(classes.has('keyboard-open'),false);
  ctx.window.visualViewport={height:460,offsetTop:0,scale:1};ctx.document.activeElement.matches=()=>false;
  ctx.updateViewportLayout();assert.equal(classes.has('keyboard-open'),false);
  delete ctx.window.visualViewport;ctx.updateViewportLayout();assert.equal(properties['--visual-height'],'800px');
  assert.equal(positions,5);
});

test('dropdown hides when no usable space remains and reappears when the keyboard closes',()=>{
  const ctx={suggestions:{style:{},classList:{contains:()=>true}},
    form:{getBoundingClientRect:()=>({left:12,width:296,top:10,bottom:60})},
    window:{innerHeight:700,addEventListener(){},visualViewport:{offsetTop:0,height:70,addEventListener(){}}}};
  vm.createContext(ctx);vm.runInContext(html.slice(html.indexOf('function positionSuggestions('),html.indexOf('function hideSuggestions(')),ctx);
  ctx.positionSuggestions();assert.equal(ctx.suggestions.style.display,'none');
  ctx.window.visualViewport.height=700;ctx.positionSuggestions();assert.equal(ctx.suggestions.style.display,'');
  assert.equal(ctx.suggestions.style.top,'66px');assert.equal(ctx.suggestions.style.bottom,'auto');
});

test('Plus selects the requested section, preserves a custom primary action, and recognizes edited labels',()=>{
  const h=profileHelpers(),p={billing_status:'active',links:{shop:'https://example.com/shop',careers:'https://example.com/jobs'},primary_action:{label:'Request a quote',url:'https://example.com/quote'}};
  assert.equal(h.profileAction(p,'example вакансии').url,'https://example.com/jobs');
  assert.equal(h.profileAction(p,'example').label,'Request a quote');
  delete p.primary_action;p.links={'Карьера':'https://example.com/jobs','Магазин':'https://example.com/shop','Кроссовки':'https://example.com/shoes'};
  assert.equal(h.profileAction(p,'example').url,'https://example.com/shop');
  assert.equal(h.profileAction(p,'example работа').url,'https://example.com/jobs');
  assert.equal(h.profileAction(p,'example кроссовки').url,'https://example.com/shoes');
  p.billing_status='canceled';assert.equal(h.profileAction(p,'example вакансии'),null);
});

test('site search uses a selected official host and rejects an empty scoped query',()=>{
  const h=profileHelpers();let submitted=0,value='catalog';
  const search={dataset:{siteSearch:'example.com'},querySelector:s=>s==='input'?{value}:{value:'shop.example.com'}};
  Object.assign(h,{activeMode:'exact',document:{querySelectorAll:()=>[]},updateClearButton(){},form:{requestSubmit(){submitted++},scrollIntoView(){}}});
  h.bindProfileSearch({querySelectorAll:()=>[search]});search.onsubmit({preventDefault(){}});
  assert.equal(h.q.value,'site:shop.example.com catalog');assert.equal(h.freshnessSelect.value,'');
  value='site:other.com';search.onsubmit({preventDefault(){}});assert.equal(submitted,1);
  const markup=h.profileSearchMarkup({domain:'example.com',billing_status:'active',primary_action:{label:'Catalog',url:'https://shop.example.com/catalog'},links:{help:'https://help.example.com/'}});
  assert.match(markup,/value="shop.example.com" selected/);
  assert.match(markup,/value="help.example.com"/);
});

function editorHarness(response){
  const editor={elements:Object.fromEntries(['tagline','description','accent','primary_label','primary_url'].map(name=>[name,{value:name==='accent'?'#365fb7':''}]))};
  const status={textContent:''},save={disabled:false},modal={open:true,classList:{contains:()=>modal.open}};let closed=0,refreshed=0;
  const ctx={editorProfile:{domain:'example.com'},editorSession:1,ownershipTokens:{'example.com':'owner'},
    document:{querySelector:s=>s==='#profileEditorForm'?editor:s==='#profileEditorStatus'?status:s==='#profileEditorSave'?save:s==='#profileEditorLinks'?{children:[]}:modal},
    fetch:async()=>response,closeModal(){closed++;modal.open=false},closeOrganizationProfile(){closed++},async updateCompanyPanel(){refreshed++}};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function editorDraft('),html.indexOf('function updateEditorPreview(')),ctx);
  vm.runInContext(html.slice(html.indexOf('function closeProfileEditor('),html.indexOf('function openProfileEditor(')),ctx);
  vm.runInContext(html.slice(html.indexOf("document.querySelector('#profileEditorForm').onsubmit="),html.indexOf('function openClaim(')),ctx);
  return {ctx,editor,status,save,modal,closed:()=>closed,refreshed:()=>refreshed};
}
test('profile editor remains open after malformed or unconfirmed successful responses',async()=>{
  for(const response of [{ok:true,json:async()=>{throw Error('Unexpected token <')}},{ok:true,json:async()=>({})},{ok:false,json:async()=>({detail:'Subscription inactive'})}]){
    const h=editorHarness(response);await h.editor.onsubmit({preventDefault(){},currentTarget:h.editor});
    assert.equal(h.closed(),0);assert.equal(h.refreshed(),0);assert.equal(h.save.disabled,false);
    assert.ok(h.status.textContent);assert.doesNotMatch(h.status.textContent,/Unexpected token/);
  }
});
test('confirmed profile save closes the editor and reloads the public company card',async()=>{
  const h=editorHarness({ok:true,json:async()=>({saved:true,domain:'example.com'})});
  await h.editor.onsubmit({preventDefault(){},currentTarget:h.editor});
  assert.equal(h.closed(),2);assert.equal(h.refreshed(),1);assert.equal(h.save.disabled,false);
});
test('an old editor save cannot close another editor or alter its pending save',async()=>{
  let release;const h=editorHarness(null);h.ctx.fetch=()=>new Promise(resolve=>{release=resolve});
  const saving=h.editor.onsubmit({preventDefault(){},currentTarget:h.editor});
  h.ctx.editorSession++;h.ctx.editorProfile={domain:'other.com'};h.status.textContent='Saving other card';
  release({ok:true,json:async()=>({saved:true,domain:'example.com'})});await saving;
  assert.equal(h.closed(),0);assert.equal(h.refreshed(),0);assert.equal(h.save.disabled,true);
  assert.equal(h.status.textContent,'Saving other card');
});
test('a closed editor does not show a late save error',async()=>{
  let release;const h=editorHarness(null);h.ctx.fetch=()=>new Promise(resolve=>{release=resolve});
  const saving=h.editor.onsubmit({preventDefault(){},currentTarget:h.editor});h.modal.open=false;h.status.textContent='Closed';
  release({ok:false,json:async()=>({detail:'Server error'})});await saving;
  assert.equal(h.status.textContent,'Closed');assert.equal(h.closed(),0);
});

test('company recommendations use the displayed query while the next query is being typed',()=>{
  const h=profileHelpers(),p={billing_status:'active',links:{careers:'https://example.com/jobs',shop:'https://example.com/shop'}};
  h.resultsContext.query='example вакансии';h.q.value='example магазин';
  assert.equal(h.profileAction(p).url,'https://example.com/jobs');
  assert.match(h.profileLinksMarkup(p.links),/recommended[^]*https:\/\/example.com\/jobs/);
  h.resultsContext.query='example магазин';assert.equal(h.profileAction(p).url,'https://example.com/shop');
});

test('verification refresh uses the original search filters and permits editing the next query',async()=>{
  const applied=[],requested=[];
  const ctx={URLSearchParams,activeMode:'verified',freshnessSelect:{value:'y'},searchGeneration:2,lastElapsed:1400,
    q:{value:'draft next query'},resultsContext:{query:'corrected',mode:'web',freshness:'w'},
    fetch:async url=>{requested.push(url);return {ok:true,json:async()=>({results:[]})}},applyResponse:(...args)=>applied.push(args)};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function searchRequestUrl('),html.indexOf('function renderBrief(')),ctx);
  vm.runInContext(html.slice(html.indexOf('async function refreshVerification('),html.indexOf('function stopVerificationPolling(')),ctx);
  await ctx.refreshVerification('corrected',2,ctx.resultsContext);
  assert.equal(requested[0],'/api/search?q=corrected&mode=web&freshness=w&engine=auto');
  assert.equal(applied.length,1);assert.equal(applied[0][1],'corrected');assert.equal(applied[0][3],true);
  await ctx.refreshVerification('old query',1,ctx.resultsContext);assert.equal(applied.length,1);
  ctx.resultsContext.autocorrect=false;await ctx.refreshVerification('original',2,ctx.resultsContext);
  assert.equal(requested[2],'/api/search?q=original&mode=web&freshness=w&autocorrect=false&engine=auto');
});

test('verification polling waits for each response and leaves a newer search timer intact',async()=>{
  const timers=new Map(),waiting=[];let id=0,calls=0;
  const ctx={pollTimer:null,searchGeneration:1,currentResults:[{}],needsVerification:()=>true,
    status:{classList:{remove(){}},textContent:''},setTimeout:fn=>{timers.set(++id,fn);return id},clearTimeout:timer=>timers.delete(timer),
    refreshVerification:()=>{calls++;return new Promise(resolve=>waiting.push(resolve))}};
  vm.createContext(ctx);vm.runInContext(html.slice(html.indexOf('function stopVerificationPolling('),html.indexOf('form.onsubmit=async')),ctx);
  const fire=timer=>{const fn=timers.get(timer);timers.delete(timer);return fn()};
  ctx.startVerificationPolling('first',1,{});const first=fire(ctx.pollTimer);
  assert.equal(timers.size,0);assert.equal(calls,1);assert.equal(ctx.pollTimer,null);
  waiting.shift()();await first;assert.equal(timers.size,1);
  const second=fire(ctx.pollTimer);ctx.searchGeneration=2;ctx.startVerificationPolling('second',2,{});
  const newTimer=ctx.pollTimer;waiting.shift()();await second;
  assert.equal(ctx.pollTimer,newTimer);assert.equal(timers.size,1);
  const latest=fire(newTimer);ctx.currentResults=[];waiting.shift()();await latest;assert.equal(timers.size,0);
});

test('window resize does not collapse expanded mobile company tools',()=>{
  const tools={open:true},panel={dataset:{layout:'mobile'},querySelector:()=>tools},slot={prepend(node){node.parentElement=this}};
  panel.parentElement=slot;let resize;
  const ctx={companyPanel:panel,window:{matchMedia:()=>({matches:true}),addEventListener:(event,fn)=>resize=fn},document:{querySelector:()=>slot}};
  vm.createContext(ctx);vm.runInContext(html.slice(html.indexOf('function placeCompanyPanel('),html.indexOf('let viewportReference=null;')),ctx);
  vm.runInContext(html.match(/window.addEventListener\('resize',\(\)=>placeCompanyPanel\(\)\);/)[0],ctx);
  resize({type:'resize'});assert.equal(tools.open,true);
});

test('mobile result refresh preserves company search focus, selection, scroll and expanded tools',()=>{
  const tools={open:true},document={activeElement:null};let restored=0;
  const input={isConnected:true,selectionStart:2,selectionEnd:7,focus(){document.activeElement=this;restored++},setSelectionRange(start,end){this.selectionStart=start;this.selectionEnd=end}};
  document.activeElement=input;
  const panel={dataset:{layout:'mobile'},scrollTop:56,contains:el=>el===input,querySelector:()=>tools};
  const target=()=>({prepend(node){node.parentElement=this;document.activeElement=null}}),aside=target();let slot=target();panel.parentElement=slot;
  document.querySelector=selector=>selector==='#insights'?aside:slot;
  const results={querySelectorAll:()=>[],contains:node=>node.parentElement===slot,appendChild(){}};
  const ctx={document,companyPanel:panel,results,window:{matchMedia:()=>({matches:true})},
    displayedResults:()=>[{url:'https://example.com'}],updateCompanyPanel(){},isOfficialStatus:()=>true,renderCard(){slot=target();return {}},groupResults:()=>[],updateMetrics(){}};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function placeCompanyPanel('),html.indexOf('let viewportReference=null;')),ctx);
  vm.runInContext(html.slice(html.indexOf('function renderResults('),html.indexOf('function showSkeletons(')),ctx);
  ctx.renderResults();assert.equal(document.activeElement,input);assert.equal(restored,1);assert.equal(input.selectionStart,2);assert.equal(input.selectionEnd,7);
  assert.equal(panel.scrollTop,56);assert.equal(tools.open,true);assert.equal(panel.parentElement,slot);
});

function claimHarness(){
  const button={disabled:false,textContent:''},body={innerHTML:'',querySelector:()=>button},modal={classList:{contains:()=>true}};
  const ctx={claimContext:{domain:'first.com',token:'first-token'},claimBody:body,claimModal:modal,ownershipTokens:{},
    storeValue(){},escapeHtml:String,profilePlusValueMarkup:()=>'',updateCompanyPanel:async()=>{},navigator:{clipboard:{writeText:async()=>{}}}};
  vm.createContext(ctx);vm.runInContext(html.slice(html.indexOf('async function startClaim('),html.indexOf('function closeClaim(')),ctx);
  return ctx;
}
test('a challenge response cannot overwrite a different domain dialog',async()=>{
  const h=claimHarness();let release;h.fetch=()=>new Promise(resolve=>{release=resolve});
  const creating=h.startClaim();h.claimContext={domain:'second.com',token:''};h.claimBody.innerHTML='Second domain';
  release({ok:true,json:async()=>({token:'token-for-first',challenge_url:'https://first.com/proof'})});await creating;
  assert.equal(h.claimContext.token,'');assert.equal(h.claimBody.innerHTML,'Second domain');
});
test('a late ownership verification stores its own token without changing the next dialog',async()=>{
  const h=claimHarness();let release;h.fetch=()=>new Promise(resolve=>{release=resolve});
  const verifying=h.verifyClaim();h.claimContext={domain:'second.com',token:'second-token'};h.claimBody.innerHTML='Second domain';
  release({ok:true,json:async()=>({verified:true})});await verifying;
  assert.equal(h.ownershipTokens['first.com'],'first-token');assert.equal(h.ownershipTokens['second.com'],undefined);
  assert.equal(h.claimBody.innerHTML,'Second domain');
});

test('editor preview escapes owner copy and excludes unsafe link actions',()=>{
  const h=profileHelpers(),preview={style:{setProperty(){}},innerHTML:''};
  h.editorProfile={domain:'example.com',organization:'<img onerror="x">',billing_status:'active'};
  h.escapeHtml=value=>String(value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');h.safeAccent=()=> '#365fb7';
  h.document={querySelector:()=>preview};
  h.editorDraft=()=>({tagline:'<script>alert(1)</script>',description:'Example',accent:'#365fb7',primary_label:'Bad',primary_url:'javascript:alert(1)',links:[{label:'Unsafe',url:'javascript:alert(1)'},{label:'Catalog',url:'https://example.com/shop'}]});
  vm.runInContext(html.slice(html.indexOf('function updateEditorPreview('),html.indexOf('function closeProfileEditor(')),h);
  h.updateEditorPreview();assert.match(preview.innerHTML,/&lt;script>/);assert.doesNotMatch(preview.innerHTML,/<script>|<img|javascript:|>Unsafe</);
  assert.match(preview.innerHTML,/>Catalog</);
});

test('query correction preserves the next draft and the original-query action disables correction',()=>{
  const boxes=[],q={value:'typing next query'};let submitted=false;
  const ctx={q,skipNextCorrection:false,updateClearButton(){},escapeHtml:String,form:{requestSubmit(){submitted=true}},
    document:{querySelector:s=>s==='#correction'?null:{appendChild:box=>boxes.push(box)},createElement:()=>({})}};
  vm.createContext(ctx);vm.runInContext(html.slice(html.indexOf('function showCorrection('),html.indexOf('const modalStack=[];')),ctx);
  ctx.showCorrection('pumma','puma');assert.equal(q.value,'typing next query');assert.equal(boxes.length,1);
  boxes[0].onclick({target:{closest:selector=>selector==='[data-use-original]'}});
  assert.equal(q.value,'pumma');assert.equal(ctx.skipNextCorrection,true);assert.equal(submitted,true);
  ctx.skipNextCorrection=false;ctx.showCorrection('pumma','puma');assert.equal(q.value,'puma');
});

function responseHarness(context){
  const status={textContent:'',classList:{toggle(){}}};
  const ctx={resultsContext:context,currentResults:[],lastElapsed:null,status,summary:{},toolbar:{classList:{toggle(){}}},
    renderBrief(){},renderResults(){},updateMetrics(){},needsVerification:x=>!!x.verification?.pending,
    modeLabel:mode=>mode,showCorrection(){},performance:{now:()=>1200}};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function hasPendingSearch('),html.indexOf('function showSearchError(')),ctx);
  vm.runInContext(html.slice(html.indexOf('function applyResponse('),html.indexOf('async function refreshVerification(')),ctx);
  return ctx;
}
test('empty progressive snapshots stay pending and do not report instant first results',()=>{
  const context={requestQuery:'original',query:'original',mode:'verified',engine:'auto',freshness:'',started:100};
  const ctx=responseHarness(context);
  ctx.applyResponse({results:[],search_pending:true,verification_pending:false},'original',12,false,context);
  assert.equal(ctx.lastElapsed,null);
  assert.match(ctx.status.textContent,/Ищем в интернете/);
  assert.equal(ctx.hasPendingSearch(context),true);
  ctx.applyResponse({results:[{title:'found'}],search_pending:false,verification_pending:false,searched_query:'original'},'original',12,true,context);
  assert.equal(ctx.lastElapsed,1100);
  assert.equal(ctx.hasPendingSearch(context),false);
});
test('a background correction changes the displayed query but keeps the original request key',()=>{
  const context={requestQuery:'pumma',query:'pumma',mode:'web',engine:'auto',freshness:'',started:0};
  const ctx=responseHarness(context);const corrected=[];
  ctx.showCorrection=(...args)=>corrected.push(args);
  const data={results:[{title:'PUMA'}],corrected_query:'PUMA',searched_query:'PUMA',search_pending:false,verification_pending:false};
  ctx.applyResponse(data,'pumma',20,true,context);
  ctx.applyResponse(data,'pumma',20,true,context);
  assert.equal(context.query,'PUMA');assert.equal(context.requestQuery,'pumma');
  assert.deepEqual(corrected,[['pumma','PUMA']]);
});
test('pending officiality checks show skeletons instead of a false empty state',()=>{
  let skeletons=0;
  const ctx={resultsContext:{searchPending:false,verificationPending:true},currentResults:[],document:{activeElement:null},
    results:{innerHTML:'old',contains:()=>false,querySelectorAll:()=>[]},companyPanel:{contains:()=>false,scrollTop:0},
    displayedResults:()=>[],updateCompanyPanel(){},showSkeletons(){skeletons++},updateMetrics(){}};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function renderResults(){'),html.indexOf('function showSkeletons(){')),ctx);
  ctx.renderResults();assert.equal(skeletons,1);assert.doesNotMatch(ctx.results.innerHTML,/Ничего не найдено/);
});
test('verified mode with no initial results continues polling while web expansion runs',async()=>{
  const timers=[];const context={mode:'verified',searchPending:true,verificationPending:false};
  const ctx={resultsContext:context,currentResults:[],searchGeneration:1,pollTimer:null,
    needsVerification:()=>false,setTimeout:fn=>{timers.push(fn);return timers.length},clearTimeout(){},
    refreshVerification:async()=>{context.searchPending=false}};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('function stopVerificationPolling('),html.indexOf('form.onsubmit=async')),ctx);
  assert.equal(ctx.hasPendingSearch(context),true);
  ctx.startVerificationPolling('query',1,context);await timers[0]();
  assert.equal(ctx.pollTimer,null);assert.equal(timers.length,1);
});
test('an upstream error after a pending empty response becomes a retryable error',async()=>{
  const context={query:'sample',searchPending:true,verificationPending:false}, errors=[];
  const ctx={resultsContext:context,searchGeneration:1,currentResults:[],searchRequestUrl:()=>'/api/search',
    fetch:async()=>({ok:false,json:async()=>({detail:'Unavailable'})}),showSearchError:(...args)=>errors.push(args)};
  vm.createContext(ctx);
  vm.runInContext(html.slice(html.indexOf('async function refreshVerification('),html.indexOf('function stopVerificationPolling(')),ctx);
  await ctx.refreshVerification('sample',1,context);
  assert.equal(context.searchPending,false);assert.equal(errors[0][0],'Unavailable');
});
