'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
test('spinner sheet closes on Escape or outside clicks without stealing other focus',()=>{
 const events={},sheetEvents={};let focusCount=0,prevented=0;
 const inside={},outside={},summary={focus:()=>focusCount++};
 const sheet={open:true,contains:target=>target===inside,querySelector:()=>summary,
  addEventListener:(type,fn)=>sheetEvents[type]=fn};
 const c=vm.createContext({document:{readyState:'loading',querySelector:()=>sheet,
  addEventListener:(type,fn)=>events[type]=fn},console});
 vm.runInContext(fs.readFileSync(path.join(root,'workbench/app.js'),'utf8'),c);
 c.wireSpinnerEgg();
 sheetEvents.keydown({key:'Escape',preventDefault:()=>prevented++,stopPropagation:()=>{}});
 assert.equal(sheet.open,false);assert.equal(focusCount,1);assert.equal(prevented,1);
 sheet.open=true;events.click({target:inside});assert.equal(sheet.open,true);
 events.click({target:outside});assert.equal(sheet.open,false);assert.equal(focusCount,1);
 sheetEvents.keydown({key:'Escape',preventDefault:()=>prevented++,stopPropagation:()=>{}});
 assert.equal(prevented,1);
});
class Node {
 constructor(tag='div',o={},children=[]){this.tagName=tag;this.attrs=o.attrs||{};this.children=[];this.listeners=o.on||{};this.hidden=false;this.value='';this._text=o.text||'';children.forEach(c=>this.appendChild(c));}
 appendChild(c){this.children.push(typeof c==='string'?{textContent:c}:c);return c;}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 set textContent(t){this._text=t;this.children=[];}
 setAttribute(k,v){this.attrs[k]=v;} getAttribute(k){return this.attrs[k];}
 addEventListener(k,f){this.listeners[k]=f;} focus(){this.focused=true;}
 querySelectorAll(){return this.children.filter(n=>n.attrs&&n.attrs['data-recipe']);}
}
function all(n){return n.children.flatMap(c=>[c,...(c.children?all(c):[])]);}
function harness(){
 const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);};
 const saved={context_case:{case_json:'{"private":9007199254740993}'},request_observations:{private:true},cc_run:{id:'EXPLICIT'},open_run:true};
 const example={context_case:{case_json:'{"exact":9007199254740993}\n',report:{summary:{passed:2,failed:1,not_assessed:1}}},request_observations:{synthetic:true}};
 example.mechanism_evidence={projection:{schema:'cc-context-recipe-evidence/1',recipe_id:'owned-core',mechanisms:[{id:'owned-core-boundary',claims:[{id:'claim-core-fixture',statement:'固定合成 core 的结构判断',level:'synthetic_fixture',source_ids:['source-core'],limits:['实际 request 未评估']}]}],sources:[{id:'source-core',title:'固定 source',kind:'authored_source',revision:'a'.repeat(40),observed_on:'2026-11-13',path:'context_lab/observations.py',locator:{kind:'python_symbol',symbol:'normalize_capture'},url:'https://example.com/fixed',limits:['source 不等于 native']}],caveats:['native 生命周期未执行']},json:'{"fixed":9007199254740993,"recipe_id":"owned-core"}\n',markdown:'# 固定机制依据\n\n9007199254740993 · 旧观察日期保留\n'};
 const data={...saved,recipes:[{id:'owned-core',title:'完整 core',question:'旧指导在哪里？',summary:'SYNTHETIC',guide_path:'docs/handbook/owned-core.md',case_path:'experiments/recipes/cases/owned-core.json',mechanisms:[{id:'owned-core-boundary',title:'Core 的位置',explanation:'机制说明',sources:['docs/context-map.md']}],procedure:['检查原值']}],recipe_examples:{'owned-core':example}};
 const downloads=[],tabs=[];
 const c=vm.createContext({document:{readyState:'loading',addEventListener:()=>{}},console});
 vm.runInContext(fs.readFileSync(path.join(root,'workbench/app.js'),'utf8'),c);
 Object.assign(c,{$:node,getData:()=>data,clear:n=>n.textContent='',el:(tag,o={},kids=[])=>new Node(tag,o,kids),sourceLink:p=>new Node('a',{text:p}),activateTab:(...a)=>tabs.push(a),downloadLocalArtifact:(...a)=>downloads.push(a),caseState:{stepId:'old',filter:'FAIL'},observationState:{baselineId:'private',candidateId:'old',query:'old'},caseAttachment:{markdown:'FIXED PRIVATE ATTACHMENT'},observationAttachment:{markdown:'FIXED OBSERVATION'}});
 vm.runInContext(fs.readFileSync(path.join(root,'workbench/journeys.js'),'utf8'),c);c.wireJourney();
 return {c,data,saved,example,node,downloads,tabs};
}
test('recipe open and return retain exact loaded material and frozen attachments',()=>{
 const h=harness();assert.equal(h.c.selectRecipe('owned-core'),true);
 assert.equal(h.data.context_case,h.example.context_case);assert.equal(h.data.cc_run,null);
 assert.equal(h.c.observationState.baselineId,null);assert.equal(h.c.caseState.filter,'all');
 assert.equal(h.c.caseAttachment.markdown,'FIXED PRIVATE ATTACHMENT');
 h.c.restoreLoadedMaterials();
 assert.equal(h.data.context_case,h.saved.context_case);assert.equal(h.data.cc_run,h.saved.cc_run);
 assert.equal(h.data.request_observations,h.saved.request_observations);assert.deepEqual(h.tabs.at(-1),['run',true]);
});
test('home download uses fixed canonical string without parsing original integers',()=>{
 const h=harness();const btn=all(h.node('journey-detail')).find(n=>n.textContent==='下载固定案例 JSON');btn.listeners.click();
 assert.equal(h.downloads[0][0],h.example.context_case.case_json);assert.match(h.downloads[0][0],/9007199254740993/);
});
test('unknown or prototype recipe cannot replace selected inputs',()=>{
 const h=harness();for(const id of ['unknown','__proto__','constructor'])assert.equal(h.c.selectRecipe(id),false);
 assert.equal(h.data.context_case,h.saved.context_case);assert.equal(h.data.cc_run,h.saved.cc_run);
});
test('auxiliary controls expand honestly; closing active auxiliary view returns home',()=>{
 const h=harness();h.node('tab-run').setAttribute('aria-selected','true');h.c.setResearchTools(true);
 assert.equal(h.node('atlas-research-tabs').hidden,false);h.node('atlas-tools-toggle').listeners.click();
 assert.equal(h.node('atlas-research-tabs').hidden,true);assert.deepEqual(h.tabs.at(-1),['home',true]);
});
test('independent study keeps its own input and is never labeled as selected recipe evidence',()=>{
 const h=harness();h.data.study_plan={title:'EXPLICIT PRIVATE STUDY'};
 h.c.studyState={scenarioId:'PRIVATE-FIXTURE',baseline:{policy_id:'EDITED'}};
 const original=h.c.studyState;h.c.selectRecipe('owned-core');h.c.renderJourneyContext('study');
 assert.equal(h.c.studyState,original);assert.equal(h.data.study_plan.title,'EXPLICIT PRIVATE STUDY');
 assert.match(h.node('journey-context').textContent,/独立 A\/B 研究/);
 assert.match(h.node('journey-context').textContent,/自己的 fixture/);
 assert.ok(!h.node('journey-context').textContent.includes('完整 core'));
 h.c.restoreLoadedMaterials();assert.equal(h.c.studyState,original);
});
test('mechanism inspection shows claim level, exact source identity and limits',()=>{
 const h=harness(),text=h.node('journey-detail').textContent;
 assert.equal(h.c.evidenceLocator({kind:'markdown_heading',heading:'按层研究'}),'markdown_heading: 按层研究');
 for(const value of ['claim-core-fixture','synthetic_fixture','a'.repeat(40),'2026-11-13','normalize_capture','实际 request 未评估','source 不等于 native'])assert.ok(text.includes(value),value);
 assert.ok(!text.includes('本页未准备逐条机制依据'));
});
test('evidence downloads use canonical JSON and Markdown strings unchanged',()=>{
 const h=harness(),buttons=all(h.node('journey-detail'));
 buttons.find(n=>n.textContent==='下载机制依据 JSON').listeners.click();
 buttons.find(n=>n.textContent==='下载机制依据 Markdown').listeners.click();
 assert.equal(h.downloads[0][0],h.example.mechanism_evidence.json);
 assert.equal(h.downloads[1][0],h.example.mechanism_evidence.markdown);
 assert.equal(h.downloads[0][1],'owned-core-mechanism-evidence.json');
 assert.match(h.downloads[0][0],/9007199254740993/);
});
test('fixed evidence survives material switching and can form a brief without invented capabilities',()=>{
 const h=harness();Object.assign(h.c,{selectedCapabilities:()=>[],model:()=>({checks:[],workflow:[]}),baselineRows:()=>[],studyAttachment:null});
 h.c.attachRecipeEvidence('unknown');assert.equal(h.c.recipeEvidenceAttachment,null);
 h.c.attachRecipeEvidence('owned-core');assert.deepEqual(h.tabs.at(-1),['change',true]);
 assert.equal(h.c.hasBriefInputs(),true);
 h.c.renderChangeOutput();assert.equal(h.node('brief-download').disabled,false);
 assert.match(h.node('change-output').textContent,/可以直接下载/);
 const fixed=h.c.recipeEvidenceAttachment;
 h.example.mechanism_evidence={...h.example.mechanism_evidence,markdown:'REPLACED PREVIEW'};
 h.c.selectRecipe('owned-core');h.c.restoreLoadedMaterials();
 assert.equal(h.c.recipeEvidenceAttachment,fixed);
 const brief=h.c.buildBriefMarkdown();assert.ok(brief.includes(fixed.markdown));assert.ok(!brief.includes('REPLACED PREVIEW'));
 assert.ok(brief.includes('_未选择 capability。_'));
 assert.equal(h.c.caseAttachment.markdown,'FIXED PRIVATE ATTACHMENT');
 h.c.renderRecipeEvidenceAttachment();assert.equal(h.node('recipe-brief-attachment').hidden,false);
 all(h.node('recipe-brief-attachment')).find(n=>n.textContent==='下载已固定依据 JSON').listeners.click();
 assert.equal(h.downloads.at(-1)[0],fixed.json);
 h.c.renderChange=()=>h.c.renderRecipeEvidenceAttachment();
 all(h.node('recipe-brief-attachment')).find(n=>n.textContent==='移除机制依据附件').listeners.click();
 assert.equal(h.c.hasBriefInputs(),false);assert.equal(h.node('recipe-brief-attachment').hidden,true);
});
test('an old bundle without bindings states the gap and exposes no evidence export',()=>{
 const h=harness();delete h.example.mechanism_evidence;h.c.renderJourney();
 assert.match(h.node('journey-detail').textContent,/未准备逐条机制依据/);
 assert.ok(!all(h.node('journey-detail')).some(n=>n.textContent==='下载机制依据 JSON'));
 h.c.attachRecipeEvidence('owned-core');assert.equal(h.c.recipeEvidenceAttachment,null);
});
