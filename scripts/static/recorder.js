// ══════════════════════════════════════════════════════════════
// DAT RECORDER — JARVIS R-1
// ══════════════════════════════════════════════════════════════
(function() {
  let _datCtx       = null;
  let _datBuffer    = null;
  let _datSource    = null;
  let _datStartTime = 0;   // audioCtx.currentTime au moment du play
  let _datOffset    = 0;   // position dans le buffer au moment du play
  let _datState     = 'stop'; // stop|play|pause|rec
  let _datSR        = _SAMPLE_RATE;
  let _datBit       = 24;
  let _datFmt       = 'wav';
  let _datFilename  = '';
  let _datDuration  = 0;
  let _datRAF       = null;
  let _datRecorder  = null;
  let _datRecChunks = [];
  let _datScrollX   = 0;
  let _datScrollDir = 1;
  let _datScrollRAF = null;
  // Broadcast meter state
  let _datRmsL = 0, _datRmsR = 0;          // smoothed RMS
  let _datPeakL = -144, _datPeakR = -144;  // peak hold (dB)
  let _datPeakTL = 0,   _datPeakTR = 0;    // hold frames counter
  let _datPeakVL = 0,   _datPeakVR = 0;    // gravity fall speed
  const _DAT_PEAK_HOLD = 60, _DAT_PEAK_GRAV = 0.012, _DAT_PEAK_VMAX = 0.4;
  // Dedicated DAT analysers (separate from JARVIS main analysers)
  let _datAnL = null, _datAnR = null;

  function _ctx() {
    // Réutilise l'audioCtx global JARVIS pour traverser la chaîne DSP
    if (typeof audioCtx !== 'undefined' && audioCtx && audioCtx.state !== 'closed') return audioCtx;
    if (!_datCtx || _datCtx.state === 'closed')
      _datCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: _datSR });
    return _datCtx;
  }
  // Point d'entrée DAT → destination directe (ne passe PAS par l'analyser JARVIS)
  function _dspIn() {
    return _ctx().destination;
  }

  // ── Statut LCD ──────────────────────────────────────────────
  function _setStatus(state) {
    _datState = state;
    // Status LED dot
    const led = document.getElementById('dat-status-led');
    if (led) led.className = 'dat-led-dot' +
      (state==='play'?' on-green':state==='rec'?' on-red':state==='pause'?' on-amber':'');
    // Status label
    const lbl = document.getElementById('dat-status-lbl');
    if (lbl) lbl.textContent = { stop:'STOP', play:'PLAY', pause:'PAUSE', rec:'● REC' }[state] || state.toUpperCase();
    // Indicator dots + labels
    ['play','pause','stop','rec','load','ff','rew'].forEach(k => {
      const dot = document.getElementById('dat-ind-' + k);
      if (dot) dot.className = 'dat-ind-dot';
      const elbl = document.getElementById('dat-ind-lbl-' + k);
      if (elbl) elbl.className = 'dat-ind-lbl';
    });
    const map = { play:'play', pause:'pause', stop:'stop', rec:'rec' };
    const onKey = map[state] || 'stop';
    const onDot = document.getElementById('dat-ind-' + onKey);
    if (onDot) onDot.className = 'dat-ind-dot ' + (state === 'rec' ? 'rec' : 'on');
    const onLbl = document.getElementById('dat-ind-lbl-' + onKey);
    if (onLbl) onLbl.className = 'dat-ind-lbl ' + (state === 'rec' ? 'rec' : 'on');
    // Transport buttons
    ['play','pause','stop','rec'].forEach(k => {
      const btn = document.getElementById('dat-btn-' + k);
      if (btn) btn.classList.remove('dat-active','dat-rec-active');
    });
    if (state === 'play')  document.getElementById('dat-btn-play')?.classList.add('dat-active');
    if (state === 'pause') document.getElementById('dat-btn-pause')?.classList.add('dat-active');
    if (state === 'rec')   document.getElementById('dat-btn-rec')?.classList.add('dat-rec-active');
  }

  // ── Compteur temps ──────────────────────────────────────────
  function _fmtTime(s) {
    if (isNaN(s) || s < 0) s = 0;
    const mm  = String(Math.floor(s / 60)).padStart(2,'0');
    const ss  = String(Math.floor(s % 60)).padStart(2,'0');
    const ms  = String(Math.floor((s % 1) * 1000)).padStart(3,'0');
    return `${mm}:${ss}.${ms}`;
  }

  function _currentPos() {
    if (_datState === 'play') {
      const ctx = _ctx();
      if (ctx) return Math.min(_datOffset + (ctx.currentTime - _datStartTime), _datDuration);
    }
    return _datOffset;
  }

  // ── RAF loop ────────────────────────────────────────────────
  function _datLoop() {
    _datRAF = requestAnimationFrame(_datLoop);
    const pos = _currentPos();
    const ctr = document.getElementById('dat-counter');
    if (ctr) ctr.textContent = _fmtTime(pos);
    const rem = document.getElementById('dat-remain');
    if (rem && _datDuration > 0) rem.textContent = 'REM ' + _fmtTime(_datDuration - pos);
    // Progress
    const pct = _datDuration > 0 ? (pos / _datDuration) * 100 : 0;
    const fill = document.getElementById('dat-progress-fill');
    const head = document.getElementById('dat-progress-head');
    if (fill) fill.style.width = pct + '%';
    if (head) head.style.left  = pct + '%';
    // LCD VU meters
    _drawDatMeters();
    // Auto-stop at end
    if (_datState === 'play' && _datDuration > 0 && pos >= _datDuration - 0.05) {
      datSTOP(); _datOffset = 0;
    }
  }

  const _DAT_PALETTE = { // NDT-CANVAS-EXEMPT: palette canvas DAT player — toutes valeurs → ctx.fillStyle/shadowColor/addColorStop
    CYAN:   '#00cfff',
    GREEN:  '#00c890',
    AMBER:  '#ffbd2e',
    RED:    '#ff4444',
    BG:     '#050d18',
    GROOVE: '#03090f',
    UNLIT:  'rgba(0,22,40,0.88)',
  };

  function _datCollectLevels() {
    let linL = 0, linR = 0;
    try {
      if (_datAnL && _datState === 'play') {
        const tL = new Float32Array(_datAnL.fftSize);
        const tR = new Float32Array(_datAnR.fftSize);
        _datAnL.getFloatTimeDomainData(tL);
        _datAnR.getFloatTimeDomainData(tR);
        let s2L = 0, s2R = 0;
        for (let i = 0; i < tL.length; i++) { s2L += tL[i]*tL[i]; s2R += tR[i]*tR[i]; }
        linL = Math.sqrt(s2L / tL.length);
        linR = Math.sqrt(s2R / tR.length);
      } else if (_datState === 'rec' && _datAnL) {
        const tL = new Float32Array(_datAnL.fftSize);
        _datAnL.getFloatTimeDomainData(tL);
        let s2 = 0;
        for (let i = 0; i < tL.length; i++) s2 += tL[i]*tL[i];
        linL = linR = Math.sqrt(s2 / tL.length);
      }
    } catch(e){/* AudioAnalyser pas encore prêt dans le RAF — skip frame */}
    return [linL, linR];
  }

  function _datDrawChan({ ctx, label, db, pkDb, y0, barH, rmsH, PAD_L, MW, dbToX, DB_MIN, DB_MAX, majors }) {
    const isL = label === 'L';
    const labelCol = isL ? _DAT_PALETTE.CYAN : _DAT_PALETTE.GREEN;
    ctx.font = 'bold 11px Orbitron, monospace';
    ctx.textAlign = 'center';
    ctx.fillStyle = labelCol + 'cc';
    ctx.shadowColor = labelCol; ctx.shadowBlur = 6;
    ctx.fillText(label, PAD_L / 2, y0 + barH * 0.65 + 3);
    ctx.shadowBlur = 0;
    ctx.fillStyle = _DAT_PALETTE.GROOVE;
    ctx.fillRect(PAD_L, y0, MW, barH + rmsH + 1);
    const xSig  = dbToX(db);
    const x6    = dbToX(-6);
    const x0pos = dbToX(0);
    if (xSig > PAD_L) {
      const x1 = Math.min(xSig, x6);
      const gC = ctx.createLinearGradient(PAD_L, 0, x6, 0);
      gC.addColorStop(0,   isL ? '#003844' : '#003830');
      gC.addColorStop(0.5, isL ? '#007799' : '#007755');
      gC.addColorStop(1,   isL ? '#00cfff' : '#00c890');
      ctx.fillStyle = gC;
      ctx.fillRect(PAD_L, y0, x1 - PAD_L, barH);
    }
    if (xSig > x6) {
      const x1 = Math.min(xSig, x0pos);
      const gA = ctx.createLinearGradient(x6, 0, x0pos, 0);
      gA.addColorStop(0, '#7a5800'); gA.addColorStop(1, _DAT_PALETTE.AMBER);
      ctx.fillStyle = gA;
      ctx.fillRect(x6, y0, x1 - x6, barH);
    }
    if (xSig > x0pos) {
      ctx.fillStyle = _DAT_PALETTE.RED;
      ctx.shadowColor = _DAT_PALETTE.RED; ctx.shadowBlur = 8;
      ctx.fillRect(x0pos, y0, xSig - x0pos, barH);
      ctx.shadowBlur = 0;
    }
    if (xSig < PAD_L + MW) {
      ctx.fillStyle = _DAT_PALETTE.UNLIT;
      ctx.fillRect(xSig, y0, PAD_L + MW - xSig, barH);
    }
    ctx.fillStyle = 'rgba(5,13,26,0.6)';
    majors.filter(d => d > DB_MIN && d < DB_MAX).forEach(d => {
      ctx.fillRect(dbToX(d) - 0.5, y0, 1, barH);
    });
    const RY = y0 + barH + 1;
    const xRms = dbToX(db - 3);
    if (xRms > PAD_L) {
      const gR2 = ctx.createLinearGradient(PAD_L, 0, x6, 0);
      gR2.addColorStop(0, isL ? '#002230' : '#002820');
      gR2.addColorStop(1, isL ? '#007799' : '#00885a');
      ctx.fillStyle = gR2;
      ctx.fillRect(PAD_L, RY, Math.min(xRms, x6) - PAD_L, rmsH);
      if (xRms > x6)    { ctx.fillStyle = '#7a5800'; ctx.fillRect(x6,    RY, Math.min(xRms, x0pos) - x6,    rmsH); }
      if (xRms > x0pos) { ctx.fillStyle = '#aa2222'; ctx.fillRect(x0pos, RY, xRms - x0pos,                  rmsH); }
    }
    ctx.fillStyle = _DAT_PALETTE.UNLIT;
    ctx.fillRect(Math.max(PAD_L, xRms), RY, MW - Math.max(0, xRms - PAD_L), rmsH);
    const xPk = dbToX(pkDb);
    if (xPk > PAD_L && xPk < PAD_L + MW) {
      const pkCol = pkDb > 0 ? _DAT_PALETTE.RED : pkDb > -6 ? _DAT_PALETTE.AMBER : labelCol;
      ctx.fillStyle = pkCol;
      ctx.shadowColor = pkCol; ctx.shadowBlur = 6;
      ctx.fillRect(xPk - 1, y0 - 1, 2, barH + rmsH + 2);
      ctx.shadowBlur = 0;
    }
    const dbStr = db > -140 ? (db > 0 ? '+' : '') + db.toFixed(2) : '-∞';
    const pkStr = pkDb > -140 ? (pkDb > 0 ? '+' : '') + pkDb.toFixed(2) + ' dB' : '-∞ dB';
    ctx.textAlign = 'left';
    ctx.font = 'bold 12px Share Tech Mono, monospace';
    const sigCol = db > 0 ? _DAT_PALETTE.RED : db > -6 ? _DAT_PALETTE.AMBER : _DAT_PALETTE.CYAN;
    ctx.fillStyle = sigCol;
    ctx.shadowColor = sigCol; ctx.shadowBlur = 4;
    ctx.fillText(dbStr, PAD_L + MW + 6, y0 + barH * 0.65 + 1);
    ctx.shadowBlur = 0;
    ctx.font = '8px Share Tech Mono, monospace';
    const pkCol2 = pkDb > 0 ? _DAT_PALETTE.RED+'99' : pkDb > -6 ? _DAT_PALETTE.AMBER+'99' : 'rgba(0,207,255,0.4)';
    ctx.fillStyle = pkCol2;
    ctx.fillText(pkStr, PAD_L + MW + 6, y0 + barH + rmsH + 2);
  }

  function _datDrawBalance({ ctx, dbL, dbR, PAD_L, MW, cx, BAL_Y, BAL_H }) {
    const balDb   = dbL - dbR;
    const balNorm = Math.max(-1, Math.min(1, balDb / 12));
    ctx.fillStyle = _DAT_PALETTE.GROOVE;
    ctx.fillRect(PAD_L, BAL_Y, MW, BAL_H);
    if (Math.abs(balNorm) > 0.005) {
      if (balNorm > 0) {
        const gL = ctx.createLinearGradient(cx - balNorm*(MW/2), 0, cx, 0);
        gL.addColorStop(0, '#003844'); gL.addColorStop(1, '#00cfff');
        ctx.fillStyle = gL;
        ctx.fillRect(cx - balNorm*(MW/2), BAL_Y, balNorm*(MW/2), BAL_H);
      } else {
        const gR = ctx.createLinearGradient(cx, 0, cx + (-balNorm)*(MW/2), 0);
        gR.addColorStop(0, '#00c890'); gR.addColorStop(1, '#003830');
        ctx.fillStyle = gR;
        ctx.fillRect(cx, BAL_Y, (-balNorm)*(MW/2), BAL_H);
      }
    }
    ctx.fillStyle = 'rgba(0,207,255,0.5)';
    ctx.fillRect(cx - 0.5, BAL_Y - 1, 1, BAL_H + 2);
    ctx.font = '7px Share Tech Mono'; ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(0,207,255,0.35)';
    ctx.fillText('Balance', cx, BAL_Y - 2);
    ctx.textAlign = 'left'; ctx.fillStyle = 'rgba(0,207,255,0.45)';
    ctx.font = '8px Share Tech Mono';
    const lstr = dbL > -140 ? (dbL>0?'+':'')+dbL.toFixed(2)+' dB' : '-∞ dB';
    const rstr = dbR > -140 ? (dbR>0?'+':'')+dbR.toFixed(2)+' dB' : '-∞ dB';
    ctx.fillText(lstr, PAD_L, BAL_Y + BAL_H + 9);
    ctx.textAlign = 'right';
    ctx.fillText(rstr, PAD_L + MW, BAL_Y + BAL_H + 9);
    if (Math.abs(balDb) > 0.05) {
      const bstr = (balDb>0?'+':'')+balDb.toFixed(2);
      const bx = cx + balNorm*(MW/4);
      ctx.textAlign = 'center';
      ctx.fillStyle = balNorm > 0 ? '#e87000cc' : '#00c890cc';
      ctx.font = 'bold 8px Share Tech Mono';
      ctx.fillText(bstr, bx, BAL_Y + BAL_H/2 + 3);
    }
  }

  // ── Broadcast-style stereo VU meter (L/R + balance) ─────────
  function _drawDatMeters() {
    const cv = document.getElementById('dat-lcd-meters');
    if (!cv) return;
    const CW = cv.offsetWidth || 800;
    if (cv.width !== CW) cv.width = CW;
    const ctx = cv.getContext('2d');
    const W = cv.width, H = cv.height;

    const [linL, linR] = _datCollectLevels();

    const aAtk = 0.7, aRel = 0.04;
    _datRmsL = linL > _datRmsL ? linL*aAtk + _datRmsL*(1-aAtk) : linL*aRel + _datRmsL*(1-aRel);
    _datRmsR = linR > _datRmsR ? linR*aAtk + _datRmsR*(1-aAtk) : linR*aRel + _datRmsR*(1-aRel);

    const toDb = v => v > 1e-6 ? 20*Math.log10(v) : -144;
    const dbL = toDb(_datRmsL), dbR = toDb(_datRmsR);
    const pkLinL = Math.max(_datRmsL, linL), pkLinR = Math.max(_datRmsR, linR);
    const pdbL = toDb(pkLinL), pdbR = toDb(pkLinR);

    const phUpdate = (db, pkDb, pkT, pkV) => {
      if (db > pkDb) return [db, 0, 0];
      pkT++;
      if (pkT > _DAT_PEAK_HOLD) { pkV = Math.min(pkV + _DAT_PEAK_GRAV, _DAT_PEAK_VMAX); pkDb -= pkV; }
      return [Math.max(-144, pkDb), pkT, pkV];
    };
    [_datPeakL, _datPeakTL, _datPeakVL] = phUpdate(dbL, _datPeakL, _datPeakTL, _datPeakVL);
    [_datPeakR, _datPeakTR, _datPeakVR] = phUpdate(dbR, _datPeakR, _datPeakTR, _datPeakVR);

    const PAD_L = 22, PAD_R = 96;
    const MW = W - PAD_L - PAD_R;
    const DB_MIN = -48, DB_MAX = 6;
    const dbToX = db => PAD_L + MW * Math.max(0, Math.min(1, (db - DB_MIN) / (DB_MAX - DB_MIN)));

    ctx.fillStyle = _DAT_PALETTE.BG;
    ctx.fillRect(0, 0, W, H);
    for (let sy = 0; sy < H; sy += 3) { ctx.fillStyle = 'rgba(0,0,0,0.06)'; ctx.fillRect(0, sy, W, 1); }

    const SCALE_Y = 84, TICK_MAJOR = 8, TICK_MINOR = 4;
    const majors = [-45,-42,-39,-36,-33,-30,-27,-24,-21,-18,-15,-12,-9,-6,-3,0,3,6];
    ctx.font = '8px Share Tech Mono, monospace';
    ctx.textAlign = 'center';
    majors.forEach(db => {
      if (db < DB_MIN || db > DB_MAX) return;
      const x = dbToX(db);
      const isMid = db === 0 || db === 6 || db === 3 || db === -3 || db === -6 || db === -9 || db === -18 || db === -27 || db === -36 || db === -45;
      ctx.strokeStyle = db === 0 ? 'rgba(255,255,255,0.4)' : db > 0 ? 'rgba(255,68,68,0.35)' : 'rgba(0,207,255,0.2)';
      ctx.lineWidth = db === 0 ? 1.2 : 0.7;
      ctx.beginPath(); ctx.moveTo(x, SCALE_Y - (isMid ? TICK_MAJOR : TICK_MINOR)); ctx.lineTo(x, SCALE_Y); ctx.stroke();
      if (isMid) {
        ctx.fillStyle = db === 0 ? 'rgba(255,255,255,0.75)' : db > 0 ? 'rgba(255,68,68,0.8)' : 'rgba(0,207,255,0.5)';
        ctx.fillText(db === 0 ? '0 dB' : (db > 0 ? '+'+db : db), x, SCALE_Y + 9);
      }
    });

    _datDrawChan({ ctx, label:'L', db:dbL, pkDb:_datPeakL, y0:4,  barH:20, rmsH:8, PAD_L, MW, dbToX, DB_MIN, DB_MAX, majors });
    _datDrawChan({ ctx, label:'R', db:dbR, pkDb:_datPeakR, y0:36, barH:20, rmsH:8, PAD_L, MW, dbToX, DB_MIN, DB_MAX, majors });

    const BAL_Y = 68, BAL_H = 13;
    const cx = PAD_L + MW / 2;
    _datDrawBalance({ ctx, dbL, dbR, PAD_L, MW, cx, BAL_Y, BAL_H });
  }

  // ── Filename scroll ─────────────────────────────────────────
  function _startScroll(text) {
    if (_datScrollRAF) cancelAnimationFrame(_datScrollRAF);
    const el = document.getElementById('dat-filename-inner');
    if (!el) return;
    el.textContent = text;
    _datScrollX = 0;
    const wrap = document.getElementById('dat-filename-inner').parentElement;
    function scroll() {
      _datScrollRAF = requestAnimationFrame(scroll);
      if (!wrap || !el) return;
      const overflow = el.scrollWidth - wrap.clientWidth;
      if (overflow <= 0) return;
      _datScrollX += 0.4 * _datScrollDir;
      if (_datScrollX >= overflow) { _datScrollDir = -1; }
      if (_datScrollX <= 0)        { _datScrollDir =  1; }
      el.style.transform = `translateX(${-_datScrollX}px)`;
    }
    scroll();
  }

  // ── PUBLIC API ──────────────────────────────────────────────
  window.datLOAD = function() {
    document.getElementById('dat-file-input').click();
  };

  window.datOnFile = async function(file) {
    if (!file) return;
    _datFilename = file.name;
    const szKB = (file.size / 1024).toFixed(0);
    const szEl = document.getElementById('dat-file-size');
    if (szEl) szEl.textContent = szKB > 1024 ? (szKB/1024).toFixed(1)+' MB' : szKB+' KB';
    _startScroll(file.name);
    const ind = document.getElementById('dat-ind-load');
    if (ind) ind.className = 'dat-ind-dot on';
    try {
      const ab = await file.arrayBuffer();
      const ctx = _ctx();
      _datBuffer = await ctx.decodeAudioData(ab);
      _datDuration = _datBuffer.duration;
      _datOffset = 0;
      // Update specs from buffer
      const srEl = document.getElementById('dat-sr-lbl');
      if (srEl) srEl.textContent = _datBuffer.sampleRate;
      const rem = document.getElementById('dat-remain');
      if (rem) rem.textContent = 'DUR ' + _fmtTime(_datDuration);
    } catch(e) {
      _startScroll('ERREUR — FORMAT NON SUPPORTÉ : ' + file.name);
    }
  };

  function _datMakeAnalysers(ctx) {
    // Toujours recréer pour éviter les connexions orphelines (les analyseurs sont dans le path)
    try { if (_datAnL) _datAnL.disconnect(); } catch(e){/* AudioNode déjà déconnecté */}
    try { if (_datAnR) _datAnR.disconnect(); } catch(e){/* AudioNode déjà déconnecté */}
    _datAnL = ctx.createAnalyser(); _datAnL.fftSize = 4096; _datAnL.smoothingTimeConstant = 0.55;
    _datAnR = ctx.createAnalyser(); _datAnR.fftSize = 4096; _datAnR.smoothingTimeConstant = 0.55;
    window._datAnL = _datAnL;  // exposé pour le mixer RAF (autre IIFE)
    window._datAnR = _datAnR;

    // _datAnL/R sont des dead-end analyseurs DAT uniquement — pas de connexion vers analyserL/R JARVIS
  }

  function _initDatEq(ctx) {
    // Reuse if already wired in this context
    if (window._datEqSub && window._datEqSub.context === ctx && ctx.state !== 'closed') return;
    ['_datEqSub','_datEqBass','_datEqMids','_datEqTreble'].forEach(k => {
      if (window[k]) { try { window[k].disconnect(); } catch(e) {} }
    });
    const mk = (type, freq, q) => {
      const f = ctx.createBiquadFilter();
      f.type = type; f.frequency.value = freq; f.Q.value = q; f.gain.value = 0;
      return f;
    };
    window._datEqSub    = mk('lowshelf',  80,    0.7);
    window._datEqBass   = mk('peaking',   300,   0.8);
    window._datEqMids   = mk('peaking',   3000,  0.9);
    window._datEqTreble = mk('highshelf', 10000, 0.7);
    // Chain: Sub → Bass → Mids → Treble → DSP compressor
    window._datEqSub.connect(window._datEqBass);
    window._datEqBass.connect(window._datEqMids);
    window._datEqMids.connect(window._datEqTreble);
    const sink = window._dspCompressor || window._dspAnalyser || ctx.destination;
    try { window._datEqTreble.connect(sink); } catch(e) {}
    // Reconnect _datPreDsp to head of chain
    if (window._datPreDsp) {
      try { window._datPreDsp.disconnect(); } catch(e) {}
      try { window._datPreDsp.connect(window._datEqSub); } catch(e) {}
    }
    // Restore gains from current UI sliders
    [['sub',window._datEqSub],['bass',window._datEqBass],
     ['mids',window._datEqMids],['treble',window._datEqTreble]].forEach(([b,n]) => {
      const sl = document.getElementById('dat-eq-'+b);
      const noGain = ['highpass','lowpass','notch','bandpass'].includes(n.type);
      if (sl && !noGain) n.gain.value = parseFloat(sl.value) || 0;
    });
  }

  window.datPLAY = function() {
    if (!_datBuffer) return;
    if (_datState === 'play') return;
    if (_datState === 'rec') datSTOP();
    const ctx = _ctx();
    if (ctx.state === 'suspended') ctx.resume();
    if (_datSource) { try { _datSource.stop(); } catch(e){/* AudioNode déjà stoppé */} }
    _datMakeAnalysers(ctx);
    _datSource = ctx.createBufferSource();
    _datSource.buffer = _datBuffer;
    const nCh = _datBuffer.numberOfChannels;

    // ── Gain fader DAT (toujours dans la chaîne, créé une seule fois) ──
    if (!window._datMixGain || window._datMixGain.context !== ctx || window._datMixGain.context.state === 'closed') {
      window._datMixGain = ctx.createGain();
      window._datMixGain.gain.value = 1.0;
    }
    const datGain = window._datMixGain;

    // ── Nœud de transit stable DAT → EQ music → DSP compressor ──
    if (!window._datPreDsp || window._datPreDsp.context !== ctx) {
      window._datPreDsp = ctx.createGain();
    }
    // Init/rewire EQ music chain (idempotent si déjà câblé)
    _initDatEq(ctx);

    // Pan DAT : créé une seule fois, persistant
    if (!window._datPanNode || window._datPanNode.context !== ctx) {
      window._datPanNode = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    }

    // ── Limiteur anti-saturation DAT (brickwall -1 dBFS) ──────────
    if (!window._datLimiter || window._datLimiter.context !== ctx) {
      const lim = ctx.createDynamicsCompressor();
      lim.threshold.value = -3;    // brickwall à -3 dBFS — 2.5dB de marge avant _dspLimiter
      lim.ratio.value     = 20;    // ratio très élevé
      lim.knee.value      = 0;     // hard brickwall — pas de zone floue au-dessus de 0dBFS
      lim.attack.value    = 0.001; // 1ms — réaction immédiate
      lim.release.value   = 0.100; // 100ms
      window._datLimiter = lim;
    }

    // Déconnexion systématique avant chaque play (évite accumulation de sources)
    try { datGain.disconnect(); } catch(e) {}
    if (window._datLimiter) { try { window._datLimiter.disconnect(); } catch(e) {} }
    if (window._datPanNode) { try { window._datPanNode.disconnect(); } catch(e) {} }

    if (nCh >= 2) {
      // Stéréo : source → datGain → _datLimiter → [panNode] → splitterPost → _datAnL/R → mergerPost → _datPreDsp → DSP
      const splitterPost = ctx.createChannelSplitter(2);
      const mergerPost   = ctx.createChannelMerger(2);
      _datSource.connect(datGain);
      datGain.connect(window._datLimiter);
      if (window._datPanNode) { window._datLimiter.connect(window._datPanNode); window._datPanNode.connect(splitterPost); }
      else window._datLimiter.connect(splitterPost);
      splitterPost.connect(_datAnL, 0);
      splitterPost.connect(_datAnR, 1);
      _datAnL.connect(mergerPost, 0, 0);
      _datAnR.connect(mergerPost, 0, 1);
      try { mergerPost.connect(window._datPreDsp); } catch(e) {}
    } else {
      // Mono : source → datGain → _datLimiter → [panNode] → _datAnL (in-path) → _datPreDsp → DSP
      _datSource.connect(datGain);
      datGain.connect(window._datLimiter);
      const panOrLim = window._datPanNode || window._datLimiter;
      if (window._datPanNode) window._datLimiter.connect(window._datPanNode);
      try { panOrLim.connect(_datAnL); } catch(e) {}
      try { _datAnL.connect(window._datPreDsp); } catch(e) {}
      _datAnR = _datAnL;
      window._datAnR = _datAnR;
    }
    _datSource.start(0, _datOffset);
    _datStartTime = ctx.currentTime;
    _setStatus('play');
    window._datActive = true;
    if (!_datRAF) _datLoop();
  };

  window.datPAUSE = function() {
    if (_datState !== 'play') return;
    _datOffset = _currentPos();
    if (_datSource) { try { _datSource.stop(); } catch(e){/* AudioNode déjà stoppé */} _datSource = null; }
    window._datActive = false;
    _setStatus('pause');
  };

  window.datSTOP = function() {
    window._datActive = false;
    if (_datSource) { try { _datSource.stop(); } catch(e){/* AudioNode déjà stoppé */} _datSource = null; }
    if (_datRecorder && _datState === 'rec') {
      _datRecorder.stop();
    }
    _datOffset = 0;
    _setStatus('stop');
    if (_datRAF) { cancelAnimationFrame(_datRAF); _datRAF = null; }
    const ctr = document.getElementById('dat-counter');
    if (ctr) ctr.textContent = '00:00.000';
    const fill = document.getElementById('dat-progress-fill');
    const head = document.getElementById('dat-progress-head');
    if (fill) fill.style.width = '0%';
    if (head) head.style.left  = '0%';
  };

  window.datFF = function() {
    const ind = document.getElementById('dat-ind-ff');
    if (ind) { ind.className='dat-ind-dot on'; setTimeout(()=>ind.className='dat-ind-dot',400); }
    const wasPlaying = _datState === 'play';
    if (wasPlaying) datPAUSE();
    _datOffset = Math.min(_datOffset + 10, _datDuration - 0.1);
    if (wasPlaying) datPLAY();
  };

  window.datREW = function() {
    const ind = document.getElementById('dat-ind-rew');
    if (ind) { ind.className='dat-ind-dot on'; setTimeout(()=>ind.className='dat-ind-dot',400); }
    const wasPlaying = _datState === 'play';
    if (wasPlaying) datPAUSE();
    _datOffset = Math.max(_datOffset - 10, 0);
    if (wasPlaying) datPLAY();
  };

  window.datSeek = function(e) {
    const wrap = document.getElementById('dat-progress-wrap');
    if (!wrap || !_datDuration) return;
    const rect = wrap.getBoundingClientRect();
    const pct  = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const wasPlaying = _datState === 'play';
    if (wasPlaying) datPAUSE();
    _datOffset = pct * _datDuration;
    const ctr = document.getElementById('dat-counter');
    if (ctr) ctr.textContent = _fmtTime(_datOffset);
    if (wasPlaying) datPLAY();
  };

  window.datREC = async function() {
    if (_datState === 'rec') { datSTOP(); return; }
    try {
      // Sélection codec réellement supporté par le navigateur
      const candidates = [
        { mime:'audio/ogg;codecs=opus',  ext:'ogg'  },
        { mime:'audio/webm;codecs=opus', ext:'webm' },
        { mime:'audio/webm',             ext:'webm' },
        { mime:'audio/mp4',              ext:'mp4'  },
      ];
      const chosen = candidates.find(c => MediaRecorder.isTypeSupported(c.mime))
                  || { mime:'', ext:'webm' };
      const mime = chosen.mime;
      const recExt = chosen.ext;
      const stream = await navigator.mediaDevices.getDisplayMedia({ audio:true, video:false })
                     .catch(() => navigator.mediaDevices.getUserMedia({ audio:{ echoCancellation:false, noiseSuppression:false } }));
      // Connect stream to DAT analysers for VU metering
      const recCtx = _ctx();
      _datMakeAnalysers(recCtx);
      try {
        const src = recCtx.createMediaStreamSource(stream);
        // Analyseurs IN PATH pour le monitoring REC (même logique que PLAY)
        const recSp = recCtx.createChannelSplitter(2);
        const recMg = recCtx.createChannelMerger(2);
        src.connect(recSp);
        recSp.connect(_datAnL, 0);
        recSp.connect(_datAnR, 1);
        _datAnL.connect(recMg, 0, 0);
        _datAnR.connect(recMg, 0, 1);
        // recMg → dspAnalyser pour monitoring en temps réel
        try { recMg.connect(_dspIn()); } catch(e3) { /* DSP node may not be ready */ }
      } catch(e2) { /* non-fatal recording setup error */ }
      _datRecChunks = [];
      _datRecorder  = new MediaRecorder(stream, { mimeType: mime });
      _datRecorder.ondataavailable = e => { if (e.data.size > 0) _datRecChunks.push(e.data); };
      _datRecorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(_datRecChunks, { type: mime || 'audio/webm' });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href = url; a.download = 'jarvis_rec_' + Date.now() + '.' + recExt;
        a.click(); URL.revokeObjectURL(url);
        _startScroll('SAVED — ' + a.download + ' (' + (mime||'webm') + ')');
      };
      _datRecorder.start(100);
      _setStatus('rec');
      if (!_datRAF) _datLoop();
    } catch(e) {
      _startScroll('ERREUR ENREGISTREMENT — ' + e.message);
    }
  };

  window.datSetSR = function(sr) {
    _datSR = sr;
    ['44','48'].forEach(k => document.getElementById('dat-sr-'+k)?.classList.remove('active'));
    document.getElementById('dat-sr-' + (sr===44100?'44':'48'))?.classList.add('active');
    const el = document.getElementById('dat-sr-lbl');
    if (el) el.textContent = sr;
  };

  window.datSetBit = function(b) {
    _datBit = b;
    ['16','24','32'].forEach(k => document.getElementById('dat-bit-'+k)?.classList.remove('active'));
    document.getElementById('dat-bit-' + b)?.classList.add('active');
    const el = document.getElementById('dat-bits-lbl');
    if (el) el.textContent = b;
  };

  window.datSetFmt = function(f) {
    _datFmt = f;
    ['wav','flac','mp3','ogg'].forEach(k => document.getElementById('dat-fmt-'+k)?.classList.remove('active'));
    document.getElementById('dat-fmt-' + f)?.classList.add('active');
    const el = document.getElementById('dat-fmt-lbl');
    if (el) el.textContent = f.toUpperCase();
  };

  // Modal open/close
  let _datMeterRAF = null;
  function _datMeterLoop() {
    _drawDatMeters();
    _datMeterRAF = requestAnimationFrame(_datMeterLoop);
  }

  window.openDatModal = function() {
    const m = document.getElementById('dat-modal');
    if (m) m.classList.add('open');
    if (!_datMeterRAF) _datMeterLoop();
  };
  window.closeDatModal = function() {
    const m = document.getElementById('dat-modal');
    if (m) m.classList.remove('open');
    if (_datMeterRAF) { cancelAnimationFrame(_datMeterRAF); _datMeterRAF = null; }
  };

  // Init
  _setStatus('stop');
  _drawDatMeters();
})();
