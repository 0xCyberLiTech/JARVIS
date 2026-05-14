// ══════════════════════════════════════════════════════════════
// AUDIO VIZ — Visualisation stéréo de la voix (Web Audio)
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// Couche de visualisation audio temps réel : graphe Web Audio stéréo,
// STEREOGRAM 3D, GR meter (compresseur), VU-mètre stéréo, goniomètre à
// persistance phosphore, analyseur spectral, sonar vocal, visualiseur
// circulaire. Embarque ses appels de démarrage (_drawSpectrum, visualize,
// listeners visibilitychange/focus). Fichier .js classique (scope global).
// Chargé APRÈS jarvis_main.js.

// Création différée — évite un crash si le navigateur bloque avant interaction
let audioCtx = null, analyser = null, analyserL = null, analyserR = null;
let dataArray = new Uint8Array(128);
let fftL = new Uint8Array(512), fftR = new Uint8Array(512);
let timL = new Float32Array(1024), timR = new Float32Array(1024);

function _ensureAudioCtx() {
  if (audioCtx) return true;
  try {
    audioCtx  = new (window.AudioContext || window.webkitAudioContext)();
    analyser  = audioCtx.createAnalyser();
    analyser.fftSize = 256; analyser.smoothingTimeConstant = 0.75;
    analyser.connect(audioCtx.destination);
    analyserL = audioCtx.createAnalyser(); analyserL.fftSize = 4096; analyserL.smoothingTimeConstant = 0.8;
    analyserR = audioCtx.createAnalyser(); analyserR.fftSize = 4096; analyserR.smoothingTimeConstant = 0.8;
    // Merger stéréo : analyserL/R → analyser → destination (signal passe DANS les analyseurs)
    const _stereoMerger = audioCtx.createChannelMerger(2);
    analyserL.connect(_stereoMerger, 0, 0);
    analyserR.connect(_stereoMerger, 0, 1);
    _stereoMerger.connect(analyser);
    // Haas persistant : source mono → analyserL (direct) + _haasDelayNode → _haasGainNode → analyserR
    _haasDelayNode = audioCtx.createDelay(0.05);
    _haasDelayNode.delayTime.value = 0.018;
    _haasGainNode = audioCtx.createGain();
    _haasGainNode.gain.value = 0.85;
    _haasDelayNode.connect(_haasGainNode);
    _haasGainNode.connect(analyserR);
    dataArray = new Uint8Array(analyser.frequencyBinCount);
    fftL = new Uint8Array(analyserL.frequencyBinCount);
    fftR = new Uint8Array(analyserR.frequencyBinCount);
    timL = new Float32Array(analyserL.fftSize);
    timR = new Float32Array(analyserR.fftSize);
    return true;
  } catch(e) { return false; }
}

let speaking = false;
let _analyserEnabled = true;

// ── Resume audioCtx proactif quand l'onglet redevient actif ──
// Browser suspend l'AudioContext en background → latence au retour. Resume préventif évite ça.
function _audioCtxResumeProactive() {
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => { /* permission/policy denial — silencieux */ });
  }
}
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') _audioCtxResumeProactive();
});
window.addEventListener('focus', _audioCtxResumeProactive);

// ── Connexion source stéréo dans le graphe Web Audio ──
function _connectStereoSource(source) {
  const numCh = source.buffer ? source.buffer.numberOfChannels : 1;
  if (numCh >= 2) {
    // Stéréo : source → splitter → analyserL/R → stereoMerger → analyser → destination
    const splitter = audioCtx.createChannelSplitter(2);
    source.connect(splitter);
    splitter.connect(analyserL, 0);
    splitter.connect(analyserR, 1);
  } else {
    // Mono → Haas persistant sur R
    source.connect(analyserL);
    if (_haasDelayNode) source.connect(_haasDelayNode);
    else                source.connect(analyserR);
  }
}

// ══════════════════════════════════════
// STEREOGRAM 3D — PERSPECTIVE STEREO FIELD
// ══════════════════════════════════════
let _specRaf = null;
let _peakHoldL = null;
let _peakHoldR = null;
const _PEAK_DECAY  = 0.008;
const _SAMPLE_RATE    = 48000;  // taux d'échantillonnage cible DSP — edge-tts, DeepFilterNet, AudioContext fallback
const _FREQ_MIN    = 20;
const _FREQ_MAX    = _SAMPLE_RATE / 2;  // Nyquist 24kHz
let _freqLabelsInit = false;


// ── GR Meter canvas — compresseur gain reduction ──
let _grSmooth = 0;
function _drawGrMeter(reduction) {
  const cv = document.getElementById('rack-gr-canvas');
  if (!cv) return;
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  const GR_MAX = 24;   // max dB de réduction affichée
  const SEG = 80;
  const PAD_L = 8, PAD_R = 8, PAD_T = 6, PAD_B = 20;
  const MW = W - PAD_L - PAD_R;
  const MH = H - PAD_T - PAD_B;
  const SEG_W = MW / SEG;
  const GAP = 1;

  // Smooth
  const target = Math.min(GR_MAX, Math.abs(reduction || 0));
  _grSmooth += (target - _grSmooth) * 0.18;

  ctx.fillStyle = '#010608';
  ctx.fillRect(0, 0, W, H);

  // Background groove
  ctx.fillStyle = '#020c12';
  ctx.fillRect(PAD_L, PAD_T, MW, MH);

  // Lit segments (right→left as GR increases)
  const litSegs = Math.round((_grSmooth / GR_MAX) * SEG);
  for (let i = 0; i < SEG; i++) {
    const x = PAD_L + (SEG - 1 - i) * SEG_W;  // right to left
    const lit = i < litSegs;
    const pct = i / SEG;
    let color;
    if (!lit) {
      color = pct > 0.6 ? 'rgba(30,5,0,0.8)' : pct > 0.3 ? 'rgba(20,12,0,0.8)' : 'rgba(10,15,5,0.8)';
    } else {
      if (pct > 0.70) color = '#ff2200';
      else if (pct > 0.45) color = '#ff7700';
      else if (pct > 0.20) color = '#ffaa00';
      else color = '#ddcc00';
      ctx.shadowColor = color;
      ctx.shadowBlur = 5;
    }
    ctx.fillStyle = color;
    ctx.fillRect(x + GAP, PAD_T + 1, SEG_W - GAP - 1, MH - 2);
    ctx.shadowBlur = 0;
  }

  // Scale: 0, -3, -6, -9, -12, -18, -24 dB (right to left)
  const marks = [0, -3, -6, -9, -12, -18, -24];
  ctx.font = '8px Share Tech Mono, monospace';
  ctx.textAlign = 'center';
  marks.forEach(db => {
    const pct = Math.abs(db) / GR_MAX;
    const x = PAD_L + MW * (1 - pct);
    ctx.fillStyle = db < -12 ? 'rgba(255,80,0,.5)' : db < -6 ? 'rgba(255,150,0,.4)' : 'rgba(200,180,0,.35)';
    ctx.fillRect(x - 0.5, PAD_T + MH, 1, 4);
    ctx.fillStyle = 'rgba(140,120,60,.55)';
    ctx.fillText(db === 0 ? '0' : String(db), x, H - 4);
  });
  // "GR dB" label left
  ctx.textAlign = 'left';
  ctx.fillStyle = 'rgba(255,150,0,.2)';
  ctx.fillText('GR dB', PAD_L, H - 4);
}

// ── VU-mètre professionnel stéréo avec maintien des crêtes ──
let _vuHoldL = 0, _vuHoldR = 0;
let _vuHoldTL = 0, _vuHoldTR = 0;
let _vuHoldVL = 0, _vuHoldVR = 0;
let _vuSubL   = 0, _vuSubR   = 0;   // slow-decay peak for sub-bars
let _vuClipCL = 0, _vuClipCR = 0;   // near-clip hit counters
const _VU_HOLD_FRAMES = 55;
const _VU_HOLD_GRAV   = 0.00035;
const _VU_HOLD_VMAX   = 0.06;
const _VU_DB_MIN = -54, _VU_DB_MAX = 6;
function _vuLin2db(v) { return v > 1e-8 ? 20 * Math.log10(v) : -Infinity; }
function _vuFmt(db, plus) { return !isFinite(db) ? '-∞' : (db >= 0 && plus ? '+' : '') + db.toFixed(2); }

