/* Contract regressions for the real case presenter and brief integration.
 * Synthetic DOM and projection only; Python owns evaluation and serialization. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const test=require('node:test');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const sources=Object.fromEntries(['app','observations','cases'].map(name=>[name,fs.readFileSync(path.join(root,'workbench',name+'.js'),'utf8')]));
const exact='9007199254740993';
const rounded='9007199254740992';

class Element {
  constructor(tag='div',props={},children=[]){
    this.tagName=tag;this.children=[];this.attrs=props.attrs||{};this.listeners={};
    this._text=props.text===undefined?'':String(props.text);this.hidden=false;this.disabled=false;this.value='';
    Object.entries(props.on||{}).forEach(([event,handler])=>this.addEventListener(event,handler));
    children.forEach(child=>this.appendChild(child));
  }
  get textContent(){return this._text+this.children.map(child=>child.textContent).join('');}
  set textContent(value){this._text=String(value);this.children=[];}
  appendChild(child){this.children.push(child);return child;}
  addEventListener(event,handler){this.listeners[event]=handler;}
  fire(event,input={}){assert.equal(typeof this.listeners[event],'function','missing handler '+event);return this.listeners[event](input);}
  getAttribute(key){return this.attrs[key];}
  setAttribute(key,value){this.attrs[key]=String(value);}
  querySelectorAll(selector){return descendants(this,n=>selector==='[data-case-step]'&&Object.hasOwn(n.attrs,'data-case-step'));}
  focus(){this.focused=true;}
  scrollIntoView(){this.scrolled=true;}
}
function descendants(node,predicate){return node.children.flatMap(child=>[...(predicate(child)?[child]:[]),...descendants(child,predicate)]);}
const plain=value=>JSON.parse(JSON.stringify(value));

function harness({noCase=false,safe=true}={}){
  const nodes=new Map();
  const node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
  const observation=id=>({capture_id:id,wire_format:'openai-responses',evidence:{kind:'synthetic_fixture',observed_at:null},
    runtime:{harness:'synthetic',version:null},unresolved_context:[],request_body:{input:[{exact:Number(exact)}]}});
  const captures=['DECOY_FIRST','DECOY_SECOND','CAPTURE_LATE','CAPTURE_EARLY'].map(observation);
  const comparison={baseline:captures[3],candidate:captures[2],alignment:'same_format_json_pointer',runtime_changes:[]};
  const checks=[
    {id:'large',step_id:'early',actual_present:true,actual:Number(exact),expected:Number(exact),status:'PASS'},
    {id:'missing',step_id:'early',actual_present:false,actual:null,expected:null,status:'PASS'},
    {id:'null',step_id:'late',actual_present:true,actual:null,expected:null,status:'FAIL'},
    {id:'blocked',step_id:'absent',actual_present:null,actual:null,expected:null,status:'NOT_ASSESSED'},
  ].map(c=>({requirement_id:'R1',pointer:'/input/0/exact',operator:'equals',reason:'SYNTHETIC '+c.id,...c}));
  const report={case:{case_id:'CASE-EXACT',title:'合成问题',question:'指定位置是否保留原值？',study_plan:{title:'FIXED PLAN'}},
    requirements:[{id:'R1',text:'局部结构要求',level:'request_structure',status:'FAIL',check_ids:checks.map(c=>c.id)},
      {id:'R2',text:'真实行为',level:'model_behavior',status:'NOT_ASSESSED',check_ids:[]}],
    summary:{passed:1,failed:1,not_assessed:1},
    steps:[{id:'early',label:'Earlier',observation:captures[3]},{id:'late',label:'Later',observation:captures[2]},
      {id:'absent',label:'Missing evidence',observation:null}],checks,
    comparisons:[{id:'DECLARED_REVERSE_ORDER',baseline:'early',candidate:'late',status:'COMPARED',comparison},
      {id:'BLOCKED',baseline:'late',candidate:'absent',status:'NOT_ASSESSED',comparison:null}],
    study:{schema:'synthetic-study'},limitations:['SYNTHETIC：导入声明不是独立 runtime 验证']};
  const canonicalBody='{\n  "exact": '+exact+'\n}';
  const projection={report,case_json:'{"case_id":"CASE-EXACT","exact":'+exact+'}\n',
    report_json:'{"case_id":"CASE-EXACT","actual":'+exact+'}\n',markdown:'# CASE-EXACT\n\n'+exact+'\n',
    display:{checks:{large:{expected:exact,actual:exact},missing:{expected:'null',actual:'null'},
      null:{expected:'null',actual:'null'},blocked:{expected:'null',actual:'null'}},
    steps:{early:canonicalBody,late:canonicalBody,absent:null}},study_markdown:'# FIXED STUDY',study_browser_safe:safe};
  const data={context_case:noCase?null:projection,model:{capabilities:[],checks:[],workflow:[]},
    request_observations:{captures,comparisons:{CAPTURE_EARLY:{CAPTURE_LATE:comparison}},reports:{},json_reports:{},display_values:{}}};
  const downloads=[],tabs=[],restores=[];
  const context=vm.createContext({document:{readyState:'loading',addEventListener:()=>{}},console});
  // Suppress app boot, then replace only DOM/environment boundaries. The real
  // buildBriefMarkdown, observation lookup and case handlers remain in use.
  vm.runInContext(sources.app,context,{filename:'workbench/app.js'});
  Object.assign(context,{$:node,getData:()=>data,clear:n=>{n.children=[];n._text='';},
    el:(tag,props={},children=[])=>new Element(tag,props,children),
    activateTab:(...args)=>tabs.push(args),
    restoreStudy:plan=>restores.push(plan),baselineRows:()=>[],selectedCapabilities:()=>[],
    studyState:{baseline:{policy_id:'CURRENT'}},studyAttachment:null});
  vm.runInContext(sources.observations,context,{filename:'workbench/observations.js'});
  context.downloadLocalArtifact=(...args)=>downloads.push(args);
  vm.runInContext(sources.cases,context,{filename:'workbench/cases.js'});
  context.observationState.baselineId='DECOY_FIRST';context.observationState.candidateId='DECOY_SECOND';
  context.wireCase();
  return {context,node,data,projection,downloads,tabs,restores,canonicalBody};
}

test('canonical expected, actual and request body display preserve large integers',()=>{
  const h=harness();h.context.renderCase();
  assert.equal(h.projection.report.checks[0].actual,Number(rounded),'fixture must expose JS precision loss');
  const firstCheck=h.node('case-checks').children[0];
  assert.deepEqual(descendants(firstCheck,n=>n.tagName==='pre').map(n=>n.textContent),[exact,exact]);
  const body=descendants(h.node('case-step-detail'),n=>n.tagName==='pre');
  assert.deepEqual(body.map(n=>n.textContent),[h.canonicalBody]);
  assert.ok(!firstCheck.textContent.includes(rounded));
  assert.match(h.node('case-step-detail').textContent,/origin\/lifecycle unknown/);
  assert.match(h.node('case-summary').textContent,/模型行为与外部交付未评估/);
});

test('all three downloads use frozen canonical text without Number roundtrips',()=>{
  const h=harness();
  const cases=[['case-save','case_json','context-case.json','application/json'],
    ['case-report-json','report_json','context-case-report.json','application/json'],
    ['case-report-md','markdown','context-case.md','text/markdown']];
  for(const [id,key,name,type] of cases){
    h.node(id).fire('click');
    const download=h.downloads.at(-1);
    assert.deepEqual(download,[h.projection[key],name,type]);
    assert.ok(download[0].includes(exact));assert.ok(!download[0].includes(rounded));
  }
});

test('missing location, JSON null and blocked evidence remain three different visible states',()=>{
  const h=harness();h.context.renderCase();
  const cards=h.node('case-checks').children;
  const values=cards.map(card=>descendants(card,n=>n.tagName==='pre').at(-1).textContent);
  assert.equal(values[1],'该位置不存在（不是 JSON null）');
  assert.equal(values[2],'null');
  assert.equal(values[3],'无法判断；没有可用原值');
  assert.match(cards[3].textContent,/NOT_ASSESSED/);
  assert.match(h.node('case-requirements').textContent,/没有可执行的结构检查；不自动通过/);
  h.node('case-filter').fire('change',{target:{value:'NOT_ASSESSED'}});
  assert.equal(h.node('case-checks').children.length,1);
  assert.match(h.node('case-checks').textContent,/blocked/);
  h.context.caseState.stepId='absent';h.context.renderCaseStep();
  assert.match(h.node('case-step-detail').textContent,/没有 capture/);
  assert.equal(descendants(h.node('case-step-detail'),n=>n.tagName==='pre').length,0);
});

test('no case disables case actions while independent study and observation paths remain intact',()=>{
  const h=harness({noCase:true});
  const observationBefore=plain(h.context.observationState),studyBefore=plain(h.context.studyState);
  h.context.renderCase();
  for(const id of ['case-save','case-report-json','case-report-md','case-to-brief']){
    assert.equal(h.node(id).disabled,true);h.node(id).fire('click');
  }
  h.node('case-open-study').fire('click');
  assert.match(h.node('case-question').textContent,/独立 --study\/--capture/);
  assert.equal(h.downloads.length,0);assert.equal(h.tabs.length,0);assert.equal(h.restores.length,0);
  assert.deepEqual(plain(h.context.observationState),observationBefore);
  assert.deepEqual(plain(h.context.studyState),studyBefore);
  assert.equal(h.data.request_observations.captures.length,4);
  assert.equal(h.context.caseAttachment,null);
});

test('declared comparison opens its exact capture pair rather than the first two captures',()=>{
  const h=harness();h.context.renderCase();
  const buttons=descendants(h.node('case-comparisons'),n=>n.tagName==='button');
  assert.equal(buttons[0].disabled,false);assert.equal(buttons[1].disabled,true);
  h.context.observationState.query='stale search';h.context.observationState.selected=99;
  buttons[0].fire('click');
  assert.equal(h.context.observationState.baselineId,'CAPTURE_EARLY');
  assert.equal(h.context.observationState.candidateId,'CAPTURE_LATE');
  assert.equal(h.context.observationState.selected,0);assert.equal(h.context.observationState.query,'');
  assert.equal(h.node('observation-search').value,'');
  assert.equal(h.context.observationComparison(),h.projection.report.comparisons[0].comparison);
  assert.deepEqual(h.tabs.at(-1),['observation',true]);
  const before=plain(h.context.observationState),count=h.tabs.length;
  buttons[1].fire('click');h.context.openCaseComparison('unknown');
  assert.deepEqual(plain(h.context.observationState),before);assert.equal(h.tabs.length,count);
});

test('case attachment and actual brief retain their fixed snapshot through unrelated selections and removal',()=>{
  const h=harness();h.node('case-to-brief').fire('click');
  const fixed=plain(h.context.caseAttachment);
  assert.deepEqual(fixed,{caseId:'CASE-EXACT',caseJson:h.projection.case_json,reportJson:h.projection.report_json,markdown:h.projection.markdown});
  h.context.studyState.baseline.policy_id='CHANGED';h.context.studyAttachment={markdown:'# OTHER STUDY'};
  h.context.observationState.baselineId='CAPTURE_LATE';h.context.observationAttachment={markdown:'# OTHER OBSERVATION'};
  h.context.caseState.stepId='late';h.context.renderCase();
  h.projection.case_json='MUTATED';h.projection.report_json='MUTATED';h.projection.markdown='MUTATED';
  assert.deepEqual(plain(h.context.caseAttachment),fixed);
  const brief=h.context.buildBriefMarkdown();
  assert.ok(brief.includes(fixed.markdown));assert.ok(brief.includes(exact));
  assert.ok(!brief.includes('MUTATED'));
  h.context.renderCaseAttachment();
  const current=plain(h.context.caseState),report=h.context.caseResult();
  descendants(h.node('case-brief-attachment'),n=>n.tagName==='button')[0].fire('click');
  assert.equal(h.context.caseAttachment,null);assert.equal(h.node('case-brief-attachment').hidden,true);
  assert.deepEqual(plain(h.context.caseState),current);assert.equal(h.context.caseResult(),report);
  assert.ok(!h.context.buildBriefMarkdown().includes(fixed.markdown));
});

test('unsafe study restore is blocked even when its handler is invoked directly',()=>{
  const h=harness({safe:false});h.context.renderCase();
  const before=plain(h.context.studyState);
  assert.equal(h.node('case-open-study').disabled,true);
  assert.match(h.node('case-status').textContent,/浏览器安全范围/);
  h.node('case-open-study').fire('click');
  assert.equal(h.restores.length,0);assert.equal(h.tabs.length,0);
  assert.deepEqual(plain(h.context.studyState),before);
  assert.equal(h.projection.case_json.includes(exact),true);
});

test('safe associated study restores the declared plan and restore errors stay visible',()=>{
  const h=harness();h.context.renderCase();
  assert.equal(h.node('case-open-study').disabled,false);
  h.node('case-open-study').fire('click');
  assert.equal(h.restores[0],h.projection.report.case.study_plan);
  assert.deepEqual(h.tabs.at(-1),['study',true]);
  const before=h.tabs.length;
  h.context.restoreStudy=()=>{throw new Error('SYNTHETIC restore rejected');};
  h.node('case-open-study').fire('click');
  assert.equal(h.tabs.length,before);assert.match(h.node('case-status').textContent,/restore rejected/);
});

test('actual study bootstrap refuses unsafe case plans before any restore and explains independent scenarios',()=>{
  const studySource=fs.readFileSync(path.join(root,'workbench/study.js'),'utf8');
  for(const safe of [false,true]){
    const h=harness({safe});h.data.study_plan=h.projection.report.case.study_plan;
    vm.runInContext(studySource,h.context,{filename:'workbench/study.js'});
    let bootstrapRestores=0;
    h.context.setStudyPreset=()=>{};
    h.context.restoreStudy=()=>{bootstrapRestores++;};
    h.context.wireStudy();
    assert.equal(bootstrapRestores,safe?1:0);
    assert.equal(h.node('study-case-notice').hidden,safe);
    if(!safe)assert.match(h.node('study-case-notice').textContent,/独立的合成情境/);
  }
});
