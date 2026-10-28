/* Study presentation over canonical Python observations; no scheduler here.
 * Plans contain synthetic fixture snapshots. Imports never execute source,
 * commands, or data supplied by the plan. No persistence or network. */
'use strict';

var studyAttachment = null;
var studyState = {scenarioId: null, sourceId: null, query: '', changedOnly: false,
  baseline: {policy_id:'P1_fixed_interval', placement_id:'PL_main_defer', history_mode:'same'},
  candidate: {policy_id:'P1_fixed_interval', placement_id:'PL_main_defer', history_mode:'fresh'}};
var STUDY_PRESETS = [
  {title:'01 / 经历怎样承接', question:'换成 fresh session 后，哪些旧经历退出，哪些当下信息仍然进入？',
   candidate:{policy_id:'P1_fixed_interval',placement_id:'PL_main_defer',history_mode:'fresh'}},
  {title:'02 / 自己的时间放在哪里', question:'在独立 session 醒来，而不是等待主聊天结束，会看见怎样不同的当下与记忆？',
   candidate:{policy_id:'P1_fixed_interval',placement_id:'PL_independent',history_mode:'same'}},
  {title:'03 / 来源变化与节律', question:'加入事件与 self-wake 后，来源进入和内部经历承接的时序怎样变化？',
   candidate:{policy_id:'P6_hybrid',placement_id:'PL_main_defer',history_mode:'same'}}
];
var STUDY_PRESERVE = ['人类原话、sender、时刻、附件与 reply target 保真',
  '过期环境和已纠正的记忆不能冒充 current；历史是否仍在需单独检查',
  '内部结果只能在产生之后承接，不能把内部活动写成外部交付'];