function _vuUpdHold(peak, hold, holdT, holdV) {
  if (peak > hold) return [peak, 0, 0];
  holdT++;
  if (holdT > _VU_HOLD_FRAMES) { holdV = Math.min(holdV + _VU_HOLD_GRAV, _VU_HOLD_VMAX); hold = Math.max(0, hold - holdV); }
  return [hold, holdT, holdV];
}
function _vuDrawMain({ lp, y, rms, hold, holdT, clipC, label }) {
  const {ctx, PAD_L, MW, BM, BS, xY, xR} = lp;
  const dRms = _vuLin2db(rms), dHold = _vuLin2db(hold);
  const xRms = lp.dbX(dRms), xHold = lp.dbX(dHold);
  ctx.fillStyle = '#010810'; ctx.fillRect(PAD_L, y, MW, BM);
  ctx.fillStyle = 'rgba(100,70,0,.10)'; ctx.fillRect(xY, y+1, xR-xY, BM-2);
  ctx.fillStyle = 'rgba(80,0,0,.14)';   ctx.fillRect(xR, y+1, PAD_L+MW-xR, BM-2);
  if (xRms > PAD_L) {
    const x1 = Math.min(xRms, xY);
    if (x1 > PAD_L) {
      const gB = ctx.createLinearGradient(PAD_L, 0, xY, 0);
      gB.addColorStop(0, '#004870'); gB.addColorStop(0.55, '#0090c0'); gB.addColorStop(1, '#00b8e0');
      ctx.fillStyle = gB; ctx.fillRect(PAD_L, y+1, x1-PAD_L, BM-2);
    }
    if (xRms > xY) {
      const x2 = Math.min(xRms, xR);
      const gY = ctx.createLinearGradient(xY, 0, xR, 0);
      gY.addColorStop(0, '#b09000'); gY.addColorStop(1, '#e0b800');
      ctx.fillStyle = gY; ctx.fillRect(xY, y+1, x2-xY, BM-2);
    }
    if (xRms > xR) { ctx.fillStyle = '#c01010'; ctx.fillRect(xR, y+1, xRms-xR, BM-2); }
    ctx.fillStyle = 'rgba(255,255,255,.04)'; ctx.fillRect(PAD_L, y+1, xRms-PAD_L, 2);
  }
  ctx.fillStyle = 'rgba(220,170,0,.25)'; ctx.fillRect(xY-.5, y, 1, BM);
  ctx.fillStyle = 'rgba(255,40,0,.35)';  ctx.fillRect(xR-.5, y, 1, BM);
  const showH = holdT < _VU_HOLD_FRAMES + 80 && hold > 1e-4;
  if (showH) {
    const hCol = dHold > 0 ? '#ff5522' : dHold > -6 ? '#ffe040' : '#ffffff';
    ctx.shadowColor = hCol; ctx.shadowBlur = 10;
    ctx.fillStyle = hCol; ctx.fillRect(xHold-1, y+1, 2, BM-2); ctx.shadowBlur = 0;
  }
  ctx.font = 'bold 11px Orbitron,monospace'; ctx.fillStyle = '#00cfff77'; ctx.textAlign = 'center';
  ctx.fillText(label, PAD_L/2, y+BM*.62+3);
  const rx = PAD_L+MW+8;
  if (showH) {
    const hStr = _vuFmt(dHold, true) + ' dB' + (clipC > 0 ? ` (${Math.min(clipC,99)})` : '');
    const hCol = dHold > 0 ? '#ff3300' : dHold > -6 ? '#ffcc00' : '#00cfff99';
    ctx.font = 'bold 11px Share Tech Mono,monospace'; ctx.fillStyle = hCol; ctx.textAlign = 'left';
    ctx.fillText(hStr, rx, y+Math.round(BM*0.36));
  }
  const rmsCol = !isFinite(dRms) ? '#1a2a30' : dRms > 0 ? '#ff220088' : dRms > -6 ? '#ffcc0088' : '#00a8d488';
  ctx.font = '9px Share Tech Mono,monospace'; ctx.fillStyle = rmsCol; ctx.textAlign = 'left';
  ctx.fillText(_vuFmt(dRms, true) + ' dB', rx, y+Math.round(BM*0.82));
}
function _vuDrawSub(lp, y, rms, slowPeak) {
  const {ctx, PAD_L, MW, BS} = lp;
  const dRms = _vuLin2db(rms), dSlow = _vuLin2db(slowPeak);
  const xRms = lp.dbX(dRms), xSlow = lp.dbX(dSlow);
  ctx.fillStyle = '#010810'; ctx.fillRect(PAD_L, y, MW, BS);
  if (xRms > PAD_L) { ctx.fillStyle = '#0a2e50'; ctx.fillRect(PAD_L, y+1, xRms-PAD_L, BS-2); }
  if (xSlow > xRms) {
    const g = ctx.createLinearGradient(xRms, 0, xSlow, 0);
    g.addColorStop(0, '#6a1200'); g.addColorStop(1, '#b02800');
    ctx.fillStyle = g; ctx.fillRect(xRms, y+1, xSlow-xRms, BS-2);
    const crest = dSlow - dRms;
    if (isFinite(crest) && crest > 0.5) {
      ctx.font = '8px Share Tech Mono,monospace'; ctx.fillStyle = '#cc441188'; ctx.textAlign = 'center';
      ctx.fillText('[' + crest.toFixed(1) + ' dB]', (xRms+xSlow)/2, y+BS*.72+1);
    }
  }
  ctx.font = '9px Share Tech Mono,monospace'; ctx.fillStyle = '#00cfff55'; ctx.textAlign = 'left';
  ctx.fillText(_vuFmt(dRms, true) + ' dB', PAD_L+MW+8, y+Math.round(BS*0.62)+2);
}
function _vuDrawScale(lp, y) {
  const {ctx, PAD_L, MW, SCL} = lp;
  ctx.fillStyle = '#010810'; ctx.fillRect(PAD_L, y, MW, SCL);
  [-54,-51,-48,-45,-42,-39,-36,-33,-30,-27,-24,-21,-18,-15,-12,-9,-6,-3,0,3,6].forEach(db => {
    const x = lp.dbX(db), major = db % 6 === 0;
    ctx.fillStyle = db >= 0 ? 'rgba(255,55,0,.55)' : db > -6 ? 'rgba(255,190,0,.38)' : 'rgba(0,200,255,.22)';
    ctx.fillRect(x-.5, y, 1, major ? 4 : 2);
    if (major) {
      ctx.font = '8px Share Tech Mono,monospace'; ctx.textAlign = 'center';
      ctx.fillStyle = db >= 0 ? 'rgba(255,80,0,.75)' : 'rgba(0,175,215,.52)';
      ctx.fillText(db === 0 ? '0' : (db > 0 ? '+' : '')+db, x, y+SCL-1);
    }
  });
  ctx.font = '7px Orbitron,monospace'; ctx.fillStyle = '#1a3040'; ctx.textAlign = 'right';
  ctx.fillText('dB', PAD_L+MW-2, y+SCL-1);
}
function _vuDrawBalance(lp, y, rmsL, rmsR) {
  const {ctx, PAD_L, MW} = lp;
  const dL = _vuLin2db(rmsL), dR = _vuLin2db(rmsR);
  if (!isFinite(dL) && !isFinite(dR)) return;
  const bal = isFinite(dL) && isFinite(dR) ? Math.max(-6, Math.min(6, dL-dR)) : 0;
  const cx = PAD_L+MW/2, bpx = MW/12;
  ctx.fillStyle = 'rgba(0,207,255,.08)'; ctx.fillRect(PAD_L, y, MW, 1);
  ctx.font = '7px Orbitron,monospace'; ctx.fillStyle = '#00cfff33'; ctx.textAlign = 'center';
  ctx.fillText('Balance', cx, y+9);
  [-6,-3,0,3,6].forEach(db => {
    const x = cx+db*bpx;
    ctx.fillStyle = 'rgba(0,180,210,.30)'; ctx.fillRect(x-.5, y+10, 1, 4);
    ctx.font = '7px Share Tech Mono,monospace'; ctx.fillStyle = 'rgba(0,175,210,.40)'; ctx.textAlign = 'center';
    ctx.fillText(db === 0 ? '0' : (db > 0 ? '+' : '')+db, x, y+21);
  });
  const bW = Math.abs(bal)*bpx, barY = y+23, barH = 10;
  ctx.fillStyle = '#010810'; ctx.fillRect(cx-6*bpx, barY, 12*bpx, barH);
  if (bW > 1) {
    const bx = bal >= 0 ? cx : cx-bW;
    const g = ctx.createLinearGradient(bx, 0, bx+bW, 0);
    g.addColorStop(0, bal >= 0 ? '#7a4200' : '#5a3800'); g.addColorStop(1, bal >= 0 ? '#c06800' : '#a05800');
    ctx.fillStyle = g; ctx.fillRect(bx, barY, bW, barH);
  }
  ctx.fillStyle = '#00cfff66'; ctx.fillRect(cx-.5, barY, 1, barH);
  const valY = y+37;
  ctx.font = '8px Share Tech Mono,monospace'; ctx.fillStyle = '#00cfff44';
  ctx.textAlign = 'left';  ctx.fillText(_vuFmt(dL, true)+' dB', PAD_L, valY);
  ctx.textAlign = 'right'; ctx.fillText(_vuFmt(dR, true)+' dB', PAD_L+MW, valY);
  if (bW > 1) { ctx.fillStyle = '#cc660077'; ctx.textAlign = 'center'; ctx.fillText((bal >= 0 ? '+' : '')+bal.toFixed(1)+' dB', cx, valY); }
}
function _drawVuMeter(rmsL, rmsR, peakL, peakR) {
  const cv = document.getElementById('rack-vu-meter');
  if (!cv) return;
  const W = cv.width, H = cv.height;
  const PAD_L = 28, MW = W - PAD_L - 156, BM = 26, BS = 14, SCL = 16;
  const GAP = 4;
  const lp = {
    ctx: cv.getContext('2d'), PAD_L, MW, BM, BS, SCL,
    dbX(db) { return PAD_L + Math.max(0, Math.min(1, (Math.max(_VU_DB_MIN, Math.min(_VU_DB_MAX, db)) - _VU_DB_MIN) / (_VU_DB_MAX - _VU_DB_MIN))) * MW; }
  };
  lp.xY = lp.dbX(-6); lp.xR = lp.dbX(0);
  lp.ctx.fillStyle = '#020508'; lp.ctx.fillRect(0, 0, W, H);
  [_vuHoldL, _vuHoldTL, _vuHoldVL] = _vuUpdHold(peakL, _vuHoldL, _vuHoldTL, _vuHoldVL);
  [_vuHoldR, _vuHoldTR, _vuHoldVR] = _vuUpdHold(peakR, _vuHoldR, _vuHoldTR, _vuHoldVR);
  _vuSubL = Math.max(peakL, _vuSubL * 0.975);
  _vuSubR = Math.max(peakR, _vuSubR * 0.975);
  if (peakL >= 0.944) _vuClipCL++; else _vuClipCL = Math.max(0, _vuClipCL - 1);
  if (peakR >= 0.944) _vuClipCR++; else _vuClipCR = Math.max(0, _vuClipCR - 1);
  const yLM = GAP, yLS = yLM+BM+GAP, ySC = yLS+BS+GAP, yRS = ySC+SCL+GAP, yRM = yRS+BS+GAP, yBL = yRM+BM+GAP+6;
  _vuDrawMain({ lp, y: yLM, rms: rmsL, hold: _vuHoldL, holdT: _vuHoldTL, clipC: _vuClipCL, label: 'L' });
  _vuDrawSub (lp, yLS, rmsL, _vuSubL);
  _vuDrawScale(lp, ySC);
  _vuDrawSub (lp, yRS, rmsR, _vuSubR);
  _vuDrawMain({ lp, y: yRM, rms: rmsR, hold: _vuHoldR, holdT: _vuHoldTR, clipC: _vuClipCR, label: 'R' });
  _vuDrawBalance(lp, yBL, rmsL, rmsR);
}

