/* Synthetic VM checks of the real observation presenter; no browser/network. */
'use strict';

const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const test=require('node:test');
const vm=require('node:vm');

const source=fs.readFileSync(path.join(__dirname,'../workbench/observations.js'),'utf8');
const exact='9007199254740993';
const rounded='9007199254740992';

class Element {
  constructor(tag='div',props={},children=[]){
    this.tagName=tag;this.children=[];this.listeners={};this.attrs=props.attrs||{};
    this._text=props.text===undefined?'':String(props.text);this.hidden=false;this.disabled=false;
    this.value='';this.checked=false;
    Object.entries(props.on||{}).forEach(([name,handler])=>this.addEventListener(name,handler));
    children.forEach(child=>this.appendChild(child));
  }
  get textContent(){return this._text+this.children.map(child=>child.textContent).join('');}
  set textContent(value){this._text=String(value);this.children=[];}
  get options(){return this.children;}
  appendChild(child){this.children.push(child);return child;}
  addEventListener(name,handler){this.listeners[name]=handler;}
  fire(name,event={}){assert.ok(this.listeners[name],`missing ${name} listener`);return this.listeners[name](event);}
  querySelector(selector){
    const match=selector.match(/\[data-observation-row="(\d+)"\]/);
    return this.children.find(child=>match&&String(child.attrs['data-observation-row'])===match[1])||null;
  }
  focus(){this.focused=true;}
  click(){if(this.listeners.click)this.fire('click');}
  remove(){}
}

function all(root,predicate){return [...(predicate(root)?[root]:[]),...root.children.flatMap(child=>all(child,predicate))];}

function setup(){
  const elements=new Map();
  const get=id=>{if(!elements.has(id))elements.set(id,new Element(id.includes('baseline')||id.includes('candidate')?'select':'div'));return elements.get(id);};
  const capture=id=>({capture_id:id,wire_format:'openai-responses',evidence:{kind:'synthetic_fixture',observed_at:null},
    evidence_scope:{request_body:'complete',observed_fields:null},
    runtime:{harness:'synthetic',version:null},unresolved_context:[],sections:[]});
  const a=capture('A'),b=capture('B');
  const section={pointer:'/input/0',kind:'opaque',role:null,origin:'unknown',lifecycle:'unknown',value:{exact:Number(exact)}};
  const comparison={baseline:a,candidate:b,alignment:'same_format_json_pointer',evidence_scope_alignment:'complete',
    runtime_changes:[],comparable_top_level_fields:['input'],unobserved_top_level_fields:[],changed_top_level_fields:['input'],
    sections:[{pointer:'/input/0',change:'modified',baseline:section,candidate:{...section}},
              {pointer:'/input/1',change:'unchanged',baseline:{...section,pointer:'/input/1'},candidate:{...section,pointer:'/input/1'}}]};
  const jsonText='{"schema":"harness-context-comparison/1","synthetic_exact":'+exact+'}\n';
  const markdown='# SYNTHETIC canonical Markdown\n\n'+exact+'\n\n## Candidate\n\nBODY B\n';
  const value='{\n  "exact": '+exact+'\n}';
  const display={sections:[{baseline:value,candidate:value},{baseline:'UNCHANGED SYNTHETIC',candidate:'UNCHANGED SYNTHETIC'}],
    bodies:{baseline:{body:value,parameters:value},candidate:{body:value,parameters:value}}};
  const data={captures:[a,b],comparisons:{A:{B:{...comparison,baseline_id:'A',candidate_id:'B',export_tokens:[jsonText],markdown_prefix:'# SYNTHETIC canonical Markdown\n'}},
    B:{A:{...comparison,baseline_id:'B',candidate_id:'A',export_tokens:['{"reverse":true}\n'],markdown_prefix:'# REVERSED'}}},
    serializations:{A:{json:'{"exact":'+exact+'}',markdown:exact,sections:{}},B:{json:'{}',markdown:'BODY B',sections:{}}},
    display_values:{A:{body:value,parameters:value,sections:{'/input/0':value,'/input/1':'UNCHANGED SYNTHETIC'}},
      B:{body:value,parameters:value,sections:{'/input/0':value,'/input/1':'UNCHANGED SYNTHETIC'}}}};
  a.sections=[section,{...section,pointer:'/input/1'}];b.sections=a.sections;
  const downloads=[],activated=[],preview=[];
  const context=vm.createContext({getData:()=>({request_observations:data}),$:get,
    clear:element=>{element.children=[];element._text='';},el:(tag,props={},children=[])=>new Element(tag,props,children),
    changeState:{caps:{},intent:'synthetic'},activateTab:(...args)=>activated.push(args),updateBriefPreview:()=>preview.push(true),
    document:{body:new Element('body')},URL:{createObjectURL:()=> 'blob:synthetic',revokeObjectURL:()=>{}},
    Blob:class {constructor(parts,options){this.parts=parts;this.options=options;}},setTimeout:()=>0});
  vm.runInContext(source,context,{filename:'workbench/observations.js'});
  context.observationState.baselineId='A';context.observationState.candidateId='B';
  context.downloadObservation=(...args)=>downloads.push(args);
  return {context,data,get,downloads,activated,preview,jsonText,markdown,value};
}

