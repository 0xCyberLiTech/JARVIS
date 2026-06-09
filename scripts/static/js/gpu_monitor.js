// ══════════════════════════════════════════════════════════════
// GPU MONITOR — anneaux CPU/RAM/GPU/VRAM (chat HUD)
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-15.
//
// Affichage temps réel des stats système dans les anneaux SVG du
// chat HUD : CPU charge, RAM, GPU charge, VRAM (système + LLM).
// Constantes graphiques (CIRC, _RTX_BLUE/GREEN, _VRAM_GRADIENT_*),
// fetch /api/stats, anim hexagone, polling périodique.
//
// Fichier .js classique (scope global). Chargé APRÈS jarvis_main.js
// et AVANT les autres modules. Top-level : pollVramLlm() au load.

const CIRC=289.0;
function setArc(id,pct){const el=document.getElementById(id);if(el)el.style.strokeDashoffset=CIRC-(Math.min(pct,100)/100)*CIRC;}
function setArcColor(id,color){const el=document.getElementById(id);if(el){el.style.stroke=color;el.style.filter=`drop-shadow(0 0 5px ${color})`;}}
function dynColor(v,w,c){if(v>=c)return{text:'c-red',bar:'b-red',hex:_cssVar('--red')};if(v>=w)return{text:'c-yellow',bar:'b-yellow',hex:_cssVar('--yellow')};return{text:'c-green',bar:'b-green',hex:_cssVar('--green')};}
function setBar(id,pct,cls){const el=document.getElementById(id);if(el){el.style.width=Math.min(pct,100)+'%';el.className='bar-fill '+cls;}}
function setMiniBar(id,pct,cls){const el=document.getElementById(id);if(el){el.style.width=Math.min(pct,100)+'%';el.className='mini-gauge-fill '+cls;}}