// Convertit une fréquence en position X (log scale)
function _logX(freq, W) {
  const lo = Math.log10(_FREQ_MIN), hi = Math.log10(_FREQ_MAX);
  return ((Math.log10(Math.max(freq, _FREQ_MIN)) - lo) / (hi - lo)) * W;
}

// Retourne la fréquence du bin i

// Couleur d'une barre selon son niveau normalisé (0=silence, 1=clip)

// Génère les labels de fréquences positionnés sur l'axe log
function _initFreqLabels(W) {
  const container = document.getElementById('rack-freq-labels');
  if (!container || _freqLabelsInit) return;
  _freqLabelsInit = true;
  const marks = [
    {f:20,'l':'20'},{f:50,'l':'50'},{f:100,'l':'100'},{f:200,'l':'200'},
    {f:500,'l':'500'},{f:1000,'l':'1k'},{f:2000,'l':'2k'},{f:5000,'l':'5k'},
    {f:10000,'l':'10k'},{f:20000,'l':'20k'},{f:24000,'l':'24k Hz'}
  ];
  container.style.position = 'relative';
  marks.forEach(({f, l}) => {
    const pct = (_logX(f, 100) ).toFixed(2);
    const span = document.createElement('span');
    span.textContent = l;
    span.className = 'freq-label-pos';
    span.style.left = pct + '%';
    container.appendChild(span);
  });
}