test('canonical comparison JSON and download preserve integers outside JS Number precision',()=>{
  const {context,jsonText,downloads,get}=setup();
  assert.equal('request_body' in context.observationComparison().baseline,false);
  assert.equal(context.observationJson(),jsonText);
  context.wireObservation();
  get('observation-download-json').fire('click');
  assert.equal(downloads.length,1);
  assert.equal(downloads[0][0],jsonText);
  assert.equal(downloads[0][1],'request-comparison.json');
  assert.equal(downloads[0][2],'application/json');
  assert.ok(downloads[0][0].includes(exact));
  assert.ok(!downloads[0][0].includes(rounded));
});

test('body, parameters and section details display canonical strings rather than rounded payloads',()=>{
  const {context,get,value}=setup();
  context.renderObservation();
  const bodyValues=all(get('observation-bodies'),element=>element.tagName==='pre').map(element=>element.textContent);
  assert.deepEqual(bodyValues,[value,value,value,value]);
  const sectionValues=all(get('observation-detail'),element=>element.tagName==='pre').map(element=>element.textContent);
  assert.deepEqual(sectionValues,[value,value]);
  assert.ok(!get('observation-bodies').textContent.includes(rounded));
  assert.match(get('observation-limits').textContent,/unknown/);
  assert.match(get('observation-identity').textContent,/合成/);
  assert.match(get('observation-identity').textContent,/完整 request body 文件对象/);
  assert.match(get('observation-summary').textContent,/evidence|complete|证据范围/);
});

test('partial scope labels observed fields and renders unobserved comparison rows without implying removal',()=>{
  const {context,data,get}=setup();
  const baseline={...data.captures[0],
    evidence_scope:{request_body:'partial',observed_fields:['system','tools']},
    request_body:{system:'SYNTHETIC SYSTEM',tools:[]}};
  const candidate={...data.captures[1],
    evidence_scope:{request_body:'partial',observed_fields:['system','tools','messages']},
    request_body:{system:'SYNTHETIC SYSTEM',tools:[],messages:[]}};
  const section={pointer:'/messages',kind:'message',role:null,origin:'unknown',lifecycle:'unknown',value:[]};
  data.captures[0]=baseline;data.captures[1]=candidate;
  data.comparisons.A.B={...data.comparisons.A.B,
    evidence_scope_alignment:'partial_scope_mismatch',
    comparable_top_level_fields:['system','tools'],unobserved_top_level_fields:['messages'],
    changed_top_level_fields:[],
    sections:[{pointer:'/system',change:'unchanged',baseline_observed:true,candidate_observed:true,
      baseline:{...section,pointer:'/system',kind:'instructions',value:'SYNTHETIC SYSTEM'},
      candidate:{...section,pointer:'/system',kind:'instructions',value:'SYNTHETIC SYSTEM'}},
      {pointer:'/messages',change:'unobserved',baseline_observed:false,candidate_observed:true,
        baseline:null,candidate:section}]};
  data.display_values.A={body:'{"system":"SYNTHETIC SYSTEM","tools":[]}',parameters:'{}',sections:{'/system':'SYNTHETIC SYSTEM'}};
  data.display_values.B={body:'{"system":"SYNTHETIC SYSTEM","tools":[],"messages":[]}',parameters:'{}',
    sections:{'/system':'SYNTHETIC SYSTEM','/messages':'[]'}};
  context.observationState.selected=1;
  context.renderObservation();
  assert.match(get('observation-identity').textContent,/部分 request body/);
  assert.match(get('observation-identity').textContent,/未列出字段未知，不是空值/);
  assert.match(get('observation-summary').textContent,/partial_scope_mismatch/);
  assert.match(get('observation-summary').textContent,/messages/);
  assert.match(get('observation-detail').textContent,/不能判为 added、removed 或不存在/);
});