function studyScenario() { return findById(scenarios(), studyState.scenarioId); }
function studyObservation(side) {
  var s=studyScenario(), c=studyState[side];
  return s?.observations?.[c.policy_id]?.[c.placement_id]?.[c.history_mode];
}
function studyPlan() {
  if (!$('study-question').value.trim()) throw Error('请先填写研究问题，再保存或交接。');
  return {schema:'cc-context-study/1', title:$('study-title').value.trim() || 'Context study',
    question:$('study-question').value.trim(),
    preserve:$('study-preserve').value.split('\n').map(s=>s.trim()).filter(Boolean),
    fixture:studyScenario().fixture,
    baseline:Object.assign({},studyState.baseline),candidate:Object.assign({},studyState.candidate)};
}
function studyChangedAxes() {
  return ['policy_id','placement_id','history_mode'].filter(k=>studyState.baseline[k]!==studyState.candidate[k]);
}
function studyConfigText(c) { return c.policy_id+' / '+c.placement_id+' / '+c.history_mode; }
function studySelect(id, label, items, value, callback) {
  var select=el('select',{attrs:{id:id},on:{change:e=>callback(e.target.value)}});
  items.forEach(item=>select.appendChild(el('option',{text:item.label||item.id,attrs:{value:item.id}})));
  select.value=value;
  return el('label',{cls:'field'},[el('span',{cls:'field__label',text:label}),select]);
}
function setStudyPreset(index) {
  var preset=STUDY_PRESETS[index];
  studyState.baseline={policy_id:'P1_fixed_interval',placement_id:'PL_main_defer',history_mode:'same'};
  studyState.candidate=Object.assign({},preset.candidate);
  $('study-title').value=preset.title.slice(5);
  $('study-question').value=preset.question;
  $('study-preserve').value=STUDY_PRESERVE.join('\n');
  renderStudy();
}
function renderStudy() {
  if (!scenarios().length) return;
  if (!studyScenario()) studyState.scenarioId=scenarios()[0].id;
  var scenario=studyScenario();
  var select=$('study-scenario'); clear(select);
  scenarios().forEach(s=>select.appendChild(el('option',{text:s.title,attrs:{value:s.id}})));
  select.value=scenario.id;
  var configs=$('study-configs');clear(configs);
  ['baseline','candidate'].forEach(function(side,i) {
    var config=studyState[side];
    if(!findById(scenario.policies,config.policy_id)) config.policy_id=scenario.policies[0].id;
    if(!findById(scenario.placements,config.placement_id)) config.placement_id=scenario.placements[0].id;
    var group=el('fieldset',{cls:'study-config study-config--'+side});
    group.appendChild(el('legend',{text:(i?'B / 改变条件':'A / 比较基线')}));
    group.appendChild(studySelect('study-'+side+'-policy','触发方式',scenario.policies,config.policy_id,
      value=>{config.policy_id=value;renderStudy();}));
    group.appendChild(studySelect('study-'+side+'-placement','活动位置',scenario.placements,config.placement_id,
      value=>{config.placement_id=value;renderStudy();}));
    group.appendChild(studySelect('study-'+side+'-history','经历承接',[
      {id:'same',label:'same · 延续自己的历史'},{id:'fresh',label:'fresh · 仅明确 carryover'}],config.history_mode,
      value=>{config.history_mode=value;renderStudy();}));
    configs.appendChild(group);
  });
  var axes=studyChangedAxes();
  $('study-axis-note').textContent=axes.length===0?'两组条件相同，可用作对照基线；没有配置差异。':
    axes.length===1?'本次改变 '+axes[0]+'。下面的差异属于这份合成材料与规则，不是现实行为预测。':
    '同时改变 '+axes.join('、')+' · compound comparison，不能把全部差异归因于一个因素。';
  var summaries=$('study-summaries');clear(summaries);
  ['baseline','candidate'].forEach(function(side,i) {
    var obs=studyObservation(side);
    var run=resolveRun(scenario,studyState[side].policy_id,studyState[side].placement_id,studyState[side].history_mode);
    var section=el('div',{cls:'study-run-summary'});
    section.appendChild(el('span',{cls:'study-run-letter',text:i?'B':'A'}));
    section.appendChild(el('p',{text:run.wakes.length+' 次实际开始 · '+obs.sources.filter(s=>s.exposures.some(e=>e.current)).length+
      ' 个来源曾进入 current · '+obs.sources.filter(s=>s.exposures.some(e=>e.history)).length+' 个曾在 history'}));
    section.appendChild(el('p',{cls:'field__note',text:'计数只描述可见轨迹，不构成质量排名或更少更好的结论。'}));
    summaries.appendChild(section);
  });
  renderStudySources();renderStudyOpportunities();
  updateStudyActions();
}
function updateStudyActions() {
  var invalid=!$('study-question').value.trim();
  ['study-plan-download','study-report-download','study-to-brief'].forEach(id=>$(id).disabled=invalid);
  $('study-question').setAttribute('aria-invalid',String(invalid));
  if(invalid) $('study-status').textContent='请填写研究问题；当前内容仍保留，补齐后可保存与交接。';
  else if($('study-status').textContent.startsWith('请填写研究问题')) $('study-status').textContent='';
}
function studySources() {
  var a=studyObservation('baseline'), b=studyObservation('candidate');
  return a.sources.map(function(source) {
    var other=findById(b.sources,source.id);
    return {id:source.id,payload:source.payload,provenance:source.provenance,
      baseline:source,candidate:other,
      changed:JSON.stringify(source.exposures)!==JSON.stringify(other?.exposures)};
  });
}
function renderStudySources() {
  var all=studySources(), q=studyState.query.trim().toLowerCase();
  var filtered=all.filter(s=>(!studyState.changedOnly||s.changed)&&
    (!q||JSON.stringify([s.id,s.payload,s.provenance]).toLowerCase().includes(q)));
  if(!filtered.some(s=>s.id===studyState.sourceId)) studyState.sourceId=filtered[0]?.id||null;
  var list=$('study-source-list');clear(list);
  filtered.forEach(function(source) {
    var type=source.payload?.type||source.provenance?.type||'';
    list.appendChild(el('button',{cls:'study-source-btn',attrs:{type:'button','data-study-source':source.id,
      'aria-pressed':String(studyState.sourceId===source.id)},on:{click:function(){studyState.sourceId=source.id;renderStudySources();}}},[
      el('span',{text:source.id}),el('small',{text:type+(source.changed?' · 轨迹不同':' · 轨迹相同')})]));
  });
  if(!filtered.length) list.appendChild(el('p',{cls:'empty-state',text:'没有匹配来源。清空检索或关闭差异筛选可恢复。'}));
  renderStudyTrace(all.find(s=>s.id===studyState.sourceId));
}
function studyExposureText(exposure) {
  var flags=[];
  if(exposure.current) flags.push('current');
  if(exposure.history) flags.push('history');
  if(exposure.excluded) flags.push('excluded');
  if(exposure.produced_after_input) flags.push('produced AFTER input');
  return flags.length?flags.join(' + '):'本轮未选入';
}
function renderStudyTrace(source) {
  var root=$('study-trace');clear(root);
  if(!source) {root.appendChild(el('p',{cls:'empty-state',text:'选择一个来源查看 A/B 轨迹。'}));return;}
  root.appendChild(el('h3',{cls:'study-source-title',text:source.id}));
  var original=source.payload;
  root.appendChild(el('p',{cls:'study-source-body',text:original.text||original.body||'(此来源没有正文)'}));
  root.appendChild(el('p',{cls:'field__note',text:original.type+' · 合成时间 t='+original.t+
    (original.observed_at!=null?' · observed='+original.observed_at:'')+
    (original.expires_at!=null?' · expires='+original.expires_at:'')+
    (original.corrects?' · corrects '+original.corrects:'')+
    (original.source_memory_id?' · source '+original.source_memory_id:'')+'（秒）'}));
  root.appendChild(el('p',{cls:'study-legend',text:'● current　▤ history　× excluded　＋ 轮后产生。current 退出不代表 history 或 archive 已删除。'}));
  var payload=el('details',{cls:'study-payload'});
  payload.appendChild(el('summary',{text:'来源原文与 provenance'}));
  payload.appendChild(el('pre',{text:JSON.stringify({payload:source.payload,provenance:source.provenance},null,2)}));
  root.appendChild(payload);
  var columns=el('div',{cls:'study-trace-columns'});
  ['baseline','candidate'].forEach(function(side,i) {
    var trace=source[side], column=el('div',{cls:'study-trace-column'});
    column.appendChild(el('h4',{text:i?'B / 改变条件':'A / 比较基线'}));
    var exposures=asArray(trace?.exposures);
    var visible=exposures.filter(e=>e.current||e.history||e.excluded||e.produced_after_input);
    var strip=el('div',{cls:'study-exposure-strip',attrs:{'aria-label':(i?'B':'A')+' 每轮来源位置'}});
    exposures.forEach(e=>strip.appendChild(el('span',{cls:'study-exposure'+(e.current?' is-current':'')+(e.history?' is-history':'')+
      (e.produced_after_input?' is-produced':''),attrs:{title:JSON.stringify(e)},text:e.current?'●':e.history?'▤':e.produced_after_input?'+':e.excluded?'×':'·'})));
    column.appendChild(strip);
    if(!visible.length) column.appendChild(el('p',{text:'所有已准入轮次都未选择该来源。这不表示全局删除；来源 snapshot 仍在研究包。'}));
    visible.forEach(function(e) {
      var item=el('details',{cls:'study-exposure-detail'});
      item.appendChild(el('summary',{text:str(e.actual_start_text||e.actual_start)+' · '+studyExposureText(e)}));
      item.appendChild(el('pre',{text:JSON.stringify(e,null,2)}));
      if(e.wake_id) item.appendChild(el('button',{cls:'study-replay-link',attrs:{type:'button'},text:'检查这一轮完整输入 →',
        on:{click:function(){
          var c=studyState[side];
          replayState.scenarioId=studyState.scenarioId;replayState.policyId=c.policy_id;
          replayState.placementId=c.placement_id;replayState.mode=c.history_mode;replayState.wakeId=e.wake_id;
          activateTab('replay',true);
        }}}));
      column.appendChild(item);
    });
    columns.appendChild(column);
  });
  root.appendChild(columns);
}
function renderStudyOpportunities() {
  var root=$('study-opportunity-table');clear(root);
  var a=studyObservation('baseline').opportunities,b=studyObservation('candidate').opportunities;
  var same=studyState.baseline.policy_id===studyState.candidate.policy_id;
  var table=el('table',{cls:'sources-table'}),head=el('thead'),row=el('tr');
  ['原始候选','A / 准入与开始','B / 准入与开始'].forEach(x=>row.appendChild(el('th',{text:x,attrs:{scope:'col'}})));
  head.appendChild(row);table.appendChild(head);var body=el('tbody');
  function id(o){return o.trigger_id||o.id;}
  function cell(o){return o?JSON.stringify(o,null,2):'无对应机会';}
  var entries=same?Array.from(new Set(a.concat(b).map(id))).map(k=>[k,a.find(o=>id(o)===k),b.find(o=>id(o)===k)]):
    a.map(o=>['A / '+id(o),o,null]).concat(b.map(o=>['B / '+id(o),null,o]));
  if(!same) root.appendChild(el('p',{text:'不同 trigger policy · cross_policy_not_compared。下面保留两套候选，不作强行匹配。'}));
  entries.forEach(function(entry){
    var tr=el('tr');tr.appendChild(el('td',{text:entry[0]}));
    entry.slice(1).forEach(o=>tr.appendChild(el('td',{},[el('pre',{text:cell(o)})])));body.appendChild(tr);
  });
  table.appendChild(body);root.appendChild(table);
}
function studyMarkdown() {
  var plan=studyPlan(),axes=studyChangedAxes();
  var lines=['# '+plan.title,'','> 离线合成对照 · MODEL NOT RUN。不是捕获的 CC request；不证明实际模型行为或外部交付。','',
    '研究问题：'+plan.question,'','场景：'+plan.fixture.scenario_id,
    '','- A: '+studyConfigText(plan.baseline),'- B: '+studyConfigText(plan.candidate),
    '- 改动轴：'+(axes.join(', ')||'无')+(axes.length>1?'（compound，不能单因果归因）':''),'',
    '## 声明的保留条件（不自动判为通过）','',...plan.preserve.map(x=>'- '+x),'',
    '## 逐来源观察','',
    '以下是 canonical run_session 结果经 context_study.project_run 投影的来源轨迹。没有按 packet 下标配对。'];
  studySources().forEach(function(source){
    lines.push('','### '+source.id,'',source.changed?'A/B 轨迹不同。':'A/B 轨迹相同。','',
      '```json',JSON.stringify({payload:source.payload,provenance:source.provenance,
        baseline:source.baseline.exposures,candidate:source.candidate.exposures},null,2),'```');
  });
  lines.push('','## 机会与未验层级','',studyState.baseline.policy_id===studyState.candidate.policy_id?
    '同一 policy 的候选按 trigger ID 对齐；合并成员可共享实际开始。':'不同 policy，候选分列，不作匹配。','',
    '```json',JSON.stringify({baseline:studyObservation('baseline').opportunities,candidate:studyObservation('candidate').opportunities},null,2),'```','',
    '真实 request、模型语义、安装/激活、scheduler 与外部交付均未在本研究执行。',
    'typed decision 仍为独立 shadow 实验；此比较没有采用其回答或改变后续 ledger。','',
    '## 重跑输入','',
    '另存下列 JSON 为 plan.json，运行 `python3 scripts/run_context_study.py plan.json --out .cache/context-study`。',
    'snapshot 固定输入；重跑使用当前引擎版本，不能据此保证跨代码版本结果不变。','',
    '```json',JSON.stringify(plan,null,2),'```');
  return lines.join('\n');
}
function downloadStudy(text, name, type) {
  var url=URL.createObjectURL(new Blob([text],{type:type+';charset=utf-8'}));
  var anchor=el('a',{attrs:{href:url,download:name}});document.body.appendChild(anchor);anchor.click();anchor.remove();
  setTimeout(()=>URL.revokeObjectURL(url),60000);
  $('study-status').textContent='已导出 '+name+'；仅在本地生成。';
}
function stableStudyValue(value) {
  if(Array.isArray(value)) return value.map(stableStudyValue);
  if(isObj(value)) return Object.fromEntries(Object.keys(value).sort().map(k=>[k,stableStudyValue(value[k])]));
  return value;
}
function restoreStudy(plan) {
  var keys=['schema','title','question','preserve','fixture','baseline','candidate'];
  if(!isObj(plan)||Object.keys(plan).some(k=>!keys.includes(k))||keys.some(k=>!Object.prototype.hasOwnProperty.call(plan,k))||
     plan.schema!=='cc-context-study/1'||typeof plan.title!=='string'||typeof plan.question!=='string'||!plan.question.trim()||
     !Array.isArray(plan.preserve)||plan.preserve.some(x=>typeof x!=='string')) throw Error('研究 plan 合同不完整或包含未知字段。');
  var scenario=scenarios().find(s=>JSON.stringify(stableStudyValue(s.fixture))===JSON.stringify(stableStudyValue(plan.fixture)));
  if(!scenario) throw Error('fixture snapshot 与本页面不一致。请用 CLI 重跑，或 python3 scripts/build_context_atlas.py --study plan.json 生成对应页面。');
  ['baseline','candidate'].forEach(function(side){var c=plan[side];
    if(!isObj(c)||Object.keys(c).sort().join(',')!=='history_mode,placement_id,policy_id'||
       typeof c.policy_id!=='string'||typeof c.placement_id!=='string'||typeof c.history_mode!=='string'||
       !findById(scenario.policies,c.policy_id)||!findById(scenario.placements,c.placement_id)||
       !['same','fresh'].includes(c.history_mode)||
       !Object.prototype.hasOwnProperty.call(scenario.observations[c.policy_id][c.placement_id],c.history_mode)) throw Error(side+' 条件不在当前投影内。');
  });
  // All validation precedes mutation, so failed import keeps the current work.
  studyState.scenarioId=scenario.id;
  studyState.baseline=Object.assign({},plan.baseline);studyState.candidate=Object.assign({},plan.candidate);
  studyState.sourceId=null;studyState.query='';studyState.changedOnly=false;
  $('study-source-search').value='';$('study-changed-only').checked=false;
  $('study-title').value=plan.title;$('study-question').value=plan.question;$('study-preserve').value=plan.preserve.join('\n');
  renderStudy();
}
function attachStudy() {
  studyAttachment={plan:JSON.parse(JSON.stringify(studyPlan())),markdown:studyMarkdown()};
  ['ambient','recall','channel','history','wake','delivery'].forEach(id=>changeState.caps[id]=true);
  changeState.intent=null;activateTab('change',true);
}
function renderStudyAttachment() {
  var root=$('study-brief-attachment');clear(root);root.hidden=!studyAttachment;
  if(!studyAttachment) return;
  root.appendChild(el('strong',{text:'已附对照研究：'+studyAttachment.plan.question}));
  root.appendChild(el('p',{text:'brief 携带带入时的配置、完整合成 snapshot 和实际来源轨迹。之后修改研究不会悄悄改写此附件。'}));
  root.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'移除研究附件',on:{click:function(){studyAttachment=null;renderStudyAttachment();updateBriefPreview();}}}));
}
function wireStudy() {
  STUDY_PRESETS.forEach((preset,i)=>$('study-presets').appendChild(el('button',{cls:'intent-btn',attrs:{type:'button'},
    on:{click:()=>setStudyPreset(i)}},[el('span',{cls:'intent-btn__label',text:preset.title}),el('span',{cls:'intent-btn__desc',text:preset.question})])));
  $('study-scenario').addEventListener('change',e=>{studyState.scenarioId=e.target.value;studyState.sourceId=null;renderStudy();});
  $('study-source-search').addEventListener('input',e=>{studyState.query=e.target.value;renderStudySources();});
  $('study-changed-only').addEventListener('change',e=>{studyState.changedOnly=e.target.checked;renderStudySources();});
  $('study-question').addEventListener('input',updateStudyActions);
  $('study-plan-download').addEventListener('click',()=>downloadStudy(JSON.stringify(studyPlan(),null,2)+'\n','context-study-plan.json','application/json'));
  $('study-report-download').addEventListener('click',()=>downloadStudy(studyMarkdown(),'context-study.md','text/markdown'));
  $('study-to-brief').addEventListener('click',attachStudy);
  $('study-import').addEventListener('click',()=>{try{restoreStudy(JSON.parse($('study-import-text').value));$('study-status').textContent='研究已恢复，使用 snapshot 对应的 canonical 观察。';}
    catch(err){$('study-status').textContent='未导入：'+err.message;}});
  setStudyPreset(0);
  var unsafeCase=getData().context_case?.study_browser_safe===false;
  $('study-case-notice').hidden=!unsafeCase;
  $('study-case-notice').textContent=unsafeCase?'当前 case 的 study 含超出安全整数范围的值，没有载入此编辑器；这里使用独立的合成情境。请从案例下载 canonical JSON 并在 CLI 重跑。':'';
  if(getData().study_plan&&!unsafeCase) {try{restoreStudy(getData().study_plan);}catch(err){$('study-status').textContent=err.message;}}
}
