/* CC run is an explicit local evidence bundle. No acquisition or evaluation. */
'use strict';
var runState={attemptId:null};
function runData(){return getData().cc_run;}
function renderRun(){
  var data=runData(),list=$('run-requests'),detail=$('run-detail');clear(list);clear(detail);
  ['run-download','run-to-brief'].forEach(id=>$(id).disabled=!data);
  if(!data){
    $('run-summary').textContent='没有导入 CC run。先用 import_cc_run.py 显式导入选定材料，再以 build_context_atlas.py --run run.json 打开。';
    $('run-fingerprint').textContent='';return;
  }
  $('run-summary').textContent=data.title;
  $('run-fingerprint').textContent=data.conditions_text;
  var groups=new Map();
  data.requests.forEach(request=>{
    if(!groups.has(request.group))groups.set(request.group,[]);
    groups.get(request.group).push(request);
  });
  if(!data.requests.some(r=>r.id===runState.attemptId))runState.attemptId=data.requests[0]?.id||null;
  groups.forEach((requests,group)=>{
    list.appendChild(el('h3',{cls:'subhead',text:group}));
    requests.forEach(request=>list.appendChild(el('button',{cls:'study-source-btn',attrs:{type:'button',
      'data-run-request':request.id,'aria-pressed':String(request.id===runState.attemptId)},
      on:{click:()=>{runState.attemptId=request.id;renderRun();
        list.querySelectorAll('[data-run-request]').forEach(button=>{
          if(button.getAttribute('data-run-request')===request.id)button.focus();
        });}}},[
        el('span',{text:request.id}),el('small',{text:request.label})])));
  });
  if(!data.requests.length)detail.appendChild(el('p',{text:'本次选定材料没有 request；response/event 仍保留，不推断它们对应的缺失请求。'}));
  var selected=data.requests.find(r=>r.id===runState.attemptId);
  if(selected){
    detail.appendChild(el('h3',{text:selected.id}));
    detail.appendChild(el('p',{cls:'observation-evidence',text:selected.label}));
    detail.appendChild(el('p',{cls:'observation-evidence',text:selected.scope_text}));
    detail.appendChild(el('button',{cls:'btn btn--primary',attrs:{type:'button'},text:'查看这份 request 原值 →',on:{click:()=>{
      observationState.baselineId=selected.capture_id;observationState.candidateId=null;
      observationState.selected=0;activateTab('observation',true);
    }}}));
    detail.appendChild(el('details',{},[el('summary',{text:'请求与 index 的完整关联记录'}),el('pre',{text:selected.exact_text})]));
  }
  detail.appendChild(el('h3',{text:'未关联材料、损失与证据边界'}));
  detail.appendChild(el('p',{text:data.gap_summary}));
  detail.appendChild(el('details',{},[el('summary',{text:'查看响应 / event、内容损失与未关联引用'}),el('pre',{text:data.gaps_text})]));
}
function wireRun(){
  $('run-download').addEventListener('click',()=>{
    var data=runData();if(!data)return;
    downloadLocalArtifact(data.bundle_json,'cc-run-snapshot.json','application/json');
    $('run-status').textContent='已下载固定 run snapshot，包含所选 captures、sidecar 和未评估项；可用 --run 重新打开。';
  });
  $('run-to-brief').addEventListener('click',()=>{
    var data=runData();if(!data)return;
    observationAttachment={kind:'cc_run',baselineId:data.run_id,candidateId:null,jsonText:data.bundle_json,markdown:data.markdown};
    ['core','tools','hooks','channel','history'].forEach(id=>changeState.caps[id]=true);
    changeState.intent=null;activateTab('change',true);
  });
}