test('raw body headings reflect each side scope independently',()=>{
  const {context,data,get}=setup();
  const complete={...data.captures[0],
    evidence_scope:{request_body:'complete',observed_fields:null}};
  const partial={...data.captures[1],
    evidence_scope:{request_body:'partial',observed_fields:['system','tools']}};
  data.captures[0]=complete;data.captures[1]=partial;
  data.comparisons.A.B={...data.comparisons.A.B,
    evidence_scope_alignment:'partial_scope_mismatch',
    comparable_top_level_fields:['system','tools'],unobserved_top_level_fields:[],
    changed_top_level_fields:[],
    sections:[{pointer:'/system',change:'unchanged',baseline_observed:true,candidate_observed:true,
      baseline:{pointer:'/system',kind:'instructions',role:null,origin:'unknown',lifecycle:'unknown',value:'SYNTHETIC'},
      candidate:{pointer:'/system',kind:'instructions',role:null,origin:'unknown',lifecycle:'unknown',value:'SYNTHETIC'}}]};
  data.display_values.A.B={...data.display_values.A.B,
    bodies:{baseline:{body:'{"system":"SYNTHETIC","tools":[]}',parameters:'{}'},
      candidate:{body:'{"system":"SYNTHETIC","tools":[]}',parameters:'{}'}},
    sections:[{baseline:'SYNTHETIC',candidate:'SYNTHETIC'}]};
  context.renderObservation();
  const headings=all(get('observation-bodies'),element=>element.tagName==='h4').map(element=>element.textContent);
  assert.ok(headings.includes('A / 完整 body'));
  assert.ok(headings.includes('B / 声明的部分 request body（不是完整请求）'));
  assert.ok(!headings.includes('B / 完整 body'));
  assert.ok(headings.includes('观察到的其余 request parameters'));
});

test('section search finds canonical integer text and continues to find pointer/kind metadata',()=>{
  const {context,get}=setup();
  context.observationState.query=exact;
  context.renderObservationSections();
  assert.equal(get('observation-sections').children.length,1);
  assert.match(get('observation-detail').textContent,new RegExp(exact));
  context.observationState.query=rounded;
  context.renderObservationSections();
  assert.equal(get('observation-sections').children.length,0,'rounded Number payload must not be searchable as the original value');
  for(const query of ['/input/0','opaque']){
    context.observationState.query=query;
    context.renderObservationSections();
    assert.equal(get('observation-sections').children.length,1,query);
  }
  context.observationState.query='';context.observationState.changesOnly=false;
  context.renderObservationSections();
  assert.equal(get('observation-sections').children.length,2);
});

test('Markdown export uses the canonical report without reserializing values',()=>{
  const {context,get,downloads,markdown}=setup();
  context.wireObservation();get('observation-download-markdown').fire('click');
  assert.equal(downloads[0][0],markdown);
  assert.equal(downloads[0][1],'request-observation.md');
});

test('attachment freezes canonical JSON, Markdown and capture IDs across comparison changes and removal',()=>{
  const {context,data,get,activated,preview,jsonText,markdown}=setup();
  context.attachObservation();
  assert.equal(context.observationAttachment.jsonText,jsonText);
  assert.equal(context.observationAttachment.markdown,markdown);
  assert.equal(context.observationAttachment.baselineId,'A');
  assert.equal(context.observationAttachment.candidateId,'B');
  assert.equal(activated[0][0],'change');
  context.observationState.baselineId='B';context.observationState.candidateId='A';
  data.comparisons.A.B.export_tokens=['MUTATED'];data.comparisons.A.B.markdown_prefix='MUTATED';
  assert.equal(context.observationAttachment.jsonText,jsonText);
  assert.equal(context.observationAttachment.markdown,markdown);
  context.renderObservationAttachment();
  assert.match(get('observation-brief-attachment').textContent,/A → B/);
  const remove=all(get('observation-brief-attachment'),element=>element.tagName==='button')[0];
  remove.fire('click');
  assert.equal(context.observationAttachment,null);
  assert.equal(context.observationState.baselineId,'B');
  assert.equal(context.observationState.candidateId,'A');
  assert.equal(context.observationJson(),'{"reverse":true}\n');
  assert.equal(get('observation-brief-attachment').hidden,true);
  assert.equal(preview.length,1);
});


