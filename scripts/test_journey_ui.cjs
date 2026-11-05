'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
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
 const data={...saved,recipes:[{id:'owned-core',title:'完整 core',question:'旧指导在哪里？',summary:'SYNTHETIC',guide_path:'docs/handbook/owned-core.md',case_path:'experiments/recipes/cases/owned-core.json',mechanisms:[],procedure:['检查原值']}],recipe_examples:{'owned-core':example}};
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
