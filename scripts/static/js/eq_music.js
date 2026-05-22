// ══════════════════════════════════════════════════════════════
// EQ MUSIC — DAT Player + gestion moteurs TTS
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// Égaliseur « musique » du lecteur DAT (bandes spécialisées, presets,
// interaction canvas) + gestion et polling de statut des moteurs TTS
// (Kokoro/Piper/SAPI5 — _ttsStatusPoll). Suit le regroupement d'origine.
// Fichier .js classique (scope global). Chargé APRÈS jarvis_main.js.


const DAT_EQ_BANDS = [
  { id:'sub',    freq:80,    type:'lowshelf',  Q:0.7, color:_cssVar('--orange3'), label:'SUB' },
  { id:'bass',   freq:300,   type:'peaking',   Q:0.8, color:_cssVar('--yellow2'), label:'BASS' },
  { id:'mids',   freq:3000,  type:'peaking',   Q:0.9, color:_cssVar('--teal'),    label:'MIDS' },
  { id:'treble', freq:10000, type:'highshelf', Q:0.7, color:_cssVar('--sky'),     label:'TREBLE' },
];
const _datEqState = [
  { freq:80,    q:0.7, type:'lowshelf',  bypassed:false, gain:0 },
  { freq:300,   q:0.8, type:'peaking',   bypassed:false, gain:0 },
  { freq:3000,  q:0.9, type:'peaking',   bypassed:false, gain:0 },
  { freq:10000, q:0.7, type:'highshelf', bypassed:false, gain:0 },
];
const _datEqFreqRange = [[20,400],[100,2000],[500,8000],[2000,24000]];

function _datEqNode(band) {
  return { sub:window._datEqSub, bass:window._datEqBass, mids:window._datEqMids, treble:window._datEqTreble }[band];
}

function _datEqUpdateCounters(idx) {
  const band = DAT_EQ_BANDS[idx];
  const s = _datEqState[idx];
  const fc = document.getElementById('dat-eq-fc-'+band.id);
  if (fc) fc.textContent = s.freq >= 1000 ? (s.freq/1000).toFixed(2)+'k' : s.freq.toFixed(0)+'Hz';
  const qc = document.getElementById('dat-eq-qc-'+band.id);
  if (qc) qc.textContent = s.q.toFixed(2);
}

function setDatEqBand(band, val) {
  const idx = _datEqBandIdx(band);
  const v = parseFloat(val);
  if (idx >= 0) _datEqState[idx].gain = v;
  const node = _datEqNode(band);
  const noGainTypes = ['highpass','lowpass','notch','bandpass'];
  if (node && idx >= 0 && !_datEqState[idx].bypassed && !noGainTypes.includes(_datEqState[idx].type))
    node.gain.value = v;
  const label = document.getElementById('dat-eq-'+band+'-val');
  if (label) label.textContent = (v >= 0 ? '+' : '') + v.toFixed(1) + ' dB';
  const gc = document.getElementById('dat-eq-gc-'+band);
  if (gc) gc.textContent = (v >= 0 ? '+' : '') + v.toFixed(1);
  const sl = document.getElementById('dat-eq-'+band);
  if (sl) updateSliderPct(sl);
  drawDatEqCurve();
  _datEqSchedulePush();
}

function datEqSetFreq(bandId, freq) {
  const idx = _datEqBandIdx(bandId);
  if (idx < 0) return;
  const [fMin, fMax] = _datEqFreqRange[idx];
  freq = Math.max(fMin, Math.min(fMax, freq));
  _datEqState[idx].freq = freq;
  DAT_EQ_BANDS[idx].freq = freq;
  const node = _datEqNode(bandId);
  if (node) node.frequency.value = freq;
  _datEqUpdateCounters(idx);
  drawDatEqCurve();
  _datEqSchedulePush();
}

function datEqSetQ(bandId, q) {
  const idx = _datEqBandIdx(bandId);
  if (idx < 0) return;
  q = Math.max(0.1, Math.min(12, q));
  _datEqState[idx].q = q;
  DAT_EQ_BANDS[idx].Q = q;
  const node = _datEqNode(bandId);
  if (node) node.Q.value = q;
  _datEqUpdateCounters(idx);
  drawDatEqCurve();
}

function datEqSetType(bandId, type) {
  const idx = _datEqBandIdx(bandId);
  if (idx < 0) return;
  _datEqState[idx].type = type;
  DAT_EQ_BANDS[idx].type = type;
  const node = _datEqNode(bandId);
  if (node) {
    const waTypes = {highpass:'highpass',lowpass:'lowpass',notch:'notch',
                     peaking:'peaking',lowshelf:'lowshelf',highshelf:'highshelf',bandpass:'bandpass'};
    try { node.type = waTypes[type] || 'peaking'; } catch(e) { /* BiquadFilterNode.type throws on invalid value */ }
    const noGain = ['highpass','lowpass','notch','bandpass'].includes(type);
    if (noGain) { node.gain.value = 0; }
    else { node.gain.value = _datEqState[idx].gain; }
  }
  document.querySelectorAll(`.dat-eq-type-btn[data-band="${bandId}"]`).forEach(b =>
    b.classList.toggle('active', b.dataset.type === type));
  drawDatEqCurve();
}