test('missing comparison clears prior values and supplies a rebuild selection',()=>{
  const {context,data,get}=setup();context.renderObservation();
  delete data.comparisons.A.B;
  context.renderObservation();
  assert.match(get('observation-summary').textContent,/未准备此比较/);
  assert.equal(get('observation-bodies').textContent,'');
  assert.equal(get('observation-identity').textContent,'');
  assert.equal(get('observation-download-json').disabled,true);
  assert.match(get('observation-detail').textContent,/comparison-pairs.json/);
});

test('capture selectors follow replacement materials even when the count is unchanged',()=>{
  const {context,data,get}=setup();context.renderObservation();
  data.captures=data.captures.map((capture,index)=>({...capture,capture_id:['C','D'][index]}));
  data.serializations.C=data.serializations.A;data.serializations.D=data.serializations.B;
  data.display_values.C=data.display_values.A;data.display_values.D=data.display_values.B;
  context.renderObservation();
  assert.deepEqual(get('observation-baseline').options.map(option=>option.attrs.value),['C','D']);
  assert.deepEqual(get('observation-candidate').options.map(option=>option.attrs.value),['','C','D']);
  assert.equal(get('observation-baseline').value,'C');
  assert.equal(get('observation-candidate').value,'');
  assert.match(get('observation-identity').textContent,/A \/ C/);
  assert.equal(context.observationJson(),data.serializations.C.json+'\n');
});

test('capture selector labels refresh while preserving a valid selected pair',()=>{
  const {context,data,get,jsonText}=setup();context.renderObservation();
  data.captures[0]={...data.captures[0],evidence:{kind:'captured_request',observed_at:null}};
  context.renderObservation();
  assert.match(get('observation-baseline').options[0].textContent,/captured_request/);
  assert.equal(get('observation-baseline').value,'A');
  assert.equal(get('observation-candidate').value,'B');
  assert.equal(context.observationJson(),jsonText);
});

test('empty materials clear old evidence and recover without changing frozen attachments',()=>{
  const {context,data,get,jsonText}=setup();context.renderObservation();context.attachObservation();
  const captures=data.captures;data.captures=[];
  context.renderObservation();
  for(const side of ['baseline','candidate']){
    assert.equal(get('observation-'+side).options.length,0);
    assert.equal(get('observation-'+side).value,'');
    assert.equal(get('observation-'+side).disabled,true);
  }
  for(const id of ['observation-identity','observation-limits','observation-sections','observation-detail','observation-bodies'])
    assert.equal(get(id).textContent,'',id);
  for(const id of ['observation-download-json','observation-download-markdown','observation-to-brief'])
    assert.equal(get(id).disabled,true);
  assert.match(get('observation-summary').textContent,/没有请求观察/);
  assert.equal(context.observationView(),null);
  assert.equal(context.observationAttachment.jsonText,jsonText);
  data.captures=captures;context.renderObservation();
  assert.equal(get('observation-baseline').disabled,false);
  assert.equal(get('observation-candidate').disabled,false);
  assert.equal(get('observation-baseline').value,'A');
  assert.equal(get('observation-candidate').value,'');
  assert.equal(get('observation-download-json').disabled,false);
  assert.equal(context.observationAttachment.jsonText,jsonText);
});

test('single request renders independently and never needs a self comparison',()=>{
  const {context,data,get}=setup();context.observationState.candidateId=null;
  context.renderObservation();
  assert.match(get('observation-summary').textContent,/单份 request/);
  assert.equal(context.observationComparison(),null);
  assert.equal(context.observationJson(),data.serializations.A.json+'\n');
  assert.equal(get('observation-download-json').disabled,false);
});

test('special legal IDs use own pair keys and null sentinel never selects string null',()=>{
  for(const id of ['toString','constructor','__proto__']){
    const {context,data,get}=setup();
    data.captures.push({...data.captures[0],capture_id:id});
    context.observationState.candidateId=id;
    assert.equal(context.observationComparison(),null);
    assert.doesNotThrow(()=>context.renderObservation());
    assert.match(get('observation-summary').textContent,/未准备/);
    context.observationState.baselineId=id;context.observationState.candidateId='B';
    assert.equal(context.observationComparison(),null);
  }
  const {context,data}=setup();
  data.comparisons.A.null={...data.comparisons.A.B};
  context.observationState.candidateId=null;
  assert.equal(context.observationComparison(),null);
  assert.equal(context.observationView().single,true);
});
