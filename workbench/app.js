/* CC Context Lab — Context Atlas renderer.
 *
 * Plain ES2020, no dependencies, no network. Reads one inlined JSON blob:
 *   JSON.parse(document.getElementById('atlas-data').textContent)
 *
 * Views: overview (context map), replay (wake packets), study (A/B), change (drill +
 * brief export), sources (upstream catalog). Everything is rendered with
 * createElement/textContent — never innerHTML with data — so projected text
 * cannot inject markup or script.
 *
 * This is an offline research viewer. It does not fetch, execute shell
 * commands, deploy, or call any provider.
 */
'use strict';

/* ---------------------------------------------------------------- helpers */

function $(id) { return document.getElementById(id); }

/** Create an element. `opts.text` sets textContent; attrs set attributes. */
function el(tag, opts, children) {
  var node = document.createElement(tag);
  opts = opts || {};
  if (opts.cls) node.className = opts.cls;
  if (opts.text != null) node.textContent = String(opts.text);
  if (opts.attrs) {
    for (var k in opts.attrs) {
      if (Object.prototype.hasOwnProperty.call(opts.attrs, k)) {
        var v = opts.attrs[k];
        if (v != null && v !== false) node.setAttribute(k, String(v));
      }
    }
  }
  if (opts.on) {
    for (var ev in opts.on) {
      if (Object.prototype.hasOwnProperty.call(opts.on, ev)) node.addEventListener(ev, opts.on[ev]);
    }
  }
  if (children) {
    for (var i = 0; i < children.length; i++) {
      var c = children[i];
      if (c == null) continue;
      node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
  }
  return node;
}

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

function isObj(v) { return v && typeof v === 'object' && !Array.isArray(v); }
function asArray(v) { return Array.isArray(v) ? v : (v == null ? [] : [v]); }
function str(v) { return v == null ? '' : String(v); }

/** Only allow http(s) and repo-relative hrefs; otherwise return ''. */
function safeHref(url) {
  if (!url) return '';
  var s = String(url).trim();
  if (/^https?:\/\//i.test(s)) return s;
  if (/^\.\.?\//.test(s) || /^[A-Za-z0-9._\-\/]+$/.test(s)) return s; // relative repo path
  return '';
}

var SYNTH_RE = /^(HYPOTHETICAL_PACKET|Not a captured)/i;

/* ------------------------------------------------------------------ data */

var DATA = null;

function getData() {
  if (DATA) return DATA;
  var node = $('atlas-data');
  if (!node) { DATA = {}; return DATA; }
  try {
    DATA = JSON.parse(node.textContent || '{}') || {};
  } catch (err) {
    DATA = { __parse_error: String(err && err.message || err) };
  }
  return DATA;
}

function model() { return getData().model || {}; }
function upstreams() { return asArray(getData().upstreams); }
function scenarios() { return asArray(getData().scenarios); }

function findById(list, id) {
  for (var i = 0; i < list.length; i++) if (list[i] && list[i].id === id) return list[i];
  return null;
}

/* Cap a timeline domain so an out-of-range fixture tick never blows up the axis. */
function timelineDomain(scenario) {
  var dur = Number(scenario && scenario.duration_seconds);
  if (!isFinite(dur) || dur <= 0) {
    var max = 0;
    asArray(scenario && scenario.timeline).forEach(function (o) {
      var t = Number(o && (o.end != null ? o.end : o.t));
      if (isFinite(t) && t > max) max = t;
    });
    dur = max || 1;
  }
  return dur;
}

/* ------------------------------------------------------- replay data find */

/**
 * Resolve the {wakes, packets, audit} report for one selection. Prefers the
 * canonical projection scenario.runs[policyId][placementId][mode].
 */
function resolveRun(scenario, policyId, placementId, mode) {
  return scenario?.runs?.[policyId]?.[placementId]?.[mode] || null;
}

function scenariosForPolicy(scenario, policyId) {
  return Object.keys(scenario?.runs?.[policyId] || {});
}

var ovState = {layout:'graph', selected:'wake'};

function renderOverview() {
  var m = model();
  var caps = asArray(m.capabilities);
  var stages = asArray(m.stages);
  var edges = asArray(m.edges);

  var canvas = $('overview-canvas');
  clear(canvas);
  var figure = $('overview-map');
  figure.classList.toggle('map--graph', ovState.layout === 'graph');

  if (!caps.length) {
    canvas.appendChild(el('div', { cls: 'empty-state' }, [
      el('p', { cls: 'empty-state__title', text: '没有 model 数据' }),
      el('p', { text: '尚未投影 model.capabilities。等待 coordinator 生成 .cache/context-atlas/data.json 后重载。' })
    ]));
    renderOverviewDetail(null);
    return;
  }

  if (ovState.layout === 'graph') renderOverviewGraph(canvas, caps, stages, edges);
  else renderOverviewLanes(canvas, caps, stages);

  renderOverviewLegend(stages);

  if (!ovState.selected || !findById(caps, ovState.selected)) {
    var first = caps[0];
    if (first) ovState.selected = first.id;
  }
  highlightSelected();
  renderOverviewDetail(findById(caps, ovState.selected));
}

function stageOrder(stages, caps) {
  var order = stages.map(function (s) { return s.id; });
  caps.forEach(function (c) { if (order.indexOf(c.stage) === -1) order.push(c.stage); });
  return order;
}

function stageLabel(stages, id) {
  var s = findById(stages, id);
  return s ? s.label : id;
}

function renderOverviewLanes(canvas, caps, stages) {
  var order = stageOrder(stages, caps);
  order.forEach(function (stageId, idx) {
    var laneCaps = caps.filter(function (c) { return c.stage === stageId; });
    if (!laneCaps.length) return;
    var lane = el('div', { cls: 'lane', attrs: { 'data-stage': stageId } });
    lane.appendChild(el('div', { cls: 'lane__head' }, [
      el('span', { cls: 'lane__idx', text: '0' + (idx + 1) }),
      el('span', { cls: 'lane__label', text: stageLabel(stages, stageId) })
    ]));
    var cards = el('div', { cls: 'lane__cards', attrs: { role: 'group', 'aria-label': stageLabel(stages, stageId) } });
    laneCaps.forEach(function (cap) { cards.appendChild(nodeCard(cap)); });
    lane.appendChild(cards);
    canvas.appendChild(lane);
  });
}

function nodeCard(cap) {
  var btn = el('button', {
    cls: 'node-card',
    attrs: {
      type: 'button', 'data-cap': cap.id, 'aria-pressed': 'false',
      'aria-label': (cap.title || cap.id) + (cap.owner ? ' · owner ' + cap.owner : '')
    },
    on: { click: function () { selectCapability(cap.id); } }
  });
  btn.appendChild(el('span', { cls: 'node-card__id', text: cap.id }));
  btn.appendChild(el('span', { cls: 'node-card__title', text: cap.title || cap.id }));

  return btn;
}

function renderOverviewGraph(canvas, caps, stages, edges) {
  stageOrder(stages, caps).forEach(function(stage) {
    var col=el('div',{cls:'graph-col'});
    col.appendChild(el('div',{cls:'graph-col__head',text:stageLabel(stages,stage)}));
    caps.filter(c=>c.stage===stage).forEach(function(cap) {
      col.appendChild(el('div',{cls:'graph-node'},[nodeCard(cap)]));
    });
    canvas.appendChild(col);
  });
  requestAnimationFrame(drawGraphEdges);
}

function drawGraphEdges() {
  if (ovState.layout !== 'graph' || $('panel-overview').hidden) return;
  var canvas=$('overview-canvas'), ns='http://www.w3.org/2000/svg';
  canvas.querySelector('.graph-svg')?.remove();
  var svg=document.createElementNS(ns,'svg');
  svg.setAttribute('class','graph-svg'); svg.setAttribute('aria-hidden','true');
  var defs=document.createElementNS(ns,'defs'), marker=document.createElementNS(ns,'marker');
  Object.entries({id:'relation-arrow',viewBox:'0 0 10 10',refX:'9',refY:'5',markerWidth:'6',markerHeight:'6',orient:'auto-start-reverse'}).forEach(([k,v])=>marker.setAttribute(k,v));
  var arrow=document.createElementNS(ns,'path'); arrow.setAttribute('d','M 0 0 L 10 5 L 0 10 z'); arrow.setAttribute('fill','#cf9367');
  marker.appendChild(arrow);defs.appendChild(marker);svg.appendChild(defs);
  var rect=canvas.getBoundingClientRect();
  model().edges.forEach(function(e) {
    var a=canvas.querySelector('[data-cap="'+e.from+'"]')?.getBoundingClientRect();
    var b=canvas.querySelector('[data-cap="'+e.to+'"]')?.getBoundingClientRect();
    if(!a||!b) return;
    var forward=b.left>a.left+10, same=Math.abs(b.left-a.left)<10;
    var x1=(forward||same?a.right:a.left)-rect.left, x2=(forward?b.left:b.right)-rect.left;
    var y1=a.top+a.height/2-rect.top, y2=b.top+b.height/2-rect.top;
    var bend=same?Math.max(x1,x2)+12:(x1+x2)/2;
    var path=document.createElementNS(ns,'path');
    path.setAttribute('d',`M ${x1} ${y1} C ${bend} ${y1}, ${bend} ${y2}, ${x2} ${y2}`);
    var selected=e.from===ovState.selected||e.to===ovState.selected;
    path.setAttribute('fill','none');path.setAttribute('stroke','#cf9367');
    path.setAttribute('stroke-width',selected?'2':'1');path.setAttribute('opacity',selected?'1':'.15');
    path.setAttribute('marker-end','url(#relation-arrow)');
    svg.appendChild(path);
  });
  canvas.prepend(svg);
}

function renderOverviewLegend(stages) {
  var legend = $('overview-legend');
  clear(legend);
  var order = stageOrder(stages, asArray(model().capabilities));
  order.forEach(function (s) { legend.appendChild(el('span', { text: stageLabel(stages, s) })); });
  legend.appendChild(el('span', { text: '选择环节，突出显示与它相连的研究关系'  }));
}

function selectCapability(id) {
  ovState.selected = id;
  highlightSelected();
  renderOverviewDetail(findById(asArray(model().capabilities), id));
  drawGraphEdges();
}

function highlightSelected() {
  var cards = document.querySelectorAll('#overview-canvas [data-cap]');
  for (var i = 0; i < cards.length; i++) {
    var on = cards[i].getAttribute('data-cap') === ovState.selected;
    cards[i].setAttribute('aria-pressed', on ? 'true' : 'false');
    cards[i].setAttribute('data-selected', on ? 'true' : 'false');
  }
}

function renderOverviewDetail(cap) {
  var empty = $('overview-empty');
  var body = $('overview-detail');
  clear(body);
  if (!cap) {
    empty.hidden = false;
    body.hidden = true;
    return;
  }
  empty.hidden = true;
  body.hidden = false;

  var caps = asArray(model().capabilities);
  var edges = asArray(model().edges);
  var stages = asArray(model().stages);

  body.appendChild(el('span', { cls: 'inspector__id', text: cap.id + ' · ' + stageLabel(stages, cap.stage) }));
  body.appendChild(el('h3', { cls: 'inspector__title', text: cap.title || cap.id }));
  if (cap.summary) body.appendChild(el('p', { cls: 'inspector__summary', text: cap.summary }));

  var kv = el('dl', { cls: 'kv' });
  addKV(kv, '归属', cap.owner || '—');
  addKV(kv, '阶段', stageLabel(stages, cap.stage));
  body.appendChild(kv);

  var ifaces = asArray(cap.输入入口);
  if (ifaces.length) {
    var section = miniSection('输入入口');
    var tags = el('div', { cls: 'taglist' });
    ifaces.forEach(function (x) {
      tags.appendChild(el('span', { cls: 'tag', text: typeof x === 'string' ? x : (x && (x.label || x.id)) || JSON.stringify(x) }));
    });
    section.appendChild(tags);
    body.appendChild(section);
  }

  var rel = edges.filter(function (e) { return e.from === cap.id || e.to === cap.id; });
  if (rel.length) {
    var es = miniSection('相连的环节');
    rel.forEach(function (e) {
      var dir = e.from === cap.id ? '\u2192' : '\u2190';
      var other = e.from === cap.id ? e.to : e.from;
      var otherCap = findById(caps, other);
      var line = el('p', { cls: 'bullet' });
      line.appendChild(document.createTextNode(dir + ' ' + (otherCap ? otherCap.title : other)));
      if (e.label) line.appendChild(el('span', { cls: 'src-cov', text: '  \u00b7 ' + e.label }));
      es.appendChild(line);
    });
    body.appendChild(es);
  }

  var evidence = asArray(cap.evidence);
  var lim = asArray(cap.limits);
  if (evidence.length || lim.length) {
    var evSec = miniSection('已有证据');
    if (!evidence.length) evSec.appendChild(el('p', { cls: 'src-cov', text: '未附逐条证据。' }));
    evidence.forEach(function (ev) {
      var row = el('div', { cls: 'evi' });
      var top = el('div', { cls: 'evi__top' });
      top.appendChild(levelTag(ev.level));
      if (ev.label) top.appendChild(el('span', { cls: 'evi__src', text: ev.label }));
      row.appendChild(top);
      row.appendChild(el('p', { cls: 'evi__claim', text: ev.claim || '' }));
      if (ev.source) row.appendChild(sourceLink(ev.source));
      evSec.appendChild(row);
    });
    if (lim.length) {
      evSec.appendChild(el('p', { cls: 'section-mini__h', text: '已知边界' }));
      var ul = el('ul', { cls: 'limits' });
      lim.forEach(function (l) { ul.appendChild(el('li', { text: typeof l === 'string' ? l : JSON.stringify(l) })); });
      evSec.appendChild(ul);
    }
    body.appendChild(evSec);
  }

  var qs = asArray(cap.operating_questions);
  if (qs.length) {
    var qSec = miniSection('操作前要回答的问题');
    qs.forEach(function (q) { qSec.appendChild(el('p', { cls: 'qbullet', text: typeof q === 'string' ? q : JSON.stringify(q) })); });
    body.appendChild(qSec);
  }

  var outEdges = edges.filter(function (e) { return e.from === cap.id; });
  if (outEdges.length) {
    var ds = miniSection('下游影响');
    outEdges.forEach(function (e) {
      var dCap = findById(caps, e.to);
      ds.appendChild(el('p', { cls: 'bullet', text: '影响 ' + (dCap ? (dCap.title || e.to) : e.to) + (e.label ? '：' + e.label : '') }));
    });
    body.appendChild(ds);
  }

  var checksById = {};
  asArray(model().checks).forEach(function (c) { checksById[c.id] = c; });
  var linked = asArray(cap.check_ids).map(function (id) { return checksById[id]; }).filter(Boolean);
  if (linked.length) {
    var cSec = miniSection('相关验证');
    linked.forEach(function (c) {
      var row = el('div', { cls: 'check' });
      var top = el('div', { cls: 'check__top' });
      top.appendChild(el('span', { cls: 'check__id', text: c.id }));
      top.appendChild(el('span', { cls: 'check__title', text: c.title || '' }));
      row.appendChild(top);
      if (c.command) row.appendChild(el('code', { cls: 'cmd', text: c.command }));
      cSec.appendChild(row);
    });
    body.appendChild(cSec);
  }
}

function addKV(dl, k, v) {
  dl.appendChild(el('dt', { cls: 'kv__k', text: k }));
  dl.appendChild(el('dd', { cls: 'kv__v', text: v }));
}

function miniSection(title) {
  var s = el('div', { cls: 'section-mini' });
  s.appendChild(el('p', { cls: 'section-mini__h', text: title }));
  return s;
}

function levelTag(level) {
  var key = str(level).toLowerCase();
  var known = { public_source: 1, offline_test: 1, local_probe: 1, runtime: 1, unverified: 1 };
  var cls = known[key] ? 'lv lv--' + key : 'lv lv--default';
  return el('span', { cls: cls, text: level || 'unspecified' });
}

function sourceLink(source) {
  var path = safeHref(source);
  var wrap = el('div', {cls:'src-links'});
  if (path) wrap.appendChild(el('a', {cls:'linklike', text:source,
    attrs:{href:/^https?:/.test(path) ? path : (safeHref(getData().repo_base)||'../..')+'/'+path, target:'_blank',rel:'noopener noreferrer'}}));
  else wrap.appendChild(el('span', {text:source}));
  return wrap;
}

/* ================================================================ REPLAY */

var replayState = { scenarioId: null, policyId: null, placementId: null, mode: 'same', wakeId: null };

function renderReplay() {
  var list = scenarios();
  var scenSel = $('replay-scenario');
  var body = $('replay-body');
  var empty = $('replay-empty');

  if (!list.length) {
    clear(scenSel);
    body.hidden = true;
    empty.hidden = false;
    clear(empty);
    empty.appendChild(el('p', { cls: 'empty-state__title', text: '没有 scenario 数据' }));
    empty.appendChild(el('p', { text: '尚未投影 scenarios。等待 coordinator 生成 .cache/context-atlas/data.json 后重载。' }));
    return;
  }
  empty.hidden = true;
  body.hidden = false;

  if (!replayState.scenarioId || !findById(list, replayState.scenarioId)) replayState.scenarioId = list[0].id;
  if (!scenSel.options.length) {
    list.forEach(function (s) {
      scenSel.appendChild(el('option', { text: s.title || s.id, attrs: { value: s.id } }));
    });
;
  }
  scenSel.value = replayState.scenarioId;

  syncReplaySelectors();
}

function currentScenario() { return findById(scenarios(), replayState.scenarioId); }

function syncReplaySelectors() {
  var scenario = currentScenario();
  var polSel = $('replay-policy');
  var plSel = $('replay-placement');
  var modeSel = $('replay-mode');
  clear(polSel);
  clear(plSel);

  if (!scenario) return;

  var policies = asArray(scenario.policies);
  if (!policies.length) polSel.appendChild(el('option', { text: '(no policies)', attrs: { value: '' } }));
  policies.forEach(function (p) {
    polSel.appendChild(el('option', { text: (p.label || p.kind || p.id) + ' \u00b7 ' + p.id, attrs: { value: p.id } }));
  });
  if (!replayState.policyId || !findById(policies, replayState.policyId)) {
    replayState.policyId = policies.length ? policies[0].id : null;
  }
  polSel.value = replayState.policyId || '';

  var placements = asArray(scenario.placements);
  var withData = scenariosForPolicy(scenario, replayState.policyId);
  var usable = placements.filter(function (pl) { return !withData.length || withData.indexOf(pl.id) !== -1; });
  if (!usable.length) usable = placements;
  usable.forEach(function (pl) {
    plSel.appendChild(el('option', { text: (pl.rule || pl.id) + ' \u00b7 ' + pl.id, attrs: { value: pl.id } }));
  });
  if (!replayState.placementId || !usable.some(function (p) { return p.id === replayState.placementId; })) {
    replayState.placementId = usable.some(p=>p.id==='PL_main_defer') ? 'PL_main_defer' : usable[0]?.id;
  }
  plSel.value = replayState.placementId || '';
  modeSel.value = replayState.mode;

  var desc = $('replay-scenario-desc');
  desc.textContent = (scenario.description || '') + (scenario.assumptions ? ' \u2014 \u5047\u8bbe: ' + scenario.assumptions : '');

  renderReplayBody();
}

function renderReplayBody() {
  var scenario = currentScenario();
  var rep = resolveRun(scenario, replayState.policyId, replayState.placementId, replayState.mode);
  var lanes = $('timeline-lanes');
  var wakeList = $('replay-wake-list');
  var auditBox = $('replay-audit');
  var inspect = $('replay-inspect');
  clear(lanes); clear(wakeList); clear(auditBox); clear(inspect);

  if (!rep) {
    lanes.appendChild(el('div', { cls: 'empty-state' }, [
      el('p', { cls: 'empty-state__title', text: '该组合本轮没有投影数据' }),
      el('p', { text: '此 policy \u00d7 placement \u00d7 mode 不在当前投影的 runs 中。换一个 policy / placement，或等待新的投影。' })
    ]));
    $('replay-inspect-hint').textContent = '无数据';
    return;
  }

  var wakes = asArray(rep.wakes).map(function(w) {
    return {...w,candidate_id:w.id,actual_start:fmtSeconds(w.actual_start),trigger_time:fmtSeconds(w.trigger_time),trigger_owner_kind:w.owner_kind,trigger_owner_detail:w.owner_detail};
  });
  var packets = asArray(rep.packets);

  renderTimeline(scenario, wakes, rep);

  if (!wakes.length) wakeList.appendChild(el('li', { cls: 'empty-state', text: '本选择没有准入的 wake。' }));
  wakes.forEach(function (w) { wakeList.appendChild(wakeListItem(w)); });
  renderAudit(rep.audit || {}, auditBox);

  if (!replayState.wakeId || !packets.some(function (p) { return p.wake && p.wake.candidate_id === replayState.wakeId; })) {
    replayState.wakeId = packets.length ? packets[0].wake.candidate_id : null;
  }
  renderPacketInspect();
  highlightWakeSelection();
}

function renderTimeline(scenario, wakes, rep) {
  var lanes = $('timeline-lanes');
  var axis = $('timeline-axis');
  var domain = timelineDomain(scenario);
  var timeline = asArray(scenario.timeline);

  function lane(label, cls) {
    var l = el('div', { cls: 'tl-lane ' + (cls || '') });
    l.appendChild(el('span', { cls: 'tl-lane__label', text: label }));
    lanes.appendChild(l);
    return l;
  }

  var chatLane = lane('chat_active', 'tl-lane--chat');
  var hadChat = false;
  timeline.forEach(function (o) {
    if (o.type !== 'chat_interval') return;
    hadChat = true;
    addBand(chatLane, o.t, o.end != null ? o.end : o.t, domain, 'tl-band tl-band--chat', 'chat_active ' + fmtRange(o.t, o.end));
  });
  if (!hadChat) chatLane.appendChild(el('span', { cls: 'src-cov', attrs: { style: 'position:absolute;left:0;top:8px;' }, text: '本场景无 chat_interval' }));

  var busyMain = lane('turn_busy \u00b7 main', 'tl-lane--busy');
  var hadMain = false;
  timeline.forEach(function (o) {
    if (o.type !== 'busy_interval' || (o.session || 'main') !== 'main') return;
    hadMain = true;
    addBand(busyMain, o.t, o.end != null ? o.end : o.t, domain, 'tl-band tl-band--busy-main', 'turn_busy main ' + fmtRange(o.t, o.end));
  });
  if (!hadMain) busyMain.appendChild(el('span', { cls: 'src-cov', attrs: { style: 'position:absolute;left:0;top:8px;' }, text: '本场景无 main busy' }));

  var busyIndep = lane('turn_busy \u00b7 independent', 'tl-lane--busy');
  var hadIndep = false;
  timeline.forEach(function (o) {
    if (o.type !== 'busy_interval' || o.session !== 'independent') return;
    hadIndep = true;
    addBand(busyIndep, o.t, o.end != null ? o.end : o.t, domain, 'tl-band tl-band--busy-indep', 'turn_busy independent ' + fmtRange(o.t, o.end));
  });
  if (!hadIndep) busyIndep.appendChild(el('span', { cls: 'src-cov', attrs: { style: 'position:absolute;left:0;top:8px;' }, text: '本场景无独立 session busy' }));

  var markerLane = lane('实际 wake · 点击圆点', 'tl-lane--markers');
  wakes.forEach(function (w) {
    var start = parseHMS(w.actual_start);
    if (start == null) return;
    var pct = pctOf(start, domain);
    var btn = el('button', {
      cls: 'tl-marker',
      attrs: {
        type: 'button', 'data-wake-btn': w.candidate_id, style: 'left:' + pct + '%;',
        'aria-label': 'wake ' + w.candidate_id + ' at ' + w.actual_start, 'data-wake-selected': 'false'
      },
      on: { click: function () { selectWake(w.candidate_id); } }
    });
    btn.title=w.candidate_id+' · '+w.actual_start;
    btn.appendChild(el('span',{cls:'tl-marker__glyph',text:String(wakes.indexOf(w)+1)}));
    markerLane.appendChild(btn);

    var trig = parseHMS(w.trigger_time);
    if (trig != null && trig < start) {
      var tPct = pctOf(trig, domain);
      markerLane.appendChild(el('span', {
        cls: 'tl-connector',
        attrs: { style: 'left:' + tPct + '%;width:' + Math.max(0.6, pct - tPct) + '%;top:11px;border:none;background:repeating-linear-gradient(90deg,var(--copper-soft) 0 3px,transparent 3px 6px);' }
      }));
    }
  });

  var audit = rep.audit || {};
  var skippedIds = asArray(audit.skipped_ids);
  if (skippedIds.length) {
    var skipLane = lane('skipped（placement audit）', 'tl-lane--markers');
    skippedIds.forEach(function (id) {
      var t = findTriggerTime(scenario, id);
      if(t==null) return;
      var attrs = { title: id + ' · skipped · '+fmtSeconds(t), 'aria-label':id+' · skipped · '+fmtSeconds(t), tabindex:'0' };
      if (t != null) attrs.style = 'left:' + pctOf(t, domain) + '%;';
      skipLane.appendChild(el('span', { cls: 'tl-skip', attrs: attrs }));
    });
  }

  if (asArray(audit.dropped_ids).length) {
    var dropLane=lane('取消 / dropped','tl-lane--markers');
    audit.dropped_ids.forEach(function(id) {
      var t=findTriggerTime(scenario,id); if(t==null) return;
      dropLane.appendChild(el('span',{cls:'tl-skip',attrs:{style:'left:'+pctOf(t,domain)+'%;',title:id+' · '+fmtSeconds(t)+' · '+(audit.dropped_reasons[id]||'cancelled'),tabindex:'0'}}));
    });
  }
  clear(axis);
  var n = 5;
  for (var i = 0; i <= n; i++) axis.appendChild(el('span', { text: fmtSeconds(Math.round((domain * i) / n)) }));
}

function findTriggerTime(scenario, candId) {
  var candidate=findById(scenario.candidates_by_policy[replayState.policyId],candId);
  return candidate ? candidate.trigger_time : null;
}

function addBand(lane, t, end, domain, cls, title) {
  var left = pctOf(t, domain);
  var width = Math.max(0.4, pctOf(end, domain) - left);
  lane.appendChild(el('span', { cls: cls, attrs: { style: 'left:' + left + '%;width:' + width + '%;', title: title } }));
}

function pctOf(seconds, domain) {
  if (!isFinite(seconds)) return 0;
  return Math.max(0, Math.min(100, (seconds / domain) * 100));
}

function fmtRange(t, end) { return fmtSeconds(t) + (end != null ? '\u2013' + fmtSeconds(end) : ''); }

function fmtSeconds(s) {
  s = Math.max(0, Math.round(Number(s) || 0));
  var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return pad(h) + ':' + pad(m) + ':' + pad(sec);
}
function pad(n) { return (n < 10 ? '0' : '') + n; }
function parseHMS(hms) {
  if (hms == null) return null;
  var m = /^(\d+):(\d{2}):(\d{2})$/.exec(String(hms));
  if (!m) return null;
  return Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]);
}

function wakeListItem(w) {
  var li = el('li');
  var btn = el('button', {
    cls: 'wake-item',
    attrs: {
      type: 'button', 'data-wake-item': w.candidate_id, 'data-wake-selected': 'false',
      'aria-label': 'wake ' + w.candidate_id + ' actual start ' + w.actual_start
    },
    on: { click: function () { selectWake(w.candidate_id); } }
  });
  var row = el('div', { cls: 'wake-item__row' });
  row.appendChild(el('span', { cls: 'wake-item__id', text: w.candidate_id }));
  row.appendChild(el('span', { cls: 'wake-item__time', text: (w.trigger_time || '?') + ' \u2192 ' + (w.actual_start || '?') }));
  btn.appendChild(row);

  var flags = el('div', { cls: 'wake-item__row' });
  flags.appendChild(el('span', { cls: 'pill', text: 'owner ' + (w.trigger_owner_kind || '?') + '/' + (w.trigger_owner_detail || '?') }));
  flags.appendChild(el('span', { cls: 'pill', text: 'target ' + (w.execution_target || '?'), attrs: { 'data-target': w.execution_target || '' } }));
  if (w.deferred) flags.appendChild(el('span', { cls: 'pill pill--defer', text: 'deferred' }));
  if (w.coalesced) flags.appendChild(el('span', { cls: 'pill pill--coal', text: 'coalesced \u00d7' + asArray(w.coalesced_trigger_ids).length }));
  btn.appendChild(flags);

  var meta = el('div', { cls: 'wake-item__meta' });
  meta.appendChild(document.createTextNode('turn_busy@trigger=' + String(w.turn_busy_at_trigger) + ' \u00b7 chat_active@trigger=' + String(w.chat_active_at_trigger)));
  btn.appendChild(meta);

  li.appendChild(btn);
  return li;
}

function selectWake(id) {
  replayState.wakeId = id;
  highlightWakeSelection();
  renderPacketInspect();
}

function highlightWakeSelection() {
  var btns = document.querySelectorAll('[data-wake-btn]');
  for (var i = 0; i < btns.length; i++) btns[i].setAttribute('data-wake-selected', btns[i].getAttribute('data-wake-btn') === replayState.wakeId ? 'true' : 'false');
  var items = document.querySelectorAll('[data-wake-item]');
  for (var j = 0; j < items.length; j++) items[j].setAttribute('data-wake-selected', items[j].getAttribute('data-wake-item') === replayState.wakeId ? 'true' : 'false');
}

function renderAudit(audit, box) {
  var hasAny = ['skipped_ids', 'dropped_ids', 'coalesced_trigger_ids', 'consumed_self_wake_ids'].some(function (k) { return asArray(audit[k]).length; });
  var ledger = audit.session_ledger_ids;
  var hasLedger = isObj(ledger) && (asArray(ledger.main).length || asArray(ledger.independent).length);
  if (!hasAny && !hasLedger) {
    box.appendChild(el('p', { cls: 'audit__empty', text: 'audit 无跳过 / 取消 / 合并记录。' }));
    return;
  }
  if (asArray(audit.skipped_ids).length) {
    box.appendChild(el('p', { cls: 'audit__h', text: 'skipped (skipped_during_chat_active)' }));
    asArray(audit.skipped_ids).forEach(function (id) {
      var p = el('p', { cls: 'audit__row' });
      p.appendChild(el('span', { cls: 'audit__id', text: id }));
      p.appendChild(el('span', { cls: 'audit__why', text: ' \u00b7 ' + str((audit.skipped_reasons || {})[id]) }));
      box.appendChild(p);
    });
  }
  if (asArray(audit.dropped_ids).length) {
    box.appendChild(el('p', { cls: 'audit__h', text: 'cancelled / dropped' }));
    asArray(audit.dropped_ids).forEach(function (id) {
      var p = el('p', { cls: 'audit__row' });
      p.appendChild(el('span', { cls: 'audit__id', text: id }));
      p.appendChild(el('span', { cls: 'audit__why', text: ' \u00b7 ' + str((audit.dropped_reasons || {})[id]) }));
      box.appendChild(p);
    });
  }
  if (asArray(audit.coalesced_trigger_ids).length) {
    box.appendChild(el('p', { cls: 'audit__h', text: 'coalesced triggers' }));
    box.appendChild(el('p', { cls: 'audit__row', text: asArray(audit.coalesced_trigger_ids).join(', ') }));
  }
  if (asArray(audit.consumed_self_wake_ids).length) {
    box.appendChild(el('p', { cls: 'audit__h', text: 'consumed self-wake plans' }));
    box.appendChild(el('p', { cls: 'audit__row', text: asArray(audit.consumed_self_wake_ids).join(', ') }));
  }
  if (hasLedger) {
    box.appendChild(el('p', { cls: 'audit__h', text: 'session ledger ids（已实际交付/产生的来源）' }));
    box.appendChild(el('p', { cls: 'audit__row', text: 'main: ' + (asArray(ledger.main).join(', ') || '(empty)') }));
    box.appendChild(el('p', { cls: 'audit__row', text: 'independent: ' + (asArray(ledger.independent).join(', ') || '(empty)') }));
  }
}

function renderPacketInspect() {
  var inspect = $('replay-inspect');
  var hint = $('replay-inspect-hint');
  clear(inspect);
  var scenario = currentScenario();
  var rep = resolveRun(scenario, replayState.policyId, replayState.placementId, replayState.mode);
  var pkt = null;
  if (rep) {
    asArray(rep.packets).forEach(function (p) { if (p.wake && p.wake.candidate_id === replayState.wakeId) pkt = p; });
  }
  if (!pkt) {
    hint.textContent = '无数据';
    inspect.appendChild(el('p', { cls: 'empty-state', text: '该组合没有可检查的 packet。' }));
    return;
  }
  hint.textContent = pkt.wake.candidate_id;

  var w = pkt.wake || {};
  var head = el('div', { cls: 'pkt-head' });
  head.appendChild(el('h4', { cls: 'pkt-head__title', text: 'wake ' + (w.candidate_id || '?') }));
  head.appendChild(el('p', { cls: 'pkt-head__sub', text: 'trigger ' + (w.trigger_time || '?') + ' \u00b7 actual start ' + (w.actual_start || '?') + ' \u00b7 session ' + (pkt.session_identity || '?') }));
  inspect.appendChild(head);

  var facts = el('div', { cls: 'pkt-wakefacts' });
  facts.appendChild(el('span', { cls: 'pill', text: 'placement ' + pkt.placement.rule + ' → ' + pkt.execution_target }));
  facts.appendChild(el('span', { cls: 'pill', text: 'owner ' + (w.trigger_owner_kind || '?') + '/' + (w.trigger_owner_detail || '?') }));
  facts.appendChild(el('span', { cls: 'pill', text: 'mode ' + (pkt.session_mode || '?') }));
  if (w.turn_busy_at_trigger) facts.appendChild(el('span', { cls: 'pill pill--defer', text: 'turn_busy@trigger' }));
  if (w.chat_active_at_trigger) facts.appendChild(el('span', { cls: 'pill pill--skip', text: 'chat_active@trigger' }));
  if (w.deferred) facts.appendChild(el('span', { cls: 'pill pill--defer', text: 'deferred \u2192 重选于 actual start' }));
  if (w.coalesced) facts.appendChild(el('span', { cls: 'pill pill--coal', text: 'coalesced from ' + asArray(w.coalesced_trigger_ids).join(', ') }));
  inspect.appendChild(facts);
  if (w.placement_reason) inspect.appendChild(el('p', { cls: 'block__note', text: 'placement_reason: ' + w.placement_reason }));

  if (SYNTH_RE.test(str(pkt.label))) {
    inspect.appendChild(el('p', { cls: 'block__note', text: '来源标记: ' + pkt.label + ' \u2014 ' + (pkt.warning || '') }));
  }

  appendBlocks(inspect, 'current ambient（actual start 重选，非历史）', asArray(pkt.fresh_ambient_blocks), function (b) {
    var blk = blockEl('block--human', b.id, [pi('observed ' + (b.observed_at || '?') + (b.expires_at ? ' \u00b7 expires ' + b.expires_at : '')), pi('current', 'current')]);
    blk.appendChild(el('p', { cls: 'block__body', text: b.text || '' }));
    return blk;
  });

  appendBlocks(inspect, 'current memory（active，未被纠正/过期）', asArray(pkt.memory_items), function (b) {
    var blk = blockEl('block--human', b.id, [pi('current', 'current')]);
    blk.appendChild(el('p', { cls: 'block__body', text: b.text || '' }));
    return blk;
  });

  appendBlocks(inspect, 'passive recall（fixture-supplied，无 retrieval backend）', asArray(pkt.passive_recall_blocks), function (b) {
    var blk = blockEl('block--human', b.id, [pi('current', 'current'), pi('source ' + (b.source_memory_id || 'n/a'))]);
    blk.appendChild(el('p', { cls: 'block__body', text: b.body || '' }));
    return blk;
  });

  var humans = asArray(pkt.user_text_blocks);
  if (humans.length) {
    var sec = miniSection('human message \u2014 正文与包装分开');
    humans.forEach(function (b) {
      var blk = blockEl('block--human', b.id, [pi(b.origin || 'human'), pi(b.access || '')]);
      blk.appendChild(el('p', { cls: 'block__note', text: 'exact_user_text（保真正文）' }));
      blk.appendChild(el('blockquote', { cls: 'block__quote', text: b.exact_user_text || '' }));
      var wp = b.wrapper || {};
      blk.appendChild(el('p', { cls: 'block__note', text: 'wrapper metadata（包装，不等于正文）' }));
      var wrap = el('div', { cls: 'wrapper' });
      addKV2(wrap, 'channel', wp.channel, 'sender', wp.sender);
      addKV2(wrap, 'sender_time', wp.sender_time, 'received_at', wp.received_at);
      addKV2(wrap, 'reply_target', wp.reply_target, 'attachment', wp.attachment ? (wp.attachment.kind + ':' + wp.attachment.name) : '(none)');
      blk.appendChild(wrap);
      sec.appendChild(blk);
    });
    inspect.appendChild(sec);
  }

  var internals = asArray(pkt.internal_result_blocks);
  if (internals.length) {
    var isec = miniSection('internal-only prior results（内部结果，未外发）');
    internals.forEach(function (b) {
      var blk = blockEl('block--internal', b.id, [pi('status ' + (b.status || 'internal_only')), pi('delivered ' + String(b.delivered))]);
      blk.appendChild(el('p', { cls: 'block__body', text: b.body || '' }));
      if (b.note) blk.appendChild(el('p', { cls: 'block__note', text: b.note }));
      isec.appendChild(blk);
    });
    inspect.appendChild(isec);
  }

  var carried = asArray(pkt.carried_history_or_carryover);
  if (carried.length) {
    var hsec = miniSection('historical / carriedover material（历史，不声明为当前事实）');
    carried.forEach(function (c) {
      var blk = blockEl('block--history', c.id || c.kind || 'carried', [pi('history', 'history'), pi(c.kind || '')]);
      var body = c.text || c.body || c.exact_user_text || '';
      if (body) blk.appendChild(el('p', { cls: 'block__body', text: body }));
      else blk.appendChild(el('p', { cls: 'block__note', text: JSON.stringify(c) }));
      hsec.appendChild(blk);
    });
    inspect.appendChild(hsec);
  }

  var excluded = asArray(pkt.excluded);
  if (excluded.length) {
    var esec = miniSection('excluded sources / reasons（archive 或未选，不是当前输入）');
    var table = el('table', { cls: 'excl-table' });
    var tb = el('tbody');
    excluded.forEach(function (e) {
      var tr = el('tr');
      tr.appendChild(el('td', { cls: 'audit__id', text: (e.id || '?') + (e.kind ? ' [' + e.kind + ']' : '') }));
      tr.appendChild(el('td', { text: e.reason || '' }));
      tb.appendChild(tr);
    });
    table.appendChild(tb);
    esec.appendChild(table);
    inspect.appendChild(esec);
  }

  var post = asArray(pkt.scripted_outcomes);
  var produced = asArray(pkt.scripted_produced_results);
  if (post.length || produced.length) {
    var psec = miniSection('scripted POST-turn results（轮后注记，非本轮输入）');
    post.forEach(function (o) {
      var blk = el('div', { cls: 'block block--post' });
      var top = el('div', { cls: 'block__top' });
      top.appendChild(el('span', { cls: 'block__id', text: 'outcome' }));
      top.appendChild(el('span', { cls: 'pill pill--post', text: o.scripted_outcome || '' }));
      top.appendChild(el('span', { cls: 'pill', text: 'external_delivery ' + (o.external_delivery || 'n/a') }));
      top.appendChild(el('span', { cls: 'pill', text: 'next plan ' + (o.next_wake_plan || 'n/a') }));
      blk.appendChild(top);
      if (o.note) blk.appendChild(el('p', { cls: 'block__note', text: o.note }));
      psec.appendChild(blk);
    });
    produced.forEach(function (b) {
      var blk = el('div', { cls: 'block block--post' });
      blk.appendChild(pi('produced AFTER this input', 'post'));
      blk.appendChild(el('p', { cls: 'block__body', text: b.body || '' }));
      blk.appendChild(el('p', { cls: 'block__note', text: 'status=' + (b.status || 'internal_only') + ' \u00b7 delivered=' + String(b.delivered) }));
      psec.appendChild(blk);
    });
    inspect.appendChild(psec);
  }
}

function appendBlocks(root, title, list, build) {
  if (!list.length) return;
  var sec = miniSection(title);
  list.forEach(function (b) { sec.appendChild(build(b)); });
  root.appendChild(sec);
}

function blockEl(cls, id, pills) {
  var blk = el('div', { cls: 'block ' + (cls || '') });
  var top = el('div', { cls: 'block__top' });
  top.appendChild(el('span', { cls: 'block__id', text: id }));
  (pills || []).forEach(function (p) { if (p) top.appendChild(p); });
  blk.appendChild(top);
  return blk;
}
function pi(text, cls) { return el('span', { cls: 'pill' + (cls ? ' pill--' + cls : ''), text: text }); }
function addKV2(dl, k1, v1, k2, v2) {
  dl.appendChild(el('span', { cls: 'wrapper__k', text: k1 }));
  dl.appendChild(el('span', { text: v1 == null ? '(none)' : String(v1) }));
  if (k2) {
    dl.appendChild(el('span', { cls: 'wrapper__k', text: k2 }));
    dl.appendChild(el('span', { text: v2 == null ? '(none)' : String(v2) }));
  }
}

/* ================================================================= CHANGE */

var changeState = { caps: {} };

function renderChange() {
  var m = model();
  var intents = asArray(m.intents);
  var caps = asArray(m.capabilities);

  var iItems = $('change-intent-items');
  var cItems = $('change-capability-items');
  clear(iItems); clear(cItems);

  if (!caps.length && !intents.length) {
    iItems.appendChild(el('p', { cls: 'empty-state', text: '尚未投影 model.intents / capabilities。' }));
    renderChangeOutput();
    return;
  }

  intents.forEach(function (it) { iItems.appendChild(intentCapabilityRow(it)); });
  caps.forEach(function (cap) { cItems.appendChild(capabilityRow(cap)); });

  $('change-mode-hint').textContent=changeState.intent?'（使用预设）':'（自定义选择）';
  renderBaseline();
  renderStudyAttachment();
  renderObservationAttachment();
  renderCaseAttachment();
  renderChangeOutput();
}

function intentCapabilityRow(intent) {
  return el('button',{cls:'intent-btn',attrs:{type:'button','data-intent':intent.id,'aria-pressed':String(changeState.intent===intent.id)},
    on:{click:function(){changeState.caps={};intent.capability_ids.forEach(id=>changeState.caps[id]=true);changeState.intent=intent.id;renderChange();}}},
    [el('span',{cls:'intent-btn__label',text:intent.label}),el('span',{cls:'intent-btn__desc',text:intent.description||''})]);
}

function capabilityRow(cap) {
  var label = el('label', { cls: 'pick__item', attrs: { 'data-cap': cap.id, 'data-active': changeState.caps[cap.id] ? 'true' : 'false' } });
  label.appendChild(el('input', {
    attrs: { type: 'checkbox', 'data-cap-cb': cap.id, checked:changeState.caps[cap.id] ? 'checked' : null },
    on: {
      change: function (e) {
        changeState.caps[cap.id] = e.target.checked;
        changeState.intent=null;
        document.querySelectorAll('[data-intent]').forEach(b=>b.setAttribute('aria-pressed','false'));
        $('change-mode-hint').textContent='（自定义选择）';
        label.setAttribute('data-active', e.target.checked ? 'true' : 'false');
        renderChangeOutput();
      }
    }
  }));
  var lbox = el('span', { cls: 'pick__label' });
  lbox.appendChild(el('span', { cls: 'pick__title', text: cap.title || cap.id }));
  if (cap.owner) lbox.appendChild(el('span', { cls: 'pick__owner', text: 'owner: ' + cap.owner }));

  label.appendChild(lbox);
  return label;
}


function selectedCapabilities() {
  return asArray(model().capabilities).filter(function (c) { return changeState.caps[c.id]; });
}

function renderChangeOutput() {
  var out = $('change-output');
  var hint = $('change-summary-hint');
  clear(out);
  var selected = selectedCapabilities();
  $('brief-download').disabled=!selected.length;
  $('brief-status').textContent=selected.length?'':'先选择要改的范围';
  if (!selected.length) {
    hint.textContent = '未选择';
    out.appendChild(el('div', { cls: 'empty-state' }, [
      el('p', { cls: 'empty-state__title', text: '选择改动范围' }),
      el('p', { text: '先选一个改动意图，或勾选需要研究的环节。这里会整理相关检查、证据和交接问题。' })
    ]));
    updateBriefPreview();
    return;
  }
  hint.textContent = selected.length + ' 个环节 · ' + unionCheckIds(selected).length + ' 项检查';

  var evidenceRows = [];
  var limitRows = [];
  var ownerSet = {};
  var questionRows = [];
  selected.forEach(function (cap) {
    asArray(cap.evidence).forEach(function (ev) { evidenceRows.push({ cap: cap, ev: ev }); });
    asArray(cap.limits).forEach(function (l) { limitRows.push({ cap: cap, l: l }); });
    if (cap.owner) ownerSet[cap.owner] = true;
    asArray(cap.operating_questions).forEach(function (q) { questionRows.push({ cap: cap, q: q }); });
  });

  var head = el('div', { cls: 'section-mini' });
  head.appendChild(el('p', { cls: 'section-mini__h', text: '本次范围' }));
  head.appendChild(el('p', { text: '涉及环节：' + selected.map(function (c) { return c.title; }).join('、') }));
  head.appendChild(el('p', { text: '配置与状态归属：' + (Object.keys(ownerSet).join(', ') || '（未标注 owner）') + ' — 生产配置归原 runtime repo / runbook 所有。' }));
  out.appendChild(head);

  var checksById = {};
  asArray(model().checks).forEach(function (c) { checksById[c.id] = c; });
  var ids = unionCheckIds(selected);
  var groups = groupChecksByScope(ids.map(function (id) { return checksById[id]; }).filter(Boolean));
  var anyChecks = false;
  ['offline', 'read_only_network', 'local_probe', 'runtime_missing'].forEach(function (scope) {
    var list = groups[scope] || [];
    if (!list.length) return;
    anyChecks = true;
    var g = el('div', { cls: 'scope-group' });
    var gh = el('div', { cls: 'scope-group__h' });
    gh.appendChild(el('span', { text: scopeTitle(scope) }));
    gh.appendChild(el('span', { cls: 'scope-group__hint', text: scopeHint(scope) }));
    g.appendChild(gh);
    list.forEach(function (c) { g.appendChild(checkCard(c, selected)); });
    out.appendChild(g);
  });
  if (!anyChecks) out.appendChild(el('p', { cls: 'empty-state', text: '所选 capability 没有 check_ids；这不表示无需检查，而是本轮投影没有给出对应检查。' }));

  if (evidenceRows.length) {
    var es = miniSection('已有证据');
    evidenceRows.forEach(function (r) {
      var row = el('div', { cls: 'evi' });
      var top = el('div', { cls: 'evi__top' });
      top.appendChild(levelTag(r.ev.level));
      top.appendChild(el('span', { cls: 'evi__src', text: r.cap.id + (r.ev.label ? ' \u00b7 ' + r.ev.label : '') }));
      row.appendChild(top);
      row.appendChild(el('p', { cls: 'evi__claim', text: r.ev.claim || '' }));
      if (r.ev.source) row.appendChild(sourceLink(r.ev.source));
      es.appendChild(row);
    });
    out.appendChild(es);
  }

  if (questionRows.length) {
    var qs = miniSection('操作前要回答的问题');
    questionRows.forEach(function (r) {
      qs.appendChild(el('p', { cls: 'qbullet', text: r.cap.id + ': ' + (typeof r.q === 'string' ? r.q : JSON.stringify(r.q)) }));
    });
    out.appendChild(qs);
  }

  if (limitRows.length) {
    var ls = miniSection('尚未验证');
    var ul = el('ul', { cls: 'limits' });
    limitRows.forEach(function (r) { ul.appendChild(el('li', { text: r.cap.id + ': ' + (typeof r.l === 'string' ? r.l : JSON.stringify(r.l)) })); });
    ls.appendChild(ul);
    out.appendChild(ls);
  }

  updateBriefPreview();
}

function unionCheckIds(selectedCaps) {
  var seen = {}, out = [];
  selectedCaps.forEach(function (cap) {
    asArray(cap.check_ids).forEach(function (id) { if (!seen[id]) { seen[id] = true; out.push(id); } });
  });
  return out;
}

function groupChecksByScope(checks) {
  var groups = {};
  checks.forEach(function (c) {
    var scope = c.category;
    if (!groups[scope]) groups[scope] = [];
    groups[scope].push(c);
  });
  return groups;
}

function scopeTitle(scope) {
  return {
    offline: '离线检查',
    local_probe: 'local probe（需要显式授权）',
    runtime_missing: 'runtime evidence missing（尚缺）',
    read_only_network: '只读网络查询'
  }[scope] || scope;
}

function scopeHint(scope) {
  return {
    offline: '按各检查的前提运行；官方 checker 使用干净副本与独立 config。',
    local_probe: '启动本地命令会话/探针，需本轮显式授权；不是自动 fallback，也不接真实 provider。',
    runtime_missing: '真实请求 / 自然行为证据缺失；不能由离线结果推断为已验证。',
    read_only_network: '查询公开来源，不更新 pin，不安装。'
  }[scope] || '';
}

function checkCard(c, selectedCaps) {
  var card = el('div', { cls: 'check', attrs: { 'data-check': c.id } });
  var top = el('div', { cls: 'check__top' });
  top.appendChild(el('span', { cls: 'check__id', text: c.scope }));
  top.appendChild(el('span', { cls: 'check__title', text: c.title || '' }));
  card.appendChild(top);
  if (c.command) {
    var code = el('code', { cls: 'cmd' });
    code.appendChild(el('span', { cls: 'cmd__tag', text: 'TEXT ONLY' }));
    code.appendChild(document.createTextNode(c.command));
    card.appendChild(code);
  }
  if (c.description) card.appendChild(el('p', { cls: 'check__desc', text: c.description }));
  if (c.source) card.appendChild(sourceLink(c.source));
  var from = selectedCaps.filter(function (cap) { return asArray(cap.check_ids).indexOf(c.id) !== -1; }).map(function (cap) { return cap.id; });
  if (from.length) card.appendChild(el('p', { cls: 'check__from', text: '对应环节：' + from.join(', ') }));
  return card;
}

/* ----------------------------------------------------------- brief export */

function buildBriefMarkdown() {
  var sel = selectedCapabilities();
  var m = model();
  var checksById = {};
  asArray(m.checks).forEach(function (c) { checksById[c.id] = c; });
  var ids = unionCheckIds(sel);
  var groups = groupChecksByScope(ids.map(function (id) { return checksById[id]; }).filter(Boolean));

  var title = ($('brief-title') && $('brief-title').value.trim()) || 'Context change brief';
  var target = ($('brief-target-version') && $('brief-target-version').value.trim()) || '(未填写)';
  var date = str(getData().generated_on) || '(未知)';

  var L = [];
  L.push('# ' + title);
  L.push('');
  L.push('> 由 cc-context-lab Context Atlas 离线生成。命令仅作文本展示，未执行；本报表不产生部署或兼容性判定。');
  L.push('');
  L.push('- 生成数据日期 generated_on: ' + date);
  L.push('- schema: ' + (str(getData().schema) || '(unknown)'));
  L.push('- 目标版本 label（用户输入，**非已验证版本**）: ' + target);
  L.push('');
  L.push('## 已有证据基线');
  L.push('');
  baselineRows().forEach(r=>L.push('- '+r.label+'：'+r.value+'；'+r.note+'；source: '+r.source));
  L.push('');
  L.push('## 所选范围');
  L.push('');
  if (!sel.length) {
    L.push('_未选择 capability。_');
  } else {
    sel.forEach(function (cap) {
      L.push('- `' + cap.id + '` \u2014 ' + (cap.title || '') + '（owner: ' + (cap.owner || '未标注') + '）');
      if (cap.summary) L.push('  - ' + cap.summary);
    });
  }
  L.push('');
  L.push('## Evidence（所选 capability 的来源与层级）');
  L.push('');
  if (!sel.length) L.push('_无。_');
  sel.forEach(function (cap) {
    asArray(cap.evidence).forEach(function (ev) {
      L.push('- [' + (ev.level || 'unspecified') + '] ' + cap.id + (ev.label ? ' \u00b7 ' + ev.label : '') + '：' + (ev.claim || ''));
      if (ev.source) L.push('  - source: ' + ev.source);
    });
  });
  L.push('');
  L.push('## Checks / commands（TEXT ONLY，按 scope 分组）');
  L.push('');
  ['offline', 'read_only_network', 'local_probe', 'runtime_missing'].forEach(function (scope) {
    var list = groups[scope] || [];
    if (!list.length) return;
    L.push('### ' + scopeTitle(scope));
    L.push('');
    L.push('_' + scopeHint(scope) + '_');
    L.push('');
    list.forEach(function (c) {
      L.push('- **' + (c.title || c.id) + '** (`' + c.id + '`)');
      if (c.command) L.push('  - command: `' + c.command + '`');
      if (c.description) L.push('  - ' + c.description);
      if (c.source) L.push('  - source: ' + c.source);
    });
    L.push('');
  });
  if (!ids.length) L.push('_所选 capability 没有 check_ids。_');
  L.push('');
  L.push('## Limitations / unverified layers');
  L.push('');
  var anyLim = false;
  sel.forEach(function (cap) {
    asArray(cap.limits).forEach(function (l) { anyLim = true; L.push('- ' + cap.id + ': ' + l); });
  });
  if (!anyLim) L.push('_所选 capability 未附 limits；这不代表无缺口，须按 repo current-state 为准。_');
  L.push('');
  L.push('## Operator handoff questions');
  L.push('');
  var anyQ = false;
  sel.forEach(function (cap) {
    asArray(cap.operating_questions).forEach(function (q) { anyQ = true; L.push('- ' + cap.id + ': ' + q); });
  });
  if (!anyQ) L.push('_无 操作前要回答的问题。_');
  L.push('');
  L.push('## runtime ownership / handoff / rollback');
  L.push('');
  L.push('原 runtime repo / runbook 拥有生产配置。交付 candidate 前需确认：');
  L.push('');
  L.push('1. 按所选检查的前提完成验证；官方 checker 使用隔离副本与独立 config，保留逐版本分层报告。');
  L.push('2. 本地 probe 需单独授权，且不接真实 provider。');
  L.push('3. 交接步骤、安装/回滚命令与验收判据由 runtime owner 提供；本 brief 不预置可执行部署命令。');
  L.push('4. rollback 问题：如何定位上一版 candidate、如何还原原 source、如何确认恢复后行为一致？');
  L.push('5. 真实请求 / 模型行为证据仍需单独实验，不得由离线结果补成已验证。');
  asArray(m.workflow).forEach(function (w) {
    if (w && w.title) {
      L.push('');
      L.push('- ' + w.title + '（' + (w.owner || '未标注') + '）：' + (w.body || ''));
    }
  });
  L.push('');
  L.push('---');
  L.push('研究 authority 在 repo 文档；本界面为离线 viewer。');
  if (studyAttachment) {
    L.push('');
    L.push('## 附：本次对照研究（带入时的固定快照）');
    L.push('');
    L.push(studyAttachment.markdown);
  }
  if (observationAttachment) {
    L.push('');
    L.push(observationAttachment.kind==='cc_run'?'## 附：CC Run（带入时的固定快照）':'## 附：请求观察（带入时的固定快照）');
    L.push('');
    L.push(observationAttachment.markdown);
  }
  if (caseAttachment) {
    L.push('','## 附：完整 context case（带入时的固定快照）','',caseAttachment.markdown);
  }
  return L.join('\n');
}

function updateBriefPreview() {
  var pre = $('brief-preview');
  if (!pre) return;
  pre.textContent = buildBriefMarkdown();
}

function downloadBrief() {
  if(!selectedCapabilities().length) return;
  var text = buildBriefMarkdown();
  var status = $('brief-status');
  try {
    var blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    var titleEl = $('brief-title');
    var name = (titleEl && titleEl.value.trim()) || 'context-change-brief';
    name = name.replace(/[^\w\u4e00-\u9fa5.\-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80) || 'context-change-brief';
    a.href = url;
    a.download = name + '.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Attached studies are larger than the original brief. Allow the browser
    // download handoff to acquire the Blob before releasing its object URL.
    setTimeout(function () { URL.revokeObjectURL(url); }, 60000);
    if (status) status.textContent = '已生成 ' + a.download;
  } catch (err) {
    if (status) status.textContent = '下载失败: ' + (err && err.message || err);
  }
}

/* ================================================================ SOURCES */

var srcState = { query: '' };

function renderSources() {
  var m = model();

  var officialList = $('official-list');
  clear(officialList);
  var official = asArray(m.official_sources);
  if (!official.length) officialList.appendChild(el('li', { cls: 'src-cov', text: '未投影 official_sources。' }));
  official.forEach(function (o) {
    var href = safeHref(o.url);
    var li = el('li');
    if (href) li.appendChild(el('a', { text: o.title || o.url, attrs: { href: href, target: '_blank', rel: 'noopener noreferrer' } }));
    else li.appendChild(el('span', { text: o.title || '' }));
    if (o.url) li.appendChild(el('small', { text: o.url }));
    officialList.appendChild(li);
  });

  var search = $('sources-search');
  if (!search.dataset.bound) {
    search.addEventListener('input', function () { srcState.query = search.value; renderSourceRows(); });
    search.dataset.bound = '1';
  }
  renderSourceRows();
}

function renderSourceRows() {
  var list = upstreams();
  var tbody = $('sources-tbody');
  var empty = $('sources-empty');
  var table = $('sources-table');
  clear(tbody);

  if (!list.length) {
    table.hidden = true;
    empty.hidden = false;
    clear(empty);
    empty.appendChild(el('p', { cls: 'empty-state__title', text: '没有 upstream 数据' }));
    empty.appendChild(el('p', { text: '尚未投影 upstreams。等待 coordinator 生成 .cache/context-atlas/data.json 后重载。' }));
    return;
  }
  table.hidden = false;

  var q = str(srcState.query).trim().toLowerCase();
  var rows = list.filter(function (u) {
    if (!q) return true;
    var hay = [u.repo, u.role, u.revision, u.coverage, u.observed_on].map(str).join(' ').toLowerCase();
    return hay.indexOf(q) !== -1;
  });

  if (!rows.length) {
    empty.hidden = false;
    clear(empty);
    empty.appendChild(el('p', { cls: 'empty-state__title', text: '没有匹配的 source' }));
    empty.appendChild(el('p', { text: '没有 repo / role / revision 命中 “' + srcState.query + '”。清空搜索可看全部 ' + list.length + ' 项。' }));
    return;
  }
  empty.hidden = true;

  rows.forEach(function (u) {
    var tr = el('tr');
    var tdRepo = el('td', { cls: 'src-repo' });
    var href = safeHref(u.url);
    if (href) tdRepo.appendChild(el('a', { text: u.repo || u.url, attrs: { href: href, target: '_blank', rel: 'noopener noreferrer' } }));
    else tdRepo.appendChild(document.createTextNode(u.repo || '(no repo)'));
    tr.appendChild(tdRepo);

    var tdRev = el('td');
    tdRev.appendChild(el('span', { cls: 'src-rev', text: str(u.revision || '(unpinned)').slice(0, 12) }));
    tdRev.appendChild(el('span', { cls: 'src-date', text: 'observed ' + (u.observed_on || '?') }));
    tr.appendChild(tdRev);

    tr.appendChild(el('td', { cls: 'src-role', text: u.role || '' }));

    var tdCov = el('td');
    tdCov.appendChild(el('span', { cls: 'src-cov', text: u.coverage || '' }));
    if (u.revision) tdCov.appendChild(el('span', { cls: 'src-date', text: 'rev ' + u.revision }));
    tr.appendChild(tdCov);

    var tdRv = el('td');
    tdRv.appendChild(el('span', { cls: 'rv ' + (u.runtime_verified ? 'rv--yes' : 'rv--no'), text: u.runtime_verified ? 'verified' : 'not verified' }));
    tr.appendChild(tdRv);

    var tdTip = el('td');
    if (u.newer_tip) {
      var tip = u.newer_tip;
      tdTip.appendChild(el('div', { cls: 'src-tip', text: 'tip ' + str(tip.revision).slice(0, 12) }));
      tdTip.appendChild(el('div', { cls: 'src-tip', text: 'bounded_read=' + String(tip.bounded_read) + ' \u00b7 full_read=' + String(tip.full_read) }));
    } else {
      tdTip.appendChild(el('span', { cls: 'src-tip__none', text: '\u2014 无已 fetch 的更新 tip' }));
    }
    tr.appendChild(tdTip);

    tbody.appendChild(tr);
  });
}

/* =================================================================== TABS */

function activateTab(name, focusTab) {
  var tabs = document.querySelectorAll('#atlas-tabbar [role="tab"]');
  for (var i = 0; i < tabs.length; i++) {
    var on = tabs[i].getAttribute('data-tab') === name;
    tabs[i].setAttribute('aria-selected', on ? 'true' : 'false');
    tabs[i].tabIndex = on ? 0 : -1;
    if (on && focusTab) tabs[i].focus();
  }
  var panels = document.querySelectorAll('[data-panel]');
  for (var j = 0; j < panels.length; j++) panels[j].hidden = panels[j].getAttribute('data-panel') !== name;
  if (name === 'overview') requestAnimationFrame(drawGraphEdges);
  if (name === 'replay') renderReplay();
  if (name === 'case') renderCase();
  if (name === 'study') renderStudy();
  if (name === 'observation') renderObservation();
  if (name === 'run') renderRun();
  if (name === 'change') renderChange();
  if (name === 'sources') renderSources();
}

function wireTabs() {
  var tabbar = $('atlas-tabbar');
  tabbar.addEventListener('click', function (e) {
    var t = e.target.closest('[role="tab"]');
    if (t) activateTab(t.getAttribute('data-tab'), false);
  });
  tabbar.addEventListener('keydown', function (e) {
    var tabs = Array.prototype.slice.call(tabbar.querySelectorAll('[role="tab"]'));
    var idx = tabs.indexOf(document.activeElement);
    if (idx === -1) return;
    var next = null;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = tabs[(idx + 1) % tabs.length];
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = tabs[(idx - 1 + tabs.length) % tabs.length];
    else if (e.key === 'Home') next = tabs[0];
    else if (e.key === 'End') next = tabs[tabs.length - 1];
    if (next) { e.preventDefault(); activateTab(next.getAttribute('data-tab'), true); }
  });

  var ctrls = $('overview-controls');
  ctrls.addEventListener('click', function (e) {
    var b = e.target.closest('[data-ov-layout]');
    if (!b) return;
    ovState.layout = b.getAttribute('data-ov-layout');
    var btns = ctrls.querySelectorAll('[data-ov-layout]');
    for (var i = 0; i < btns.length; i++) {
      var on = btns[i] === b;
      btns[i].classList.toggle('is-active', on);
      btns[i].setAttribute('aria-pressed', on ? 'true' : 'false');
    }
    renderOverview();
  });

  var sel = $('replay-selectors');
  sel.addEventListener('change', function (e) {
    var ctl = e.target.getAttribute('data-ctl');
    if (ctl === 'scenario') { replayState.scenarioId = e.target.value; replayState.wakeId = null; replayState.policyId = null; replayState.placementId = null; syncReplaySelectors(); }
    else if (ctl === 'policy') { replayState.policyId = e.target.value; replayState.wakeId = null; syncReplaySelectors(); }
    else if (ctl === 'placement') { replayState.placementId = e.target.value; replayState.wakeId = null; renderReplayBody(); }
    else if (ctl === 'mode') { replayState.mode = e.target.value; replayState.wakeId = null; renderReplayBody(); }
  });

  $('brief-title').addEventListener('input', updateBriefPreview);
  $('brief-target-version').addEventListener('input', updateBriefPreview);
  $('brief-download').addEventListener('click', downloadBrief);
}

/* ==================================================================== BOOT */

function renderMasthead() {
  var d=getData();
  $('atlas-date-chip').textContent='快照 · '+(d.generated_on||'未知日期');
  if(d.__parse_error) $('atlas-snapshot-chip').textContent='数据解析失败：'+d.__parse_error;
}

function boot() {
  getData();
  renderMasthead();
  wireTabs();
  wireStudy();
  wireObservation();
  wireRun();
  wireCase();
  renderOverview();
  new ResizeObserver(()=>requestAnimationFrame(drawGraphEdges)).observe($('overview-canvas'));
  activateTab(getData().open_run ? 'run' : getData().open_case ? 'case' : getData().open_observation ? 'observation' : getData().study_plan && !getData().context_case ? 'study' : 'overview', false);
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
else boot();

function baselineRows() {
  var c=getData().compatibility, t=getData().target_runtime;
  var rows=c.checks.map(function(x){return {label:'官方离线 · CC '+x.executable_version,value:x.offline_status+' · '+x.test_kit.passed+' tests',note:'strict='+x.validation.success+'；'+c.checked_on+'；candidate '+c.candidate_manifest_version,source:'references/context-profile-compatibility.json'};});
  rows.push({label:'目标 types',value:t.generated_types_version+' · '+t.generated_types_count+' 份',note:t.checked_on+'；仅已列 symbols 已读',source:'references/target-runtime-2.1.289.json'});
  rows.push({label:'本地 composition',value:t.composition.length+' 段 / '+t.section_events.length+' 个事件',note:t.checked_on+'；'+t.resolved.traits.join('/')+'；端点请求 '+t.requests_to_configured_loopback_endpoint,source:'references/target-runtime-2.1.289.json'});
  c.checks.forEach(x=>rows.push({label:'请求 / 模型 / 安装 · '+x.executable_version,value:[x.request_behavior,x.model_behavior,x.production_installation].map(v=>({not_tested:'未测',not_performed:'未安装'}[v]||v)).join(' / '),note:'request='+x.request_behavior+'；model='+x.model_behavior+'；installation='+x.production_installation,source:'references/context-profile-compatibility.json'}));
  return rows;
}
function renderBaseline() {
  var root=$('change-baseline');clear(root);
  root.appendChild(el('h3',{cls:'baseline__h',text:'已有证据 · 不随填写的目标版本改变'}));
  var grid=el('div',{cls:'baseline__grid'});
  baselineRows().forEach(r=>grid.appendChild(el('div',{cls:'obs'},[el('div',{cls:'obs__layer',text:r.label}),el('div',{cls:'obs__value',text:r.value}),el('p',{cls:'obs__note',text:r.note}),sourceLink(r.source)])));
  root.appendChild(grid);
}