let ticks=0;
function _updateMonArcs(d){
  const gc=dynColor(d.gpu_util,50,85);
  setArc('arc-gpu',d.gpu_util); setArcColor('arc-gpu',gc.hex);
  const _tgu=document.getElementById('txt-gpu-util'); if(_tgu){_tgu.textContent=d.gpu_util+'%';_tgu.style.fill=gc.hex;}
  const vp=d.mem_used/d.mem_total*100;
  setArc('arc-vram',vp);
  document.getElementById('txt-vram-used').textContent=d.mem_used.toFixed(1)+' GB';
  document.getElementById('txt-vram-total').textContent='/ '+d.mem_total.toFixed(0)+' GB';
  const tc=dynColor(d.temp,60,80);
  setArc('arc-temp',d.temp); setArcColor('arc-temp',tc.hex);
  const _ttt=document.getElementById('txt-temp'); if(_ttt){_ttt.textContent=d.temp+'°';_ttt.style.fill=tc.hex;}
  const pp=d.power_draw/d.power_limit*100;
  setArc('arc-power',pp);
  document.getElementById('txt-power').textContent=d.power_draw.toFixed(0)+'W';
  const cc=dynColor(d.cpu,50,85);
  setArc('arc-cpu',d.cpu); setArcColor('arc-cpu',cc.hex);
  const _tcu=document.getElementById('txt-cpu'); if(_tcu){_tcu.textContent=d.cpu.toFixed(0)+'%';_tcu.style.fill=cc.hex;}
  const rp=d.ram_used/d.ram_total*100;
  setArc('arc-ram',rp);
  document.getElementById('txt-ram-used').textContent=d.ram_used.toFixed(1)+' GB';
  document.getElementById('txt-ram-total').textContent='/ '+d.ram_total.toFixed(0)+' GB';
  return {gc,vp,tc,pp,cc,rp};
}
function _updateMonGraphsAndPanels(d,gc,vp,tc,pp,cc){
  graphs.vram.max=d.mem_total; graphs.power.max=d.power_limit||500;
  drawChart('gpu',d.gpu_util); drawChart('vram',d.mem_used);
  drawChart('temp',d.temp);   drawChart('power',d.power_draw);
  document.getElementById('g-lbl-gpu').textContent=d.gpu_util+'%';
  document.getElementById('g-lbl-vram').textContent=d.mem_used.toFixed(1)+' GB';
  document.getElementById('g-lbl-temp').textContent=d.temp+'°C';
  document.getElementById('g-lbl-power').textContent=d.power_draw.toFixed(0)+' W';
  document.getElementById('d-gpu-util').textContent=d.gpu_util+'%'; setBar('b-gpu-util',d.gpu_util,gc.bar);
  document.getElementById('d-enc').textContent=d.enc_util+'%';       setBar('b-enc',d.enc_util,'b-cyan');
  document.getElementById('d-dec').textContent=d.dec_util+'%';       setBar('b-dec',d.dec_util,'b-blue');
  document.getElementById('d-clk-gpu').textContent=d.clk_gpu+' MHz';setBar('b-clk-gpu',d.clk_gpu/30,'b-cyan');
  document.getElementById('d-clk-mem').textContent=d.clk_mem+' MHz';setBar('b-clk-mem',d.clk_mem/150,'b-blue');
  document.getElementById('d-temp').textContent=d.temp+'°C';         setBar('b-temp',d.temp,tc.bar);
  document.getElementById('d-power').textContent=d.power_draw.toFixed(0)+' W / '+d.power_limit.toFixed(0)+' W'; setBar('b-power',pp,'b-purple');
  document.getElementById('d-fan').textContent=d.fan!==null?d.fan+'%':'N/A'; setBar('b-fan',d.fan||0,'b-blue');
  document.getElementById('d-vram').textContent=d.mem_used.toFixed(1)+' GB'; setBar('b-vram',vp,'b-blue');
  document.getElementById('d-vram-total').textContent=d.mem_total.toFixed(1)+' GB';
  document.getElementById('d-vram-free').textContent=d.mem_free.toFixed(1)+' GB';
  document.getElementById('d-cpu').textContent=d.cpu.toFixed(0)+'%'; setBar('b-cpu-p',d.cpu,cc.bar);
  document.getElementById('d-cpu-count').textContent=d.cpu_count;
  document.getElementById('d-cpu-freq').textContent=d.cpu_freq+' MHz';
  document.getElementById('d-uptime').textContent=d.uptime;
  document.getElementById('d-net-up').textContent=d.net_up.toFixed(2)+' MB/s'; setBar('b-net-up',Math.min(d.net_up/10*100,100),'b-green');
  document.getElementById('d-net-dn').textContent=d.net_dn.toFixed(2)+' MB/s'; setBar('b-net-dn',Math.min(d.net_dn/10*100,100),'b-cyan');
  document.getElementById('d-disk-r').textContent=d.disk_r.toFixed(0)+' MB/s'; setBar('b-disk-r',Math.min(d.disk_r/5*100,100),'b-cyan');
  document.getElementById('d-disk-w').textContent=d.disk_w.toFixed(0)+' MB/s'; setBar('b-disk-w',Math.min(d.disk_w/5*100,100),'b-purple');
}
function _updateMonSidebar(d,vp,pp,rp){
  setMiniBar('m-gpu',d.gpu_util,'b-cyan');   document.getElementById('mv-gpu').textContent=d.gpu_util+'%';
  const _nf=document.getElementById('hud-neural-fill');
  const _nv=document.getElementById('hud-neural-val');
  if(_nf) _nf.style.width=d.gpu_util+'%';
  if(_nv) _nv.textContent=d.gpu_util+'%';
  setMiniBar('m-vram',vp,'b-blue');           document.getElementById('mv-vram').textContent=d.mem_used.toFixed(1)+' GB';
  setMiniBar('m-temp',d.temp,'b-green');      document.getElementById('mv-temp').textContent=d.temp+'°';
  setMiniBar('m-power',pp,'b-purple');        document.getElementById('mv-power').textContent=d.power_draw.toFixed(0)+'W';
  setMiniBar('m-cpu',d.cpu,'b-green');        document.getElementById('mv-cpu').textContent=d.cpu.toFixed(0)+'%';
  setMiniBar('m-ram',rp,'b-blue');            document.getElementById('mv-ram').textContent=d.ram_used.toFixed(1)+' GB';
}
function _updateMonRtxPanel(d,pp){
  const mu=d.mem_util??0;
  const bw=d.clk_mem?Math.round(d.clk_mem*256*2/8/1000):0;
  const marge=d.power_limit?(d.power_limit-d.power_draw):0;
  const eff=d.power_draw>1?(d.gpu_util/d.power_draw*100).toFixed(1):'—';
  document.getElementById('d-mem-util').textContent=mu+'%';         setBar('b-mem-util',mu,'b-blue');
  document.getElementById('d-membw').textContent=bw+' GB/s';        setBar('b-membw',Math.min(bw/960*100,100),'b-cyan');
  document.getElementById('d-pow-budget').textContent=pp.toFixed(0)+'%'; setBar('b-pow-budget',pp,'b-purple');
  const pst=d.p_state!==null&&d.p_state!==undefined?'P'+d.p_state:'—';
  document.getElementById('d-pstate').textContent=pst;
  const thrEl=document.getElementById('d-throttle');
  if(thrEl){thrEl.textContent=d.throttle?'⚠ ACTIF':'✓ NORMAL';thrEl.className='stat-val '+(d.throttle?'c-warn':'c-green');}
  const pcieEl=document.getElementById('d-pcie');
  if(pcieEl) pcieEl.textContent=d.pcie_gen&&d.pcie_width?`Gen${d.pcie_gen} ×${d.pcie_width}`:'—';
  document.getElementById('d-pow-adv').textContent=d.power_draw.toFixed(0)+' W';  setBar('b-pow-adv',pp,'b-purple');
  document.getElementById('d-pow-limit').textContent=d.power_limit?d.power_limit.toFixed(0)+' W':'—';
  document.getElementById('d-pow-marge').textContent=marge>0?'+'+marge.toFixed(0)+' W':marge.toFixed(0)+' W';
  document.getElementById('d-eff').textContent=eff!=='—'?eff+' %/W':'—';
  document.getElementById('d-vram-adv').textContent=d.mem_free?d.mem_free.toFixed(1)+' GB':'—';
}
function _updateMonCuda(d){
  const cudaVerEl=document.getElementById('d-cuda-ver');
  if(cudaVerEl&&d.cuda_ver) cudaVerEl.textContent=d.cuda_ver;
  const drvVerEl=document.getElementById('d-drv-ver');
  if(drvVerEl&&d.driver_ver) drvVerEl.textContent=d.driver_ver;
  if(d.max_clk_gpu){
    document.getElementById('d-max-clk-gpu').textContent=d.max_clk_gpu+' MHz';
    setBar('b-max-clk-gpu',Math.min(d.max_clk_gpu/30,100),'b-cyan');
  }
  if(d.max_clk_mem){
    document.getElementById('d-max-clk-mem').textContent=d.max_clk_mem+' MHz';
    setBar('b-max-clk-mem',Math.min(d.max_clk_mem/150,100),'b-blue');
  }
  const trEl2=document.getElementById('d-throttle-reason');
  if(trEl2&&d.throttle_reason!==null&&d.throttle_reason!==undefined){
    trEl2.textContent=d.throttle_reason;
    trEl2.className='stat-val '+(d.throttle_reason==='NONE'||d.throttle_reason==='IDLE'?'c-green':'c-warn');
  }
  if(d.temp_warn!=null){
    var tw=document.getElementById('d-temp-warn');
    tw.textContent=d.temp_warn+' °C';
    tw.classList.toggle('temp-danger', d.temp>=d.temp_warn);
    tw.classList.toggle('temp-warn',   d.temp< d.temp_warn);
  }
  if(d.temp_slow) document.getElementById('d-temp-slow').textContent=d.temp_slow+' °C';
  if(d.temp_shut) document.getElementById('d-temp-shut').textContent=d.temp_shut+' °C';
  if(d.cuda_proc_count!==undefined) document.getElementById('d-cuda-procs-count').textContent=d.cuda_proc_count;
  if(d.cuda_procs!==undefined) document.getElementById('d-cuda-procs').textContent=d.cuda_procs;
  const cudaBadge=document.getElementById('dsp-cuda-badge');
  const cudaLabel=document.getElementById('dsp-cuda-label');
  const cudaState=document.getElementById('dsp-cuda-state');
  const cudaDot=document.getElementById('dsp-cuda-dot');
  if(cudaBadge&&d.cuda_ver&&d.cuda_ver!=='N/A'){
    cudaBadge.classList.remove('dsp-cuda-cpu'); cudaBadge.classList.add('dsp-cuda-on');
    if(cudaDot){cudaDot.classList.add('cuda-dot-on');cudaDot.classList.remove('cuda-dot-cpu');}
    if(cudaLabel) cudaLabel.textContent='CUDA '+d.cuda_ver;
    if(cudaState){cudaState.textContent='● ON';cudaState.classList.add('cuda-lbl-on');cudaState.classList.remove('cuda-lbl-cpu');}
  }else if(cudaBadge){
    cudaBadge.classList.remove('dsp-cuda-on'); cudaBadge.classList.add('dsp-cuda-cpu');
    if(cudaDot){cudaDot.classList.add('cuda-dot-cpu');cudaDot.classList.remove('cuda-dot-on');}
    if(cudaLabel) cudaLabel.textContent='CUDA';
    if(cudaState){cudaState.textContent='○ CPU';cudaState.classList.add('cuda-lbl-cpu');cudaState.classList.remove('cuda-lbl-on');}
  }
  _fxUpdateCudaScreen(d.cuda_ver);
}
function updateMonitor(d){
  ticks++;
  const el=document.getElementById('gpu-name'); if(el)el.textContent=d.name;
  const fu=document.getElementById('f-uptime'); if(fu)fu.textContent='REFRESH : '+ticks+'s';
  const {gc,vp,tc,pp,cc,rp}=_updateMonArcs(d);
  _updateMonGraphsAndPanels(d,gc,vp,tc,pp,cc);
  _updateMonSidebar(d,vp,pp,rp);
  _updateMonRtxPanel(d,pp);
  _updateMonCuda(d);
}