function _specSetLcd(id, txt, val) {
  const e = document.getElementById(id); if (!e) return;
  e.textContent = txt;
  if (val !== undefined) {
    e.classList.toggle('alert', val > -6);
    e.classList.toggle('warn',  val > -18 && val <= -6);
  }
}
var _SPEC_NUM_BARS = 160;
function _specDrawMirror(ctx2, W, H, halfH, barW, MAX_H){
  ctx2.setLineDash([2,6]); ctx2.lineWidth=0.5;
  [0.33,0.66,1.0].forEach(v=>{
    const yU=halfH-v*halfH*0.93, yD=halfH+v*halfH*0.93;
    ctx2.strokeStyle=v===1.0?'rgba(0,207,255,0.14)':'rgba(0,160,200,0.07)';
    ctx2.beginPath(); ctx2.moveTo(0,yU); ctx2.lineTo(W,yU); ctx2.stroke();
    ctx2.beginPath(); ctx2.moveTo(0,yD); ctx2.lineTo(W,yD); ctx2.stroke();
  });
  ctx2.setLineDash([2,5]);
  [50,100,200,500,1000,2000,5000,10000,20000].forEach(freq=>{
    const x=Math.log10(freq/_FREQ_MIN)/Math.log10(_FREQ_MAX/_FREQ_MIN)*W;
    ctx2.strokeStyle='rgba(0,150,190,0.08)';
    ctx2.beginPath(); ctx2.moveTo(x,0); ctx2.lineTo(x,H); ctx2.stroke();
  });
  ctx2.setLineDash([]);
  for(let b=0;b<_SPEC_NUM_BARS;b++){
    const bm=_specBinMap[b], cnt=bm[1]-bm[0]+1;
    let sL=0,sR=0; for(let i=bm[0];i<=bm[1];i++){sL+=fftL[i];sR+=fftR[i];}
    const vL=Math.pow(sL/cnt/255,0.72), vR=Math.pow(sR/cnt/255,0.72);
    const hL=vL*MAX_H, hR=vR*MAX_H, x=b*barW;
    const [cr,cg,cb]=_specColorTable[b];
    if(hL>0.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+','+(0.35+vL*0.65).toFixed(2)+')';ctx2.fillRect(x,halfH-hL,barW-0.5,hL);}
    if(hR>0.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+','+(0.35+vR*0.65).toFixed(2)+')';ctx2.fillRect(x,halfH,barW-0.5,hR);}
    _peakHoldL[b]=Math.max(vL,_peakHoldL[b]-_PEAK_DECAY); _peakHoldR[b]=Math.max(vR,_peakHoldR[b]-_PEAK_DECAY);
    const phL=_peakHoldL[b]*MAX_H, phR=_peakHoldR[b]*MAX_H;
    if(phL>1.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+',0.95)';ctx2.fillRect(x,halfH-phL-1.5,barW-0.5,1.5);}
    if(phR>1.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+',0.95)';ctx2.fillRect(x,halfH+phR,barW-0.5,1.5);}
  }
  ctx2.fillStyle='rgba(0,207,255,0.35)'; ctx2.fillRect(0,halfH-0.5,W,1);
  ctx2.font='9px Share Tech Mono,monospace'; ctx2.textAlign='left';
  ctx2.fillStyle='rgba(0,207,255,0.55)'; ctx2.fillText('L',5,13); ctx2.fillText('R',5,H-6);
  ctx2.font='7px Share Tech Mono,monospace'; ctx2.textAlign='right'; ctx2.fillStyle='rgba(0,180,220,0.45)';
  [[-6,1.0],[-12,0.66],[-18,0.33]].forEach(([db,v])=>{ctx2.fillText(db+'dB',W-2,halfH-v*halfH*0.93+3);});
}
function _specDrawScope(ctx2, W, H, sr){
  const PAD=8, qH=(H-PAD*3)/2;
  const yL0=PAD, yR0=PAD*2+qH;
  const STEP=Math.max(1,Math.floor(timL.length/W));
  let peakAmp=1e-4;
  for(let i=0;i<timL.length;i++){const a=Math.abs(timL[i]);if(a>peakAmp)peakAmp=a;}
  for(let i=0;i<timR.length;i++){const a=Math.abs(timR[i]);if(a>peakAmp)peakAmp=a;}
  _scopeGain=_scopeGain*0.94+Math.min(10,0.82/peakAmp)*0.06;
  const SWING=qH*0.46*_scopeGain;
  for(let y=0;y<H;y+=3){ctx2.fillStyle='rgba(0,0,0,0.18)';ctx2.fillRect(0,y,W,1);}
  ctx2.setLineDash([4,6]); ctx2.lineWidth=0.5; ctx2.strokeStyle='rgba(0,207,255,0.08)';
  ctx2.beginPath(); ctx2.moveTo(0,yR0-PAD/2); ctx2.lineTo(W,yR0-PAD/2); ctx2.stroke();
  ctx2.setLineDash([]);
  [yL0+qH/2,yR0+qH/2].forEach((cy,ci)=>{
    ctx2.setLineDash([2,8]); ctx2.lineWidth=0.5;
    ctx2.strokeStyle=ci===0?'rgba(0,207,255,0.15)':'rgba(204,102,255,0.15)';
    ctx2.beginPath(); ctx2.moveTo(0,cy); ctx2.lineTo(W,cy); ctx2.stroke();
    ctx2.setLineDash([]);
  });
  for(let d=1;d<8;d++){
    const xd=W*d/8; ctx2.setLineDash([2,6]); ctx2.lineWidth=0.4;
    ctx2.strokeStyle='rgba(0,130,160,0.08)';
    ctx2.beginPath(); ctx2.moveTo(xd,0); ctx2.lineTo(xd,H); ctx2.stroke();
    ctx2.setLineDash([]);
  }
  const _drawWave=(tim,yBase,colRgb)=>{
    const cy=yBase+qH/2;
    ctx2.beginPath(); ctx2.moveTo(0,cy);
    for(let i=0;i<tim.length;i+=STEP) ctx2.lineTo((i/tim.length)*W,cy-tim[i]*SWING);
    ctx2.lineTo(W,cy); ctx2.closePath(); ctx2.fillStyle='rgba('+colRgb+',0.07)'; ctx2.fill();
    ctx2.shadowBlur=8; ctx2.shadowColor='rgba('+colRgb+',0.6)';
    ctx2.lineWidth=2.5; ctx2.strokeStyle='rgba('+colRgb+',0.35)';
    ctx2.beginPath();
    for(let i=0;i<tim.length;i+=STEP){const x=(i/tim.length)*W,y=cy-tim[i]*SWING;i===0?ctx2.moveTo(x,y):ctx2.lineTo(x,y);}
    ctx2.stroke(); ctx2.shadowBlur=0; ctx2.lineWidth=1.2; ctx2.strokeStyle='rgba('+colRgb+',0.95)';
    ctx2.beginPath();
    for(let i=0;i<tim.length;i+=STEP){const x=(i/tim.length)*W,y=cy-tim[i]*SWING;i===0?ctx2.moveTo(x,y):ctx2.lineTo(x,y);}
    ctx2.stroke();
  };
  _drawWave(timL,yL0,'0,207,255'); _drawWave(timR,yR0,'204,102,255'); ctx2.shadowBlur=0;
  const bufMs=((timL.length/(sr||_SAMPLE_RATE))*1000).toFixed(0);
  ctx2.font='9px Share Tech Mono,monospace'; ctx2.textAlign='left';
  ctx2.fillStyle='rgba(0,207,255,0.8)'; ctx2.fillText('L',5,yL0+12);
  ctx2.fillStyle='rgba(204,102,255,0.8)'; ctx2.fillText('R',5,yR0+12);
  ctx2.font='7px Share Tech Mono,monospace'; ctx2.textAlign='right'; ctx2.fillStyle='rgba(0,180,220,0.4)';
  ctx2.fillText(bufMs+' ms  ×'+_scopeGain.toFixed(1),W-4,10);
}
function _specDrawPiano(ctx2, W, H, sr, bins){
  const A0F=27.5,C8F=4186.0,logA0=Math.log10(A0F),logC8=Math.log10(C8F);
  const KEY_H=22,BAR_MAX=H-KEY_H-4,BLK=new Set([1,3,6,8,10]);
  for(let k=0;k<88;k++){
    const f0=A0F*Math.pow(2,k/12),f1=A0F*Math.pow(2,(k+1)/12);
    const x0=(Math.log10(f0)-logA0)/(logC8-logA0)*W,x1=(Math.log10(f1)-logA0)/(logC8-logA0)*W;
    const kw=Math.max(1,x1-x0-0.5);
    const bk0=Math.max(0,Math.floor(f0*bins/(sr/2))),bk1=Math.min(bins-1,Math.ceil(f1*bins/(sr/2)));
    let sum=0,cnt=0; for(let i=bk0;i<=bk1;i++){sum+=(fftL[i]+fftR[i])*0.5;cnt++;}
    const v=cnt>0?Math.pow(sum/cnt/255,0.72):0;
    const [cr,cg,cb]=_specColorTable[Math.min(159,Math.floor(k/88*160))];
    const bh=v*BAR_MAX;
    if(bh>0.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+','+(0.3+v*0.7).toFixed(2)+')';ctx2.fillRect(x0,H-KEY_H-bh,kw,bh);}
    ctx2.fillStyle=BLK.has(k%12)?'rgba(0,0,0,0.75)':'rgba(15,25,45,0.75)';
    ctx2.fillRect(x0,H-KEY_H,kw,KEY_H-1);
  }
  ctx2.font='7px Share Tech Mono,monospace'; ctx2.textAlign='center';
  for(let oct=0;oct<=8;oct++){
    const fC=16.352*Math.pow(2,oct); if(fC<A0F||fC>C8F) continue;
    const xC=(Math.log10(fC)-logA0)/(logC8-logA0)*W;
    ctx2.fillStyle='rgba(0,207,255,0.4)'; ctx2.fillText('C'+oct,xC,H-KEY_H+11);
    ctx2.strokeStyle='rgba(0,207,255,0.07)'; ctx2.lineWidth=0.5;
    ctx2.beginPath(); ctx2.moveTo(xC,0); ctx2.lineTo(xC,H-KEY_H); ctx2.stroke();
  }
  ctx2.textAlign='left';
}
function _specDrawSplit(ctx2, W, H){
  const halfW=W/2, bw2=halfW/_SPEC_NUM_BARS, MAXH2=(H-4)*0.9;
  ctx2.setLineDash([2,5]); ctx2.lineWidth=0.5;
  [50,200,1000,5000,20000].forEach(freq=>{
    const rx=Math.log10(freq/_FREQ_MIN)/Math.log10(_FREQ_MAX/_FREQ_MIN)*halfW;
    ctx2.strokeStyle='rgba(0,150,190,0.07)';
    ctx2.beginPath(); ctx2.moveTo(rx,0); ctx2.lineTo(rx,H); ctx2.stroke();
    ctx2.beginPath(); ctx2.moveTo(halfW+rx,0); ctx2.lineTo(halfW+rx,H); ctx2.stroke();
  });
  ctx2.setLineDash([]);
  for(let b=0;b<_SPEC_NUM_BARS;b++){
    const bm=_specBinMap[b], cnt=bm[1]-bm[0]+1;
    let sL=0,sR=0; for(let i=bm[0];i<=bm[1];i++){sL+=fftL[i];sR+=fftR[i];}
    const vL=Math.pow(sL/cnt/255,0.72),vR=Math.pow(sR/cnt/255,0.72);
    const [cr,cg,cb]=_specColorTable[b];
    const xL=b*bw2,xR=halfW+b*bw2,hbL=vL*MAXH2,hbR=vR*MAXH2;
    if(hbL>0.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+','+(0.35+vL*0.65).toFixed(2)+')';ctx2.fillRect(xL,H-hbL,bw2-0.5,hbL);}
    if(hbR>0.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+','+(0.35+vR*0.65).toFixed(2)+')';ctx2.fillRect(xR,H-hbR,bw2-0.5,hbR);}
    _peakHoldL[b]=Math.max(vL,_peakHoldL[b]-_PEAK_DECAY); _peakHoldR[b]=Math.max(vR,_peakHoldR[b]-_PEAK_DECAY);
    const phL=_peakHoldL[b]*MAXH2,phR=_peakHoldR[b]*MAXH2;
    if(phL>1.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+',0.95)';ctx2.fillRect(xL,H-phL-1.5,bw2-0.5,1.5);}
    if(phR>1.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+',0.95)';ctx2.fillRect(xR,H-phR-1.5,bw2-0.5,1.5);}
  }
  ctx2.fillStyle='rgba(0,207,255,0.45)'; ctx2.fillRect(halfW-0.5,0,1,H);
  ctx2.font='9px Share Tech Mono,monospace'; ctx2.textAlign='left';
  ctx2.fillStyle='rgba(0,207,255,0.7)'; ctx2.fillText('L',5,13);
  ctx2.fillStyle='rgba(204,102,255,0.7)'; ctx2.fillText('R',halfW+5,13);
  ctx2.font='7px Share Tech Mono,monospace'; ctx2.textAlign='right'; ctx2.fillStyle='rgba(0,180,220,0.35)';
  [-6,-12,-18].forEach(db=>{const h2=Math.pow(10,db/20)*MAXH2;ctx2.fillText(db+'dB',halfW-4,H-h2+3);ctx2.fillText(db+'dB',W-4,H-h2+3);});
}
function _specUpdateMetrics(rmsL, rmsR, peakLinL, peakLinR, corrClamped){
  const pL=Math.min(100,rmsL*300), pR=Math.min(100,rmsR*300);
  ['rack-peak-l','rack-vu-l'].forEach(id=>{const e=document.getElementById(id);if(e)e.style.width=pL+'%';});
  ['rack-peak-r','rack-vu-r'].forEach(id=>{const e=document.getElementById(id);if(e)e.style.width=pR+'%';});
  const svL=document.getElementById('rack-vu-stereo-l'), svR=document.getElementById('rack-vu-stereo-r');
  if(svL) svL.style.width=_stereoActive?pL+'%':'0%';
  if(svR) svR.style.width=_stereoActive?pR+'%':'0%';
  const dbL=rmsL>1e-4?(20*Math.log10(rmsL)).toFixed(1):'-∞';
  const dbR=rmsR>1e-4?(20*Math.log10(rmsR)).toFixed(1):'-∞';
  const rmsAvg=(rmsL+rmsR)/2;
  const dbRms=rmsAvg>1e-4?(20*Math.log10(rmsAvg)).toFixed(1):'-∞';
  _specSetLcd('rack-peak-l-db',dbL+' dB',parseFloat(dbL));
  _specSetLcd('rack-peak-r-db',dbR+' dB',parseFloat(dbR));
  _specSetLcd('rack-rms-val',dbRms+' dB',parseFloat(dbRms));
  const epM=document.getElementById('rack-peak-db'); if(epM) epM.textContent=dbL+' dB';
  const eCorr=document.getElementById('rack-corr-fill'), eCorrVal=document.getElementById('rack-corr-val');
  const silent=(rmsL+rmsR)<0.002;
  if(eCorr){
    if(silent){eCorr.style.transition='none';eCorr.style.left='50%';eCorr.style.width='0%';}
    else{
      eCorr.style.transition='width .12s,left .12s,background .2s';
      const w=Math.abs(corrClamped)*50;
      eCorr.style.left=corrClamped>=0?'50%':(50-w)+'%'; eCorr.style.width=w+'%';
      const cGood=corrClamped>0.3, cWarn=corrClamped>-0.1;
      eCorr.classList.toggle('corr-good', cGood);
      eCorr.classList.toggle('corr-warn', !cGood&&cWarn);
      eCorr.classList.toggle('corr-bad',  !cGood&&!cWarn);
    }
  }
  if(eCorrVal){
    if(silent){eCorrVal.textContent='—';eCorrVal.className=(eCorrVal.className.replace(/\bcorr-val-\S+/g,'')+' corr-val-silent').trim();}
    else{eCorrVal.textContent=corrClamped.toFixed(2);const cv=corrClamped>0.3?'corr-val-good':corrClamped>-0.1?'corr-val-warn':'corr-val-bad';eCorrVal.className=(eCorrVal.className.replace(/\bcorr-val-\S+/g,'')+' '+cv).trim();}
  }
}
function _drawSpectrum() {
  _specRaf = requestAnimationFrame(_drawSpectrum);
  if (!_analyserEnabled || !analyserL || !analyserR) return;
  const _anlL = window._datActive?(window._datAnL||analyserL):analyserL;
  const _anlR = window._datActive?(window._datAnR||analyserR):analyserR;
  _anlL.getByteFrequencyData(fftL); _anlR.getByteFrequencyData(fftR);
  _anlL.getFloatTimeDomainData(timL); _anlR.getFloatTimeDomainData(timR);
  const cv = document.getElementById('rack-spectrum-canvas');
  if (!cv) return;
  const ctx2=cv.getContext('2d'), W=cv.width, H=cv.height, halfH=H/2;
  const bins=fftL.length, sr=audioCtx.sampleRate||_SAMPLE_RATE;
  if(!_peakHoldL||_peakHoldL.length!==_SPEC_NUM_BARS){_peakHoldL=new Float32Array(_SPEC_NUM_BARS);_peakHoldR=new Float32Array(_SPEC_NUM_BARS);}
  const _freqLblEl=document.getElementById('rack-freq-labels');
  _disp(_freqLblEl, _rackSpecMode==='mirror'||_rackSpecMode==='split');
  if(_rackSpecMode==='mirror'||_rackSpecMode==='split') _initFreqLabels(W);
  if(!_specColorTable){
    _specColorTable=new Array(_SPEC_NUM_BARS);
    for(let ci=0;ci<_SPEC_NUM_BARS;ci++){
      const h=ci/_SPEC_NUM_BARS; let cr,cg,cb;
      if(h<0.20){const t=h/0.20;cr=0;cg=Math.round(120+t*110);cb=Math.round(255-t*105);}
      else if(h<0.50){const t=(h-0.20)/0.30;cr=Math.round(t*55);cg=Math.round(230+t*25);cb=Math.round(150-t*150);}
      else if(h<0.75){const t=(h-0.50)/0.25;cr=Math.round(55+t*200);cg=Math.round(255-t*60);cb=0;}
      else{const t=(h-0.75)/0.25;cr=255;cg=Math.round(195-t*195);cb=0;}
      _specColorTable[ci]=[cr,cg,cb];
    }
  }
  if(!_specBinMap||_specBinMap.length!==_SPEC_NUM_BARS){
    _specBinMap=new Array(_SPEC_NUM_BARS);
    for(let b=0;b<_SPEC_NUM_BARS;b++){
      const f0=_FREQ_MIN*Math.pow(_FREQ_MAX/_FREQ_MIN,b/_SPEC_NUM_BARS);
      const f1=_FREQ_MIN*Math.pow(_FREQ_MAX/_FREQ_MIN,(b+1)/_SPEC_NUM_BARS);
      _specBinMap[b]=[Math.max(0,Math.floor(f0*bins/(sr/2))),Math.min(bins-1,Math.ceil(f1*bins/(sr/2)))];
    }
  }
  const barW=W/_SPEC_NUM_BARS, MAX_H=halfH*0.93;
  ctx2.fillStyle='#000508'; ctx2.fillRect(0,0,W,H);
  if(_rackSpecMode==='mirror')      _specDrawMirror(ctx2,W,H,halfH,barW,MAX_H);
  else if(_rackSpecMode==='scope')  _specDrawScope(ctx2,W,H,sr);
  else if(_rackSpecMode==='piano')  _specDrawPiano(ctx2,W,H,sr,bins);
  else if(_rackSpecMode==='split')  _specDrawSplit(ctx2,W,H);
  let sumL2=0,sumR2=0,sumLR=0,peakLinL=0,peakLinR=0;
  for(let i=0;i<timL.length;i++){
    const aL=Math.abs(timL[i]),aR=Math.abs(timR[i]);
    sumL2+=aL*aL;sumR2+=aR*aR;sumLR+=timL[i]*timR[i];
    if(aL>peakLinL)peakLinL=aL;if(aR>peakLinR)peakLinR=aR;
  }
  const rmsL=Math.sqrt(sumL2/timL.length), rmsR=Math.sqrt(sumR2/timR.length);
  const corr=sumLR/(Math.sqrt(sumL2*sumR2)+1e-9);
  _specUpdateMetrics(rmsL,rmsR,peakLinL,peakLinR,Math.max(-1,Math.min(1,corr)));
  _drawGonio(timL,timR);
  _drawVuMeter(rmsL,rmsR,peakLinL,peakLinR);
}

