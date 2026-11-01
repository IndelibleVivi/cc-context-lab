/* Presentation of canonical context_lab observations, with no wire parser or
 * requests in the browser. The builder precomputes every included comparison. */
'use strict';

var observationState={baselineId:null,candidateId:null,selected:0,query:'',changesOnly:true};
var observationAttachment=null;

function observationData(){return getData().request_observations||{captures:[],comparisons:{},serializations:{},display_values:{}};}
function observationComparison(){
  if(observationState.candidateId===null)return null;
  var data=observationData(),rows=Object.hasOwn(data.comparisons,observationState.baselineId)?data.comparisons[observationState.baselineId]:null;
  var pair=rows&&Object.hasOwn(rows,observationState.candidateId)?rows[observationState.candidateId]:null;
  return pair?Object.assign({},pair,{baseline:data.captures.find(c=>c.capture_id===pair.baseline_id),
    candidate:data.captures.find(c=>c.capture_id===pair.candidate_id)}):null;
}
function observationView(){
  var comparison=observationComparison();if(comparison)return comparison;
  if(observationState.candidateId!==null)return null;
  var capture=observationData().captures.find(c=>c.capture_id===observationState.baselineId);
  return capture?{single:true,baseline:capture,candidate:null,sections:capture.sections.map(s=>({pointer:s.pointer,change:'observed',baseline:s,candidate:null}))}:null;
}
function observationReportBody(){
  var data=observationData(),view=observationView();if(!view)return '';
  var a=data.serializations[view.baseline.capture_id].markdown;
  return view.single?'# 请求 context 结构观察\n\n'+a+'\n':view.markdown_prefix+'\n'+a+
    '\n\n## Candidate\n\n'+data.serializations[view.candidate.capture_id].markdown+'\n';
}
function observationJsonBody(){
  var data=observationData(),view=observationView();if(!view)return '';
  if(view.single)return data.serializations[view.baseline.capture_id].json+'\n';
  return view.export_tokens.map(function(token){
    if(typeof token==='string')return token;
    var capture=data.serializations[token.capture];
    return token.section===undefined?capture.json:capture.sections[token.section];
  }).join('');
}
function observationJson(){
  var data=observationData(),text=observationJsonBody();if(!text)return '';
  return data.run_evidence_json?'{"schema":"cc-run-observation-export/1","run":'+data.run_evidence_json+',"result":'+text.trimEnd()+'}\n':text;
}
function observationReport(){
  var text=observationReportBody();return text?(observationData().run_markdown||'')+text:'';
}
function observationDisplay(){
  var data=observationData(),view=observationView();if(!view)return null;
  var values={baseline:data.display_values[view.baseline.capture_id],candidate:view.single?null:data.display_values[view.candidate.capture_id]};
  return {bodies:values,sections:view.sections.map(row=>Object.fromEntries(['baseline','candidate'].map(side=>
    [side,row[side]?values[side].sections[row[side].pointer]:null])))};
}
function observationMissingPair(){
  ['observation-identity','observation-limits','observation-sections','observation-detail','observation-bodies'].forEach(id=>clear($(id)));
  $('observation-summary').textContent='未准备此比较。选择单份观察，或下载比较选择后重新构建；这不表示没有变化。';
  var root=$('observation-detail');
  root.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'下载这组比较选择',on:{click:function(){
    downloadLocalArtifact(JSON.stringify([[observationState.baselineId,observationState.candidateId]],null,2)+'\n','comparison-pairs.json','application/json');
  }}}));
  if(getData().context_case)root.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'下载固定 case 输入',on:{click:function(){
    downloadLocalArtifact(getData().context_case.case_json,'context-case.json','application/json');
  }}}));
  root.appendChild(el('pre',{text:observationData().rebuild_command||'python3 scripts/build_context_atlas.py --capture <原 capture> --pairs comparison-pairs.json --out .cache/context-atlas'}));
}
function observationLabel(capture){return capture.capture_id+' · '+capture.wire_format+' · '+capture.evidence.kind;}
function observationScopeLabel(capture){
  var scope=capture.evidence_scope;
  if(!scope||scope.request_body==='complete')return '完整 request body 文件对象';
  return '部分 request body · 已观察顶层字段：'+scope.observed_fields.map(field=>'/'+field).join('、')+
    '；未列出字段未知，不是空值';
}