var _statsPollTimer = null;
async function pollStats(){
  try{const r=await fetch('/api/stats');const d=await r.json();updateMonitor(d);}catch(e){}
  _statsPollTimer = setTimeout(pollStats,_POLL_STATS_MS);
}
pollStats();

// ── VRAM LLM Ollama ────────────────────────────────────────────────────
var _VRAM_TOTAL  = 0; // sera rempli par l'API (pynvml réel)
var _VRAM_MODEL_COLORS = {
  'phi4':     _cssVar('--cyan'),
  'qwen':     _cssVar('--orange2'),
  'gemma':    _cssVar('--green'),
  'mxbai':    _cssVar('--purple'),
  'deepseek': _cssVar('--yellow'),
  'llava':    _cssVar('--pink'),
};
function _vramColor(name) {
  var n = name.toLowerCase();
  for (var k in _VRAM_MODEL_COLORS) { if (n.indexOf(k) !== -1) return _VRAM_MODEL_COLORS[k]; }
  return '#4488ff';
}

function _fmtBytes(b) {
  if (b >= 1073741824) return (b/1073741824).toFixed(1)+' GB';
  if (b >= 1048576)    return (b/1048576).toFixed(0)+' MB';
  return b+' B';
}

function _vramRenderSwap(totalSwap) {
  var swWrap = document.getElementById('vram-llm-swap-wrap');
  var swBar  = document.getElementById('vram-llm-swap-bar');
  var swLbl  = document.getElementById('vram-llm-swap-lbl');
  if (!swWrap || !swBar || !swLbl) return;
  if (totalSwap > 0) {
    swWrap.style.display = 'flex';
    var swPct = Math.min(100, (totalSwap / (32 * 1024**3)) * 100);
    swBar.style.setProperty('--swap-pct', swPct + '%');
    swLbl.textContent = 'SWAP ' + _fmtBytes(totalSwap);
  } else {
    swWrap.style.display = 'none';
  }
}

