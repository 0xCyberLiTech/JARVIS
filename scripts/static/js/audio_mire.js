// ══════════════════════════════════════════════════════════════
// MIRE DE TEST AUDIO — Générateur de tonalités de test (30 s)
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// Mire de test audio : génération de tonalités calibrées, sweep, bruit,
// mesure et diagnostic de la chaîne de sortie. Fichier .js classique
// (scope global). Chargé APRÈS jarvis_main.js.

let _mireSource = null;
let _mirePlaying = false;

const MIRE_SEQUENCE = [
  { freq: 1000, dur: 2,   label: '1 kHz — Référence 0 dB' },
  { freq: 100,  dur: 2,   label: '100 Hz — Basses' },
  { freq: 250,  dur: 2,   label: '250 Hz — Bas-médiums' },
  { freq: 500,  dur: 2,   label: '500 Hz — Médiums graves' },
  { freq: 1000, dur: 2,   label: '1 kHz — Médiums' },
  { freq: 2000, dur: 2,   label: '2 kHz — Médiums aigus' },
  { freq: 4000, dur: 2,   label: '4 kHz — Présence' },
  { freq: 8000, dur: 2,   label: '8 kHz — Aigus' },
  { freq: 12000,dur: 2,   label: '12 kHz — Air' },
  { freq: 16000,dur: 2,   label: '16 kHz — Brillance' },
  // Sweep + bruit rose simulé via multi-sinusoïde
  { sweep: true, dur: 4,  label: 'Sweep 20Hz → 20kHz' },
  { noise: true, dur: 3,  label: 'Bruit rose (spectre plat)' },
  { freq: 1000, dur: 1,   label: '1 kHz — Référence finale' },
];

async function playMire() {
  if (_mirePlaying) { stopMire(); return; }
  if (!_dspInited) initDsp();
  if (audioCtx.state === 'suspended') await audioCtx.resume();
  _mirePlaying = true;

  const btn = document.getElementById('mire-btn');
  if (btn) btn.textContent = '⏹ STOP MIRE';

  for (let i = 0; i < MIRE_SEQUENCE.length && _mirePlaying; i++) {
    const step = MIRE_SEQUENCE[i];
    const mireLabel = document.getElementById('mire-label');
    if (mireLabel) mireLabel.textContent = '▶ ' + step.label;

    if (step.noise) {
      // Bruit rose via nœuds de bruit blanc filtré
      await _playPinkNoise(step.dur);
    } else if (step.sweep) {
      await _playSweep(20, 20000, step.dur);
    } else {
      await _playTone(step.freq, step.dur);
    }
  }
  if (_mirePlaying) {
    stopMire();
    const lbl = document.getElementById('mire-label');
    if (lbl) lbl.textContent = '✓ MIRE TERMINÉE';
  }
}

function stopMire() {
  _mirePlaying = false;
  if (_mireSource) { try { _mireSource.stop(); } catch(e){/* AudioNode déjà stoppé */} _mireSource = null; }
  const btn = document.getElementById('mire-btn');
  if (btn) btn.textContent = '▶ MIRE 30s';
}

async function _playTone(freq, dur) {
  return new Promise(resolve => {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.value = 0.3;
    osc.connect(gain);
    gain.connect(analyser);
    _mireSource = osc;
    osc.start();
    osc.stop(audioCtx.currentTime + dur);
    osc.onended = () => resolve();
  });
}

