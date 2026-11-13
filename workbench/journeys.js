/* Authored recipe navigation; all checks and raw-value exports stay in Python. */
'use strict';
var journeyState = {previewId:null, original:null};
var recipeEvidenceAttachment = null;
function recipeEvidenceById(id) {
  var examples=getData().recipe_examples||{};
  return Object.prototype.hasOwnProperty.call(examples,id)?examples[id].mechanism_evidence:null;
}
function evidenceLocator(value) {
  if(typeof value==='string')return value;
  if(!value)return '';
  return [value.kind,value.pointer||value.symbol||value.heading||value.value].filter(Boolean).join(': ');
}
function renderMechanismEvidence(mechanism,evidence) {
  var data=evidence?.projection;
  var bound=data?.mechanisms.find(m=>m.id===mechanism.id);
  if(!bound)return el('p',{cls:'field__note',text:'本页未准备逐条机制依据；相关阅读不能代替 claim 绑定。'});
  var detail=el('details',{cls:'recipe-evidence'},[el('summary',{text:'逐条判断与固定来源 · '+bound.claims.length+' 项'})]);
  bound.claims.forEach(claim=>{
    var row=el('article',{cls:'recipe-claim'},[
      el('div',{cls:'recipe-claim__identity'},[el('code',{text:claim.id}),levelTag(claim.level)]),
      el('p',{text:claim.statement})]);
    (claim.limits||[]).forEach(limit=>row.appendChild(el('p',{cls:'field__note',text:limit})));
    claim.source_ids.forEach(id=>{
      var source=data.sources.find(s=>s.id===id);if(!source)return;
      var sourceRow=el('section',{cls:'recipe-evidence-source'},[
        el('strong',{text:source.title}),
        el('p',{cls:'recipe-evidence-identity',text:[source.id,source.kind,source.revision,'观察 '+source.observed_on].filter(Boolean).join(' · ')}),
        el('p',{cls:'recipe-evidence-identity',text:[source.path,evidenceLocator(source.locator)].filter(Boolean).join(' · ')})]);
      (source.limits||[]).forEach(limit=>sourceRow.appendChild(el('p',{cls:'field__note',text:limit})));
      if(source.url)sourceRow.appendChild(sourceLink(source.url,'查看引用位置 ↗'));
      if(source.path)sourceRow.appendChild(sourceLink(source.path,'本地记录（当前 checkout） ↗'));
      row.appendChild(sourceRow);
    });
    detail.appendChild(row);
  });
  return detail;
}
function attachRecipeEvidence(id) {
  var evidence=recipeEvidenceById(id);if(!evidence)return;
  recipeEvidenceAttachment={recipeId:id,json:evidence.json,markdown:evidence.markdown};
  activateTab('change',true);
}
function renderRecipeEvidenceAttachment() {
  var root=$('recipe-brief-attachment');if(!root)return;
  clear(root);root.hidden=!recipeEvidenceAttachment;if(!recipeEvidenceAttachment)return;
  root.appendChild(el('strong',{text:'已附机制依据：'+recipeEvidenceAttachment.recipeId}));
  root.appendChild(el('p',{text:'固定 claim、来源版本、观察日期与限制；切换 recipe 不会替换附件，也不表示当前材料通过这些判断。'}));
  root.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'下载已固定依据 JSON',on:{click:()=>downloadLocalArtifact(recipeEvidenceAttachment.json,recipeEvidenceAttachment.recipeId+'-mechanism-evidence.json','application/json')}}));
  root.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'移除机制依据附件',on:{click:()=>{
    recipeEvidenceAttachment=null;renderChange();
  }}}));
}
function setResearchTools(open) {
  $('atlas-research-tabs').hidden=!open;
  $('atlas-tools-toggle').setAttribute('aria-expanded',String(open));
  $('atlas-tools-toggle').textContent=open?'收起研究工具 −':'研究工具 +';
}
function recipeById(id) { return (getData().recipes||[]).find(r=>r.id===id); }
function renderJourneyContext(tab) {
  var root=$('journey-context'); if(!root)return;
  clear(root); root.hidden=tab==='home';
  if(['study','replay','overview','sources'].includes(tab)) {
    var names={study:'独立 A/B 研究',replay:'独立自主轮次回放',overview:'CC 机制全景',sources:'公开来源索引'};
    root.appendChild(el('strong',{text:names[tab]}));
    root.appendChild(el('span',{text:tab==='study'?'这里保留自己的 fixture、条件与未保存编辑；切换 recipe 不会替换它。只有显式恢复 plan 才改变研究输入。':'研究工具独立于当前 recipe；不代表此案例的实际运行结果。'}));
    return;
  }
  var recipe=recipeById(getData().active_recipe_id);
  root.appendChild(el('strong',{text:recipe?recipe.title:getData().open_run?'你带入的 CC run':getData().open_case?'你带入的案例':getData().open_observation?'你带入的请求':'当前研究材料'}));
  root.appendChild(el('span',{text:recipe?'合成案例 · 结构结果与真实行为分开':'本地只读材料 · 原值与来源声明保留'}));
  root.appendChild(el('button',{cls:'btn',text:'回到问题与做法',attrs:{type:'button'},on:{click:()=>activateTab('home',true)}}));
}
function resetWorkspaceSelection() {
  caseState.stepId=null; caseState.filter='all'; $('case-filter').value='all';
  observationState.baselineId=null; observationState.candidateId=null; observationState.selected=0; observationState.query='';
  $('observation-search').value='';
}
function selectRecipe(id) {
  var d=getData(), examples=d.recipe_examples||{};
  if(!recipeById(id)||!Object.prototype.hasOwnProperty.call(examples,id))return false;
  var example=examples[id];
  d.context_case=example.context_case; d.request_observations=example.request_observations; d.cc_run=null;
  d.active_recipe_id=id; journeyState.previewId=id;
  resetWorkspaceSelection(); renderJourney(); return true;
}
function restoreLoadedMaterials() {
  var original=journeyState.original; if(!original)return;
  Object.assign(getData(),original); journeyState.previewId=null;
  resetWorkspaceSelection(); renderJourney();
  activateTab(original.open_run?'run':original.open_case?'case':original.open_observation?'observation':original.study_plan?'study':'case',true);
}
function renderJourney() {
  var d=getData(), recipes=d.recipes||[], list=$('journey-recipes'), detail=$('journey-detail');
  clear(list); clear(detail);
  var selected=recipeById(journeyState.previewId||d.active_recipe_id)||recipes[0];
  recipes.forEach((r,i)=>list.appendChild(el('button',{cls:'recipe-choice',attrs:{type:'button','aria-pressed':String(selected&&selected.id===r.id),'data-recipe':r.id},on:{click:()=>{
    journeyState.previewId=r.id;renderJourney();
    list.querySelectorAll('[data-recipe]').forEach(b=>{if(b.getAttribute('data-recipe')===r.id)b.focus();});
  }}},[el('small',{text:'0'+(i+1)+' / '+r.id}),el('strong',{text:r.title})])));
  if(!selected){detail.appendChild(el('p',{text:'本页面没有 recipe 索引。原有研究工具仍可使用。'}));return;}
  detail.appendChild(el('span',{cls:'section-kicker',text:'QUESTION / '+selected.id}));
  detail.appendChild(el('h3',{text:selected.question}));
  detail.appendChild(el('p',{text:selected.summary}));
  var evidence=recipeEvidenceById(selected.id);
  var mechanisms=el('div');
  (selected.mechanisms||[]).forEach(m=>{
    var row=el('section',{cls:'recipe-mechanism'},[el('h4',{text:m.title}),el('p',{text:m.explanation})]);
    (m.sources||[]).forEach(source=>row.appendChild(sourceLink(source)));
    row.appendChild(renderMechanismEvidence(m,evidence));mechanisms.appendChild(row);
  });detail.appendChild(mechanisms);
  if(evidence){
    var evidenceDetails=el('details',{cls:'recipe-evidence-overview'},[el('summary',{text:'机制证据表与导出'})]);
    evidence.projection.caveats.forEach(text=>evidenceDetails.appendChild(el('p',{cls:'field__note',text:text})));
    var exports=el('div',{cls:'journey-actions'});
    [['json','JSON','application/json'],['markdown','Markdown','text/markdown']].forEach(([key,label,type])=>{
      exports.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'下载机制依据 '+label,on:{click:()=>downloadLocalArtifact(evidence[key],selected.id+'-mechanism-evidence.'+(key==='json'?'json':'md'),type)}}));
    });
    exports.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'将机制依据带入 brief →',on:{click:()=>attachRecipeEvidence(selected.id)}}));
    evidenceDetails.appendChild(exports);detail.appendChild(evidenceDetails);
  }
  detail.appendChild(el('h4',{text:'按这条路径操作'}));
  var procedure=el('ol',{cls:'recipe-procedure'});(selected.procedure||[]).forEach(p=>procedure.appendChild(el('li',{text:p})));detail.appendChild(procedure);
  var example=d.recipe_examples&&d.recipe_examples[selected.id];
  if(example){
    var summary=example.context_case.report.summary;
    var result=el('div',{cls:'recipe-results'});
    ['passed','failed','not_assessed'].forEach((k,i)=>result.appendChild(el('span',{},[el('strong',{text:summary[k]}),' '+['结构通过','反例失败','未评估'][i]])));
    detail.appendChild(result);
  }
  detail.appendChild(el('p',{cls:'recipe-caveat',text:'案例有意包含失败反例。PASS 只覆盖指定结构；native 生命周期与模型行为尚未执行验收。'}));
  var actions=el('div',{cls:'journey-actions'});
  actions.appendChild(el('button',{cls:'btn btn--primary',attrs:{type:'button'},text:'打开案例，检查每个阶段 →',on:{click:()=>{if(selectRecipe(selected.id))activateTab('case',true);}}}));
  actions.appendChild(el('button',{cls:'btn',attrs:{type:'button'},text:'下载固定案例 JSON',on:{click:()=>{if(example)downloadLocalArtifact(example.context_case.case_json,'context-case.json','application/json');}}}));
  detail.appendChild(actions);detail.appendChild(sourceLink(selected.guide_path,'阅读完整做法、反例与恢复说明 ↗'));
  var cmd=el('details',{},[el('summary',{text:'在 CLI 重跑与重新打开'})]);
  cmd.appendChild(el('pre',{cls:'cmd',text:'python3 -m context_lab evidence --recipe '+selected.id+' --format json\npython3 scripts/run_context_case.py '+selected.case_path+' --out .cache/recipe-'+selected.id+'\npython3 scripts/build_context_atlas.py --recipe '+selected.id+' --out .cache/cc-context-workbench'}));
  detail.appendChild(cmd);
  $('journey-loaded').hidden=!journeyState.original||!journeyState.original.hasExplicit;
}
function wireJourney() {
  var d=getData();
  journeyState.original={context_case:d.context_case,request_observations:d.request_observations,cc_run:d.cc_run,
    active_recipe_id:d.active_recipe_id,open_run:d.open_run,open_case:d.open_case,open_observation:d.open_observation,study_plan:d.study_plan};
  journeyState.original.hasExplicit=Boolean(d.open_run||d.open_case||d.open_observation||d.study_plan);
  $('journey-loaded').addEventListener('click',restoreLoadedMaterials);
  $('atlas-tools-toggle').addEventListener('click',()=>{
    var expanded=$('atlas-tools-toggle').getAttribute('aria-expanded')==='true';
    if(expanded&&['run','study','replay','overview','sources'].some(name=>$('tab-'+name).getAttribute('aria-selected')==='true'))activateTab('home',true);
    setResearchTools(!expanded);
  });
  var links=$('journey-reading');clear(links);
  links.appendChild(el('strong',{text:'系统学习 / 带入自己的材料'}));
  [['docs/handbook/index.md','Handbook · 学习与查错'],['docs/handbook/mechanism-evidence.md','机制证据表 · claims 与来源'],['docs/cc-runs.md','导入自己的 CC 材料'],['docs/current-state.md','当前能力与证据状态']].forEach(([path,label])=>links.appendChild(sourceLink(path,label)));
  renderJourney();
}