var _VRAM_ROLE_COLORS = {SOC:'#00e5ff', GÉNÉRAL:'#4caf50', CODE:'#ff9800', RAG:'#cc66ff'};

function _vramBuildModelRows(models, cap, totalVram) {
  var rows = models.map(function(m) {
    var col = _vramColor(m.name);
    var rc  = _VRAM_ROLE_COLORS[m.role] || col;
    var pct = m.pct || 0;
    var meta = [];
    if (m.params) meta.push(m.params);
    if (m.quant)  meta.push(m.quant);
    var keep = (m.expires_at && m.expires_at !== '0001-01-01T00:00:00Z')
      ? 'exp. ' + new Date(m.expires_at).toLocaleTimeString('fr-FR', {hour:'2-digit',minute:'2-digit'})
      : '∞';
    var swapTxt = m.size_swap > 0 ? ' · <span class="vram-swap-txt">SWAP '+_fmtBytes(m.size_swap)+'</span>' : '';
    var label = '<span class="vram-role-lbl" style="--rc:'+rc+'">['+m.role+']</span>'
              + ' <span class="vram-model-name">'+m.name.split('/').pop()+'</span>'
              + (meta.length ? ' <span class="vram-model-meta">'+meta.join(' · ')+'</span>' : '')
              + ' <span class="vram-model-keep">'+keep+'</span>';
    var val   = '<span class="vram-size-val" style="--vc:'+col+'">'+_fmtBytes(m.size_vram)+'</span>'
              + ' <span class="vram-model-pct">'+pct+'%</span>'
              + swapTxt;
    var swapPct = cap ? Math.min(100 - pct, Math.round(m.size_swap / cap * 100)) : 0;
    var swapSeg = swapPct > 0
      ? '<div class="bar-fill vram-swap-seg" style="width:'+swapPct+'%"><div class="vram-swap-shimmer"></div></div>'
      : '';
    return '<div class="bar-row">'
         +   '<div class="bar-head">'+label+'<span>'+val+'</span></div>'
         +   '<div class="bar-track bar-track--flex">'
         +     '<div class="bar-fill'+(m.is_embed?' bar-fill--embed':'')+'" style="width:'+pct+'%;--bar-col:'+col+'"></div>'
         +     swapSeg
         +   '</div>'
         + '</div>';
  });
  var freePct = cap ? Math.max(0, Math.round((cap - totalVram) / cap * 100)) : 0;
  rows.push('<div class="bar-row bar-row--libre">'
    + '<div class="bar-head"><span class="vram-libre-lbl">LIBRE</span><span class="vram-libre-val">'+_fmtBytes(Math.max(0, cap - totalVram))+' · '+freePct+'%</span></div>'
    + '<div class="bar-track"><div class="bar-fill vram-libre-fill" style="width:'+freePct+'%"></div></div>'
    + '</div>');
  return rows;
}