async function _playSweep(f0, f1, dur) {
  return new Promise(resolve => {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(f0, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(f1, audioCtx.currentTime + dur);
    gain.gain.value = 0.25;
    osc.connect(gain);
    gain.connect(analyser);
    _mireSource = osc;
    osc.start();
    osc.stop(audioCtx.currentTime + dur);
    osc.onended = () => resolve();
  });
}

async function _playPinkNoise(dur) {
  return new Promise(resolve => {
    const bufSize = Math.ceil(audioCtx.sampleRate * dur);
    const buf = audioCtx.createBuffer(1, bufSize, audioCtx.sampleRate);
    const data = buf.getChannelData(0);
    // Pink noise approximation (Voss algorithm)
    let b0=0,b1=0,b2=0,b3=0,b4=0,b5=0,b6=0;
    for (let i=0; i<bufSize; i++) {
      const w = Math.random()*2-1;
      b0=0.99886*b0+w*0.0555179; b1=0.99332*b1+w*0.0750759;
      b2=0.96900*b2+w*0.1538520; b3=0.86650*b3+w*0.3104856;
      b4=0.55000*b4+w*0.5329522; b5=-0.7616*b5-w*0.0168980;
      data[i]=(b0+b1+b2+b3+b4+b5+b6+w*0.5362)*0.07;
      b6=w*0.115926;
    }
    const src = audioCtx.createBufferSource();
    src.buffer = buf;
    src.connect(analyser);
    _mireSource = src;
    src.start();
    src.onended = () => resolve();
  });
}

// ── DSP Canvas drawing ──
// _dspRafId: runs continuously once initDsp() completes (not just on DSP tab)
function _dspBarColor(v, alpha) {
  const r = v/255;
  let cr, cg, cb;
  if (r < 0.45) {
    cr = Math.round(r/0.45*50);
    cg = Math.round(180 + r/0.45*50);
    cb = Math.round(255 - r/0.45*180);
  } else if (r < 0.75) {
    const t = (r-0.45)/0.3;
    cr = Math.round(50 + t*200); cg = Math.round(230-t*80); cb = Math.round(75-t*40);
  } else {
    const t = (r-0.75)/0.25;
    cr = 250; cg = Math.round(150-t*100); cb = Math.round(35);
  }
  return `rgba(${cr},${cg},${cb},${alpha})`;
}
function _specComputeVals(barCount, N, nyq) {
  if (!_specPeaks || _specPeaks.length !== barCount) _specPeaks = new Float32Array(barCount);
  const vals = new Float32Array(barCount);
  let peakVal = 0;
  for (let i = 0; i < barCount; i++) {
    const f0 = Math.pow(20000/20, i/barCount) * 20;
    const f1 = Math.pow(20000/20, (i+1)/barCount) * 20;
    const bin0 = Math.floor(f0/nyq*N), bin1 = Math.ceil(f1/nyq*N);
    let sum = 0, cnt = 0;
    for (let b = bin0; b < bin1 && b < N; b++) { sum += _dspDataArray[b]; cnt++; }
    vals[i] = cnt > 0 ? sum/cnt : 0;
    if (vals[i] > peakVal) peakVal = vals[i];
    if (vals[i] > _specPeaks[i]) _specPeaks[i] = vals[i];
    else _specPeaks[i] = Math.max(0, _specPeaks[i] - 0.8);
  }
  return {vals, peakVal};
}
function _specDrawGrid(ctx, W, H) {
  const dBLines = [0, -6, -12, -18, -24, -36, -48];
  ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'right';
  dBLines.forEach(db => {
    const y = H * (1 - (db+60)/60);
    ctx.strokeStyle = db === 0 ? '#00cfff22' : '#00cfff0c';
    ctx.lineWidth = db === 0 ? 1.2 : 0.8;
    ctx.setLineDash(db === 0 ? [] : [4,4]);
    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke();
    ctx.setLineDash([]); ctx.fillStyle = '#00cfff44'; ctx.fillText(db+'dB', W-4, y-2);
  });
  const fLabels = [[20,'20Hz'],[100,'100'],[500,'500'],[1000,'1k'],[2000,'2k'],[5000,'5k'],[10000,'10k'],[20000,'20k']];
  ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'center'; ctx.fillStyle = '#00cfff33';
  fLabels.forEach(([f,lbl]) => {
    ctx.fillText(lbl, W * Math.log10(f/20) / Math.log10(20000/20), H-3);
  });
}
function _specDrawBars(ctx, vals, W, H, bw) {
  for (let i = 0; i < vals.length; i++) {
    const v = vals[i], x = i*bw, bH = (v/255)*(H-12);
    const grd = ctx.createLinearGradient(0, H-bH, 0, H);
    grd.addColorStop(0, _dspBarColor(v, 0.95)); grd.addColorStop(1, _dspBarColor(v, 0.15));
    ctx.fillStyle = grd; ctx.fillRect(x+0.5, H-bH-12, bw-1, bH);
    const py = H - (_specPeaks[i]/255)*(H-12) - 14;
    ctx.fillStyle = _dspBarColor(_specPeaks[i], 0.9); ctx.fillRect(x+0.5, py, bw-1, 2);
  }
}
function _specDrawLineFill(ctx, vals, W, H, bw, mode) {
  const barCount = vals.length;
  const pts = Array.from({length:barCount}, (_,i) => ({x:(i+0.5)*bw, y:H-(vals[i]/255)*(H-12)-12}));
  ctx.beginPath(); ctx.moveTo(pts[0].x, H-12); ctx.lineTo(pts[0].x, pts[0].y);
  for (let i = 1; i < barCount; i++) {
    const mx = (pts[i-1].x + pts[i].x)/2;
    ctx.bezierCurveTo(mx, pts[i-1].y, mx, pts[i].y, pts[i].x, pts[i].y);
  }
  if (mode === 'fill') {
    ctx.lineTo(pts[barCount-1].x, H-12); ctx.closePath();
    const grd = ctx.createLinearGradient(0, 0, 0, H);
    grd.addColorStop(0, '#00cfff33'); grd.addColorStop(0.5, '#00ff8822'); grd.addColorStop(1, '#00cfff05');
    ctx.fillStyle = grd; ctx.fill();
  }
  ctx.strokeStyle = '#00cfff99'; ctx.lineWidth = 1.5; ctx.stroke();
  ctx.beginPath(); ctx.strokeStyle = '#00cfff44'; ctx.lineWidth = 1;
  for (let i = 0; i < barCount; i++) {
    const px = (i+0.5)*bw, py = H-(_specPeaks[i]/255)*(H-12)-12;
    i === 0 ? ctx.moveTo(px,py) : ctx.lineTo(px,py);
  }
  ctx.stroke();
}
function _dspDrawMirror(ctx, vals, W, H, bw) {
  const cy = H/2;
  for (let i = 0; i < vals.length; i++) {
    const v = vals[i], x = i*bw, bH = (v/255)*(cy-8);
    const grd = ctx.createLinearGradient(0, cy-bH, 0, cy+bH);
    grd.addColorStop(0, _dspBarColor(v, 0.15)); grd.addColorStop(0.5, _dspBarColor(v, 0.9)); grd.addColorStop(1, _dspBarColor(v, 0.15));
    ctx.fillStyle = grd; ctx.fillRect(x+0.5, cy-bH, bw-1, bH*2);
    const ph = (_specPeaks[i]/255)*(cy-8);
    ctx.fillStyle = _dspBarColor(_specPeaks[i], 0.8);
    ctx.fillRect(x+0.5, cy-ph-2, bw-1, 2); ctx.fillRect(x+0.5, cy+ph, bw-1, 2);
  }
  ctx.strokeStyle = '#00cfff18'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(0,cy); ctx.lineTo(W,cy); ctx.stroke();
}
function _specDrawWaterfall(ctx, vals, W, H, barCount) {
  if (!_wfCanvas || _wfCanvas.width !== W || _wfCanvas.height !== H) {
    const nwf = document.createElement('canvas'); nwf.width = W; nwf.height = H;
    const nctx = nwf.getContext('2d');
    nctx.fillStyle = '#000508'; nctx.fillRect(0, 0, W, H);
    if (_wfCanvas && _wfCanvas.width > 0) nctx.drawImage(_wfCanvas, 0, 0, W, H);
    _wfCanvas = nwf; _wfCtx2 = nctx;
  }
  const imgD = _wfCtx2.getImageData(2, 0, W-2, H); _wfCtx2.putImageData(imgD, 0, 0);
  const binH = H / barCount;
  for (let i = 0; i < barCount; i++) {
    _wfCtx2.fillStyle = _wfColor(vals[i]/255);
    _wfCtx2.fillRect(W-2, Math.floor((barCount-1-i)*binH), 2, Math.ceil(binH)+1);
  }
  ctx.drawImage(_wfCanvas, 0, 0, W, H);
  ctx.font = '7px Share Tech Mono'; ctx.textAlign = 'right';
  [[0,'20k'],[0.25,'5k'],[0.5,'1k'],[0.75,'100'],[0.98,'20Hz']].forEach(([pct,lbl]) => {
    ctx.fillStyle = 'rgba(0,207,255,0.5)'; ctx.fillText(lbl, W-4, pct*H+8);
  });
  for (let i = 0; i < H; i++) { ctx.fillStyle = _wfColor(1-i/H); ctx.fillRect(0, i, 4, 1); }
}
function _specDrawWave(ctx, W, H) {
  const waveArr = new Uint8Array(_dspAnalyser.fftSize);
  _dspAnalyser.getByteTimeDomainData(waveArr);
  const cy = H/2;
  ctx.strokeStyle = '#00cfff0a'; ctx.lineWidth = 0.5;
  for (let d = 1; d < 4; d++) {
    ctx.beginPath(); ctx.moveTo(0, cy-cy*d/4); ctx.lineTo(W, cy-cy*d/4); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, cy+cy*d/4); ctx.lineTo(W, cy+cy*d/4); ctx.stroke();
  }
  ctx.strokeStyle = '#00cfff18'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(W, cy); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0, cy);
  for (let x = 0; x < W; x++) {
    const y = (waveArr[Math.min(waveArr.length-1, Math.floor(x*waveArr.length/W))]/128-1)*(cy-10)+cy;
    ctx.lineTo(x, y);
  }
  ctx.lineTo(W, cy); ctx.closePath();
  const wGrd = ctx.createLinearGradient(0, 0, 0, H);
  wGrd.addColorStop(0, 'rgba(0,207,255,0.28)'); wGrd.addColorStop(0.5, 'rgba(0,207,255,0.08)'); wGrd.addColorStop(1, 'rgba(0,207,255,0.28)');
  ctx.fillStyle = wGrd; ctx.fill();
  ctx.beginPath();
  for (let x = 0; x < W; x++) {
    const y = (waveArr[Math.min(waveArr.length-1, Math.floor(x*waveArr.length/W))]/128-1)*(cy-10)+cy;
    x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.strokeStyle = '#00cfff'; ctx.lineWidth = 1.5; ctx.shadowColor = '#00cfff'; ctx.shadowBlur = 6;
  ctx.stroke(); ctx.shadowBlur = 0;
  ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'right'; ctx.fillStyle = '#00cfff44';
  ctx.fillText('+1.0', W-4, 14); ctx.fillText(' 0.0', W-4, cy+4); ctx.fillText('-1.0', W-4, H-4);
}
function _specDrawDots(ctx, vals, W, H, bw, barCount) {
  ctx.fillStyle = 'rgba(0,5,8,0.35)'; ctx.fillRect(0, 0, W, H);
  const dotBw = W / barCount;
  for (let i = 0; i < barCount; i++) {
    const v = vals[i]/255;
    if (v < 0.015) continue;
    const x = (i+0.5)*dotBw, y = H-v*(H-16)-14, r = Math.max(1.5, v*5);
    ctx.strokeStyle = _dspBarColor(vals[i], v*0.5); ctx.lineWidth = dotBw*0.35;
    ctx.beginPath(); ctx.moveTo(x, H-12); ctx.lineTo(x, y+r); ctx.stroke();
    ctx.shadowColor = _dspBarColor(vals[i], 1); ctx.shadowBlur = r*3;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI*2);
    ctx.fillStyle = _dspBarColor(vals[i], 0.9); ctx.fill(); ctx.shadowBlur = 0;
  }
  ctx.beginPath(); ctx.strokeStyle = '#00cfff33'; ctx.lineWidth = 0.8;
  for (let i = 0; i < barCount; i++) {
    const px = (i+0.5)*dotBw, py = H-(_specPeaks[i]/255)*(H-16)-14;
    i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
  }
  ctx.stroke();
}
function _specDrawRadial(ctx, vals, W, H, barCount) {
  const cx = W/2, cy = H/2, maxR = Math.min(cx,cy)-8, minR = maxR*0.22;
  const linePW = (2*Math.PI*maxR)/barCount*0.72;
  ctx.beginPath(); ctx.arc(cx, cy, maxR, 0, Math.PI*2);
  const radBg = ctx.createRadialGradient(cx, cy, minR, cx, cy, maxR);
  radBg.addColorStop(0, '#010c14'); radBg.addColorStop(1, '#000408');
  ctx.fillStyle = radBg; ctx.fill();
  [0.33, 0.66, 1].forEach(p => {
    ctx.beginPath(); ctx.arc(cx, cy, minR+p*(maxR-minR), 0, Math.PI*2);
    ctx.strokeStyle = 'rgba(0,180,220,0.07)'; ctx.lineWidth = 0.7; ctx.stroke();
  });
  for (let i = 0; i < barCount; i++) {
    const angle = (i/barCount)*Math.PI*2 - Math.PI/2;
    const r1 = minR + (vals[i]/255)*(maxR-minR);
    ctx.beginPath();
    ctx.moveTo(cx+minR*Math.cos(angle), cy+minR*Math.sin(angle));
    ctx.lineTo(cx+r1*Math.cos(angle), cy+r1*Math.sin(angle));
    ctx.strokeStyle = _dspBarColor(vals[i], 0.85); ctx.lineWidth = Math.max(1.5, linePW); ctx.stroke();
  }
  ctx.beginPath();
  for (let i = 0; i <= barCount; i++) {
    const angle = (i%barCount/barCount)*Math.PI*2 - Math.PI/2;
    const r = minR + (_specPeaks[i%barCount]/255)*(maxR-minR);
    i === 0 ? ctx.moveTo(cx+r*Math.cos(angle), cy+r*Math.sin(angle)) : ctx.lineTo(cx+r*Math.cos(angle), cy+r*Math.sin(angle));
  }
  ctx.strokeStyle = 'rgba(0,207,255,0.45)'; ctx.lineWidth = 1; ctx.shadowColor = '#00cfff'; ctx.shadowBlur = 4;
  ctx.stroke(); ctx.shadowBlur = 0;
  ctx.beginPath(); ctx.arc(cx, cy, minR, 0, Math.PI*2);
  ctx.strokeStyle = 'rgba(0,207,255,0.2)'; ctx.lineWidth = 1; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI*2); ctx.fillStyle = '#00cfff55'; ctx.fill();
  ctx.font = '7px Share Tech Mono'; ctx.textAlign = 'center'; ctx.fillStyle = 'rgba(0,200,240,0.4)';
  ctx.fillText('0dB', cx, cy-maxR-3); ctx.fillText('-∞', cx, cy-minR+4);
}
function _specUpdateMeters(peakVal) {
  const db = peakVal > 0 ? (20*Math.log10(peakVal/255)).toFixed(1) : '-∞';
  const dbEl = document.getElementById('dsp-db-val');
  if (dbEl) dbEl.textContent = db + ' dB';
  const vuBar = document.getElementById('dsp-vu-bar');
  if (vuBar) vuBar.style.width = ((peakVal/255)*100).toFixed(1) + '%';
  const vuPct = (peakVal/255*100).toFixed(1) + '%';
  const vuL = document.getElementById('vu-left');
  const vuR = document.getElementById('vu-right');
  const vuDb = document.getElementById('vu-db');
  if (vuL) vuL.style.width = vuPct;
  if (vuR) vuR.style.width = vuPct;
  if (vuDb) vuDb.textContent = db + (peakVal > 0 ? 'dB' : '');
}
function startDspDraw() {
  if (_dspRafId) return;
  let _eqPulsePhase = 0;
  function draw() {
    _dspRafId = requestAnimationFrame(draw);
    _eqPulsePhase += 0.08;
    if (_eqGhostAlpha > 0) _eqGhostAlpha = Math.max(0, _eqGhostAlpha - 0.006);
    const eqCanvas = document.getElementById('eq-curve-canvas');
    if (eqCanvas && eqCanvas.offsetWidth > 0 && _eqPanelOn) drawEqCurve();
    const datEqCanvas = document.getElementById('dat-eq-curve-canvas');
    if (datEqCanvas && datEqCanvas.offsetWidth > 0) drawDatEqCurve();
    if (!_dspAnalyser) return;
    _dspAnalyser.getByteFrequencyData(_dspDataArray);
    const canvas = document.getElementById('dsp-canvas');
    if (!canvas || canvas.offsetWidth === 0) return;
    let W, H;
    if (_specMode === 'dots') {
      W = canvas.width  || canvas.offsetWidth;
      H = canvas.height || canvas.offsetHeight;
      if (canvas.width !== canvas.offsetWidth || canvas.height !== canvas.offsetHeight) {
        canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight;
        W = canvas.width; H = canvas.height;
      }
    } else {
      W = canvas.width = canvas.offsetWidth;
      H = canvas.height = canvas.offsetHeight;
    }
    const ctx = canvas.getContext('2d');
    if (_specMode !== 'dots' && _specMode !== 'waterfall') ctx.clearRect(0, 0, W, H);
    const barCount = 96;
    const {vals, peakVal} = _specComputeVals(barCount, _dspDataArray.length, audioCtx.sampleRate/2);
    const bw = W / barCount;
    if (['bars','line','fill','mirror'].includes(_specMode)) _specDrawGrid(ctx, W, H);
    if      (_specMode === 'bars')                         _specDrawBars(ctx, vals, W, H, bw);
    else if (_specMode === 'line' || _specMode === 'fill') _specDrawLineFill(ctx, vals, W, H, bw, _specMode);
    else if (_specMode === 'mirror')                       _dspDrawMirror(ctx, vals, W, H, bw);
    else if (_specMode === 'waterfall')                    _specDrawWaterfall(ctx, vals, W, H, barCount);
    else if (_specMode === 'wave')                         _specDrawWave(ctx, W, H);
    else if (_specMode === 'dots')                         _specDrawDots(ctx, vals, W, H, bw, barCount);
    else if (_specMode === 'radial')                       _specDrawRadial(ctx, vals, W, H, barCount);
    _specUpdateMeters(peakVal);
  }
  draw();
}