function datEqToggleBypass(bandId) {
  const idx = _datEqBandIdx(bandId);
  if (idx < 0) return;
  _datEqState[idx].bypassed = !_datEqState[idx].bypassed;
  const node = _datEqNode(bandId);
  if (node) {
    const noGain = ['highpass','lowpass','notch','bandpass'].includes(_datEqState[idx].type);
    if (_datEqState[idx].bypassed) {
      if (noGain) { node.type = 'allpass'; }
      else { node.gain.value = 0; }
    } else {
      node.type = _datEqState[idx].type;
      if (noGain) { node.gain.value = 0; }
      else { node.gain.value = _datEqState[idx].gain; }
    }
  }
  const btn = document.getElementById('dat-eq-byp-'+bandId);
  if (btn) btn.classList.toggle('bypassed', _datEqState[idx].bypassed);
  drawDatEqCurve();
}

// Canvas drag — DAT EQ (même logique que eqCanvasDown/Move voix)
let _datEqDrag = null; // { idx, startFreq, startGain }
const _DAT_EQ_ML=42, _DAT_EQ_MR=42, _DAT_EQ_MT=14, _DAT_EQ_MB=22;

function _datEqGetHandle(mx, my, canvas) {
  const W = canvas.width, H = canvas.height;
  const PW=W-_DAT_EQ_ML-_DAT_EQ_MR, PH=H-_DAT_EQ_MT-_DAT_EQ_MB;
  const fMin=20, fMax=24000, dbMin=-15, dbMax=15;
  let closest=-1, closestDist=28; // rayon légèrement plus grand (canvas moins haut)
  DAT_EQ_BANDS.forEach((band,i) => {
    const bx = _DAT_EQ_ML + PW*Math.log10(_datEqState[i].freq/fMin)/Math.log10(fMax/fMin);
    const gainDb = _datEqState[i].bypassed ? 0 : _datEqState[i].gain;
    const by = _DAT_EQ_MT + PH*(1-(gainDb-dbMin)/(dbMax-dbMin));
    const d = Math.sqrt((mx-bx)**2+(my-by)**2);
    if (d<closestDist) { closestDist=d; closest=i; }
  });
  return closest;
}
function datEqCanvasDown(e) {
  const c = _canvasCoords(e, 'dat-eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;
  const idx = _datEqGetHandle(mx, my, canvas);
  if (idx >= 0) {
    const gainDb = parseFloat(document.getElementById('dat-eq-'+DAT_EQ_BANDS[idx].id)?.value||0);
    _datEqDrag = { idx, startFreq:_datEqState[idx].freq, startGain:gainDb };
    canvas.style.cursor = 'grabbing';
    e.preventDefault();
  }
}
function datEqCanvasMove(e) {
  const c = _canvasCoords(e, 'dat-eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;
  if (_datEqDrag !== null) {
    const W = canvas.width, H = canvas.height;
    const PW=W-_DAT_EQ_ML-_DAT_EQ_MR, PH=H-_DAT_EQ_MT-_DAT_EQ_MB;
    const fMin=20, fMax=24000, dbMin=-15, dbMax=15;
    const nx = Math.max(0, Math.min(1, (mx-_DAT_EQ_ML)/PW));
    const newFreq = Math.round(fMin * Math.pow(fMax/fMin, nx));
    const ny = Math.max(0, Math.min(1, (my-_DAT_EQ_MT)/PH));
    const newGain = Math.max(-12, Math.min(12, dbMax - ny*(dbMax-dbMin)));
    const band = DAT_EQ_BANDS[_datEqDrag.idx];
    const sl = document.getElementById('dat-eq-'+band.id);
    if (sl) sl.value = newGain.toFixed(1);
    datEqSetFreq(band.id, newFreq);
    setDatEqBand(band.id, newGain.toFixed(1));
    e.preventDefault();
  } else {
    const idx = _datEqGetHandle(mx, my, canvas);
    canvas.style.cursor = idx >= 0 ? 'grab' : 'crosshair';
  }
}
function datEqCanvasUp() {
  _datEqDrag = null;
  const canvas = document.getElementById('dat-eq-curve-canvas');
  if (canvas) canvas.style.cursor = 'crosshair';
}
function datEqCanvasWheel(e) {
  const c = _canvasCoords(e, 'dat-eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;
  const idx = _datEqGetHandle(mx, my, canvas);
  if (idx < 0) return;
  e.preventDefault();
  const step = e.shiftKey ? 0.1 : 0.15;
  const q = Math.max(0.1, Math.min(12, _datEqState[idx].q + (e.deltaY > 0 ? -step : step)));
  datEqSetQ(DAT_EQ_BANDS[idx].id, q);
}

// ── Presets EQ Music ──
const _DAT_EQ_PRESETS = {
  'FLAT':      { sub:[0,0.7],   bass:[0,0.8],    mids:[0,0.9],    treble:[0,0.7]  },
  'BASS':      { sub:[8,0.7],   bass:[4,0.8],    mids:[-1,0.9],   treble:[0,0.7]  },
  'BRIGHT':    { sub:[0,0.7],   bass:[-1,0.8],   mids:[2,0.9],    treble:[6,0.7]  },
  'WARM':      { sub:[4,0.7],   bass:[3,0.8],    mids:[-1,0.9],   treble:[-3,0.7] },
  'CLUB':      { sub:[7,0.7],   bass:[2,0.8],    mids:[-1,0.9],   treble:[5,0.7]  },
  'ACOUSTIQUE':{ sub:[-2,0.7],  bass:[1,0.8],    mids:[3,1.2],    treble:[2,0.7]  },
  'ROCK':      { sub:[4,0.7],   bass:[2,0.8],    mids:[-2,0.9],   treble:[4,0.7]  },
  'JAZZ':      { sub:[2,0.7],   bass:[3,0.8],    mids:[1,0.9],    treble:[3,0.7]  },
};

function applyDatEqPreset(name) {
  const p = _DAT_EQ_PRESETS[name];
  if (!p) return;
  ['sub','bass','mids','treble'].forEach(band => {
    const [gain, q] = p[band];
    const sl = document.getElementById('dat-eq-' + band);
    if (sl) sl.value = gain;
    setDatEqBand(band, gain);
    datEqSetQ(band, q);
  });
  document.querySelectorAll('.dat-eq-preset-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll(`[data-dat-eq-preset="${name}"]`).forEach(b => b.classList.add('active'));
  _datEqSchedulePush();
}

let _datEqPushTimer = null;
function _datEqSchedulePush() {
  clearTimeout(_datEqPushTimer);
  _datEqPushTimer = setTimeout(pushDspParamsToBackend, _DSP_PUSH_MS);
}

function _datEqDrawSpectrum(ctx, eq) {
  const {W, ML, MR, MT, MB, PW, PH, fMin, fMax} = eq;
  const anL = window._datAnL;
  let hasData = false, specBuf = null;
  if (anL && window._datActive) { specBuf = new Uint8Array(anL.frequencyBinCount); anL.getByteFrequencyData(specBuf); hasData = true; }
  const N = specBuf ? specBuf.length : 1024;
  const nyq = (typeof audioCtx!=='undefined'&&audioCtx?audioCtx.sampleRate:_SAMPLE_RATE)/2;
  if (!window._datEqSpecPeaks||window._datEqSpecPeaks.length!==W) window._datEqSpecPeaks=new Float32Array(W);
  const peaks=window._datEqSpecPeaks;
  ctx.beginPath(); let first=true;
  for(let px=ML;px<=W-MR;px++){
    let val=0.04;
    if(hasData){const f=fMin*Math.pow(fMax/fMin,(px-ML)/PW);val=Math.max(specBuf[Math.min(Math.round(f/nyq*N),N-1)]/255,0.04);}
    peaks[px]=Math.max(peaks[px]*0.993,val);
    const sy=MT+PH*(1-val);
    if(first){ctx.moveTo(px,MT+PH);ctx.lineTo(px,sy);first=false;}else ctx.lineTo(px,sy);
  }
  ctx.lineTo(W-MR,MT+PH);ctx.closePath();
  const gSpec=ctx.createLinearGradient(0,MT,0,MT+PH);
  gSpec.addColorStop(0,'rgba(0,200,255,.25)');gSpec.addColorStop(0.45,'rgba(0,150,180,.12)');gSpec.addColorStop(1,'rgba(0,80,120,.04)');
  ctx.fillStyle=gSpec;ctx.fill();
  ctx.beginPath();ctx.strokeStyle='rgba(0,200,255,.35)';ctx.lineWidth=1;first=true;
  for(let px=ML;px<=W-MR;px++){const sy=MT+PH*(1-peaks[px]);first?(ctx.moveTo(px,sy),first=false):ctx.lineTo(px,sy);}
  ctx.stroke();
}
function _datEqDrawGrid(ctx, eq) {
  const {W, H, ML, MR, MT, MB, PH, freqToX, dbToY} = eq;
  [-12,-9,-6,-3,-1,0,1,3,6,9,12].forEach(db=>{
    const y=dbToY(db),isZero=db===0,isMajor=db%3===0;
    ctx.strokeStyle=isZero?'rgba(255,255,255,.18)':isMajor?'rgba(0,180,220,.07)':'rgba(0,150,180,.03)';
    ctx.lineWidth=isZero?1.5:isMajor?0.8:0.4;
    ctx.beginPath();ctx.moveTo(ML,y);ctx.lineTo(W-MR,y);ctx.stroke();
    if(isMajor){ctx.fillStyle='rgba(100,200,255,.55)';ctx.font='9px Share Tech Mono';ctx.textAlign='right';ctx.fillText((db>0?'+':'')+db,ML-5,y+3);}
  });
  [20,50,100,200,500,1000,2000,5000,10000,20000].forEach(f=>{
    const x=freqToX(f);
    ctx.strokeStyle='rgba(0,150,200,.06)';ctx.lineWidth=0.4;
    ctx.beginPath();ctx.moveTo(x,MT);ctx.lineTo(x,H-MB);ctx.stroke();
    ctx.fillStyle='rgba(100,200,255,.45)';ctx.font='9px Share Tech Mono';ctx.textAlign='center';
    ctx.fillText(f>=1000?f/1000+'k':f,x,H-MB+12);
  });
  ctx.fillStyle='rgba(100,200,255,.55)';ctx.font='9px Share Tech Mono';ctx.textAlign='right';
  ctx.fillText('0',ML-5,dbToY(0)+3);
}
function _datEqDrawCurve(ctx, eq) {
  const {W, fMin, fMax, dbMin, dbMax, dbToY} = eq;
  const combined = new Float32Array(W);
  DAT_EQ_BANDS.forEach((band,i)=>{
    const s=_datEqState[i]; if(s.bypassed) return;
    const coeff=eqBqCoeffs(s.type,s.freq,s.gain,s.q);
    for(let px=0;px<W;px++){combined[px]+=eqBqResponse(coeff,fMin*Math.pow(fMax/fMin,px/W));}
  });
  window._datEqLastCombined=combined;
  ctx.beginPath();let fp=true;
  for(let px=0;px<W;px++){const y=dbToY(Math.max(dbMin,Math.min(dbMax,combined[px])));fp?(ctx.moveTo(px,y),fp=false):ctx.lineTo(px,y);}
  ctx.strokeStyle='rgba(255,200,0,.9)';ctx.lineWidth=2;ctx.stroke();
}
function _datEqDrawHandles(ctx, eq) {
  const {freqToX, dbToY} = eq;
  DAT_EQ_BANDS.forEach((band,i)=>{
    const s=_datEqState[i];
    const gainDb=s.bypassed||['highpass','lowpass','notch','bandpass'].includes(s.type)?0:s.gain;
    const bx=freqToX(s.freq), by=dbToY(gainDb);
    ctx.beginPath();ctx.arc(bx,by,8,0,Math.PI*2);
    ctx.fillStyle=s.bypassed?'rgba(100,100,100,.4)':band.color+'99';ctx.fill();
    ctx.strokeStyle=s.bypassed?'#555':band.color;ctx.lineWidth=1.5;ctx.stroke();
    ctx.fillStyle=s.bypassed?'#555':'#fff';ctx.font='bold 8px Orbitron';ctx.textAlign='center';ctx.textBaseline='middle';
    ctx.fillText(band.label[0],bx,by);
  });
  ctx.textBaseline='alphabetic';
}
function drawDatEqCurve() {
  const canvas = document.getElementById('dat-eq-curve-canvas');
  if (!canvas) return;
  const W = canvas.width = canvas.offsetWidth||600, H = canvas.height = canvas.offsetHeight||160;
  const ctx = canvas.getContext('2d');
  const ML=_DAT_EQ_ML, MR=_DAT_EQ_MR, MT=_DAT_EQ_MT, MB=_DAT_EQ_MB;
  const PW=W-ML-MR, PH=H-MT-MB, dbMin=-15, dbMax=15, fMin=20, fMax=24000;
  const eq = {
    ctx, W, H, ML, MR, MT, MB, PW, PH, fMin, fMax, dbMin, dbMax,
    freqToX: f  => ML+PW*Math.log10(f/fMin)/Math.log10(fMax/fMin),
    dbToY:   db => MT+PH*(1-(db-dbMin)/(dbMax-dbMin))
  };
  const bgGrd = ctx.createRadialGradient(W/2,H/2,10,W/2,H/2,W*0.75);
  bgGrd.addColorStop(0,'#030e18');bgGrd.addColorStop(1,'#010810');
  ctx.fillStyle=bgGrd;ctx.fillRect(0,0,W,H);
  const vig=ctx.createRadialGradient(W/2,H/2,PW*0.3,W/2,H/2,W*0.65);
  vig.addColorStop(0,'rgba(0,0,0,0)');vig.addColorStop(1,'rgba(0,0,0,.55)');
  ctx.fillStyle=vig;ctx.fillRect(0,0,W,H);
  for(let y=MT;y<H-MB;y+=3){ctx.fillStyle='rgba(0,0,0,.08)';ctx.fillRect(ML,y,PW,1);}
  _datEqDrawSpectrum(ctx, eq);
  _datEqDrawGrid(ctx, eq);
  _datEqDrawCurve(ctx, eq);
  _datEqDrawHandles(ctx, eq);
}

// ── Canvas drag interaction ──
function _eqGetHandle(mx, my, canvas) {
  const W = canvas.width, H = canvas.height;
  const ML=34, MR=6, MT=8, MB=18;
  const PW=W-ML-MR, PH=H-MT-MB;
  const fMin=20, fMax=24000, dbMin=-15, dbMax=15;
  let closest=-1, closestDist=22;
  EQ_BANDS.forEach((band,i) => {
    const bx = ML + PW*Math.log10(_eqState[i].freq/fMin)/Math.log10(fMax/fMin);
    const gainDb = _eqState[i].bypassed ? 0 : parseFloat(document.getElementById('eq-'+band.id)?.value||0);
    const by = MT + PH*(1-(gainDb-dbMin)/(dbMax-dbMin));
    const d = Math.sqrt((mx-bx)**2+(my-by)**2);
    if (d<closestDist) { closestDist=d; closest=i; }
  });
  return closest;
}

function eqCanvasDown(e) {
  const c = _canvasCoords(e, 'eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;
  const idx = _eqGetHandle(mx, my, canvas);
  if (idx >= 0) {
    const gainDb = parseFloat(document.getElementById('eq-'+EQ_BANDS[idx].id)?.value||0);
    _eqDrag = { idx, startFreq:_eqState[idx].freq, startGain:gainDb };
    canvas.style.cursor = 'grabbing';
    e.preventDefault();
  }
}

function eqCanvasMove(e) {
  const c = _canvasCoords(e, 'eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;

  if (_eqDrag !== null) {
    const W = canvas.width, H = canvas.height;
    const ML=34, MR=6, MT=8, MB=18;
    const PW=W-ML-MR, PH=H-MT-MB;
    const fMin=20, fMax=24000, dbMin=-15, dbMax=15;

    // X → frequency (log)
    const nx = Math.max(0, Math.min(1, (mx-ML)/PW));
    const newFreq = Math.round(fMin * Math.pow(fMax/fMin, nx));

    // Y → gain
    const ny = Math.max(0, Math.min(1, (my-MT)/PH));
    const newGain = Math.max(-12, Math.min(12, dbMax - ny*(dbMax-dbMin)));

    const band = EQ_BANDS[_eqDrag.idx];
    const sl = document.getElementById('eq-'+band.id);
    if (sl) sl.value = newGain;
    eqSetFreq(band.id, newFreq);
    setEqBand(band.id, newGain);
    e.preventDefault();
  } else {
    // Hover: show crosshair
    const idx = _eqGetHandle(mx, my, canvas);
    canvas.style.cursor = idx >= 0 ? 'grab' : 'crosshair';
    _eqHoverX = mx;
    drawEqCurve();
  }
}

function eqCanvasUp(_e) {
  _eqDrag = null;
  const canvas = document.getElementById('eq-curve-canvas');
  if (canvas) canvas.style.cursor = 'crosshair';
}

function eqCanvasLeave(_e) {
  if (_eqDrag) { _eqDrag = null; }
  _eqHoverX = null;
  drawEqCurve();
  const canvas = document.getElementById('eq-curve-canvas');
  if (canvas) canvas.style.cursor = 'crosshair';
}

function eqCanvasWheel(e) {
  const c = _canvasCoords(e, 'eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;
  const idx = _eqGetHandle(mx, my, canvas);
  if (idx >= 0) {
    const delta = e.deltaY > 0 ? -0.15 : 0.15;
    eqSetQ(EQ_BANDS[idx].id, _eqState[idx].q + delta);
    e.preventDefault();
  }
}

function setDspGain(val) {
  const v = parseFloat(val);
  if (_dspGainNode) _dspGainNode.gain.value = Math.pow(10, v / 20);
  _dspSchedulePush();
}

function setDspCompressor(param, val) {
  const v = parseFloat(val);
  if (!_dspCompressor) return;
  if      (param === 'threshold') _dspCompressor.threshold.value = v;
  else if (param === 'ratio')     _dspCompressor.ratio.value = v;
  else if (param === 'attack')    _dspCompressor.attack.value = v / 1000;
  else if (param === 'release')   _dspCompressor.release.value = v / 1000;
  _dspSchedulePush();
}

function setDspSpeed(val) {
  _dspPlaybackRate = parseFloat(val);
  const sl = document.getElementById('dsp-speed');
  if (sl) _syncRangeSlider(sl);
}

function setDspPitch(val) {
  _dspPitchSemi = parseInt(val);
  const sl = document.getElementById('dsp-pitch');
  if (sl) _syncRangeSlider(sl);
}

function setDspVolume(val) {
  _dspVolume = parseFloat(val) / 100;
  const sl = document.getElementById('dsp-vol');
  if (sl) _syncRangeSlider(sl);
}

function syncDspVoices() {
  const mainSel = document.getElementById('voice-select');
  const dspSel  = document.getElementById('dsp-voice-sel');
  if (!mainSel || !dspSel) return;
  dspSel.innerHTML = mainSel.innerHTML;
  dspSel.value = mainSel.value;
  // Init TTS local panel in parallel
  initTtsLocal();
}

function setDspVoice(val) {
  const mainSel = document.getElementById('voice-select');
  if (mainSel) { mainSel.value = val; switchVoice(val); }
}

// ── TTS engine management ──────────────────────────────────────
let _ttsCurrentEngine = 'edge';

function initTtsLocal() {
  _ttsShowEngine('edge');
}

function _ttsShowEngine(eng) {
  _ttsCurrentEngine = eng;
  // Chat sidebar buttons
  const edgeBtn   = document.getElementById('voice-eng-edge');
  const kokoroBtn = document.getElementById('voice-eng-kokoro');
  const label     = document.getElementById('voice-mode-cloud');
  const cloudPanel  = document.getElementById('voice-cloud-panel');
  const kokoroPanel = document.getElementById('voice-kokoro-panel');
  if (edgeBtn)   edgeBtn.classList.toggle('active', eng === 'edge');
  if (kokoroBtn) kokoroBtn.classList.toggle('active', eng === 'kokoro');
  if (label) {
    if (eng === 'kokoro') label.textContent = '◈ KOKORO — NEURAL LOCAL';
    else                  label.textContent = '◉ EDGE — MICROSOFT CLOUD';
  }
  _disp(cloudPanel,  eng === 'edge',   'block');
  _disp(kokoroPanel, eng === 'kokoro', 'block');
  // DSP tab buttons + panels
  const dspEdge   = document.getElementById('dsp-eng-edge');
  const dspKokoro = document.getElementById('dsp-eng-kokoro');
  const panelEdge   = document.getElementById('dsp-panel-edge');
  const panelKokoro = document.getElementById('dsp-panel-kokoro');
  if (dspEdge)   dspEdge.classList.toggle('active', eng === 'edge');
  if (dspKokoro) dspKokoro.classList.toggle('active', eng === 'kokoro');
  _disp(panelEdge,   eng === 'edge');
  _disp(panelKokoro, eng === 'kokoro');
}

async function setDefaultTtsEngine(eng) {
  // Persiste le moteur par défaut (utilisé au démarrage et par la boucle connectivité)
  await fetch('/api/dsp-params', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ tts_default_engine: eng })
  }).catch(() => {});
  _syncDefaultEngineButtons(eng);
}

function _syncDefaultEngineButtons(eng) {
  const defEdge   = document.getElementById('dsp-def-edge');
  const defKokoro = document.getElementById('dsp-def-kokoro');
  if (defEdge)   defEdge.classList.toggle('active', eng === 'edge');
  if (defKokoro) defKokoro.classList.toggle('active', eng === 'kokoro');
}

// ── Polling statut moteurs TTS ──────────────────────────────────
async function _ttsStatusPoll() {
  try {
    const r = await fetch('/api/tts/status');
    const d = await r.json();
    ['edge','kokoro','piper','sapi'].forEach(eng => {
      const st = d[eng];
      if (!st) return;
      // Tous les boutons portant data-args contenant cet engine
      document.querySelectorAll(`[data-args*='"${eng}"'] .veng-dot`).forEach(dot => {
        dot.classList.remove('ok','err');
        const btn = dot.closest('button');
        if (btn && btn.classList.contains('active')) {
          dot.classList.add(st.ok ? 'ok' : 'err');
        }
      });
    });
  } catch(e) { /* network error — skip poll cycle */ }
}
_ttsStatusPoll();
setInterval(_ttsStatusPoll, _TTS_STATUS_POLL_MS);

function setKokoroSpeed(val) {
  const v = parseFloat(val);
  const lbl = document.getElementById('dsp-kokoro-speed-val');
  if (lbl) lbl.textContent = v.toFixed(2) + '×';
  fetch('/api/dsp-params', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ tts_kokoro_speed: v })
  }).catch(() => {});
}


async function setTtsEngine(eng) {
  if (eng !== 'edge') _lastLocalEngine = eng;
  _ttsShowEngine(eng);
  await fetch('/api/dsp-params', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ tts_engine: eng })
  }).catch(() => {});
  _ttsStatusPoll();
}