function _vramRenderLegend(d, models, legend, cap, totalVram) {
  if (models.length === 0) {
    if (d.active_model) {
      var col2 = _vramColor(d.active_model);
      legend.innerHTML = '<span class="vram-llm-item vram-llm-item--pending"><span class="vram-llm-dot" style="--mc-bg:'+col2+'55;--mc-border:'+col2+'"></span>'
                       + d.active_model.split('/').pop() + ' &nbsp;<b class="vram-llm-pending-lbl">en attente</b></span>';
    } else {
      legend.innerHTML = '<span class="vram-llm-idle">Aucun modèle chargé</span>';
    }
  } else {
    legend.innerHTML = _vramBuildModelRows(models, cap, totalVram).join('');
  }
}

function _vramUpdateStats(d) {
  var modeEl = document.getElementById('vram-stat-mode');
  var toksEl = document.getElementById('vram-stat-toks');
  var ctxEl  = document.getElementById('vram-stat-ctx');
  if (modeEl) {
    var mLabel = {soc:'SOC → phi4:14b', general:'GÉNÉRAL → gemma4:latest', code:'CODE → qwen2.5-coder:14b', code_reasoning:'C·R → qwen3:8b'};
    modeEl.textContent = mLabel[_jarvisMode] || _jarvisMode.toUpperCase();
  }
  if (toksEl && d.tokens_per_sec != null) toksEl.textContent = d.tokens_per_sec > 0 ? d.tokens_per_sec + ' tok/s' : '—';
  if (ctxEl  && d.num_ctx        != null) ctxEl.textContent  = d.num_ctx > 0 ? d.num_ctx.toLocaleString('fr-FR') + ' tok' : '—';
}