// ── Goniomètre à persistance phosphore ──
function _drawGonio(timL, timR) {
  const cv = document.getElementById('rack-gonio-canvas');
  if (!cv) return;
  const ctx2 = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  const cx = W / 2, cy = H / 2;

  // Fade phosphore : fond semi-transparent pour effet persistence
  ctx2.fillStyle = 'rgba(0,1,10,0.18)';
  ctx2.fillRect(0, 0, W, H);

  // Axes + diagonales fixes (redessinés chaque frame par-dessus le fade)
  ctx2.lineWidth = 0.5;
  ctx2.strokeStyle = 'rgba(0,207,255,0.12)';
  ctx2.beginPath(); ctx2.moveTo(cx, 4); ctx2.lineTo(cx, H-4); ctx2.stroke();
  ctx2.beginPath(); ctx2.moveTo(4, cy); ctx2.lineTo(W-4, cy); ctx2.stroke();
  ctx2.strokeStyle = 'rgba(0,207,255,0.07)';
  ctx2.beginPath(); ctx2.moveTo(4,4); ctx2.lineTo(W-4,H-4); ctx2.stroke();
  ctx2.beginPath(); ctx2.moveTo(W-4,4); ctx2.lineTo(4,H-4); ctx2.stroke();

  // Labels M / S
  ctx2.font = '7px Share Tech Mono, monospace';
  ctx2.fillStyle = 'rgba(0,207,255,0.25)';
  ctx2.textAlign = 'center';
  ctx2.fillText('M', cx, 11);
  ctx2.fillText('L', 9, cy+3);
  ctx2.fillText('R', W-9, cy+3);
  ctx2.fillText('S', cx, H-4);
  ctx2.textAlign = 'left';

  // Cercle de référence
  ctx2.beginPath();
  ctx2.arc(cx, cy, cx * 0.88, 0, Math.PI * 2);
  ctx2.strokeStyle = 'rgba(0,207,255,0.06)';
  ctx2.lineWidth = 1;
  ctx2.stroke();

  // Tracé Lissajous (rotation 45° = convention goniomètre)
  const step = Math.max(1, Math.floor(timL.length / 128));
  ctx2.lineWidth = 1.2;
  // Couleur selon énergie
  const energy = Math.sqrt((timL.reduce((a,v)=>a+v*v,0)+timR.reduce((a,v)=>a+v*v,0))/timL.length/2);
  const alpha = Math.min(0.9, 0.3 + energy * 4);
  ctx2.strokeStyle = `rgba(0,220,255,${alpha})`;

  ctx2.beginPath();
  let first = true;
  for (let i = 0; i < timL.length; i += step) {
    const m =  (timL[i] + timR[i]) * 0.707;
    const s =  (timL[i] - timR[i]) * 0.707;
    const x = cx + s * (cx - 5) * 0.9;
    const y = cy - m * (cy - 5) * 0.9;
    first ? ctx2.moveTo(x, y) : ctx2.lineTo(x, y);
    first = false;
  }
  ctx2.stroke();

  // Point central (silence = vert, signal = cyan)
  ctx2.beginPath();
  ctx2.arc(cx, cy, energy > 0.005 ? 1.5 : 2.5, 0, Math.PI * 2);
  ctx2.fillStyle = energy > 0.005 ? 'rgba(0,220,255,0.8)' : 'rgba(0,255,120,0.5)';
  ctx2.fill();
}

