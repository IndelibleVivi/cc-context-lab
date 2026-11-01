/* Context case presenter. Python owns checks, ordering and canonical exports.
 * This view never re-evaluates a check or serializes request values in JS. */
'use strict';
var caseState={stepId:null,filter:'all'};
var caseAttachment=null;
function caseData(){return getData().context_case;}
function caseResult(){return caseData()?.report;}
function caseStatus(status){return status==='PASS'?'PASS · 指定位置满足条件':status==='FAIL'?'FAIL · 指定位置不满足条件':'NOT_ASSESSED · 未评估';}
function renderCase(){
  var data=caseData(),report=caseResult();
  ['case-save','case-report-json','case-report-md','case-to-brief'].forEach(id=>$(id).disabled=!report);
  if(!report){
    $('case-question').textContent='本页没有案例。使用 build_context_atlas.py --case case.json 打开明确的案例；独立 --study/--capture 页面不混入示例案例。';return;
  }
  $('case-title').textContent=report.case.title;
  $('case-question').textContent=report.case.question;
  var limits=$('case-limits');clear(limits);
  limits.appendChild(el('p',{text:'阶段关联由研究者声明；检查只覆盖显式 body，模型行为与外部交付未评估。'}));
  var detail=el('details',{},[el('summary',{text:'证据范围与缺口 · '+report.limitations.length+' 项'})]);
  report.limitations.forEach(text=>detail.appendChild(el('p',{text:text})));limits.appendChild(detail);
  $('case-summary').textContent='要求：'+report.summary.passed+' 项满足结构条件 · '+report.summary.failed+' 项不满足 · '+report.summary.not_assessed+' 项未评估。模型行为与外部交付未评估；没有全案例成熟度或接入结论。';
  var requirements=$('case-requirements');clear(requirements);
  report.requirements.forEach(r=>requirements.appendChild(el('article',{cls:'case-requirement',attrs:{'data-status':r.status}},[
    el('p',{cls:'field__note',text:r.id+' · '+r.level}),el('h3',{text:r.text}),el('p',{text:caseStatus(r.status)}),
    el('p',{cls:'field__note',text:r.check_ids.length?'检查：'+r.check_ids.join('、'):'没有可执行的结构检查；不自动通过。'})])));
  var stages=$('case-steps');clear(stages);
  if(!report.steps.some(s=>s.id===caseState.stepId))caseState.stepId=report.steps[0]?.id;
  report.steps.forEach((s,i)=>stages.appendChild(el('button',{cls:'study-source-btn',attrs:{type:'button','aria-pressed':String(s.id===caseState.stepId),'data-case-step':s.id},
    on:{click:()=>{caseState.stepId=s.id;renderCase();stages.querySelectorAll('[data-case-step]').forEach(b=>{if(b.getAttribute('data-case-step')===s.id)b.focus();});}}},[
      el('span',{text:String(i+1).padStart(2,'0')+' / '+s.label}),el('small',{text:s.id+' · '+(s.observation?s.observation.evidence.kind:'缺少 capture')})])));
  renderCaseStep();renderCaseChecks();
  var comparisons=$('case-comparisons');clear(comparisons);
  report.comparisons.forEach(c=>{
    var row=el('div',{cls:'case-comparison'},[el('p',{text:c.id+' · '+c.baseline+' → '+c.candidate}),
      el('p',{cls:'field__note',text:c.comparison?(c.comparison.alignment==='cross_format_unaligned'?'跨格式不自动对齐':'同格式按位置比较')+'；条件变化：'+(c.comparison.runtime_changes.join('、')||'无'):'NOT_ASSESSED · 缺少比较一侧的 capture'})]);
    var aid=c.comparison?.baseline.capture_id,bid=c.comparison?.candidate.capture_id,pairs=observationData().comparisons;
    var prepared=Object.hasOwn(pairs,aid)&&Object.hasOwn(pairs[aid],bid);
    var button=el('button',{cls:'btn',attrs:{type:'button'},text:prepared?'打开这组请求比较 →':'此比较未准备 · 打开重建说明 →',on:{click:()=>openCaseComparison(c.id)}});button.disabled=!c.comparison;row.appendChild(button);comparisons.appendChild(row);
  });
  $('case-open-study').disabled=data.study_browser_safe===false;
  if(data.study_browser_safe===false)$('case-status').textContent='关联 study 含超出浏览器安全范围的整数，请使用 canonical case JSON 在 CLI 重跑，避免进入 study 编辑时丢失精度。';
  $('case-study').hidden=!report.study;
  $('case-study-report').textContent=data.study_markdown||'';
}
function renderCaseStep(){
  var data=caseData(),step=caseResult().steps.find(s=>s.id===caseState.stepId),root=$('case-step-detail');clear(root);
  if(!step)return;
  root.appendChild(el('h3',{text:step.label}));
  if(!step.observation){root.appendChild(el('p',{text:'此阶段没有 capture，相关检查和比较均未评估。阶段标签不是运行证明。'}));return;}
  var o=step.observation;
  root.appendChild(el('p',{cls:'observation-evidence',text:o.capture_id+' · '+o.wire_format+' · '+(o.evidence.kind==='synthetic_fixture'?'合成材料':'captured_request 仅为导入者声明')}));
  root.appendChild(el('p',{cls:'observation-evidence',text:o.evidence_scope?.request_body==='partial'?
    '部分 request body · 已观察顶层字段：'+o.evidence_scope.observed_fields.map(field=>'/'+field).join('、')+'；未列出字段未知，不是空值':
    '完整 request body 文件对象'}));
  root.appendChild(el('p',{cls:'field__note',text:'observed_at：'+(o.evidence.observed_at||'未记录')+'；origin/lifecycle unknown；顺序不证明真实继承。'}));
  var runtime=el('dl',{cls:'observation-runtime'});
  Object.entries(o.runtime).forEach(([k,v])=>{runtime.appendChild(el('dt',{text:k}));runtime.appendChild(el('dd',{text:v===null?'未记录':v}));});root.appendChild(runtime);
  o.unresolved_context.forEach(text=>root.appendChild(el('p',{cls:'observation-limits',text:text})));
  root.appendChild(el('h4',{text:o.evidence_scope?.request_body==='partial'?'声明的部分原始 request body（不是完整请求）':'完整原始 request body'}));
  root.appendChild(el('pre',{text:data.display.steps[step.id]}));
}
function renderCaseChecks(){
  var report=caseResult(),root=$('case-checks');clear(root);
  var checks=report.checks.filter(c=>caseState.filter==='all'||c.status===caseState.filter);
  if(!checks.length){root.appendChild(el('p',{cls:'empty-state',text:'没有此结果的检查。切回“全部”可恢复。'}));return;}
  checks.forEach(c=>{
    var value=caseData().display.checks[c.id],card=el('article',{cls:'case-check',attrs:{'data-status':c.status}},[
      el('h4',{text:c.id+' · '+caseStatus(c.status)}),el('p',{text:'要求 '+c.requirement_id+' / 阶段 '+c.step_id}),
      el('code',{text:(c.pointer===''?'(body root)':c.pointer)+' · '+c.operator}),el('p',{text:c.reason}),
      el('p',{cls:'field__note',text:c.scope_reason==='unobserved_field'?
        'scope：该顶层字段未观察，因此未评估；不能按缺失、added 或 removed 处理。':
        'scope：仅本份显式 request body；局部缺失不证明全局删除或遗忘。'})]);
    var grid=el('div',{cls:'study-trace-columns observation-values'},[
      el('div',{},[el('h4',{text:'声明的期望'}),el('pre',{text:value.expected})]),
      el('div',{},[el('h4',{text:'实际原值'}),el('pre',{text:c.actual_present===true?value.actual:c.actual_present===false?'该位置不存在（不是 JSON null）':'无法判断；没有可用原值'})])]);
    card.appendChild(grid);card.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'定位阶段 '+c.step_id+' ↑',on:{click:()=>{caseState.stepId=c.step_id;renderCase();$('case-step-detail').scrollIntoView({block:'start'});}}}));root.appendChild(card);
  });
}
function openCaseComparison(id){
  var c=caseResult()?.comparisons.find(c=>c.id===id);if(!c?.comparison)return;
  observationState.baselineId=c.comparison.baseline.capture_id;observationState.candidateId=c.comparison.candidate.capture_id;
  observationState.selected=0;observationState.query='';$('observation-search').value='';activateTab('observation',true);
}
function attachCase(){
  var data=caseData();if(!data)return;
  caseAttachment={caseId:data.report.case.case_id,caseJson:data.case_json,reportJson:data.report_json,markdown:data.markdown};
  ['core','tools','hooks','channel','history'].forEach(id=>changeState.caps[id]=true);changeState.intent=null;activateTab('change',true);
}
function renderCaseAttachment(){
  var root=$('case-brief-attachment');clear(root);root.hidden=!caseAttachment;if(!caseAttachment)return;
  root.appendChild(el('strong',{text:'已附完整案例：'+caseAttachment.caseId}));
  root.appendChild(el('p',{text:'固定问题、材料、阶段、检查结果与未验证项；不随其它视图编辑而改变。'}));
  root.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'移除案例附件',on:{click:()=>{caseAttachment=null;renderCaseAttachment();updateBriefPreview();}}}));
}
function wireCase(){
  $('case-filter').addEventListener('change',e=>{caseState.filter=e.target.value;renderCaseChecks();});
  [['case-save','case_json','context-case.json','application/json'],['case-report-json','report_json','context-case-report.json','application/json'],['case-report-md','markdown','context-case.md','text/markdown']].forEach(([id,key,name,type])=>{
    $(id).addEventListener('click',()=>{if(!caseData())return;downloadLocalArtifact(caseData()[key],name,type);$('case-status').textContent='已生成 '+name+'；完整正文与未评估项一并保留。';});
  });
  $('case-to-brief').addEventListener('click',attachCase);
  $('case-open-study').addEventListener('click',()=>{
    var plan=caseResult()?.case.study_plan;if(!plan||caseData().study_browser_safe===false)return;
    try{restoreStudy(plan);activateTab('study',true);}catch(error){$('case-status').textContent=error.message;}
  });
}