function updateVramLlm(d) {
  var bar    = document.getElementById('vram-llm-bar');
  var legend = document.getElementById('vram-llm-legend');
  var usedEl = document.getElementById('vram-llm-used');
  var swapEl = document.getElementById('vram-llm-swap');
  var alert  = document.getElementById('vram-llm-alert');
  if (!bar) return;

  var models    = (d.models || []).slice();
  // Ordre d'affichage STABLE : modèles d'embedding (RAG) toujours en dernier,
  // les autres dans leur ordre d'arrivée. Ollama réordonne sa liste quand un
  // modèle se charge → sans ce tri, le segment RAG « saute » de gauche à droite
  // dès que phi4 charge (faux ressenti de RAG déplacé en VRAM). Tri stable
  // (ES2019) → phi4/SOC toujours à gauche, RAG toujours à droite.
  models.sort(function(a, b) { return (a.is_embed ? 1 : 0) - (b.is_embed ? 1 : 0); });
  var totalVram = d.total_vram || 0;
  var totalSwap = d.total_swap || 0;
  if (d.vram_total_bytes) _VRAM_TOTAL = d.vram_total_bytes;
  var cap      = _VRAM_TOTAL || 1;
  var overflow = totalVram > cap;

  // Barre segmentée
  bar.innerHTML = '';
  if (models.length === 0) {
    if (d.active_model) {
      var col = _vramColor(d.active_model);
      var lbl = d.active_model.split(':')[0].replace('phi4-reasoning','phi4').replace('qwen2.5-coder','qwen').slice(0,10);
      bar.innerHTML = '<div class="vram-llm-seg vram-llm-pending" style="--seg-bg:'+col+'18;--seg-border:'+col+'66" title="'+d.active_model+' — en attente">'+lbl+'</div><div class="vram-llm-free" style="width:42%"></div>';
    } else {
      bar.innerHTML = '<div class="vram-llm-free" title="Libre"></div>';
    }
  } else {
    models.forEach(function(m) {
      var pct = Math.min(100, (m.size_vram / cap) * 100);
      var col = _vramColor(m.name);
      var label = m.name.split(':')[0].replace('phi4-reasoning','phi4').replace('qwen2.5-coder','qwen').replace('mxbai-embed','embed').replace('nomic-embed','embed').slice(0,10);
      var seg = document.createElement('div');
      seg.className = 'vram-llm-seg' + (overflow ? ' overflow' : '') + (m.is_embed ? ' embed' : '');
      seg.style.width = pct + '%';
      seg.style.background = col;
      var ttParts = ['['+m.role+'] ' + m.name, _fmtBytes(m.size_vram) + ' VRAM (' + (m.pct||0) + '%)'];
      if (m.params)  ttParts.push(m.params);
      if (m.quant)   ttParts.push(m.quant);
      if (m.size_swap > 0) ttParts.push('swap: ' + _fmtBytes(m.size_swap));
      if (m.expires_at && m.expires_at !== '0001-01-01T00:00:00Z') ttParts.push('expire: ' + new Date(m.expires_at).toLocaleTimeString('fr-FR'));
      seg.title = ttParts.join(' · ');
      seg.textContent = pct > 8 ? label : '';
      bar.appendChild(seg);
    });
    var freePct = Math.max(0, ((cap - totalVram) / cap) * 100);
    var free = document.createElement('div');
    free.className = 'vram-llm-free';
    free.style.width = freePct + '%';
    bar.appendChild(free);
  }

  // Légende bar-row
  _vramRenderLegend(d, models, legend, cap, totalVram);

  // Footer
  if (usedEl) usedEl.textContent = _fmtBytes(totalVram);
  var capEl = document.getElementById('vram-llm-cap');
  if (capEl && cap) capEl.textContent = '/ ' + _fmtBytes(cap);
  if (swapEl) swapEl.textContent = totalSwap > 0 ? _fmtBytes(totalSwap) : '0 MB';

  // Alerte débordement
  if (alert) alert.style.display = overflow ? 'inline' : 'none';
  if (bar.parentElement) bar.parentElement.parentElement && (bar.parentElement.style.borderColor = overflow ? '#ff444466' : '');

  // Stats + SWAP
  _vramUpdateStats(d);
  _vramRenderSwap(totalSwap);
}

