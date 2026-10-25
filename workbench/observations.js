/* Presentation of canonical context_lab observations, with no wire parser or
 * requests in the browser. The builder precomputes every included comparison. */
'use strict';

var observationState={baselineId:null,candidateId:null,selected:0,query:'',changesOnly:true};
var observationAttachment=null;

function observationData(){return getData().request_observations||{captures:[],comparisons:{},reports:{}};}
function observationComparison(){
  return observationData().comparisons[observationState.baselineId]?.[observationState.candidateId]||null;
}
function observationReport(){return observationData().reports[observationState.baselineId]?.[observationState.candidateId]||'';}
function observationJson(){return observationData().json_reports[observationState.baselineId]?.[observationState.candidateId]||'';}
function observationDisplay(){return observationData().display_values[observationState.baselineId]?.[observationState.candidateId];}
function observationLabel(capture){return capture.capture_id+' · '+capture.wire_format+' · '+capture.evidence.kind;}

function renderObservation(){
  var data=observationData(),captures=data.captures;
  var buttons=['observation-download-json','observation-download-markdown','observation-to-brief'];
  if(!captures.length){
    $('observation-summary').textContent='没有请求观察。生成页面时可用 --capture 明确指定本地 capture；默认仅使用合成示例。';
    buttons.forEach(id=>$(id).disabled=true);return;
  }
  if(!captures.some(c=>c.capture_id===observationState.baselineId)) observationState.baselineId=captures[0].capture_id;
  if(!captures.some(c=>c.capture_id===observationState.candidateId)) observationState.candidateId=(captures[1]||captures[0]).capture_id;
  ['baseline','candidate'].forEach(function(side){
    var select=$('observation-'+side);
    if(select.options.length!==captures.length){
      clear(select);captures.forEach(c=>select.appendChild(el('option',{text:observationLabel(c),attrs:{value:c.capture_id}})));
    }
    select.value=observationState[side+'Id'];
  });
  var comparison=observationComparison();
  buttons.forEach(id=>$(id).disabled=!comparison);
  if(!comparison){$('observation-summary').textContent='当前投影缺少这组比较，重新生成页面后再试。';return;}
  var identity=$('observation-identity');clear(identity);
  ['baseline','candidate'].forEach(function(side,i){
    var capture=comparison[side],panel=el('section',{cls:'observation-condition'});
    panel.appendChild(el('h3',{cls:'subhead',text:(i?'B / ':'A / ')+capture.capture_id}));
    panel.appendChild(el('p',{cls:'observation-evidence',text:capture.evidence.kind==='synthetic_fixture'?
      '合成示例 · 没有实际 runtime 捕获':'captured_request · 导入者声明，未独立验证'}));
    panel.appendChild(el('p',{cls:'field__note',text:'声明的 observed_at：'+(capture.evidence.observed_at||'未记录')+'；页面生成日期不替代它。'}));
    var list=el('dl',{cls:'observation-runtime'});
    Object.entries(Object.assign({wire_format:capture.wire_format},capture.runtime)).forEach(function(pair){
      list.appendChild(el('dt',{text:pair[0]}));list.appendChild(el('dd',{text:pair[1]===null?'未记录':String(pair[1])}));
    });panel.appendChild(list);identity.appendChild(panel);
  });
  $('observation-summary').textContent=(comparison.alignment==='cross_format_unaligned'?
    '跨 wire format · 不自动配对。相似原文不证明同一来源或输入等价。':
    '同一 wire format · 按 JSON pointer 比较位置，不按来源身份或自然语义配对。')+
    ' runtime 条件变化：'+(comparison.runtime_changes.join('、')||'无')+
    '；请求顶层字段变化：'+(comparison.changed_top_level_fields.join('、')||'无')+'。';
  var limits=$('observation-limits');clear(limits);
  limits.appendChild(el('p',{text:'origin / lifecycle 保持 unknown。request body 能证明导入文件里有什么，不能证明隐藏 context、模型正确使用或外部交付。'}));
  ['baseline','candidate'].forEach(function(side,i){
    var unresolved=comparison[side].unresolved_context;
    if(unresolved.length) limits.appendChild(el('p',{text:(i?'B':'A')+' 仍有未展开的 context：'+unresolved.join('；')}));
  });
  renderObservationSections();
  var bodies=$('observation-bodies');clear(bodies);
  ['baseline','candidate'].forEach(function(side,i){
    bodies.appendChild(el('div',{},[el('h4',{text:i?'B / 完整 body':'A / 完整 body'}),
      el('pre',{text:observationDisplay().bodies[side].body}),
      el('h4',{text:'其余 request parameters'}),el('pre',{text:observationDisplay().bodies[side].parameters})]));
  });
}
function renderObservationSections(){
  var comparison=observationComparison(),root=$('observation-sections');clear(root);
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
  detail.appendChild(el('p',{cls:'study-legend',text:row.change+' · 位置对照；origin 与 lifecycle 未由消息 role 推定。'}));
  var grid=el('div',{cls:'study-trace-columns observation-values'});
  ['baseline','candidate'].forEach(function(side,i){
    var section=row[side],column=el('section',{cls:'observation-value'});
    column.appendChild(el('h4',{text:i?'B / 原值':'A / 原值'}));
    if(!section){column.appendChild(el('p',{text:'此侧没有匹配位置；不表示来源已全局删除。'}));}
    else{
      column.appendChild(el('p',{cls:'field__note',text:'kind='+section.kind+' · role='+String(section.role)+
        ' · origin='+section.origin+' · lifecycle='+section.lifecycle}));
      column.appendChild(el('pre',{text:observationDisplay().sections[observationState.selected][side]}));
    }grid.appendChild(column);
  });detail.appendChild(grid);
}
function downloadObservation(value,name,type){
  var url=URL.createObjectURL(new Blob([value],{type:type+';charset=utf-8'}));
  var a=el('a',{attrs:{href:url,download:name}});document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),60000);
  $('observation-status').textContent='已在本地生成 '+name+'；导入声明的证据层级保持原样。';
}
function attachObservation(){
  var comparison=observationComparison();if(!comparison)return;
  observationAttachment={baselineId:comparison.baseline.capture_id,candidateId:comparison.candidate.capture_id,
    jsonText:observationJson(),markdown:observationReport()};
  ['core','tools','hooks','channel','history'].forEach(id=>changeState.caps[id]=true);
  changeState.intent=null;activateTab('change',true);
}
function renderObservationAttachment(){
  var root=$('observation-brief-attachment');clear(root);root.hidden=!observationAttachment;
  if(!observationAttachment)return;
  root.appendChild(el('strong',{text:'已附请求观察：'+observationAttachment.baselineId+' → '+observationAttachment.candidateId}));
  root.appendChild(el('p',{text:'固定带入时的原值与导入者声明；不产生 runtime 兼容性、模型使用或交付结论。'}));
  root.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'移除请求观察附件',on:{click:function(){
    observationAttachment=null;renderObservationAttachment();updateBriefPreview();
  }}}));
}
function wireObservation(){
  ['baseline','candidate'].forEach(side=>$('observation-'+side).addEventListener('change',function(e){
    observationState[side+'Id']=e.target.value;observationState.selected=0;renderObservation();
  }));
  $('observation-search').addEventListener('input',e=>{observationState.query=e.target.value;renderObservationSections();});
  $('observation-changes-only').addEventListener('change',e=>{observationState.changesOnly=e.target.checked;renderObservationSections();});
  $('observation-download-json').addEventListener('click',function(){
    if(observationComparison())downloadObservation(observationJson(),'request-comparison.json','application/json');
  });
  $('observation-download-markdown').addEventListener('click',function(){
    if(observationComparison())downloadObservation(observationReport(),'request-observation.md','text/markdown');
  });
  $('observation-to-brief').addEventListener('click',attachObservation);
}
