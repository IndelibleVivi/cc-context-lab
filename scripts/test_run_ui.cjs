/* Run presenter tests exercise the actual UI logic without a browser/parser. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const test=require('node:test');
const vm=require('node:vm');
class Element {
  constructor(tag,props={},children=[]){this.tagName=tag;this.attrs=props.attrs||{};this._text=props.text||'';this.children=children;this.listeners=props.on||{};}
  appendChild(child){this.children.push(child);return child;}
  addEventListener(name,handler){this.listeners[name]=handler;}
  querySelectorAll(){return this.children.filter(c=>c.attrs['data-run-request']);}
  getAttribute(name){return this.attrs[name];}
  focus(){this.focused=true;}
  get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
  set textContent(value){this._text=value;this.children=[];}
  click(){this.listeners.click();}
}
function all(element,tag){return [...(element.tagName===tag?[element]:[]),...element.children.flatMap(c=>all(c,tag))];}
function setup(){
  const elements=new Map(),get=id=>{if(!elements.has(id))elements.set(id,new Element('div'));return elements.get(id);};
  const data={run_id:'synthetic',title:'SYNTHETIC · 2 requests',conditions_text:'NOT_ASSESSED',gap_summary:'响应存在不等于送达',gaps_text:'{"redacted":true}',
    bundle_json:'{"exact":9007199254740993}\n',markdown:'# Run · NOT_ASSESSED\n',requests:[
      {id:'r1',capture_id:'r1',group:'recorded group',label:'matched / present',scope_text:'完整文件对象',exact_text:'R1 original'},
      {id:'r2',capture_id:'r2',group:'unknown group',label:'unindexed / unassessed',scope_text:'partial · system/tools',exact_text:'R2 original'}]};
  const downloads=[],activated=[],state={cc_run:data};
  const context=vm.createContext({getData:()=>state,$:get,clear:e=>{e.children=[];e._text='';},el:(...args)=>new Element(...args),
    observationState:{},observationAttachment:null,changeState:{caps:{},intent:'preset'},activateTab:(...args)=>activated.push(args),
    downloadLocalArtifact:(...args)=>downloads.push(args)});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../workbench/runs.js'),'utf8'),context);
  context.wireRun();return {context,get,data,state,downloads,activated};
}
test('run preserves unindexed requests, scopes and separate evidence limits',()=>{
  const {context,get}=setup();context.renderRun();
  assert.match(get('run-requests').textContent,/unindexed/);
  assert.match(get('run-detail').textContent,/响应存在不等于送达/);
  assert.match(get('run-fingerprint').textContent,/NOT_ASSESSED/);
  all(get('run-requests'),'button')[1].click();
  assert.equal(all(get('run-requests'),'button')[1].focused,true);
  assert.match(get('run-detail').textContent,/partial/);
  assert.match(get('run-detail').textContent,/R2 original/);
});
test('open request selects its own capture with no fabricated comparison',()=>{
  const {context,get,activated}=setup();context.renderRun();
  all(get('run-requests'),'button')[1].click();
  all(get('run-detail'),'button')[0].click();
  assert.equal(context.observationState.baselineId,'r2');
  assert.equal(context.observationState.candidateId,null);
  assert.equal(activated[0][0],'observation');
});
test('snapshot and brief retain exact canonical strings across later state changes',()=>{
  const {context,get,data,downloads}=setup();context.renderRun();
  const original=data.bundle_json;get('run-download').click();
  assert.equal(downloads[0][0],original);
  assert.match(downloads[0][0],/9007199254740993/);
  get('run-to-brief').click();data.bundle_json='changed';
  assert.equal(context.observationAttachment.kind,'cc_run');
  assert.equal(context.observationAttachment.jsonText,original);
  assert.match(context.observationAttachment.markdown,/NOT_ASSESSED/);
});
test('event-only input has no imaginary request; absent run clears old details',()=>{
  const {context,get,data,state}=setup();data.requests=[];context.renderRun();
  assert.match(get('run-detail').textContent,/没有 request/);
  assert.equal(all(get('run-detail'),'button').length,0);
  state.cc_run=null;context.renderRun();
  assert.equal(get('run-detail').textContent,'');
  assert.equal(get('run-download').disabled,true);
});