var _vramPollTimer = null;
async function pollVramLlm() {
  try { var r = await fetch('/api/vram'); var d = await r.json(); updateVramLlm(d); } catch(e) {}
  _vramPollTimer = setTimeout(pollVramLlm, _VRAM_POLL_MS);
}
function _refreshVramNow() { clearTimeout(_vramPollTimer); pollVramLlm(); }
pollVramLlm();

// ══ Synoptique Moteur JARVIS — /api/jarvis-state (poll 5s) ══════════════
var _JARVIS_STATE_POLL_MS = 5000;
var _jarvisStatePollTimer = null;

function _jsStat(id, val) {
  var el = document.getElementById(id);
  if (el) el.textContent = val !== undefined && val !== null ? String(val) : '—';
}
function _jsColor(id, cls) {
  var el = document.getElementById(id);
  if (!el) return;
  el.className = 'stat-val ' + (cls || '');
}

function updateJarvisState(d) {
  // LLM & Mode
  _jsStat('js-mode',  (d.mode || '—').toUpperCase());
  _jsStat('js-model', d.model || '—');
  _jsStat('js-toks',  d.toks_per_s ? d.toks_per_s + ' tok/s' : '—');

  // RAG
  var rag = d.rag || {};
  _jsStat('js-rag-chunks', rag.chunks !== undefined ? rag.chunks + ' chunks' : '—');
  _jsStat('js-rag-cache',  rag.loaded ? (rag.cache_age_s >= 0 ? 'chargé ' + rag.cache_age_s + 's' : 'chargé') : 'non chargé');
  _jsColor('js-rag-cache', rag.loaded ? 'stat-val c-green' : 'stat-val c-warn');
  _jsStat('js-rag-ttl',    rag.ttl_remaining_s >= 0 ? rag.ttl_remaining_s + 's / ' + rag.ttl_s + 's' : '—');

  // STT — null = pas encore testé (boot), false = indisponible, true = ok
  var stt = d.stt || {};
  var sttLabel = stt.available === null || stt.available === undefined
               ? 'EN VEILLE'
               : stt.available === false ? 'INDISPONIBLE'
               : stt.loaded ? 'PRÊT' : 'NON CHARGÉ';
  var sttCls = (stt.available === null || stt.available === undefined) ? 'stat-val c-cyan'
             : stt.available === false ? 'stat-val c-err'
             : stt.loaded ? 'stat-val c-green' : 'stat-val c-warn';
  _jsStat('js-stt-state', sttLabel);
  _jsColor('js-stt-state', sttCls);
  _jsStat('js-stt-model', stt.model || (stt.available ? 'whisper' : '—'));

  // TTS
  var tts = d.tts || {};
  _jsStat('js-tts-engine', (tts.engine || '—').toUpperCase());
  var qTotal = (tts.queued || 0) + (tts.deferred || 0);
  _jsStat('js-tts-queue',  qTotal + ' en attente');
  _jsColor('js-tts-queue', qTotal > 0 ? 'stat-val c-cyan' : 'stat-val c-white');
  _jsStat('js-tts-stream', tts.stream_active ? 'ACTIF' : 'IDLE');
  _jsColor('js-tts-stream', tts.stream_active ? 'stat-val c-green' : 'stat-val c-white');

  // SOC engine
  var soc = d.soc || {};
  var socOn = soc.soc_engine_active || soc.engine_active;
  _jsStat('js-soc-engine', socOn ? 'ACTIF' : 'VEILLE');
  _jsColor('js-soc-engine', socOn ? 'stat-val c-green' : 'stat-val c-white');
  _jsStat('js-soc-bans',   soc.bans_24h !== undefined ? soc.bans_24h : '—');
  _jsStat('js-soc-alerts', soc.alerts_24h !== undefined ? soc.alerts_24h : '—');
}

async function pollJarvisState() {
  try {
    var r = await fetch('/api/jarvis-state');
    var d = await r.json();
    updateJarvisState(d);
  } catch(e) {}
  _jarvisStatePollTimer = setTimeout(pollJarvisState, _JARVIS_STATE_POLL_MS);
}
pollJarvisState();

