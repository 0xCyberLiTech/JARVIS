// ══════════════════════════════════════════════════════════════
// EQ PARAMÉTRIQUE — Courbe de réponse & analyseur spectral
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// EQ paramétrique de la voix JARVIS : courbe de réponse (canvas), analyseur
// spectral, grilles dB/fréquence, poignées de bandes, mémoires EQ (10 slots
// localStorage), couplage EQ ↔ voix. Fichier .js classique (scope global).
// Chargé APRÈS jarvis_main.js.

const EQ_SR = _SAMPLE_RATE;  // match Python DSP (edge-tts 48kHz)
// ── Spectrum analyzer state ──
let _specMode    = 'fill';
let _specFftSize = 4096;
let _specPeaks   = null;
let _wfCanvas    = null;
let _wfCtx2      = null;
let _specLogAxis  = false;  // axe fréquences logarithmique
let _specPeakVis  = true;   // afficher caps peak hold
let _specGridVis  = true;   // afficher grille dB
let _specGhostOn  = false;  // traces persistantes (ghost frames)
let _specGhostBuf = [];     // anneau de frames passées

function setRackSpecMode(mode) {
  _rackSpecMode = mode;
  ['mirror','scope','piano','split'].forEach(m => {
    const btn = document.getElementById('rspec-' + m);
    if (btn) btn.classList.toggle('active', m === mode);
  });
}

function setSpecMode(mode) {
  _specMode = mode;
  document.querySelectorAll('.spec-mode-btn[data-mode]').forEach(b =>
    b.classList.toggle('active', b.dataset.mode === mode));
  // Reset canvas when leaving persistent modes
  if (mode !== 'waterfall') { _wfCanvas = null; _wfCtx2 = null; }
  if (mode !== 'dots') {
    const cv = document.getElementById('dsp-canvas');
    if (cv) { cv.width = cv.offsetWidth; cv.height = cv.offsetHeight; }
  }
  // Static freq-labels strip only useful for classic bar/line modes
  const fl = document.querySelector('.dsp-freq-labels');
  _disp(fl, ['bars','line','fill','mirror'].includes(mode));
}

function setSpecFft(size) {
  _specFftSize = size;
  if (_dspAnalyser) {
    _dspAnalyser.fftSize = size;
    _dspDataArray = new Uint8Array(_dspAnalyser.frequencyBinCount);
    _specPeaks = null;
  }
  const lbl = document.getElementById('spec-fft-label');
  if (lbl) lbl.textContent = '◈ SPECTRAL ANALYZER — FFT ' + size;
  document.querySelectorAll('.spec-mode-btn[data-fft]').forEach(b =>
    b.classList.toggle('active', parseInt(b.dataset.fft) === size));
}

// Waterfall thermal color map
function _wfColor(v) {
  if (v < 0.01) return '#000508';
  if (v < 0.20) { const t = v / 0.20; return `rgb(0,0,${Math.round(t * 170)})`; }
  if (v < 0.40) { const t = (v-0.20)/0.20; return `rgb(0,${Math.round(t*150)},${Math.round(170*(1-t))})`; }
  if (v < 0.60) { const t = (v-0.40)/0.20; return `rgb(0,${Math.round(150+t*105)},0)`; }
  if (v < 0.80) { const t = (v-0.60)/0.20; return `rgb(${Math.round(t*255)},255,0)`; }
  const t = (v-0.80)/0.20; return `rgb(255,${Math.round(255-t*205)},${Math.round(t*50)})`;
}

// ── EQ ghost curve (peak hold) ──
let _eqGhost      = null;  // Float32Array: combined curve snapshot
let _eqGhostAlpha = 0;     // 0..1, decays each RAF frame
let _eqLastCombined = null; // previous combined array for ghost capture