// Lancer le dessin du spectre
_drawSpectrum();

const speechQueue = [];
let isPlaying = false;
let _currentAudioSource = null; // source en cours pour stop immédiat
let _audioGen = 0; // incrémenté à chaque stop → invalide le onended de l'ancienne source

async function playSentence(text) {
  return new Promise(async (resolve) => {
    if (!_ensureAudioCtx()) { resolve(); return; }
    if (!_dspInited) try { initDsp(); } catch(e) {}
    try {
      const resp = await fetch('/api/tts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text})
      });
      if (!resp.ok) { resolve(); return; }
      const arrayBuffer = await resp.arrayBuffer();
      // Lire SR source depuis header WAV (offset 24, uint32 LE) avant decodeAudioData (qui détache le buffer)
      let _ttsSrcSR = audioCtx.sampleRate;
      try {
        const _hv = new DataView(arrayBuffer);
        if (arrayBuffer.byteLength >= 28 && _hv.getUint32(0, true) === 0x46464952 /*RIFF*/) {
          _ttsSrcSR = _hv.getUint32(24, true);
        }
      } catch(_) { /* skip SR detection on malformed WAV header */ }
      const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
      window._lastTtsBuf = audioBuffer;  // Capture pour DSP
      // Afficher SR source réelle (edge-tts 48kHz) vs SR AudioContext (resampling browser)
      const _srDisp = document.getElementById('rack-stereo-sr');
      if (_srDisp) _srDisp.textContent = _ttsSrcSR + ' Hz';
      const source = audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      // Apply DSP speed & pitch (playbackRate changes both; detune adjusts pitch without speed)
      if (typeof _dspPlaybackRate !== 'undefined') source.playbackRate.value = _dspPlaybackRate;
      if (typeof _dspPitchSemi   !== 'undefined') source.detune.value = _dspPitchSemi * 100;
      // Connexion stéréo L/R + master analyser
      _connectStereoSource(source);
      _currentAudioSource = source;
      const myGen = _audioGen;
      source.start();
      source.onended = () => {
        _currentAudioSource = null;
        if (_audioGen === myGen) resolve(); // ignoré si stopAudio() a été appelé entre-temps
      };
    } catch(e) {
      resolve();
    }
  });
}

async function queueSpeech(text) {
  if (!ttsEnabled) return;
  speechQueue.push(text);
  if (!isPlaying) processQueue();
}

async function processQueue() {
  if (speechQueue.length === 0) {
    isPlaying = false;
    speaking = false;
    document.getElementById('jarvis-state').classList.remove('speaking');
    if (typeof window._mixAutoDuck === 'function') window._mixAutoDuck(false);
    _clearAllReplayBtns();
    _updateAudioBtn();
    // Restore waveform bar CSS animations
    document.querySelectorAll('.waveform span').forEach(bar => {
      bar.style.animation = '';
      bar.style.height = '';
    });
    // Reset reactor rings + speaking class
    document.querySelector('.reactor-wrap')?.classList.remove('reactor-speaking');
    const ring1 = document.querySelector('.reactor-ring-1');
    const ring2 = document.querySelector('.reactor-ring-2');
    const ring3 = document.querySelector('.reactor-ring-3');
    const reticle = document.querySelector('.reactor-reticle');
    const scan = document.querySelector('.reactor-scan');
    if (ring1) ring1.style.animationDuration = '';
    if (ring2) ring2.style.animationDuration = '';
    if (ring3) ring3.style.animationDuration = '';
    if (reticle) reticle.style.animationDuration = '';
    if (scan) scan.style.animationDuration = '';
    const core = document.querySelector('.reactor-core');
    if (core) core.style.opacity = '.08';
    const glow = document.querySelector('.reactor-glow');
    if (glow) glow.style.boxShadow = '';
    return;
  }
  isPlaying = true;
  speaking = true;
  document.getElementById('jarvis-state').classList.add('speaking');
  document.querySelector('.reactor-wrap')?.classList.add('reactor-speaking');
  if (typeof window._mixAutoDuck === 'function') window._mixAutoDuck(true);
  _updateAudioBtn();
  // Disable CSS animation on waveform bars so JS can drive them
  document.querySelectorAll('.waveform span').forEach(bar => {
    bar.style.animation = 'none';
  });
  const text = speechQueue.shift();
  // Resume AudioContext if suspended (browser autoplay policy)
  if (audioCtx && audioCtx.state === 'suspended') await audioCtx.resume();
  await playSentence(text);
  processQueue();
}

// ── Contrôle audio : Stop / Relecture ──────────────────────
function stopAudio() {
  _audioGen++; // invalide tout onended en attente
  speechQueue.length = 0;
  if (_currentAudioSource) {
    try { _currentAudioSource.stop(); } catch(e) {}
    _currentAudioSource = null;
  }
  isPlaying = false; speaking = false;
  document.getElementById('jarvis-state').classList.remove('speaking');
  document.querySelector('.reactor-wrap')?.classList.remove('reactor-speaking');
  if (typeof window._mixAutoDuck === 'function') window._mixAutoDuck(false);
  document.querySelectorAll('.waveform span').forEach(b => { b.style.animation = ''; b.style.height = ''; });
  const ring1 = document.querySelector('.reactor-ring-1');
  const ring2 = document.querySelector('.reactor-ring-2');
  const ring3 = document.querySelector('.reactor-ring-3');
  const reticle = document.querySelector('.reactor-reticle');
  if (ring1) ring1.style.animationDuration = '';
  if (ring2) ring2.style.animationDuration = '';
  if (ring3) ring3.style.animationDuration = '';
  if (reticle) reticle.style.animationDuration = '';
  const core = document.querySelector('.reactor-core');
  if (core) core.style.opacity = '.08';
  const glow = document.querySelector('.reactor-glow');
  if (glow) glow.style.boxShadow = '';
  _clearAllReplayBtns();
  _updateAudioBtn();
}

let _lastJarvisText = '';
let _activeReplayBtn = null; // bouton ▶ actuellement en lecture


function replayMessage(text, btn) {
  if (!text) return;
  // Bloqué si JARVIS est en train de streamer une réponse
  if (busy) return;
  // Reclique sur le bouton actif pendant lecture → stop
  if (btn && btn === _activeReplayBtn && isPlaying) {
    stopAudio();
    return;
  }
  // Reclique sur le bouton global pendant lecture → stop
  if (!btn && isPlaying) {
    stopAudio();
    return;
  }
  stopAudio(); // coupe tout + invalide onended
  if (btn) {
    _activeReplayBtn = btn;
    _setReplayBtnState(btn, true);
  }
  queueSpeech(text);
}

function _setAllReplayBusy(isBusy) {
  document.querySelectorAll('.msg-replay-btn').forEach(function(b) {
    b.classList.toggle('stream-busy', isBusy);
  });
}

function _setReplayBtnState(btn, playing) {
  if (!btn) return;
  btn.textContent = playing ? '⏹' : '▶';
  btn.classList.toggle('playing', playing);
}

function _clearAllReplayBtns() {
  document.querySelectorAll('.msg-replay-btn').forEach(b => _setReplayBtnState(b, false));
  _activeReplayBtn = null;
}

function _updateAudioBtn() {
  const btn = document.getElementById('btn-audio-stop');
  if (!btn) return;
  if (isPlaying) {
    btn.textContent = '⏹';
    btn.title = 'Arrêter la lecture audio';
    btn.classList.add('active');
  } else {
    btn.textContent = '▶';
    btn.title = 'Relire le dernier message';
    btn.classList.remove('active');
  }
}

// ── Spectral Analyzer canvas ─────────────────────────────────
const _sCanvas = document.getElementById('spectral-canvas');
const _sCtx    = _sCanvas ? _sCanvas.getContext('2d') : null;
const _sPeaks  = new Float32Array(48).fill(0); // peak hold per bar