function renderObservation(){
  var data=observationData(),captures=data.captures;
  var buttons=['observation-download-json','observation-download-markdown','observation-to-brief'];
  if(!captures.length){
    $('observation-summary').textContent='没有请求观察。生成页面时可用 --capture 明确指定本地 capture；默认仅使用合成示例。';
    buttons.forEach(id=>$(id).disabled=true);return;
  }
  if(!captures.some(c=>c.capture_id===observationState.baselineId)) observationState.baselineId=captures[0].capture_id;
  if(observationState.candidateId!==null&&!captures.some(c=>c.capture_id===observationState.candidateId)) observationState.candidateId=null;
  ['baseline','candidate'].forEach(function(side){
    var select=$('observation-'+side);
    if(select.options.length!==captures.length+(side==='candidate'?1:0)){
      clear(select);if(side==='candidate')select.appendChild(el('option',{text:'单份观察 · 不比较',attrs:{value:''}}));captures.forEach(c=>select.appendChild(el('option',{text:observationLabel(c),attrs:{value:c.capture_id}})));
    }
    select.value=observationState[side+'Id']||'';
  });
  var comparison=observationView();
  buttons.forEach(id=>$(id).disabled=!comparison);
  if(!comparison){observationMissingPair();return;}
  var identity=$('observation-identity');clear(identity);
  (comparison.single?['baseline']:['baseline','candidate']).forEach(function(side,i){
    var capture=comparison[side],panel=el('section',{cls:'observation-condition'});
    panel.appendChild(el('h3',{cls:'subhead',text:(i?'B / ':'A / ')+capture.capture_id}));
    panel.appendChild(el('p',{cls:'observation-evidence',text:capture.evidence.kind==='synthetic_fixture'?
      '合成示例 · 没有实际 runtime 捕获':'captured_request · 导入者声明，未独立验证'}));
    panel.appendChild(el('p',{cls:'field__note',text:'声明的 observed_at：'+(capture.evidence.observed_at||'未记录')+'；页面生成日期不替代它。'}));
    panel.appendChild(el('p',{cls:'observation-evidence',text:observationScopeLabel(capture)}));
    var list=el('dl',{cls:'observation-runtime'});
    Object.entries(Object.assign({wire_format:capture.wire_format},capture.runtime)).forEach(function(pair){
      list.appendChild(el('dt',{text:pair[0]}));list.appendChild(el('dd',{text:pair[1]===null?'未记录':String(pair[1])}));
    });panel.appendChild(list);identity.appendChild(panel);
  });
  $('observation-summary').textContent=comparison.single?'单份 request 观察 · 证据范围与原值独立保留；未生成自身比较。':(comparison.alignment==='cross_format_unaligned'?
    '跨 wire format · 不自动配对。相似原文不证明同一来源或输入等价。':
    '同一 wire format · 按 JSON pointer 比较位置，不按来源身份或自然语义配对。')+
    '；证据范围：'+comparison.evidence_scope_alignment+
    '；未观察顶层字段：'+(comparison.unobserved_top_level_fields.join('、')||'无')+
    ' runtime 条件变化：'+(comparison.runtime_changes.join('、')||'无')+
    '；请求顶层字段变化：'+(comparison.changed_top_level_fields.join('、')||'无')+'。';
  var limits=$('observation-limits');clear(limits);
  if(data.run_evidence_json)limits.appendChild(el('p',{text:'本请求来自选定 CC run；content losses、来源声明与关联缺口随 JSON/Markdown 导出。完整 run 在 CC Run 页。'}));
  limits.appendChild(el('p',{text:'origin / lifecycle 保持 unknown。request body 能证明导入文件里有什么，不能证明隐藏 context、模型正确使用或外部交付。'}));
  (comparison.single?['baseline']:['baseline','candidate']).forEach(function(side,i){
    var unresolved=comparison[side].unresolved_context;
    if(unresolved.length) limits.appendChild(el('p',{text:(i?'B':'A')+' 仍有未展开的 context：'+unresolved.join('；')}));
  });
  renderObservationSections();
  var bodies=$('observation-bodies');clear(bodies);
  (comparison.single?['baseline']:['baseline','candidate']).forEach(function(side,i){
    var partial=comparison[side].evidence_scope?.request_body==='partial';
    bodies.appendChild(el('div',{},[el('h4',{text:(i?'B / ':'A / ')+
      (partial?'声明的部分 request body（不是完整请求）':'完整 body')}),
      el('pre',{text:observationDisplay().bodies[side].body}),
      el('h4',{text:partial?'观察到的其余 request parameters':'其余 request parameters'}),
      el('pre',{text:observationDisplay().bodies[side].parameters})]));
  });
}
function renderObservationSections(){
  var comparison=observationView(),root=$('observation-sections');clear(root);
  if(!comparison)return;
  var q=observationState.query.trim().toLowerCase();
  var rows=comparison.sections.map((row,index)=>({row,index})).filter(function(item){
    return (!observationState.changesOnly||item.row.change!=='unchanged')&&
      (!q||(item.row.pointer+' '+item.row.change+' '+(item.row.baseline||item.row.candidate).kind+' '+
        Object.values(observationDisplay().sections[item.index]).filter(s=>s!==null).join(' ')).toLowerCase().includes(q));
  });
  if(!rows.some(item=>item.index===observationState.selected)) observationState.selected=rows[0]?.index??null;
  rows.forEach(function(item){
    var row=item.row,section=row.candidate||row.baseline;
    root.appendChild(el('button',{cls:'study-source-btn',attrs:{type:'button','data-observation-row':item.index,
      'aria-pressed':String(item.index===observationState.selected)},on:{click:function(){
        observationState.selected=item.index;renderObservationSections();
        root.querySelector('[data-observation-row="'+item.index+'"]').focus();
      }}},[el('span',{text:row.pointer}),el('small',{text:row.change+' · '+section.kind})]));
  });
  var detail=$('observation-detail');clear(detail);
  if(!rows.length){detail.appendChild(el('p',{cls:'empty-state',text:'没有匹配 section。关闭“只看变化”或清空检索可查看完整结构。'}));return;}
  var row=comparison.sections[observationState.selected];
  detail.appendChild(el('h3',{cls:'study-source-title',text:row.pointer}));
  detail.appendChild(el('p',{cls:'study-legend',text:row.change+(comparison.single?' · 单份结构原值；':' · 位置对照；')+'origin 与 lifecycle 未由消息 role 推定。'}));
  var grid=el('div',{cls:'study-trace-columns observation-values'});
  (comparison.single?['baseline']:['baseline','candidate']).forEach(function(side,i){
    var section=row[side],column=el('section',{cls:'observation-value'});
    column.appendChild(el('h4',{text:i?'B / 原值':'A / 原值'}));
    if(!section){column.appendChild(el('p',{text:'此侧没有匹配位置；不表示来源已全局删除。'}));}
    else{
      column.appendChild(el('p',{cls:'field__note',text:'kind='+section.kind+' · role='+String(section.role)+
        ' · origin='+section.origin+' · lifecycle='+section.lifecycle}));
      column.appendChild(el('pre',{text:observationDisplay().sections[observationState.selected][side]}));
    }grid.appendChild(column);
  });detail.appendChild(grid);
  if(row.change==='unobserved'){
    detail.appendChild(el('p',{cls:'observation-limits',text:'至少一侧未观察此字段；不能判为 added、removed 或不存在。'}));
  }
}
function downloadLocalArtifact(value,name,type){
  var url=URL.createObjectURL(new Blob([value],{type:type+';charset=utf-8'}));
  var a=el('a',{attrs:{href:url,download:name}});document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),60000);
}
function downloadObservation(value,name,type){
  downloadLocalArtifact(value,name,type);
  $('observation-status').textContent='已在本地生成 '+name+'；导入声明的证据层级保持原样。';
}
function attachObservation(){
  var comparison=observationView();if(!comparison)return;
  observationAttachment={baselineId:comparison.baseline.capture_id,candidateId:comparison.candidate?.capture_id||null,
    jsonText:observationJson(),markdown:observationReport()};
  ['core','tools','hooks','channel','history'].forEach(id=>changeState.caps[id]=true);
  changeState.intent=null;activateTab('change',true);
}
function renderObservationAttachment(){
  var root=$('observation-brief-attachment');clear(root);root.hidden=!observationAttachment;
  if(!observationAttachment)return;
  root.appendChild(el('strong',{text:observationAttachment.kind==='cc_run'?'已附完整 CC Run：'+observationAttachment.baselineId:
    '已附请求观察：'+observationAttachment.baselineId+(observationAttachment.candidateId?' → '+observationAttachment.candidateId:' · 单份观察')}));
  root.appendChild(el('p',{text:'固定带入时的原值与导入者声明；不产生 runtime 兼容性、模型使用或交付结论。'}));
  root.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'移除请求观察附件',on:{click:function(){
    observationAttachment=null;renderObservationAttachment();updateBriefPreview();
  }}}));
}
function wireObservation(){
  ['baseline','candidate'].forEach(side=>$('observation-'+side).addEventListener('change',function(e){
    observationState[side+'Id']=e.target.value||null;observationState.selected=0;renderObservation();
  }));
  $('observation-search').addEventListener('input',e=>{observationState.query=e.target.value;renderObservationSections();});
  $('observation-changes-only').addEventListener('change',e=>{observationState.changesOnly=e.target.checked;renderObservationSections();});
  $('observation-download-json').addEventListener('click',function(){
    if(observationView())downloadObservation(observationJson(),observationData().run_evidence_json?'cc-run-observation.json':observationView().single?'request-observation.json':'request-comparison.json','application/json');
  });
  $('observation-download-markdown').addEventListener('click',function(){
    if(observationView())downloadObservation(observationReport(),'request-observation.md','text/markdown');
  });
  $('observation-to-brief').addEventListener('click',attachObservation);
}