async function setDspLocalVoice(val) {
  await fetch('/api/dsp-params', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ tts_local_voice: val })
  }).catch(() => {});
}


// Push DSP params to backend so TTS server applies them
function pushDspParamsToBackend() {
  const p = {
    enabled:        true,
    eq_low:         _eqState[0].gain,
    eq_mid:         _eqState[1].gain,
    eq_high:        _eqState[2].gain,
    eq_air:         _eqState[3].gain,
    comp_threshold: _dspCompressor ? _dspCompressor.threshold.value : -24,
    comp_ratio:     _dspCompressor ? _dspCompressor.ratio.value     : 4,
    comp_attack:    _dspCompressor ? _dspCompressor.attack.value    : 0.003,
    comp_release:   _dspCompressor ? _dspCompressor.release.value   : 0.25,
    gain: _dspGainNode ? (20 * Math.log10(Math.max(0.001, _dspGainNode.gain.value))) : 0,
  };
  // Voice EQ — état complet depuis _eqState (source de vérité)
  ['low','mid','high','air'].forEach(function(id,i){
    p['eq_'+id+'_type'] = _eqState[i].type;
    p['eq_'+id+'_freq'] = _eqState[i].freq;
    p['eq_'+id+'_q']    = _eqState[i].q;
    p['eq_'+id+'_byp']  = _eqState[i].bypassed;
  });
  // DAT EQ music — état complet depuis _datEqState (source de vérité)
  ['sub','bass','mids','treble'].forEach(function(id,i){
    p['dat_eq_'+id]          = _datEqState[i].gain;
    p['dat_eq_'+id+'_type']  = _datEqState[i].type;
    p['dat_eq_'+id+'_freq']  = _datEqState[i].freq;
    p['dat_eq_'+id+'_q']     = _datEqState[i].q;
    p['dat_eq_'+id+'_byp']   = _datEqState[i].bypassed;
  });
  fetch('/api/dsp-params', {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(p)
  }).catch(()=>{});
}