function drawSpectral(active) {
  if (!_sCtx) return;
  const W = _sCanvas.offsetWidth || 200;
  const H = _sCanvas.offsetHeight || 52;
  if (_sCanvas.width !== W)  _sCanvas.width  = W;
  if (_sCanvas.height !== H) _sCanvas.height = H;

  // background
  _sCtx.clearRect(0, 0, W, H);
  _sCtx.fillStyle = '#010810';
  _sCtx.fillRect(0, 0, W, H);

  const BARS = 48;
  const gap  = 1;
  const bw   = (W - gap * (BARS - 1)) / BARS;

  for (let i = 0; i < BARS; i++) {
    let val;
    if (active) {
      // Use voice frequency data (first 80 bins = voice range)
      const binIdx = Math.floor(i * 80 / BARS);
      val = dataArray[binIdx] / 255;
    } else {
      // Idle: very subtle noise floor
      val = 0.02 + Math.random() * 0.04;
    }

    const barH = Math.max(1, val * H * 0.92);
    const x    = i * (bw + gap);

    // Peak hold
    if (val > _sPeaks[i]) _sPeaks[i] = val;
    else _sPeaks[i] = Math.max(0, _sPeaks[i] - 0.012);

    // Bar gradient: bottom=dark blue → top=cyan → tip=white when loud
    const grad = _sCtx.createLinearGradient(0, H, 0, H - barH);
    if (active && val > 0.6) {
      grad.addColorStop(0, '#003366');
      grad.addColorStop(0.5, '#00cfff');
      grad.addColorStop(1, '#ffffff');
    } else if (active) {
      grad.addColorStop(0, '#002244');
      grad.addColorStop(1, '#00cfff');
    } else {
      grad.addColorStop(0, '#001122');
      grad.addColorStop(1, '#00cfff22');
    }

    _sCtx.fillStyle = grad;
    _sCtx.fillRect(x, H - barH, bw, barH);

    // Peak dot
    if (active && _sPeaks[i] > 0.05) {
      const py = H - _sPeaks[i] * H * 0.92 - 1;
      _sCtx.fillStyle = _sPeaks[i] > 0.7 ? '#ffffff' : '#00cfff88';
      _sCtx.fillRect(x, py, bw, 1);
    }
  }

  // Glow overlay when speaking
  if (active) {
    const avg = dataArray.slice(0, 80).reduce((a, b) => a + b, 0) / 80;
    const gAlpha = (avg / 255) * 0.25;
    _sCtx.fillStyle = `rgba(0,207,255,${gAlpha})`;
    _sCtx.fillRect(0, 0, W, H);
  }
}

function visualize() {
  requestAnimationFrame(visualize);
  if (!analyser) return;
  analyser.getByteFrequencyData(dataArray);
  const avg  = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
  const norm = avg / 128;

  drawSpectral(speaking);
  // Reactor — actif en permanence (idle + speaking)
  _reactorDrive(norm, dataArray);

  if (!speaking) return;

  // Animate waveform bars with real frequency data
  const bars = document.querySelectorAll('.waveform span');
  bars.forEach((bar, i) => {
    const val = dataArray[i * 2] || 0;
    bar.style.height = Math.max(4, (val / 255) * 28) + 'px';
  });
}

// ── Système sonar réactif à la voix ──────────────────────────
var _rPeaks   = [];
var _rPrevNorm = 0;
var _rPeakCooldown = 0;
const _PEAK_THRESH   = 0.28;
const _PEAK_MIN_GAP  = 80;
const _PULSE_ELS = ['.reactor-pulse-1','.reactor-pulse-2','.reactor-pulse-3'];
const _R_MIN = 16, _R_MAX = 72;

// ── Visualiseur circulaire Canvas ──────────────────────────────
var _rvCtx = null;
var _rvCanvas = null;
var _rvIdlePhase = 0;
var _rvChevrons = null;
var _rvChevronFlash = 0;  // timestamp dernier flash

function _getChevrons() {
  if (_rvChevrons && _rvChevrons.length) return _rvChevrons;
  var grp = document.querySelector('.reactor-ring-1');
  if (!grp) return null;
  _rvChevrons = grp.querySelectorAll('polygon');
  return _rvChevrons.length ? _rvChevrons : null;
}