// Mutable EQ band state (freq, Q, type, bypassed) — updated by drag/wheel/type buttons
const _eqState = [
  { freq:80,   q:0.7, type:'lowshelf',  bypassed:false, gain:0 },
  { freq:315,  q:0.8, type:'peaking',   bypassed:false, gain:0 },
  { freq:1250, q:0.9, type:'highshelf', bypassed:false, gain:0 },
  { freq:5000, q:0.7, type:'highshelf', bypassed:false, gain:0 },
];
// Frequency range limits per band [min, max]
const _eqFreqRange = [[20,400],[100,2000],[500,8000],[2000,24000]];

// Canvas drag state
let _eqDrag = null; // { idx, startFreq, startGain }

const EQ_BANDS = [
  { id:'low',  freq:80,   type:'lowshelf',  Q:0.7, color:_cssVar('--blue'),   label:'LOW' },
  { id:'mid',  freq:315,  type:'peaking',   Q:0.8, color:_cssVar('--cyan'),   label:'MID' },
  { id:'high', freq:1250, type:'highshelf', Q:0.9, color:_cssVar('--green'),  label:'HIGH' },
  { id:'air',  freq:5000, type:'highshelf', Q:0.7, color:_cssVar('--purple'), label:'AIR' },
];

function eqBqCoeffs(type, freq, gainDb, Q) {
  const A   = Math.pow(10, gainDb / 40);
  const w0  = 2 * Math.PI * freq / EQ_SR;
  const cosw= Math.cos(w0), sinw = Math.sin(w0);
  let b0,b1,b2,a0,a1,a2;
  if (type === 'lowshelf') {
    const alpha = sinw * Math.sqrt(2 * A) / 2;
    b0 =  A*((A+1)-(A-1)*cosw+2*Math.sqrt(A)*alpha);
    b1 =2*A*((A-1)-(A+1)*cosw);
    b2 =  A*((A+1)-(A-1)*cosw-2*Math.sqrt(A)*alpha);
    a0 =    (A+1)+(A-1)*cosw+2*Math.sqrt(A)*alpha;
    a1 = -2*((A-1)+(A+1)*cosw);
    a2 =    (A+1)+(A-1)*cosw-2*Math.sqrt(A)*alpha;
  } else if (type === 'highshelf') {
    const alpha = sinw * Math.sqrt(2 * A) / 2;
    b0 =  A*((A+1)+(A-1)*cosw+2*Math.sqrt(A)*alpha);
    b1 =-2*A*((A-1)+(A+1)*cosw);
    b2 =  A*((A+1)+(A-1)*cosw-2*Math.sqrt(A)*alpha);
    a0 =    (A+1)-(A-1)*cosw+2*Math.sqrt(A)*alpha;
    a1 =  2*((A-1)-(A+1)*cosw);
    a2 =    (A+1)-(A-1)*cosw-2*Math.sqrt(A)*alpha;
  } else if (type === 'highpass') {
    const qv = Q || 0.7071;
    const alpha = sinw / (2 * qv);
    b0 = (1+cosw)/2; b1 = -(1+cosw); b2 = (1+cosw)/2;
    a0 = 1+alpha; a1 = -2*cosw; a2 = 1-alpha;
  } else if (type === 'lowpass') {
    const qv = Q || 0.7071;
    const alpha = sinw / (2 * qv);
    b0 = (1-cosw)/2; b1 = 1-cosw; b2 = (1-cosw)/2;
    a0 = 1+alpha; a1 = -2*cosw; a2 = 1-alpha;
  } else if (type === 'notch') {
    const alpha = sinw / (2 * (Q || 0.8));
    b0 = 1; b1 = -2*cosw; b2 = 1;
    a0 = 1+alpha; a1 = -2*cosw; a2 = 1-alpha;
  } else if (type === 'bandpass') {
    const alpha = sinw / (2 * (Q || 0.8));
    b0 = sinw/2; b1 = 0; b2 = -sinw/2;
    a0 = 1+alpha; a1 = -2*cosw; a2 = 1-alpha;
  } else { // peaking (default)
    const alpha = sinw / (2 * (Q || 0.8));
    b0 = 1 + alpha * A;  b1 = -2*cosw;  b2 = 1 - alpha * A;
    a0 = 1 + alpha / A;  a1 = -2*cosw;  a2 = 1 - alpha / A;
  }
  return { b:[b0/a0, b1/a0, b2/a0], a:[1, a1/a0, a2/a0] };
}