function _tvBar(pct) {
  const f = Math.round(Math.min(pct,100)/5);
  return '<span class="tv-bar-bk">[</span><span class="tv-bar-fill">'+'█'.repeat(f)+'</span><span class="tv-bar-empty">'+'░'.repeat(20-f)+'</span><span class="tv-bar-bk">]</span>';
}
const _tvSep = '<span class="tv-sep-line">────────────────────────────────────────────</span>';
function _tvSec(t) { return `<div class="tv-sec">◈ ${t}</div>`; }
function _tvRow(lbl, val, ok=null) {
  const dot = ok===null ? '<span class="tv-dot-null">◎</span>' : ok ? '<span class="tv-dot-ok">◉</span>' : '<span class="tv-dot-err">◉</span>';
  return `${dot} <span class="tv-row-lbl">${lbl}</span> <span class="tv-row-val">${val}</span><br>`;
}
function _tvEqSign(v) { return v > 0.05 ? `+${v.toFixed(1)}` : v < -0.05 ? `${v.toFixed(1)}` : '0.0'; }
function _tvDiagBuildHardware(d) {
  let h = '';
  h += _tvSec('MATÉRIEL');
  h += _tvRow('CPU', `${d.cpu_cores}c/${d.cpu_threads}t @ ${d.cpu_freq} GHz &nbsp; ${d.cpu_pct}% ${_tvBar(d.cpu_pct)}`, d.cpu_pct < 80);
  if (d.cpu_temp != null) h += _tvRow('CPU TEMP', `${d.cpu_temp} °C`, d.cpu_temp < 80);
  h += _tvRow('RAM', `${d.ram_used} / ${d.ram_total} GB &nbsp; ${d.ram_pct}% ${_tvBar(d.ram_pct)}`, d.ram_pct < 85);
  if (d.swap_total > 0) h += _tvRow('SWAP', `${d.swap_used} / ${d.swap_total} GB &nbsp; ${d.swap_pct}% ${_tvBar(d.swap_pct)}`, d.swap_pct < 50);
  h += _tvSep + '<br>';
  h += _tvSec('CARTE GRAPHIQUE');
  if (d.gpu_name !== 'N/A') {
    h += _tvRow('GPU', d.gpu_name, true);
    h += _tvRow('CHARGE GPU', `${d.gpu_pct}% ${_tvBar(d.gpu_pct)}`, d.gpu_pct < 90);
    h += _tvRow('VRAM', `${d.vram_used} / ${d.vram_total} GB ${_tvBar(Math.round(d.vram_used/d.vram_total*100))}`, d.vram_used/d.vram_total < 0.9);
    if (d.gpu_temp !== null) h += _tvRow('GPU TEMP', `${d.gpu_temp} °C`, d.gpu_temp < 85);
    if (d.gpu_power !== null) h += _tvRow('PUISSANCE', `${d.gpu_power} W`, null);
    if (d.gpu_clock !== null) h += _tvRow('HORLOGE', `${d.gpu_clock} MHz`, null);
  } else { h += _tvRow('GPU', 'Non détecté', false); }
  h += _tvSep + '<br>';
  h += _tvSec('STOCKAGE & RÉSEAU');
  h += _tvRow('DISQUE C:', `${d.disk_used} / ${d.disk_total} GB &nbsp; ${d.disk_pct}% ${_tvBar(d.disk_pct)}`, d.disk_pct < 80);
  h += _tvRow('RÉSEAU', `↑ ${d.net_sent} MB &nbsp; ↓ ${d.net_recv} MB`, null);
  h += _tvRow('UPTIME', d.uptime, null); h += _tvRow('PLATEFORME', `${d.platform} — ${d.hostname}`, null);
  h += _tvSep + '<br>';
  h += _tvSec('IA STACK');
  h += _tvRow('OLLAMA', d.ollama_ok ? `<span class="tv-ok-txt">EN LIGNE</span> &nbsp; latence ${d.ollama_latency} ms` : '<span class="tv-err-txt">HORS LIGNE</span>', d.ollama_ok);
  h += _tvRow('LLM ACTIF', d.llm_model, null); h += _tvRow('PROVIDER', d.llm_provider.toUpperCase(), null);
  if (d.ollama_models && d.ollama_models.length) h += _tvRow('MODÈLES DISPO', d.ollama_models.join(' · '), null);
  h += _tvRow('VOIX TTS', d.llm_voice || '—', null);
  h += _tvRow('MÉMOIRE', `${d.memory_exchanges} échanges / ${d.memory_limit} max`, d.memory_exchanges < d.memory_limit * 0.9);
  h += _tvSep + '<br>';
  return h;
}
function _tvDiagBuildAudio({ d, dspP, acOk, acState, acSR, acLat, chainOk, eqBands }) {
  let h = '';
  h += _tvSec('CHAÎNE AUDIO WEB API');
  h += _tvRow('AudioContext', `${acState.toUpperCase()} ${acOk?'':'(non initialisé — ouvrir DSP)'}`, acOk && acState === 'running');
  h += _tvRow('SAMPLE RATE', acSR ? acSR+' Hz' : '—', acSR >= 44100);
  h += _tvRow('LATENCE BASE', acLat, null);
  h += _tvRow('CHAÎNE DSP', chainOk ? 'AnalyserNode → EQ×4 → Compressor → Gain → Destination' : acOk ? 'Partielle ou non connectée' : 'Inactive', chainOk);
  h += _tvRow('ANALYSER FFT', typeof _dspAnalyser!=='undefined'&&_dspAnalyser ? `2048 pts — ${_dspAnalyser.fftSize} Hz` : 'Absent', !!_dspAnalyser);
  h += _tvSep + '<br>';
  h += _tvSec('DSP — PARAMÈTRES ACTIFS');
  if (dspP) {
    h += _tvRow('DSP ACTIF', dspP.enabled ? '<span class="tv-ok-txt">OUI</span>' : '<span class="tv-err-txt">NON</span>', dspP.enabled);
    h += _tvRow('EQ LOW 250Hz', _tvEqSign(dspP.eq_low)+' dB', Math.abs(dspP.eq_low)<=12);
    h += _tvRow('EQ MID 1kHz', _tvEqSign(dspP.eq_mid)+' dB', Math.abs(dspP.eq_mid)<=12);
    h += _tvRow('EQ HIGH 4kHz', _tvEqSign(dspP.eq_high)+' dB', Math.abs(dspP.eq_high)<=12);
    h += _tvRow('EQ AIR 12kHz', _tvEqSign(dspP.eq_air)+' dB', Math.abs(dspP.eq_air)<=12);
    h += _tvRow('COMPRESSEUR', `Seuil ${dspP.comp_threshold} dB &nbsp;|&nbsp; Ratio ${dspP.comp_ratio}:1 &nbsp;|&nbsp; Att ${Math.round(dspP.comp_attack*1000)}ms &nbsp;|&nbsp; Rel ${Math.round(dspP.comp_release*1000)}ms`, null);
    h += _tvRow('GAIN SORTIE', _tvEqSign(dspP.gain)+' dB', Math.abs(dspP.gain)<=6);
  }
  if (eqBands) { h += '<br>'; ['LOW','MID','HIGH','AIR'].forEach((n,i) => { const b=eqBands[i]; h += _tvRow(`EQ BANDE ${n}`, `${b.freq} Hz &nbsp;|&nbsp; Q ${b.q.toFixed(2)} &nbsp;|&nbsp; ${b.type.toUpperCase()} &nbsp;|&nbsp; ${b.bypassed?'<span class="tv-warn-txt">BYPASS</span>':'<span class="tv-ok-txt">ACTIF</span>'}`, !b.bypassed); }); }
  h += _tvSep + '<br>';
  h += _tvSec('DEEPFILTERNET — IA DÉBRUITAGE');
  if (d) {
    h += _tvRow('DISPONIBLE', d.df_available ? '<span class="tv-ok-txt">OUI</span>' : '<span class="tv-warn-txt">NON (pip install deepfilternet)</span>', d.df_available);
    h += _tvRow('ACTIF', d.df_enabled ? '<span class="tv-ok-txt">OUI</span>' : '<span class="tv-dim-txt">NON</span>', d.df_enabled !== false);
    if (d.df_available) {
      h += _tvRow('SAMPLE RATE', d.df_sr+' Hz', null);
      h += _tvRow('PROCESSEUR', 'CPU (PyTorch — RTX 5080 sm_120 non supporté par cu121)', null);
      if (dspP) { h += _tvRow('ATTÉNUATION', dspP.df_atten_lim+' dB', null); h += _tvRow('POST-FILTRE', dspP.df_post_filter?'Activé':'Désactivé', null); }
    }
  } else { h += _tvRow('STATUT', 'API inaccessible', false); }
  return h;
}
async function testDspVoice() {
  let d = null;
  try { d = await fetch('/api/sysdiag').then(r => r.json()); } catch(e) {}
  let dspP = null;
  try { dspP = await _fetchDspParams(); } catch(e) {}
  const acOk = !!audioCtx, acState = acOk ? audioCtx.state : 'absent';
  const acSR = acOk ? audioCtx.sampleRate : 0;
  const acLat = acOk && audioCtx.baseLatency != null ? Math.round(audioCtx.baseLatency*1000)+' ms' : '—';
  const chainOk = acOk && !!_dspGainNode && !!_dspCompressor && !!_dspAnalyser;
  const eqBands = typeof _eqState !== 'undefined' ? _eqState : null;
  let html = `<div class="tv-diag-wrap"><div class="tv-diag-title">◈ DIAGNOSTIC DSP AUDIO — JARVIS VOICE ENGINE</div>`;
  if (d) html += _tvDiagBuildHardware(d);
  html += _tvDiagBuildAudio({ d, dspP, acOk, acState, acSR, acLat, chainOk, eqBands });
  html += '</div>';
  switchTab('chat');
  const bubble = addMessage('jarvis', '');
  bubble.innerHTML = html;
  if (d) {
    history.push({role:'user', content:`[DIAGNOSTIC DSP AUDIO — ${new Date().toLocaleTimeString('fr-FR')}]\nMatériel: CPU ${d.cpu_pct}% @ ${d.cpu_freq}GHz | RAM ${d.ram_used}/${d.ram_total}GB (${d.ram_pct}%) | GPU ${d.gpu_name} ${d.gpu_pct}% VRAM ${d.vram_used}/${d.vram_total}GB${d.gpu_temp?` ${d.gpu_temp}°C`:''}\nOllama: ${d.ollama_ok?'EN LIGNE '+d.ollama_latency+'ms':'HORS LIGNE'} | Modèle: ${d.llm_model} | Voix: ${d.llm_voice}\nDeepFilterNet: ${d.df_available?'disponible':'absent'} ${d.df_enabled?'(actif)':'(inactif)'}\nAudioContext: ${acState} ${acSR}Hz | Chaîne DSP: ${chainOk?'complète':'incomplète'}\nMémoire: ${d.memory_exchanges}/${d.memory_limit} échanges`});
    history.push({role:'assistant', content:'Diagnostic DSP et système reçu. Contexte intégré.'});
  }
  const issues = [];
  if (d) {
    if (d.cpu_pct >= 80)  issues.push(`CPU chargé à ${d.cpu_pct} pourcent`);
    if (d.ram_pct >= 85)  issues.push(`mémoire RAM à ${d.ram_pct} pourcent`);
    if (!d.ollama_ok)     issues.push('serveur Ollama hors ligne');
    if (!chainOk)         issues.push('chaîne audio DSP incomplète');
  }
  if (issues.length === 0) {
    const dfTxt = d?.df_available && d?.df_enabled ? ' DeepFilterNet actif.' : '';
    queueSpeech(`Diagnostic audio nominal.${dfTxt} AudioContext ${acState}. Chaîne D.S.P. complète. ${d ? 'Ollama en ligne, latence '+d.ollama_latency+' millisecondes.' : ''} Tous les systèmes vocaux sont opérationnels.`);
  } else {
    queueSpeech(`Attention. Diagnostic audio: ${issues.join(', ')}. Intervention recommandée.`);
  }
}