function _rvDrawIdle(ctx, cx, cy, innerR, N) {
  _rvIdlePhase += 0.0035;
  for (var s = 0; s < 4; s++) {
    var sA = _rvIdlePhase * 0.4 + s * Math.PI / 2;
    ctx.beginPath(); ctx.arc(cx, cy, innerR+10, sA, sA+0.7);
    ctx.strokeStyle = 'rgba(0,160,210,0.10)'; ctx.lineWidth = 7; ctx.stroke();
  }
  for (var i = 0; i < N; i++) {
    var angle = (i/N)*Math.PI*2 - Math.PI/2;
    var wave = 0.04 + Math.sin(_rvIdlePhase+i*0.18)*0.03 + Math.cos(_rvIdlePhase*0.7+i*0.3)*0.02;
    var len = Math.max(1, wave*26);
    ctx.beginPath();
    ctx.moveTo(cx+Math.cos(angle)*innerR, cy+Math.sin(angle)*innerR);
    ctx.lineTo(cx+Math.cos(angle)*(innerR+len), cy+Math.sin(angle)*(innerR+len));
    ctx.strokeStyle = 'rgba(0,180,220,'+(wave*5).toFixed(2)+')'; ctx.lineWidth = 1; ctx.stroke();
  }
}
function _rvDrawGlows({ ctx, cx, cy, innerR, outerR, norm, bassNorm, dataArray }) {
  if (bassNorm > 0.05) {
    var bassG = ctx.createRadialGradient(cx, cy, 0, cx, cy, innerR-4);
    bassG.addColorStop(0, 'rgba(0,240,255,'+(bassNorm*0.85).toFixed(2)+')');
    bassG.addColorStop(0.5, 'rgba(0,120,220,'+(bassNorm*0.45).toFixed(2)+')');
    bassG.addColorStop(1, 'rgba(0,0,100,0)');
    ctx.fillStyle = bassG; ctx.beginPath(); ctx.arc(cx, cy, innerR-4, 0, Math.PI*2); ctx.fill();
  }
  var gAlpha = norm*0.20;
  var grad = ctx.createRadialGradient(cx, cy, innerR-8, cx, cy, outerR+16);
  grad.addColorStop(0,   'rgba(80,230,255,'+(gAlpha*3.8).toFixed(2)+')');
  grad.addColorStop(0.3, 'rgba(0,207,255,'+(gAlpha*2.5).toFixed(2)+')');
  grad.addColorStop(0.7, 'rgba(0,80,180,'+gAlpha.toFixed(2)+')');
  grad.addColorStop(1,   'rgba(0,20,80,0)');
  ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(cx, cy, outerR+16, 0, Math.PI*2); ctx.fill();
  for (var s = 0; s < 8; s++) {
    var startA = (s/8)*Math.PI*2 - Math.PI/2, endA = ((s+0.82)/8)*Math.PI*2 - Math.PI/2;
    var sIdx0 = Math.floor(s*dataArray.length/8), sIdx1 = Math.floor((s+1)*dataArray.length/8);
    var sSum = 0; for (var si = sIdx0; si < sIdx1; si++) sSum += (dataArray[si]||0);
    var sAmp = sSum/((sIdx1-sIdx0)*255);
    if (sAmp > 0.12) {
      ctx.beginPath(); ctx.arc(cx, cy, innerR+6, startA, endA);
      ctx.lineWidth = Math.max(3, sAmp*14);
      ctx.strokeStyle = 'rgba(0,207,255,'+(sAmp*0.38).toFixed(2)+')';
      ctx.shadowBlur = 10; ctx.shadowColor = '#00cfff'; ctx.stroke(); ctx.shadowBlur = 0;
    }
  }
  ctx.beginPath(); ctx.arc(cx, cy, innerR, 0, Math.PI*2);
  ctx.strokeStyle = 'rgba(0,207,255,'+(0.32+norm*0.58).toFixed(2)+')'; ctx.lineWidth = 1.5;
  ctx.shadowBlur = 12; ctx.shadowColor = '#00cfff'; ctx.stroke(); ctx.shadowBlur = 0;
}
function _rvDrawFreqBars({ ctx, cx, cy, innerR, maxBar, N, dataArray }) {
  for (var i = 0; i < N; i++) {
    var angle = (i/N)*Math.PI*2 - Math.PI/2;
    var amp = (dataArray[Math.floor(i*dataArray.length/N)]||0)/255;
    var lenOut = Math.max(1.5, amp*maxBar), lenIn = Math.max(1, amp*(maxBar*0.42));
    var alpha = 0.18+amp*0.82, isFrac = i/N, rr, gg;
    if      (isFrac < 0.25) { rr = Math.round(amp*70);       gg = Math.round(185+amp*70); }
    else if (isFrac < 0.60) { rr = Math.round(amp*35);       gg = Math.round(205+amp*50); }
    else                    { rr = Math.round(120+amp*130);  gg = Math.round(220+amp*35); }
    var col = 'rgba('+rr+','+gg+',255,'+alpha.toFixed(2)+')';
    ctx.lineWidth = amp > 0.65 ? 2.5 : amp > 0.38 ? 2 : 1.5;
    ctx.shadowBlur = amp > 0.6 ? 14 : amp > 0.35 ? 6 : 2; ctx.shadowColor = '#00cfff';
    var xo1 = cx+Math.cos(angle)*innerR, yo1 = cy+Math.sin(angle)*innerR;
    ctx.beginPath(); ctx.moveTo(xo1, yo1);
    ctx.lineTo(cx+Math.cos(angle)*(innerR+lenOut), cy+Math.sin(angle)*(innerR+lenOut));
    ctx.strokeStyle = col; ctx.stroke();
    if (amp > 0.10) {
      ctx.beginPath(); ctx.moveTo(xo1, yo1);
      ctx.lineTo(cx+Math.cos(angle)*(innerR-lenIn), cy+Math.sin(angle)*(innerR-lenIn));
      ctx.strokeStyle = 'rgba('+rr+','+gg+',255,'+(alpha*0.42).toFixed(2)+')';
      ctx.lineWidth = 1; ctx.shadowBlur = 3; ctx.stroke();
    }
    if (amp > 0.58) {
      ctx.beginPath(); ctx.arc(cx+Math.cos(angle)*(innerR+lenOut), cy+Math.sin(angle)*(innerR+lenOut), 2.2, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(255,255,255,'+(amp*0.97).toFixed(2)+')';
      ctx.shadowBlur = 18; ctx.shadowColor = '#ffffff'; ctx.fill();
    }
  }
  ctx.shadowBlur = 0;
}
function _drawReactorViz(dataArray, norm) {
  if (!_rvCanvas) {
    _rvCanvas = document.getElementById('reactor-viz-canvas');
    if (!_rvCanvas) return;
    _rvCtx = _rvCanvas.getContext('2d');
  }
  var ctx = _rvCtx, W = _rvCanvas.width, H = _rvCanvas.height;
  var cx = W/2, cy = H/2, N = 128, innerR = 40;
  var maxBar = speaking ? Math.round(30+norm*28) : 30;
  var outerR = innerR+maxBar;
  ctx.clearRect(0, 0, W, H);
  if (!speaking) { _rvDrawIdle(ctx, cx, cy, innerR, N); return; }
  var bassSum = 0; for (var b = 0; b < 20; b++) bassSum += (dataArray[b]||0);
  var trebleSum = 0; for (var t = 80; t < N; t++) trebleSum += (dataArray[t]||0);
  var bassNorm = bassSum/(20*255), trebleNorm = trebleSum/(48*255);
  _rvDrawGlows({ ctx, cx, cy, innerR, outerR, norm, bassNorm, dataArray });
  _rvDrawFreqBars({ ctx, cx, cy, innerR, maxBar, N, dataArray });
  ctx.beginPath(); ctx.arc(cx, cy, outerR+2, 0, Math.PI*2);
  ctx.strokeStyle = 'rgba(0,207,255,'+(0.07+norm*0.22).toFixed(2)+')'; ctx.lineWidth = 1; ctx.stroke();
  if (trebleNorm > 0.18) {
    ctx.beginPath(); ctx.arc(cx, cy, outerR+7, 0, Math.PI*2);
    ctx.strokeStyle = 'rgba(190,245,255,'+(trebleNorm*0.55).toFixed(2)+')'; ctx.lineWidth = 0.8;
    ctx.shadowBlur = 8; ctx.shadowColor = '#aaddff'; ctx.stroke(); ctx.shadowBlur = 0;
  }
}

function _reactorIdleReset({ core, glow, ring1, ring2, ring3, reticle, scan }) {
  _rPeaks = [];
  _PULSE_ELS.forEach(function(sel) {
    var el = document.querySelector(sel);
    if (el) { el.setAttribute('r', _R_MIN); el.style.opacity = '0'; el.style.strokeWidth = ''; }
  });
  if (core)    core.style.opacity = '.06';
  if (glow)    glow.style.boxShadow = '';
  if (ring1)   ring1.style.animationDuration = '';
  if (ring2)   ring2.style.animationDuration = '';
  if (ring3)   ring3.style.animationDuration = '';
  if (reticle) reticle.style.animationDuration = '';
  if (scan)    scan.style.animationDuration = '';
  var chv = _getChevrons();
  if (chv) { for (var ci = 0; ci < chv.length; ci++) { chv[ci].setAttribute('opacity','0.35'); chv[ci].setAttribute('fill','#00cfff'); } }
}
function _reactorChevrons(now, norm, dataArray) {
  var chv = _getChevrons();
  if (!chv) return;
  var flashAge = now - _rvChevronFlash, flashDur = 120;
  for (var ci = 0; ci < chv.length; ci++) {
    var cFrac = ci/chv.length;
    var cAmp = (dataArray[Math.floor(cFrac*dataArray.length)]||0)/255;
    var cOp, cFill;
    if (flashAge < flashDur) {
      var fProg = flashAge/flashDur;
      cOp = (0.9-fProg*0.5).toFixed(2); cFill = fProg < 0.5 ? '#ffffff' : '#aaddff';
    } else {
      cOp = (0.2+(norm*0.55)+(cAmp*0.25)).toFixed(2); cFill = norm > 0.65 ? '#aaddff' : '#00cfff';
    }
    chv[ci].setAttribute('opacity', cOp); chv[ci].setAttribute('fill', cFill);
  }
}
function _reactorCoreGlow(core, glow, norm) {
  if (core) {
    var peakFlash = _rPeaks.length > 0 ? _rPeaks[0].intensity*0.35 : 0;
    core.style.opacity = Math.min(0.88, 0.05+norm*0.6+peakFlash).toFixed(2);
    core.setAttribute('r', (14+norm*11).toFixed(1));
    core.setAttribute('fill', norm > 0.65 ? '#aaddff' : '#00cfff');
  }
  if (glow) {
    var gi = (10+norm*40).toFixed(0), gs = (32+norm*30).toFixed(0);
    var ga = Math.floor(norm*230).toString(16).padStart(2,'0');
    glow.style.width = gs+'px'; glow.style.height = gs+'px';
    glow.style.boxShadow = ['0 0 '+gi+'px '+Math.round(gi/2)+'px #00cfff'+ga,'0 0 '+(gi*2)+'px '+gi+'px #00cfff55','0 0 '+(gi*4)+'px '+(gi*1.5)+'px #00cfff28','0 0 '+(gi*6)+'px '+(gi*2)+'px #00cfff14'].join(',');
  }
}
function _reactorDrive(norm, dataArray) {
  _drawReactorViz(dataArray, norm);
  var now = performance.now();
  var glow = document.querySelector('.reactor-glow'), core = document.querySelector('.reactor-core');
  var ring1 = document.querySelector('.reactor-ring-1'), ring2 = document.querySelector('.reactor-ring-2');
  var ring3 = document.querySelector('.reactor-ring-3'), reticle = document.querySelector('.reactor-reticle');
  var scan = document.querySelector('.reactor-scan');
  if (!speaking) { _reactorIdleReset({ core, glow, ring1, ring2, ring3, reticle, scan }); return; }
  var rising = norm > _rPrevNorm+0.04;
  if (rising && norm > _PEAK_THRESH && now-_rPeakCooldown > _PEAK_MIN_GAP) {
    _rPeaks.push({t:now, dur:350+(1-norm)*280, intensity:norm});
    _rPeakCooldown = now; _rvChevronFlash = now;
  }
  _rPrevNorm = norm;
  _rPeaks = _rPeaks.filter(function(p) { return now-p.t < p.dur; });
  _PULSE_ELS.forEach(function(sel, i) {
    var el = document.querySelector(sel); if (!el) return;
    var peak = _rPeaks[i];
    if (!peak) { el.style.opacity = '0'; el.setAttribute('r', _R_MIN); return; }
    var progress = (now-peak.t)/peak.dur;
    el.setAttribute('r', (_R_MIN+progress*(_R_MAX-_R_MIN)).toFixed(1));
    el.style.opacity = ((1-progress)*Math.min(1,peak.intensity*1.4)).toFixed(2);
    el.style.strokeWidth = (2.5-progress*2.2).toFixed(1)+'px';
  });
  _reactorChevrons(now, norm, dataArray);
  _reactorCoreGlow(core, glow, norm);
  if (ring1)   ring1.style.animationDuration   = Math.max(0.6, 6-norm*5)+'s';
  if (ring2)   ring2.style.animationDuration   = Math.max(0.3, 4-norm*3.4)+'s';
  if (ring3)   ring3.style.animationDuration   = Math.max(0.2, 2.5-norm*2)+'s';
  if (reticle) reticle.style.animationDuration = Math.max(0.45, 8-norm*7.2)+'s';
  if (scan)    scan.style.animationDuration    = Math.max(0.25, 2.5-norm*2.2)+'s';
}
visualize();