function eqBqResponse(coeff, freq) {
  const w  = 2 * Math.PI * freq / EQ_SR;
  const cr = Math.cos(w), ci = Math.sin(w);
  const c2r = Math.cos(2*w), c2i = Math.sin(2*w);
  // numerator H(e^jw) = b0 + b1*e^-jw + b2*e^-2jw
  const nr = coeff.b[0] + coeff.b[1]*cr  + coeff.b[2]*c2r;
  const ni =               coeff.b[1]*ci  + coeff.b[2]*c2i;  // note: e^-jw → cos-jsin but we use +sin for inverse
  const dr = coeff.a[0] + coeff.a[1]*cr  + coeff.a[2]*c2r;
  const di =               coeff.a[1]*ci  + coeff.a[2]*c2i;
  const mag2 = (nr*nr + ni*ni) / (dr*dr + di*di);
  return 20 * Math.log10(Math.max(1e-10, Math.sqrt(mag2)));
}

function _eqDrawBackground(lp){
  const {ctx,W,H,ML,MR,MT,MB,PW,PH}=lp;
  const bgGrd=ctx.createRadialGradient(W/2,H/2,10,W/2,H/2,W*0.75);
  bgGrd.addColorStop(0,'#030e18'); bgGrd.addColorStop(1,'#010810');
  ctx.fillStyle=bgGrd; ctx.fillRect(0,0,W,H);
  const vig=ctx.createRadialGradient(W/2,H/2,PW*0.3,W/2,H/2,W*0.65);
  vig.addColorStop(0,'rgba(0,0,0,0)'); vig.addColorStop(1,'rgba(0,0,0,.55)');
  ctx.fillStyle=vig; ctx.fillRect(0,0,W,H);
  for(let y=MT;y<H-MB;y+=3){ctx.fillStyle='rgba(0,0,0,.08)';ctx.fillRect(ML,y,PW,1);}
}
function _eqDrawLiveSpectrum(lp){
  const {ctx,W,ML,MR,MT,MB,PW,PH,fMin,fMax}=lp;
  const hasData=typeof _dspDataArray!=='undefined'&&_dspDataArray&&_dspDataArray.length>0;
  const N=hasData?_dspDataArray.length:1024;
  const nyq=(typeof audioCtx!=='undefined'&&audioCtx?audioCtx.sampleRate:_SAMPLE_RATE)/2;
  if(!window._eqSpecPeaks||window._eqSpecPeaks.length!==W) window._eqSpecPeaks=new Float32Array(W);
  const peaks=window._eqSpecPeaks, sp=SPEC_PRESETS[window._eqSpecPreset]||SPEC_PRESETS.jarvis;
  ctx.beginPath(); let first=true;
  for(let px=ML;px<=W-MR;px++){
    let val=0.04;
    if(hasData){const f=fMin*Math.pow(fMax/fMin,(px-ML)/PW);const bin=Math.min(Math.round(f/nyq*N),N-1);val=Math.max(_dspDataArray[bin]/255,0.04);}
    peaks[px]=Math.max(peaks[px]*0.993,val);
    const sy=MT+PH*(1-val);
    if(first){ctx.moveTo(px,MT+PH);ctx.lineTo(px,sy);first=false;}else ctx.lineTo(px,sy);
  }
  ctx.lineTo(W-MR,MT+PH); ctx.closePath();
  const gSpec=ctx.createLinearGradient(0,MT,0,MT+PH);
  gSpec.addColorStop(0,sp.top); gSpec.addColorStop(0.45,sp.mid); gSpec.addColorStop(1,sp.bot);
  ctx.fillStyle=gSpec; ctx.fill();
  ctx.beginPath(); ctx.strokeStyle=sp.peak; ctx.lineWidth=1; first=true;
  for(let px=ML;px<=W-MR;px++){const sy=MT+PH*(1-peaks[px]);first?(ctx.moveTo(px,sy),first=false):ctx.lineTo(px,sy);}
  ctx.stroke();
}
function _eqDrawDbGrid(lp){
  const {ctx,W,ML,MR,MT,MB,PW,PH,dbToY}=lp;
  [-12,-9,-6,-3,-1,0,1,3,6,9,12].forEach(db=>{
    const y=dbToY(db),isZero=db===0,isMajor=db%3===0;
    ctx.strokeStyle=isZero?'rgba(255,255,255,.18)':isMajor?'rgba(0,180,220,.07)':'rgba(0,150,180,.03)';
    ctx.lineWidth=isZero?1.5:isMajor?0.8:0.4;
    ctx.setLineDash(isZero?[]:isMajor?[4,6]:[1,8]);
    ctx.beginPath(); ctx.moveTo(ML,y); ctx.lineTo(W-MR,y); ctx.stroke(); ctx.setLineDash([]);
  });
  ctx.font='9px Share Tech Mono'; ctx.textAlign='right';
  [-12,-9,-6,-3,0,3,6,9,12].forEach(db=>{
    const y=dbToY(db),lbl=(db>0?'+':'')+db;
    ctx.strokeStyle=db===0?'rgba(255,255,255,.3)':'rgba(0,180,220,.2)'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(ML-4,y); ctx.lineTo(ML,y); ctx.stroke();
    ctx.fillStyle=db===0?'rgba(255,255,255,.55)':'rgba(0,200,240,.35)'; ctx.fillText(lbl,ML-6,y+3);
  });
  ctx.save(); ctx.translate(10,MT+PH/2); ctx.rotate(-Math.PI/2);
  ctx.font='7px Orbitron'; ctx.textAlign='center'; ctx.fillStyle='rgba(0,180,220,.2)'; ctx.fillText('dBFS',0,0);
  ctx.restore();
  ctx.font='9px Share Tech Mono'; ctx.textAlign='left';
  [-12,-9,-6,-3,0,3,6,9,12].forEach(db=>{
    const y=dbToY(db);
    ctx.strokeStyle=db===0?'rgba(255,255,255,.3)':'rgba(0,180,220,.2)'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(W-MR,y); ctx.lineTo(W-MR+4,y); ctx.stroke();
    ctx.fillStyle=db===0?'rgba(255,255,255,.55)':'rgba(0,200,240,.35)';
    ctx.fillText((db>0?'+':'')+db,W-MR+6,y+3);
  });
}
function _eqDrawFreqGrid(lp){
  const {ctx,W,H,ML,MR,MT,MB,freqToX}=lp;
  const fMajor=[50,100,200,500,1000,2000,5000,10000,20000,24000];
  const fMinor=[30,70,150,300,700,1500,3000,7000,15000,18000];
  const fLbls={50:'50',100:'100',200:'200',500:'500',1000:'1k',2000:'2k',5000:'5k',10000:'10k',20000:'20k',24000:'24k'};
  fMinor.forEach(f=>{
    const x=freqToX(f); if(x<ML||x>W-MR) return;
    ctx.strokeStyle='rgba(0,150,180,.04)'; ctx.lineWidth=0.5; ctx.setLineDash([1,8]);
    ctx.beginPath(); ctx.moveTo(x,MT); ctx.lineTo(x,H-MB); ctx.stroke(); ctx.setLineDash([]);
  });
  fMajor.forEach(f=>{
    const x=freqToX(f); if(x<ML||x>W-MR) return;
    ctx.strokeStyle='rgba(0,170,210,.07)'; ctx.lineWidth=0.8; ctx.setLineDash([3,7]);
    ctx.beginPath(); ctx.moveTo(x,MT); ctx.lineTo(x,H-MB); ctx.stroke(); ctx.setLineDash([]);
    ctx.strokeStyle='rgba(0,180,220,.3)'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(x,H-MB); ctx.lineTo(x,H-MB+4); ctx.stroke();
    ctx.font='9px Share Tech Mono'; ctx.textAlign='center'; ctx.fillStyle='rgba(0,200,240,.38)';
    ctx.fillText(fLbls[f],x,H-5);
  });
  ctx.font='7px Orbitron'; ctx.textAlign='right'; ctx.fillStyle='rgba(0,180,220,.2)'; ctx.fillText('Hz',W-MR-2,H-5);
  ctx.strokeStyle='rgba(0,100,140,.25)'; ctx.lineWidth=1; ctx.strokeRect(ML-0.5,MT-0.5,lp.PW+1,lp.PH+1);
  ctx.strokeStyle='rgba(0,180,220,.08)'; ctx.lineWidth=1; ctx.strokeRect(ML,MT,lp.PW,lp.PH);
}
function _eqDrawBandCurves(lp, freqs){
  const {ctx,ML,MR,dbMin,dbMax,fMin,fMax,freqToX,dbToY}=lp;
  if(_eqGhost&&_eqGhostAlpha>0){
    ctx.beginPath(); ctx.strokeStyle='rgba(0,207,255,'+(_eqGhostAlpha*0.5).toFixed(3)+')';
    ctx.lineWidth=1.5; ctx.setLineDash([6,4]);
    _eqGhost.forEach((db,i)=>{const x=freqToX(freqs[i]),y=dbToY(Math.max(dbMin,Math.min(dbMax,db)));i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
    ctx.stroke(); ctx.setLineDash([]);
  }
  EQ_BANDS.forEach((band,i)=>{
    if(_eqState[i].bypassed) return;
    const gainDb=_eqState[i].gain, noGainType=['highpass','lowpass','notch','bandpass'].includes(_eqState[i].type);
    if(!noGainType&&Math.abs(gainDb)<0.05) return;
    const coeff=eqBqCoeffs(_eqState[i].type,_eqState[i].freq,gainDb,_eqState[i].q);
    ctx.beginPath();
    freqs.forEach((f,fi)=>{const db=eqBqResponse(coeff,f);const x=freqToX(f),y=dbToY(Math.max(dbMin,Math.min(dbMax,db)));fi===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
    ctx.lineTo(freqToX(fMax),dbToY(0)); ctx.lineTo(freqToX(fMin),dbToY(0)); ctx.closePath();
    ctx.fillStyle=band.color+'18'; ctx.fill();
    ctx.beginPath(); ctx.strokeStyle=band.color+'44'; ctx.lineWidth=1;
    freqs.forEach((f,fi)=>{const db=eqBqResponse(coeff,f);const x=freqToX(f),y=dbToY(Math.max(dbMin,Math.min(dbMax,db)));fi===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
    ctx.stroke();
  });
}
function _eqDrawCombinedCurve(lp, freqs, combined){
  const {ctx,dbMin,dbMax,freqToX,dbToY}=lp;
  const N=freqs.length, zeroY=dbToY(0);
  combined.forEach((db,i)=>{
    const x0=freqToX(freqs[i]),x1=i<N-1?freqToX(freqs[i+1]):x0+1,y=dbToY(Math.max(dbMin,Math.min(dbMax,db)));
    if(db>0.1){
      const grd=ctx.createLinearGradient(0,y,0,zeroY);
      grd.addColorStop(0,'rgba(0,207,255,0.28)');grd.addColorStop(0.5,'rgba(0,160,220,0.12)');grd.addColorStop(1,'rgba(0,80,140,0.03)');
      ctx.fillStyle=grd;ctx.fillRect(x0,y,x1-x0,zeroY-y);
    }else if(db<-0.1){
      const grd=ctx.createLinearGradient(0,zeroY,0,y);
      grd.addColorStop(0,'rgba(0,100,200,0.22)');grd.addColorStop(1,'rgba(0,40,120,0.03)');
      ctx.fillStyle=grd;ctx.fillRect(x0,zeroY,x1-x0,y-zeroY);
    }
  });
  ctx.shadowColor='#00cfff'; ctx.shadowBlur=10;
  ctx.beginPath(); ctx.strokeStyle='#00cfff'; ctx.lineWidth=2;
  combined.forEach((db,i)=>{const x=freqToX(freqs[i]),y=dbToY(Math.max(dbMin,Math.min(dbMax,db)));i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
  ctx.stroke(); ctx.shadowBlur=0;
}
function _eqDrawHandles(lp){
  const {ctx,dbMin,dbMax,freqToX,dbToY}=lp;
  EQ_BANDS.forEach((band,i)=>{
    const noGainT=['highpass','lowpass','notch','bandpass'].includes(_eqState[i].type);
    const gainDb=(_eqState[i].bypassed||noGainT)?0:_eqState[i].gain;
    const x=freqToX(_eqState[i].freq),y=dbToY(Math.max(dbMin,Math.min(dbMax,gainDb)));
    if(_eqState[i].bypassed){
      ctx.beginPath(); ctx.arc(x,y,7,0,Math.PI*2); ctx.fillStyle='#1a1a2a'; ctx.fill();
      ctx.strokeStyle='#333'; ctx.lineWidth=1; ctx.stroke();
      ctx.fillStyle='#444'; ctx.font='bold 8px Orbitron'; ctx.textAlign='center'; ctx.fillText(i+1,x,y+3);
      return;
    }
    ctx.beginPath(); ctx.arc(x,y,11,0,Math.PI*2); ctx.fillStyle=band.color+'20'; ctx.fill();
    ctx.beginPath(); ctx.arc(x,y,8,0,Math.PI*2); ctx.fillStyle=band.color; ctx.fill();
    ctx.strokeStyle='#000810'; ctx.lineWidth=1.5; ctx.stroke();
    ctx.fillStyle='#fff'; ctx.font='bold 8px Orbitron'; ctx.textAlign='center'; ctx.fillText(i+1,x,y+3);
    const lbl=(gainDb>=0?'+':'')+gainDb.toFixed(1);
    ctx.font='bold 7px Share Tech Mono'; ctx.fillStyle='#ffcc44';
    ctx.fillText(lbl,x,gainDb>=0?y-13:y+20);
  });
}
function _eqDrawHover(lp, freqs, combined){
  const {ctx,W,H,ML,MR,MT,MB,PW,fMin,fMax}=lp;
  if(_eqHoverX===null||_eqHoverX<ML||_eqHoverX>W-MR) return;
  const N=freqs.length, hoverFreq=fMin*Math.pow(fMax/fMin,(_eqHoverX-ML)/PW);
  ctx.strokeStyle='#ffffff18'; ctx.lineWidth=1; ctx.setLineDash([3,3]);
  ctx.beginPath(); ctx.moveTo(_eqHoverX,MT); ctx.lineTo(_eqHoverX,H-MB); ctx.stroke(); ctx.setLineDash([]);
  const hIdx=Math.round((_eqHoverX-ML)/PW*(N-1)), hDb=combined[Math.max(0,Math.min(N-1,hIdx))]||0;
  const label=(hoverFreq<1000?hoverFreq.toFixed(0)+' Hz':(hoverFreq/1000).toFixed(2)+' kHz')+'  '+(hDb>=0?'+':'')+hDb.toFixed(1)+' dB';
  ctx.fillStyle='#00cfff99'; ctx.font='9px Share Tech Mono'; ctx.textAlign='left';
  ctx.fillText(label,_eqHoverX+6>W-120?_eqHoverX-130:_eqHoverX+6,MT+14);
}
function drawEqCurve() {
  const canvas = document.getElementById('eq-curve-canvas');
  if (!canvas) return;
  const W=canvas.width=canvas.offsetWidth||600, H=canvas.height=canvas.offsetHeight||200;
  const ctx=canvas.getContext('2d');
  const ML=42,MR=42,MT=14,MB=22, PW=W-ML-MR, PH=H-MT-MB;
  const dbMin=-15,dbMax=15,fMin=20,fMax=24000;
  const freqToX=f=>ML+PW*Math.log10(f/fMin)/Math.log10(fMax/fMin);
  const dbToY=db=>MT+PH*(1-(db-dbMin)/(dbMax-dbMin));
  const lp={ctx,W,H,ML,MR,MT,MB,PW,PH,dbMin,dbMax,fMin,fMax,freqToX,dbToY};
  _eqDrawBackground(lp);
  _eqDrawLiveSpectrum(lp);
  _eqDrawDbGrid(lp);
  _eqDrawFreqGrid(lp);
  const N=512;
  const freqs=Array.from({length:N},(_,i)=>fMin*Math.pow(fMax/fMin,i/(N-1)));
  _eqDrawBandCurves(lp,freqs);
  const combined=freqs.map(f=>EQ_BANDS.reduce((sum,band,i)=>{
    if(_eqState[i].bypassed) return sum;
    const g=_eqState[i].gain,ngt=['highpass','lowpass','notch','bandpass'].includes(_eqState[i].type);
    if(!ngt&&Math.abs(g)<0.05) return sum;
    return sum+eqBqResponse(eqBqCoeffs(_eqState[i].type,_eqState[i].freq,g,_eqState[i].q),f);
  },0));
  _eqLastCombined=new Float32Array(combined);
  _eqDrawCombinedCurve(lp,freqs,combined);
  _eqDrawHandles(lp);
  _eqDrawHover(lp,freqs,combined);
}

let _eqHoverX = null;

function eqReset() {
  EQ_BANDS.forEach(b => {
    const sl = document.getElementById('eq-'+b.id);
    if (sl) sl.value = 0;
    setEqBand(b.id, 0);
  });
}

// ── Mémoires EQ (10 slots, localStorage) ─────────────────────
const _EQ_MEM_KEY = 'jarvis_eq_mem';
const _EQ_MEM_HOLD = 800; // ms clic long = sauvegarde
let _eqMemTimer = null;
let _eqMemSlots = Array(10).fill(null);

function _eqMemLoad() {
  try { _eqMemSlots = JSON.parse(localStorage.getItem(_EQ_MEM_KEY)) || Array(10).fill(null); }
  catch(_) { _eqMemSlots = Array(10).fill(null); }
  _eqMemSlots.forEach((s, i) => _eqMemUpdateBtn(i));
}

function _eqMemSave() {
  localStorage.setItem(_EQ_MEM_KEY, JSON.stringify(_eqMemSlots));
}

function _eqMemSnapshot() {
  return EQ_BANDS.map((b, i) => ({
    id:       b.id,
    gain:     _eqState[i].gain,
    freq:     _eqState[i].freq,
    q:        _eqState[i].q,
    type:     _eqState[i].type,
    bypassed: _eqState[i].bypassed,
  }));
}

function _eqMemApply(snap) {
  snap.forEach((s, i) => {
    _eqState[i].freq     = s.freq;
    _eqState[i].q        = s.q;
    _eqState[i].type     = s.type;
    _eqState[i].bypassed = s.bypassed;
    const sl = document.getElementById('eq-'+s.id);
    if (sl) sl.value = s.gain;
    setEqBand(s.id, s.gain);
    // freq/Q/type counters
    const fc = document.getElementById('eq-fc-'+s.id);
    const gc = document.getElementById('eq-gc-'+s.id);
    const qc = document.getElementById('eq-qc-'+s.id);
    if (fc) fc.textContent = s.freq >= 1000 ? (s.freq/1000).toFixed(1)+'kHz' : s.freq+'Hz';
    if (gc) gc.textContent = (s.gain >= 0 ? '+' : '') + parseFloat(s.gain).toFixed(1);
    if (qc) qc.textContent = parseFloat(s.q).toFixed(1);
    // bypass state
    const byp = document.getElementById('eq-byp-'+s.id);
    if (byp) { byp.classList.toggle('bypassed', s.bypassed); }
    // type buttons
    document.querySelectorAll(`[data-band="${s.id}"]`).forEach(tb => {
      tb.classList.toggle('active', tb.dataset.type === s.type);
    });
  });
  if (typeof eqPushNow === 'function') eqPushNow();
}

function _eqMemUpdateBtn(idx) {
  const btn = document.getElementById('eq-mem-btn-'+idx);
  if (!btn) return;
  const filled = _eqMemSlots[idx] !== null;
  btn.classList.toggle('filled', filled);
  if (filled && _eqMemSlots[idx]._label) btn.title = _eqMemSlots[idx]._label;
}

function eqMemPress(idx) {
  const btn = document.getElementById('eq-mem-btn-'+idx);
  if (btn) {
    btn.classList.add('pressing');
    btn.style.transition = `--dummy 0s`; // force reflow
    btn.style.setProperty('transition', 'width ' + _EQ_MEM_HOLD + 'ms linear');
  }
  _eqMemTimer = setTimeout(() => {
    _eqMemTimer = null;
    // SAUVEGARDE
    const snap = _eqMemSnapshot();
    snap._label = 'M' + (idx+1) + ' — ' + new Date().toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
    _eqMemSlots[idx] = snap;
    _eqMemSave();
    if (btn) { btn.classList.remove('pressing'); btn.classList.add('saving'); }
    setTimeout(() => { if (btn) btn.classList.remove('saving'); _eqMemUpdateBtn(idx); }, 600);
  }, _EQ_MEM_HOLD);
}

function eqMemRelease(idx) {
  if (_eqMemTimer) {
    clearTimeout(_eqMemTimer);
    _eqMemTimer = null;
    const btn = document.getElementById('eq-mem-btn-'+idx);
    if (btn) btn.classList.remove('pressing');
    // RAPPEL (clic court)
    if (_eqMemSlots[idx]) {
      _eqMemApply(_eqMemSlots[idx]);
      // highlight actif
      document.querySelectorAll('.eq-mem-btn').forEach(b => b.classList.remove('active-mem'));
      if (btn) btn.classList.add('active-mem');
    }
  }
}

function eqMemClear(idx) {
  _eqMemSlots[idx] = null;
  _eqMemSave();
  _eqMemUpdateBtn(idx);
  const btn = document.getElementById('eq-mem-btn-'+idx);
  if (btn) btn.classList.remove('active-mem');
}

// → _jarvisInit()

// ── Couplage EQ ↔ Voix JARVIS ──
let _eqVoiceCoupled = true;  // actif par défaut

function toggleEqVoiceCouple() {
  _eqVoiceCoupled = !_eqVoiceCoupled;
  _updateEqCoupleBadges();
  // Envoyer enabled au backend
  fetch('/api/dsp-params', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ enabled: _eqVoiceCoupled })
  }).catch(()=>{});
  if (_eqVoiceCoupled) queueSpeech('Égaliseur couplé à la voix.');
}

// ── Découplage voix JARVIS / chaîne DSP ──────────────────────
function toggleDspVoice() {
  _dspVoiceDecoupled = !_dspVoiceDecoupled;
  const ac = audioCtx;
  if (ac && _jarvisPreGain && _dspVoiceBypass) {
    const now = ac.currentTime;
    if (_dspVoiceDecoupled) {
      // Voix → sortie directe (bypass DSP)
      _jarvisPreGain.gain.setTargetAtTime(0, now, 0.02);
      _dspVoiceBypass.gain.setTargetAtTime(1, now, 0.02);
    } else {
      // Voix → chaîne DSP (mode normal)
      _jarvisPreGain.gain.setTargetAtTime(1, now, 0.02);
      _dspVoiceBypass.gain.setTargetAtTime(0, now, 0.02);
    }
  }
  // Mise à jour boutons
  const btn = document.getElementById('dsp-voice-decouple-btn');
  if (btn) {
    btn.classList.toggle('dsp-voice-decoupled', _dspVoiceDecoupled);
    btn.title = _dspVoiceDecoupled
      ? 'Voix JARVIS découplée du DSP — cliquer pour recoupler'
      : 'Voix JARVIS couplée au DSP — cliquer pour découpler';
  }
  const rackBtn = document.getElementById('rack-voice-bypass');
  if (rackBtn) {
    rackBtn.classList.toggle('on', !_dspVoiceDecoupled);
    rackBtn.classList.toggle('off', _dspVoiceDecoupled);
  }
}
