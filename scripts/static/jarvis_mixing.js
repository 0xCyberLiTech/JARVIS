// ══════════════════════════════════════════════════════════════
// JARVIS CONSOLE — MIXING ENGINE
// ══════════════════════════════════════════════════════════════
(function() {
'use strict';
  // ── État global ──────────────────────────────────────────────
  const _mix = window._mixState = {
    channels: {},   // id → { gainNode, panNode, analyserL, analyserR, source, muted, soloed, baseGain }
    masterGain: null,  // sum des micros → masterBus
    masterBus:  null,  // vrai bus master : tout converge ici (JARVIS/DAT/micros)
    masterPan:  null,  // balance stéréo finale
    masterAnalyserL: null,
    masterAnalyserR: null,
    rafId: null,
    devices: [],
    soloActive: false,
  };

  // ── AudioContext (partage avec JARVIS) ───────────────────────
  function _ac() {
    return (typeof audioCtx !== 'undefined' && audioCtx && audioCtx.state !== 'closed')
      ? audioCtx : null;
  }

  // ── Initialisation des nœuds maîtres ────────────────────────
  function _initMaster() {
    const ac = _ac(); if (!ac) return;
    if (_mix.masterBus && _mix.masterBus.context === ac) return;

    // ── Nœuds ────────────────────────────────────────────────────
    _mix.masterGain      = ac.createGain(); _mix.masterGain.gain.value = 1; // sum micros
    _mix.masterBus       = ac.createGain(); _mix.masterBus.gain.value  = 1; // fader master unique
    _mix.masterPan       = ac.createStereoPanner ? ac.createStereoPanner() : null;
    _mix.masterAnalyserL = ac.createAnalyser(); _mix.masterAnalyserL.fftSize = 2048; _mix.masterAnalyserL.smoothingTimeConstant = 0.6;
    _mix.masterAnalyserR = ac.createAnalyser(); _mix.masterAnalyserR.fftSize = 2048; _mix.masterAnalyserR.smoothingTimeConstant = 0.6;

    // ── VU tap : masterBus → splitter → analyserL/R → merger → masterPan → destination
    // Connecter masterBus → destination EN PREMIER pour éviter tout gap audio
    // lorsque _dspGainNode sera déplacé de destination vers masterBus ci-dessous.
    try {
      const sp = ac.createChannelSplitter(2);
      const mg = ac.createChannelMerger(2);
      _mix.masterBus.connect(sp);
      sp.connect(_mix.masterAnalyserL, 0);
      sp.connect(_mix.masterAnalyserR, 1);
      _mix.masterAnalyserL.connect(mg, 0, 0);
      _mix.masterAnalyserR.connect(mg, 0, 1);
      if (_mix.masterPan) { mg.connect(_mix.masterPan); _mix.masterPan.connect(ac.destination); }
      else mg.connect(ac.destination);
    } catch(e) {
      _mix.masterBus.connect(ac.destination);
    }

    // ── Graphe : tout converge sur masterBus ──────────────────────
    // masterBus → destination étant déjà actif, on peut déplacer _dspGainNode sans gap
    // Micros → masterGain → masterBus
    _mix.masterGain.connect(_mix.masterBus);
    // Bypass JARVIS (créé dans initDsp) → masterBus (connexion différée)
    if (window._jarvisBypassGain) {
      try { window._jarvisBypassGain.disconnect(); } catch(e) {}
      window._jarvisBypassGain.connect(_mix.masterBus);
    }
    // DAT bypass → masterBus
    if (_mix._datBypassNode) {
      try { _mix._datBypassNode.disconnect(); } catch(e) {}
      _mix._datBypassNode.connect(_mix.masterBus);
    }
    // JARVIS/DAT → _dspGainNode → masterBus
    // Déconnexion spécifique de destination (pas disconnect() global)
    if (typeof _dspGainNode !== 'undefined' && _dspGainNode) {
      try { _dspGainNode.disconnect(ac.destination); } catch(e) {}
      _dspGainNode.connect(_mix.masterBus);
    }
  }

  // ── Enregistrement canal statique JARVIS ─────────────────────
  function _initJarvisChannel() {
    const ac = _ac(); if (!ac) return;
    if (_mix.channels['jarvis']) {
      // Re-tap en cas de nouvel analyserL (recréé après restart)
      const ch = _mix.channels['jarvis'];
      if (typeof analyserL !== 'undefined' && analyserL && ch._srcAnL !== analyserL) {
        try { analyserL.connect(ch.analyserL); analyserR.connect(ch.analyserR); } catch(e){/* tap déjà connecté */}
        ch._srcAnL = analyserL;
      }
      return;
    }
    const gain = ac.createGain(); gain.gain.value = 1;
    const pan  = ac.createStereoPanner ? ac.createStereoPanner() : null;
    const anL  = ac.createAnalyser(); anL.fftSize = 2048; anL.smoothingTimeConstant = 0.6;
    const anR  = ac.createAnalyser(); anR.fftSize = 2048; anR.smoothingTimeConstant = 0.6;
    // Tap sur les analyseurs JARVIS (TTS audio → anL/anR)
    let srcAnL = null;
    if (typeof analyserL !== 'undefined' && analyserL) {
      try { analyserL.connect(anL); analyserR.connect(anR); srcAnL = analyserL; } catch(e){/* tap déjà connecté */}
    }
    // Note: gain node non connecté au master (JARVIS a sa propre sortie)
    // Le fader JARVIS contrôle le niveau via _dspGain si disponible
    _mix.channels['jarvis'] = { gainNode:gain, panNode:pan, analyserL:anL, analyserR:anR,
      muted:false, soloed:false, baseGain:1, duck:true, _srcAnL:srcAnL };
  }

  // ── Enregistrement canal DAT ─────────────────────────────────
  function _initDatChannel() {
    const ac = _ac(); if (!ac) return;
    if (_mix.channels['dat']) {
      // Re-tap si _datAnL a été recréé
      const ch = _mix.channels['dat'];
      if (typeof _datAnL !== 'undefined' && _datAnL && ch._srcAnL !== _datAnL) {
        try { _datAnL.connect(ch.analyserL); _datAnR.connect(ch.analyserR); } catch(e){/* tap déjà connecté */}
        ch._srcAnL = _datAnL;
      }
      return;
    }
    const ac2 = _ac();
    const anL  = ac2.createAnalyser(); anL.fftSize = 2048; anL.smoothingTimeConstant = 0.55;
    const anR  = ac2.createAnalyser(); anR.fftSize = 2048; anR.smoothingTimeConstant = 0.55;
    // gainNode réel dans la chaîne : DAT → gainNode → DSP chain
    const gain = ac2.createGain(); gain.gain.value = 1;
    // gain → splitter → anL/anR (taps VU) + gain → DSP chain
    const splMix = ac2.createChannelSplitter(2);
    const dspDest = (typeof _dspEqLow!=='undefined' && _dspEqLow) ? _dspEqLow : ac2.destination;
    gain.connect(splMix);
    splMix.connect(anL, 0);
    splMix.connect(anR, 1);
    gain.connect(dspDest);
    // Re-tap _datAnL si disponible (fallback monitoring sans playback)
    let srcAnL = null;
    if (typeof _datAnL !== 'undefined' && _datAnL) {
      try { _datAnL.connect(anL); _datAnR.connect(anR); srcAnL = _datAnL; } catch(e){/* tap déjà connecté */}
    }
    _mix.channels['dat'] = { gainNode:gain, panNode:null, analyserL:anL, analyserR:anR,
      muted:false, soloed:false, baseGain:1, duck:true, _srcAnL:srcAnL, _dspConn:dspDest };
  }

  // ── Création d'un canal entrée micro dynamique ───────────────
  async function _armInputChannel(id, deviceId) {
    const ac = _ac(); if (!ac) return;
    const prevCh = _mix.channels[id];
    if (prevCh && prevCh.stream) { prevCh.stream.getTracks().forEach(t=>t.stop()); }
    try {
      if (ac.state === 'suspended') await ac.resume();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId: deviceId ? {exact:deviceId} : undefined,
                 echoCancellation:false, noiseSuppression:false, autoGainControl:false }
      });
      const src    = ac.createMediaStreamSource(stream);
      const gain   = ac.createGain(); gain.gain.value = prevCh ? prevCh.baseGain : 1;
      const pan    = ac.createStereoPanner ? ac.createStereoPanner() : null;
      const anL    = ac.createAnalyser(); anL.fftSize = 2048; anL.smoothingTimeConstant = 0.55;
      const anR    = ac.createAnalyser(); anR.fftSize = 2048; anR.smoothingTimeConstant = 0.55;

      // Chaîne : src → splitter → anL/anR (IN PATH) → merger → gain → pan → master
      // Les analyseurs sont dans le graph actif → getFloatTimeDomainData() fonctionne
      const sp = ac.createChannelSplitter(2);
      const mg = ac.createChannelMerger(2);
      src.connect(sp);
      sp.connect(anL, 0);       // canal L → anL
      sp.connect(anR, 1);       // canal R → anR (mono: même signal sur les 2)
      anL.connect(mg, 0, 0);    // anL → merger L
      anR.connect(mg, 0, 1);    // anR → merger R
      // AGC : DynamicsCompressor entre merger et gain (transparent par défaut)
      const agc = ac.createDynamicsCompressor();
      agc.threshold.value = 0;   // bypass : threshold à 0dBFS, ratio 1 = transparent
      agc.ratio.value     = 1;
      agc.knee.value      = 0;
      agc.attack.value    = 0.003;
      agc.release.value   = 0.2;
      mg.connect(agc);
      agc.connect(gain);

      const dest = _mix.masterGain || ac.destination;
      if (pan) { gain.connect(pan); pan.connect(dest); }
      else gain.connect(dest);

      const agcActive = prevCh?.agcActive || false;
      // Assurer cohérence nœud/état : nœud toujours transparent à l'init si agcActive=false
      if (!agcActive) { agc.threshold.value = 0; agc.ratio.value = 1; agc.knee.value = 0; }
      _mix.channels[id] = { gainNode:gain, panNode:pan, analyserL:anL, analyserR:anR,
        source:src, stream, muted:false, soloed:false, baseGain:prevCh?.baseGain||1, duck:true,
        agcNode:agc, agcActive };

      // Refléter l'état AGC sur le bouton
      const agcBtn = document.getElementById('mix-agc-'+id);
      if (agcBtn) agcBtn.classList.toggle('active', agcActive);

      // Apply DSP routing if already configured
      if (_mixDsp[id]) _applyDspRouting(id);

      const armBtn = document.getElementById('mix-arm-'+id);
      if (armBtn) { armBtn.textContent='■ LIVE'; armBtn.classList.add('armed'); }
      _mixSetStatus('Canal '+id+' actif', true);
    } catch(e) {
      _mixSetStatus('Erreur accès micro : '+e.message, false);
    }
  }

  // ── Déconnexion canal ────────────────────────────────────────
  function _disarmChannel(id) {
    const ch = _mix.channels[id];
    if (!ch) return;
    if (ch.stream) ch.stream.getTracks().forEach(t=>t.stop());
    try { if(ch.gainNode) ch.gainNode.disconnect(); } catch(e){/* AudioNode déjà déconnecté */}
    delete _mix.channels[id];
    const armBtn = document.getElementById('mix-arm-'+id);
    if (armBtn) { armBtn.textContent='▷ ARM'; armBtn.classList.remove('armed'); }
  }

  // ── Gain / Pan ───────────────────────────────────────────────
  window.mixSetGain = function(id, val) {
    const linear = Math.pow(val / 100, 2); // quadratic taper
    const db = val > 0 ? (20*Math.log10(linear)).toFixed(1) : '-∞';
    const lcd = document.getElementById('mix-lcd-'+id);
    if (lcd) lcd.textContent = (db === '-∞' ? '-∞' : (parseFloat(db)>=0?'+':'')+db) + ' dB';
    const ac = _ac();
    if (id === 'master') {
      // Un seul point de contrôle : masterBus (tout y converge)
      if (_mix.masterBus && ac)
        _mix.masterBus.gain.setTargetAtTime(linear, ac.currentTime, 0.02);
      return;
    }
    if (id === 'dat') {
      // Fader DAT : contrôle window._datMixGain (toujours dans la chaîne DAT)
      if (window._datMixGain && ac)
        window._datMixGain.gain.setTargetAtTime(linear, ac.currentTime, 0.02);
      const ch = _mix.channels['dat'];
      if (ch) ch.baseGain = linear;
      return;
    }
    if (id === 'jarvis') {
      // Fader JARVIS : contrôle _jarvisPreGain (avant _dspAnalyser, isole du DAT)
      if (typeof _jarvisPreGain !== 'undefined' && _jarvisPreGain && ac)
        _jarvisPreGain.gain.setTargetAtTime(linear, ac.currentTime, 0.02);
      const ch = _mix.channels['jarvis'];
      if (ch) ch.baseGain = linear;
      return;
    }
    const ch = _mix.channels[id];
    if (ch && ac) { ch.baseGain = linear; if (!ch.muted) ch.gainNode.gain.setTargetAtTime(linear, ac.currentTime, 0.02); }
  };

  window.mixSetPan = function(id, val) {
    const ac = _ac(); if (!ac) return;
    if (id === 'master') {
      if (_mix.masterPan) _mix.masterPan.pan.setTargetAtTime(val/100, ac.currentTime, 0.02);
      return;
    }
    if (id === 'dat') {
      if (window._datPanNode) window._datPanNode.pan.setTargetAtTime(val/100, ac.currentTime, 0.02);
      return;
    }
    const ch = _mix.channels[id]; if (!ch) return;
    if (ch.panNode) ch.panNode.pan.setTargetAtTime(val/100, ac.currentTime, 0.02);
  };

  // ── Mute / Solo ──────────────────────────────────────────────
  // État M/S pour JARVIS et DAT (hors _mix.channels)
  const _mixStaticCh = {
    jarvis: { muted:false, soloed:false, baseGain:1 },
    dat:    { muted:false, soloed:false, baseGain:1 },
    master: { muted:false }
  };

  function _mixSetStateLabel(id, muted, soloed) {
    const lcd = document.getElementById('mix-lcd-'+id);
    if (!lcd) return;
    if (muted)  { lcd.textContent = 'MUTED';  lcd.classList.remove('mix-lcd--solo','mix-lcd--dat'); lcd.classList.add('mix-lcd--muted'); return; }
    if (soloed) { lcd.textContent = 'SOLO';   lcd.classList.remove('mix-lcd--muted','mix-lcd--dat'); lcd.classList.add('mix-lcd--solo'); return; }
    // Restaure la valeur dB
    const fader = document.getElementById('mix-fader-'+id);
    if (fader) {
      const linear = Math.pow(fader.value / 100, 2);
      const db = fader.value > 0 ? (20*Math.log10(linear)).toFixed(1) : '-∞';
      lcd.textContent = (db === '-∞' ? '-∞' : (parseFloat(db)>=0?'+':'')+db) + ' dB';
      lcd.classList.remove('mix-lcd--muted','mix-lcd--solo');
      lcd.classList.toggle('mix-lcd--dat', id === 'dat');
    }
  }

  function _mixGetGainNode(id) {
    if (id === 'jarvis') return (typeof _jarvisPreGain !== 'undefined') ? _jarvisPreGain : null;
    if (id === 'dat')    return window._datMixGain || null;
    if (id === 'master') return _mix.masterBus || null;
    return _mix.channels[id]?.gainNode || null;
  }

  function _mixGetState(id) {
    return _mixStaticCh[id] || _mix.channels[id];
  }

  window.mixToggleMute = function(id) {
    const ac = _ac(); if (!ac) return;
    const state = _mixGetState(id); if (!state) return;
    state.muted = !state.muted;
    const btn = document.getElementById('mix-m-'+id);
    if (btn) btn.classList.toggle('active', state.muted);
    _mixSetStateLabel(id, state.muted, state.soloed);
    const gn = _mixGetGainNode(id); if (!gn) return;
    const target = state.muted ? 0 : state.baseGain;
    gn.gain.setTargetAtTime(target, ac.currentTime, 0.02);
  };

  window.mixToggleSolo = function(id) {
    const ac = _ac(); if (!ac) return;
    const state = _mixGetState(id); if (!state || id === 'master') return;
    state.soloed = !state.soloed;
    const btn = document.getElementById('mix-s-'+id);
    if (btn) btn.classList.toggle('active', state.soloed);
    // Regroupe tous les canaux pour calculer soloActive
    const allIds = ['jarvis','dat', ...Object.keys(_mix.channels)];
    const soloActive = allIds.some(cid => (_mixGetState(cid)?.soloed));
    _mix.soloActive = soloActive;
    allIds.forEach(cid => {
      const s  = _mixGetState(cid); if (!s) return;
      const gn = _mixGetGainNode(cid); if (!gn) return;
      const shouldPlay = !soloActive || s.soloed;
      const target = (shouldPlay && !s.muted) ? (s.baseGain || 1) : 0;
      gn.gain.setTargetAtTime(target, ac.currentTime, 0.02);
      _mixSetStateLabel(cid, s.muted, s.soloed);
    });
  };

  // ── Auto-Duck / Talkover ─────────────────────────────────────
  let _mixDucked = false;
  let _mixDuckEnabled = true; // activé par défaut

  let _mixDspBypassed = false;
  let _mixDatBypassGain = null; // connexion directe DAT → destination quand bypass

  window.mixToggleDspBypass = function() {
    const ac = _ac(); if (!ac) return;
    _mixDspBypassed = !_mixDspBypassed;
    const btn = document.getElementById('mix-dsp-bypass-btn');

    if (_mixDspBypassed) {
      // BYPASS ON : silence DSP, ouvre chemin direct pour JARVIS et DAT
      if (typeof _dspGainNode !== 'undefined' && _dspGainNode)
        _dspGainNode.gain.setTargetAtTime(0, ac.currentTime, 0.02);
      // JARVIS bypass : _jarvisBypassGain activé (analyser → destination direct)
      if (typeof _jarvisBypassGain !== 'undefined' && _jarvisBypassGain)
        _jarvisBypassGain.gain.setTargetAtTime(1, ac.currentTime, 0.02);
      // DAT bypass direct → destination
      if (window._datMixGain) {
        if (!_mixDatBypassGain) {
          _mixDatBypassGain = ac.createGain();
          _mixDatBypassGain.gain.value = 1;
          // → masterBus pour passer par VU master et pan
          const dest = _mix.masterBus || ac.destination;
          _mixDatBypassGain.connect(dest);
        }
        try { window._datMixGain.connect(_mixDatBypassGain); } catch(e) {}
      }
      if (btn) { btn.textContent='⬡ DSP OFF'; btn.classList.add('mix-action-btn--bypass'); }
    } else {
      // BYPASS OFF : réactive DSP, ferme chemin direct
      if (typeof _dspGainNode !== 'undefined' && _dspGainNode) {
        const fader = document.getElementById('mix-fader-master');
        const val = fader ? parseFloat(fader.value) : 100;
        const linear = Math.pow(val / 100, 2);
        _dspGainNode.gain.setTargetAtTime(linear, ac.currentTime, 0.02);
      }
      if (typeof _jarvisBypassGain !== 'undefined' && _jarvisBypassGain)
        _jarvisBypassGain.gain.setTargetAtTime(0, ac.currentTime, 0.02);
      if (_mixDatBypassGain && window._datMixGain) {
        try { window._datMixGain.disconnect(_mixDatBypassGain); } catch(e) {}
      }
      if (btn) { btn.textContent='⬡ DSP ON'; btn.classList.remove('mix-action-btn--bypass'); }
    }
  };

  window.mixToggleDuck = function() {
    _mixDuckEnabled = !_mixDuckEnabled;
    const btn = document.getElementById('mix-duck-toggle');
    const lbl = document.getElementById('mix-duck-lbl');
    if (btn) {
      btn.classList.toggle('mix-action-btn--inactive', !_mixDuckEnabled);
    }
    if (!_mixDuckEnabled && _mixDucked) {
      // Relâche immédiatement si on désactive pendant un duck actif
      _mixDucked = false;
      const ac = _ac(); if (!ac) return;
      if (lbl) lbl.textContent = 'OFF';
      Object.values(_mix.channels).forEach(ch => {
        if (!ch.duck || !ch.gainNode || ch.muted) return;
        ch.gainNode.gain.setTargetAtTime(ch.baseGain, ac.currentTime, 0.05);
      });
    }
    if (lbl) lbl.textContent = _mixDuckEnabled ? 'STANDBY' : 'OFF';
  };

  window._mixAutoDuck = function(isSpeaking) {
    if (!_mixDuckEnabled) return;
    const ac = _ac(); if (!ac) return;
    const duckDb  = parseFloat(document.getElementById('mix-duck-db')?.value  || '-20');
    const atkMs   = parseFloat(document.getElementById('mix-duck-atk')?.value || '200');
    const relMs   = parseFloat(document.getElementById('mix-duck-rel')?.value || '800');
    // DAT : duck fort (minimum -30 dB même si UI moins agressive)
    const datDuckGain = Math.pow(10, Math.min(duckDb, -30) / 20);
    const duckGain    = Math.pow(10, duckDb / 20);
    const led = document.getElementById('mix-duck-led');
    const lbl = document.getElementById('mix-duck-lbl');
    if (isSpeaking && !_mixDucked) {
      _mixDucked = true;
      if (led) led.classList.add('mix-led--warn');
      if (lbl) lbl.textContent = 'DUCKING';
      // Canaux dynamiques (micros armés)
      Object.values(_mix.channels).forEach(ch => {
        if (!ch.duck || !ch.gainNode || ch.muted) return;
        ch.gainNode.gain.setTargetAtTime(ch.baseGain * duckGain, ac.currentTime, atkMs/1000/3);
      });
      // DAT : duck direct sur _datMixGain — utiliser le contexte propre au DAT (_datCtx)
      if (window._datMixGain) {
        const datCh  = _mix.channels['dat'];
        const base   = datCh ? datCh.baseGain : window._datMixGain.gain.value;
        const datNow = window._datMixGain.context.currentTime; // contexte DAT, pas JARVIS
        window._datMixGain._duckBase = base;
        window._datMixGain.gain.cancelScheduledValues(datNow);
        window._datMixGain.gain.setTargetAtTime(base * datDuckGain, datNow, atkMs/1000/3);
      }
    } else if (!isSpeaking && _mixDucked) {
      _mixDucked = false;
      if (led) led.classList.remove('mix-led--warn');
      if (lbl) lbl.textContent = 'STANDBY';
      // Canaux dynamiques
      Object.values(_mix.channels).forEach(ch => {
        if (!ch.duck || !ch.gainNode || ch.muted) return;
        ch.gainNode.gain.setTargetAtTime(ch.baseGain, ac.currentTime, relMs/1000/3);
      });
      // DAT : restauration — contexte propre au DAT
      if (window._datMixGain) {
        const datCh  = _mix.channels['dat'];
        const base   = datCh ? datCh.baseGain : (window._datMixGain._duckBase || 1);
        const datNow = window._datMixGain.context.currentTime;
        window._datMixGain.gain.cancelScheduledValues(datNow);
        window._datMixGain.gain.setTargetAtTime(base, datNow, relMs/1000/3);
      }
    }
  };

  // ── VU mètre horizontal broadcast (identique DAT) ───────────
  // État peak-hold par canal (keyed par canvasId)
  if (!window._mixVuState) window._mixVuState = {};


  // ── Broadcast-style large VU meter (DSP panel) ───────────────
  // NDT-LONG-JUSTIFIED: routine canvas DSP imbriquée dans closure initMixVU — extraction impossible sans passer ~15 variables de contexte
  function _drawMixVuBig(canvasId, anL, anR) {
    const cv = document.getElementById(canvasId); if (!cv) return;
    const CW = cv.offsetWidth || cv.parentElement?.offsetWidth || 500;
    const CH = 168;
    if (cv.width !== CW)  cv.width  = CW;
    if (cv.height !== CH) cv.height = CH;
    const ctx = cv.getContext('2d');
    const W = cv.width, H = cv.height;

    // ── Peak-hold state ──
    const SK = canvasId + '_big';
    if (!_mixVuState[SK]) _mixVuState[SK] = {
      rmsL:0, rmsR:0, pkL:-144, pkR:-144,
      pkTL:0, pkTR:0, pkVL:0,   pkVR:0,
      intL:0, intR:0            // integrated (slow RMS)
    };
    const st = _mixVuState[SK];
    const PEAK_HOLD=80, PEAK_GRAV=0.008, PEAK_VMAX=0.3;

    const getRms = an => {
      if (!an) return 0;
      try {
        const t = new Float32Array(an.fftSize);
        an.getFloatTimeDomainData(t);
        let s = 0; for (let i=0;i<t.length;i++) s+=t[i]*t[i];
        return Math.sqrt(s/t.length);
      } catch(e){ return 0; }
    };
    const linL = getRms(anL), linR = getRms(anR);
    const aA=0.75, aR=0.035;
    st.rmsL = linL>st.rmsL ? linL*aA+st.rmsL*(1-aA) : linL*aR+st.rmsL*(1-aR);
    st.rmsR = linR>st.rmsR ? linR*aA+st.rmsR*(1-aA) : linR*aR+st.rmsR*(1-aR);
    // Integrated (very slow release, ≈ loudness)
    const aI=0.002;
    st.intL = Math.max(st.intL*(1-aI) + st.rmsL*aI, st.rmsL*0.1);
    st.intR = Math.max(st.intR*(1-aI) + st.rmsR*aI, st.rmsR*0.1);

    const toDb = v => v>1e-6 ? 20*Math.log10(v) : -144;
    const dbL  = toDb(st.rmsL),  dbR  = toDb(st.rmsR);
    const intL = toDb(st.intL),  intR = toDb(st.intR);

    const phUp = (db,pkDb,pkT,pkV) => {
      if (db>pkDb) return [db,0,0];
      pkT++;
      if (pkT>PEAK_HOLD){ pkV=Math.min(pkV+PEAK_GRAV,PEAK_VMAX); pkDb-=pkV; }
      return [Math.max(-144,pkDb),pkT,pkV];
    };
    [st.pkL,st.pkTL,st.pkVL]=phUp(dbL,st.pkL,st.pkTL,st.pkVL);
    [st.pkR,st.pkTR,st.pkVR]=phUp(dbR,st.pkR,st.pkTR,st.pkVR);

    // ── Layout constants ──
    const PAD_L=42, PAD_R=80, VAL_X=W-PAD_R+6;
    const MW = W - PAD_L - PAD_R;
    const DB_MIN=-48, DB_MAX=6;
    const dbToX = db => PAD_L + MW*Math.max(0,Math.min(1,(db-DB_MIN)/(DB_MAX-DB_MIN)));
    const xZero = dbToX(0), x6 = dbToX(-6);

    const CYAN=_cssVar('--cyan'), RED=_cssVar('--red');
    const BG='#020a10', GROOVE='#03111c', UNLIT='rgba(0,14,28,0.94)'; // NDT-CANVAS-EXEMPT: couleurs fond widget VU-mètre
    const TEAL='#00e6b4', TEAL_MID='#00c8d8'; // NDT-CANVAS-EXEMPT: teintes spécifiques au gradient VU
    const SCALE_COL_NEG='rgba(0,207,255,0.45)', SCALE_COL_WARN='rgba(0,220,180,0.65)', SCALE_COL_CLIP='rgba(255,68,68,0.75)'; // NDT-ALPHA-EXEMPT

    // Scale marks
    const majors=[-45,-42,-39,-36,-33,-30,-27,-24,-21,-18,-15,-12,-9,-6,-3,0,3,6];
    const labeled=[-45,-36,-27,-18,-9,-6,-3,0,3,6];

    // ── Fond ──
    ctx.fillStyle=BG; ctx.fillRect(0,0,W,H);
    // Scanlines subtiles
    for(let sy=0;sy<H;sy+=2){ ctx.fillStyle='rgba(0,0,0,0.04)'; ctx.fillRect(0,sy,W,1); }

    // ── Helper : draw one broadcast channel ──
    function drawChan(label, db, pkDb, intDb, y0) {
      const PEAK_H=26, RMS_H=10, GAP=3;
      const _totalH=PEAK_H+GAP+RMS_H;
      const yRms=y0+PEAK_H+GAP;

      // Label L/R
      ctx.font='bold 11px Orbitron,monospace'; ctx.textAlign='left'; ctx.textBaseline='middle';
      ctx.fillStyle=CYAN; ctx.shadowColor=CYAN; ctx.shadowBlur=8;
      ctx.fillText(label, 6, y0+PEAK_H/2);
      ctx.shadowBlur=0;

      // ── PEAK BAR ──
      const xSig = dbToX(db);
      // Groove
      ctx.fillStyle=GROOVE; ctx.fillRect(PAD_L, y0, MW, PEAK_H);
      // Zone 1 : navy → cyan JARVIS (< -6 dB)
      if (xSig > PAD_L) {
        const x1 = Math.min(xSig, x6);
        const gC = ctx.createLinearGradient(PAD_L,0,x6,0);
        gC.addColorStop(0,    '#001220');
        gC.addColorStop(0.12, '#001e34');
        gC.addColorStop(0.30, '#003858');
        gC.addColorStop(0.52, '#006888');
        gC.addColorStop(0.72, '#009ec8');
        gC.addColorStop(0.88, '#00c8e0');
        gC.addColorStop(1,    '#00d8f0');
        ctx.fillStyle=gC; ctx.fillRect(PAD_L,y0,x1-PAD_L,PEAK_H);
      }
      // Zone 2 : cyan → teal-green JARVIS (-6 à 0 dB)
      if (xSig > x6) {
        const x1=Math.min(xSig,xZero);
        const gT=ctx.createLinearGradient(x6,0,xZero,0);
        gT.addColorStop(0,    '#00cce0');
        gT.addColorStop(0.35, '#00d8c8');
        gT.addColorStop(0.70, '#00e2b8');
        gT.addColorStop(1,    '#00eaaa');
        ctx.fillStyle=gT; ctx.fillRect(x6,y0,x1-x6,PEAK_H);
      }
      // Zone 3 : rouge clip (> 0 dB — sécurité)
      if (xSig > xZero) {
        const gR=ctx.createLinearGradient(xZero,0,xZero+18,0);
        gR.addColorStop(0,'#cc1111'); gR.addColorStop(0.5,RED); gR.addColorStop(1,'#ff8888');
        ctx.fillStyle=gR; ctx.shadowColor=RED; ctx.shadowBlur=10;
        ctx.fillRect(xZero,y0,xSig-xZero,PEAK_H); ctx.shadowBlur=0;
      }
      // Unlit
      if (xSig < PAD_L+MW)
        { ctx.fillStyle=UNLIT; ctx.fillRect(xSig,y0,PAD_L+MW-xSig,PEAK_H); }
      // Vertical depth overlay (top=bright, bottom=dark) + highlight line
      if (xSig > PAD_L) {
        const xFill = Math.min(xSig, PAD_L+MW);
        const gV = ctx.createLinearGradient(0,y0,0,y0+PEAK_H);
        gV.addColorStop(0,   'rgba(255,255,255,.07)');
        gV.addColorStop(0.25,'rgba(255,255,255,.03)');
        gV.addColorStop(0.6, 'rgba(0,0,0,.0)');
        gV.addColorStop(1,   'rgba(0,0,0,.28)');
        ctx.fillStyle=gV; ctx.fillRect(PAD_L,y0,xFill-PAD_L,PEAK_H);
        ctx.fillStyle='rgba(255,255,255,.10)';
        ctx.fillRect(PAD_L, y0, xFill-PAD_L, 1);
        ctx.fillStyle='rgba(0,0,0,.20)';
        ctx.fillRect(PAD_L, y0+PEAK_H-1, xFill-PAD_L, 1);
      }

      // Segment separators
      ctx.fillStyle='rgba(3,8,16,0.7)';
      majors.forEach(d => { if(d>DB_MIN&&d<DB_MAX){ const x=dbToX(d); ctx.fillRect(x-0.5,y0,1,PEAK_H); } });

      // Peak hold marker
      const xPk=dbToX(pkDb);
      if (xPk>PAD_L && xPk<PAD_L+MW) {
        const pkCol=pkDb>0?RED:pkDb>-6?TEAL:CYAN;
        ctx.fillStyle=pkCol; ctx.shadowColor=pkCol; ctx.shadowBlur=8;
        ctx.fillRect(xPk-1,y0-1,2,PEAK_H+2); ctx.shadowBlur=0;
        ctx.font='bold 8px Share Tech Mono,monospace';
        ctx.textAlign = xPk < W-120 ? 'left' : 'right';
        ctx.textBaseline='middle';
        const pxLabel = xPk < W-120 ? xPk+5 : xPk-5;
        ctx.fillStyle=pkCol; ctx.shadowColor=pkCol; ctx.shadowBlur=4;
        ctx.fillText(pkDb.toFixed(2), pxLabel, y0+PEAK_H/2); ctx.shadowBlur=0;
      }

      // ── RMS BAR ──
      const xRms=dbToX(db-3);
      ctx.fillStyle=GROOVE; ctx.fillRect(PAD_L,yRms,MW,RMS_H);
      if (xRms>PAD_L) {
        const x1=Math.min(xRms,x6);
        const gR2=ctx.createLinearGradient(PAD_L,0,x6,0);
        gR2.addColorStop(0,   '#000e1c');
        gR2.addColorStop(0.3, '#002440');
        gR2.addColorStop(0.65,'#005070');
        gR2.addColorStop(1,   '#0094b8');
        ctx.fillStyle=gR2; ctx.fillRect(PAD_L,yRms,x1-PAD_L,RMS_H);
        if (xRms>x6) {
          const gRT=ctx.createLinearGradient(x6,0,xZero,0);
          gRT.addColorStop(0,'#009ab8'); gRT.addColorStop(0.6,'#00c8b8'); gRT.addColorStop(1,'#00d8a0');
          ctx.fillStyle=gRT; ctx.fillRect(x6,yRms,Math.min(xRms,xZero)-x6,RMS_H);
        }
        if (xRms>xZero) { ctx.fillStyle='#882020'; ctx.fillRect(xZero,yRms,xRms-xZero,RMS_H); }
        const xRmsFill=Math.min(xRms,PAD_L+MW);
        const gVR=ctx.createLinearGradient(0,yRms,0,yRms+RMS_H);
        gVR.addColorStop(0,'rgba(255,255,255,.06)'); gVR.addColorStop(1,'rgba(0,0,0,.22)');
        ctx.fillStyle=gVR; ctx.fillRect(PAD_L,yRms,xRmsFill-PAD_L,RMS_H);
      }
      ctx.fillStyle=UNLIT; ctx.fillRect(Math.max(PAD_L,xRms),yRms,MW-Math.max(0,xRms-PAD_L),RMS_H);
      ctx.fillStyle='rgba(2,6,14,0.7)';
      majors.forEach(d=>{ if(d>DB_MIN&&d<DB_MAX){ const x=dbToX(d); ctx.fillRect(x-0.5,yRms,1,RMS_H); }});

      // Marqueur intégré (cyan JARVIS)
      const xInt=dbToX(intDb);
      if (xInt>PAD_L && xInt<PAD_L+MW) {
        ctx.fillStyle=TEAL_MID; ctx.shadowColor=TEAL_MID; ctx.shadowBlur=5;
        ctx.fillRect(xInt-1,yRms-1,2,RMS_H+2); ctx.shadowBlur=0;
        ctx.font='7px Share Tech Mono,monospace'; ctx.textAlign='left'; ctx.textBaseline='middle';
        ctx.fillStyle=TEAL_MID;
        const iStr='['+intDb.toFixed(1)+' dB]';
        const ix = xInt+4 < W-PAD_R-50 ? xInt+4 : xInt-50;
        ctx.fillText(iStr, ix, yRms+RMS_H/2);
      }

      // ── Right side values ──
      ctx.textAlign='right'; ctx.textBaseline='middle';
      // Peak hold dB (large, right)
      ctx.font='bold 9px Share Tech Mono,monospace';
      const pkCol2=st['pk'+label]>0?RED:st['pk'+label]>-6?TEAL:CYAN;
      ctx.fillStyle=pkCol2; ctx.shadowColor=pkCol2; ctx.shadowBlur=4;
      ctx.fillText(pkDb.toFixed(2)+' dB', W-4, y0+PEAK_H/2); ctx.shadowBlur=0;
      // RMS dB (smaller, right of RMS bar)
      ctx.font='7px Share Tech Mono,monospace';
      ctx.fillStyle='rgba(0,207,255,0.5)';
      ctx.fillText(db.toFixed(2)+' dB', W-4, yRms+RMS_H/2);
    }

    // ── Scale ruler (top) ──
    const SCALE_T=8, TICK_H=5;
    ctx.font='6.5px Share Tech Mono,monospace'; ctx.textAlign='center'; ctx.textBaseline='top';
    majors.forEach(db=>{
      if(db<DB_MIN||db>DB_MAX)return;
      const x=dbToX(db);
      ctx.strokeStyle=db>0?SCALE_COL_CLIP:db>-6?SCALE_COL_WARN:SCALE_COL_NEG;
      ctx.lineWidth=db===0?1.5:0.7; ctx.beginPath();
      ctx.moveTo(x,SCALE_T); ctx.lineTo(x,SCALE_T+TICK_H); ctx.stroke();
    });
    labeled.forEach(db=>{
      if(db<DB_MIN||db>DB_MAX)return;
      const x=dbToX(db);
      ctx.fillStyle=db>0?SCALE_COL_CLIP:db>-6?SCALE_COL_WARN:SCALE_COL_NEG;
      ctx.fillText(db===0?'0 dB':(db>0?'+'+db:db), x, SCALE_T+TICK_H+1);
    });
    // ── Draw L and R channels ──
    const L_Y = 22;   // top of L bar
    const R_Y = L_Y + 26 + 10 + 16; // after L peak + L rms + gap

    // 0dB vertical line — limité à la zone des deux canaux
    ctx.strokeStyle='rgba(255,255,255,0.18)'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(xZero, SCALE_T); ctx.lineTo(xZero, R_Y + 26 + 10 + 3); ctx.stroke();

    drawChan('L', dbL, st.pkL, intL, L_Y);
    drawChan('R', dbR, st.pkR, intR, R_Y);

    // ── Scale ruler (bottom, between channels and balance) ──
    const MID_SCALE_Y = R_Y + 26 + 10 + 6;
    ctx.font='6.5px Share Tech Mono,monospace'; ctx.textAlign='center'; ctx.textBaseline='top';
    majors.forEach(db=>{
      if(db<DB_MIN||db>DB_MAX)return;
      const x=dbToX(db);
      ctx.strokeStyle=db>0?SCALE_COL_CLIP:db>-6?SCALE_COL_WARN:SCALE_COL_NEG;
      ctx.lineWidth=db===0?1.5:0.7; ctx.beginPath();
      ctx.moveTo(x,MID_SCALE_Y); ctx.lineTo(x,MID_SCALE_Y+4); ctx.stroke();
    });
    labeled.forEach(db=>{
      if(db<DB_MIN||db>DB_MAX)return;
      const x=dbToX(db);
      ctx.fillStyle=db>0?SCALE_COL_CLIP:db>-6?SCALE_COL_WARN:SCALE_COL_NEG;
      ctx.fillText(db===0?'0':db, x, MID_SCALE_Y+5);
    });

    // ── Balance section ──
    const BAL_Y = MID_SCALE_Y + 18;
    const BAL_PEAK_H=16, BAL_RMS_H=7, BAL_GAP=2;
    const cx = PAD_L + MW/2;

    // "Balance" label
    ctx.font='6px Orbitron,monospace'; ctx.textAlign='center'; ctx.textBaseline='bottom';
    ctx.fillStyle='rgba(0,207,255,0.3)'; ctx.fillText('Balance', cx, BAL_Y-1);

    // Balance bar bg
    ctx.fillStyle=GROOVE; ctx.fillRect(PAD_L,BAL_Y,MW,BAL_PEAK_H);

    // Compute balance from L/R
    const balDb=dbL-dbR, balNorm=Math.max(-1,Math.min(1,balDb/12));
    // Left side (L louder): red bar going left from center
    // Right side (R louder): cyan bar going right from center
    if (Math.abs(balNorm)>0.005) {
      if (balNorm>0) { // L louder → cyan bar left of center
        const bW=balNorm*(MW/2);
        const gB=ctx.createLinearGradient(cx-bW,0,cx,0);
        gB.addColorStop(0,'rgba(0,207,255,0.3)'); gB.addColorStop(1,'rgba(0,207,255,0.85)');
        ctx.fillStyle=gB; ctx.fillRect(cx-bW,BAL_Y,bW,BAL_PEAK_H);
      } else { // R louder → red bar right of center
        const bW=(-balNorm)*(MW/2);
        const gB=ctx.createLinearGradient(cx,0,cx+bW,0);
        gB.addColorStop(0,'rgba(204,100,100,0.85)'); gB.addColorStop(1,'rgba(204,100,100,0.3)');
        ctx.fillStyle=gB; ctx.fillRect(cx,BAL_Y,bW,BAL_PEAK_H);
      }
    }
    // Unlit sides
    ctx.fillStyle=UNLIT;
    if (balNorm>0) ctx.fillRect(cx,BAL_Y,MW/2,BAL_PEAK_H);
    else           ctx.fillRect(PAD_L,BAL_Y,MW/2+balNorm*(MW/2),BAL_PEAK_H);

    // Center tick
    ctx.fillStyle='rgba(255,255,255,0.5)'; ctx.fillRect(cx-0.5,BAL_Y-1,1,BAL_PEAK_H+2);

    // Balance numeric values
    ctx.font='bold 8px Share Tech Mono,monospace'; ctx.textBaseline='middle';
    const balL=Math.max(0,balDb), balR=Math.max(0,-balDb);
    // Left val
    ctx.textAlign='left';
    ctx.fillStyle=balL>0?CYAN:'rgba(0,207,255,0.3)';
    ctx.fillText((balL>0?'+':'')+balL.toFixed(2), PAD_L+4, BAL_Y+BAL_PEAK_H/2);
    // Right val
    ctx.textAlign='right';
    ctx.fillStyle=balR>0?'#ff8080':'rgba(204,100,100,0.3)';
    ctx.fillText((balR>0?'+':'')+balR.toFixed(2)+' dB', PAD_L+MW-4, BAL_Y+BAL_PEAK_H/2);
    // Center numeric offset
    ctx.textAlign='center';
    ctx.fillStyle='rgba(0,210,200,0.8)';
    const balFine=dbL-dbR;
    ctx.fillText((balFine>=0?'+':'')+balFine.toFixed(2), cx-20, BAL_Y+BAL_PEAK_H/2);
    ctx.fillStyle='rgba(0,207,255,0.6)';
    ctx.fillText('+'+(Math.abs(balFine/12)).toFixed(2), cx+20, BAL_Y+BAL_PEAK_H/2);

    // Balance RMS bar
    const BRMSY=BAL_Y+BAL_PEAK_H+BAL_GAP;
    const balRmsNorm=Math.max(-1,Math.min(1,(intL-intR)/12));
    ctx.fillStyle=GROOVE; ctx.fillRect(PAD_L,BRMSY,MW,BAL_RMS_H);
    if (Math.abs(balRmsNorm)>0.005) {
      const bW2=Math.abs(balRmsNorm)*(MW/2);
      if (balRmsNorm>0) {
        ctx.fillStyle='rgba(0,207,255,0.4)'; ctx.fillRect(cx-bW2,BRMSY,bW2,BAL_RMS_H);
        // amber center marker
        const xOff=cx+Math.min(balRmsNorm*10,MW/2-4);
        ctx.fillStyle=TEAL_MID; ctx.fillRect(xOff-0.5,BRMSY-1,1,BAL_RMS_H+2);
        ctx.font='6px Share Tech Mono'; ctx.textAlign='left'; ctx.textBaseline='middle';
        ctx.fillStyle=TEAL_MID; ctx.fillText('+'+(intL-intR).toFixed(2), xOff+3, BRMSY+BAL_RMS_H/2);
      } else {
        ctx.fillStyle='rgba(0,207,255,0.4)'; ctx.fillRect(cx,BRMSY,bW2,BAL_RMS_H);
        const xOff=cx-Math.min(-balRmsNorm*10,MW/2-4);
        ctx.fillStyle=CYAN; ctx.fillRect(xOff-0.5,BRMSY-1,1,BAL_RMS_H+2);
        ctx.font='6px Share Tech Mono'; ctx.textAlign='right'; ctx.textBaseline='middle';
        ctx.fillStyle=CYAN; ctx.fillText('+'+(intR-intL).toFixed(2), xOff-3, BRMSY+BAL_RMS_H/2);
      }
    }
    ctx.fillStyle='rgba(255,255,255,0.35)'; ctx.fillRect(cx-0.5,BRMSY-1,1,BAL_RMS_H+2);
  }

  // NDT-LONG-JUSTIFIED: routine canvas DSP imbriquée dans closure initMixVU — extraction impossible sans passer ~15 variables de contexte
  function _drawMixVu(canvasId, anL, anR, fixedH) {
    const cv = document.getElementById(canvasId); if (!cv) return;
    // Sync résolution canvas (offsetWidth = 0 si modal caché → fallback parent)
    const CW = cv.offsetWidth || cv.parentElement?.offsetWidth || 140;
    const CH = fixedH || 80;
    if (cv.width !== CW)  cv.width  = CW;
    if (cv.height !== CH) cv.height = CH;
    const ctx = cv.getContext('2d');
    const W = cv.width, H = cv.height;

    // ── État peak-hold par canal ──
    if (!_mixVuState[canvasId]) _mixVuState[canvasId] = {
      rmsL:0, rmsR:0, pkL:-144, pkR:-144,
      pkTL:0, pkTR:0, pkVL:0, pkVR:0
    };
    const st = _mixVuState[canvasId];
    const PEAK_HOLD=60, PEAK_GRAV=0.012, PEAK_VMAX=0.4;

    // ── Collect RMS ──
    const getRms = an => {
      if (!an) return 0;
      try {
        const t = new Float32Array(an.fftSize);
        an.getFloatTimeDomainData(t);
        let s2 = 0; for (let i=0;i<t.length;i++) s2+=t[i]*t[i];
        return Math.sqrt(s2/t.length);
      } catch(e){ return 0; }
    };
    const linL = getRms(anL), linR = getRms(anR);

    // Smooth RMS (fast attack, slow release)
    const aAtk=0.7, aRel=0.04;
    st.rmsL = linL > st.rmsL ? linL*aAtk+st.rmsL*(1-aAtk) : linL*aRel+st.rmsL*(1-aRel);
    st.rmsR = linR > st.rmsR ? linR*aAtk+st.rmsR*(1-aAtk) : linR*aRel+st.rmsR*(1-aRel);

    const toDb = v => v > 1e-6 ? 20*Math.log10(v) : -144;
    const dbL = toDb(st.rmsL), dbR = toDb(st.rmsR);

    // Peak hold gravity
    const phUp = (db, pkDb, pkT, pkV) => {
      if (db > pkDb) return [db, 0, 0];
      pkT++;
      if (pkT > PEAK_HOLD) { pkV = Math.min(pkV+PEAK_GRAV, PEAK_VMAX); pkDb -= pkV; }
      return [Math.max(-144, pkDb), pkT, pkV];
    };
    [st.pkL, st.pkTL, st.pkVL] = phUp(dbL, st.pkL, st.pkTL, st.pkVL);
    [st.pkR, st.pkTR, st.pkVR] = phUp(dbR, st.pkR, st.pkTR, st.pkVR);

    // ── Layout ──
    const PAD_L = 14, PAD_R = 0;
    const MW = W - PAD_L - PAD_R;
    const DB_MIN = -48, DB_MAX = 6;
    const dbToX = db => PAD_L + MW * Math.max(0, Math.min(1, (db-DB_MIN)/(DB_MAX-DB_MIN)));

    // ── Palette JARVIS — studio unifié ──
    const J_CYAN=_cssVar('--cyan'), J_RED=_cssVar('--red');
    const J_AMBER='#ffbd2e'; // NDT-CANVAS-EXEMPT: teinte amber studio (différente de --amber #ffaa00)
    const J_BG='#050d18', J_GROOVE='#03090f', J_UNLIT='rgba(0,18,30,0.92)'; // NDT-CANVAS-EXEMPT: couleurs fond widget balance
    const majors = [-45,-36,-27,-18,-9,-6,-3,0,3,6];

    // ── Fond + scanlines ──
    ctx.fillStyle = J_BG; ctx.fillRect(0,0,W,H);
    for (let sy=0;sy<H;sy+=2){ ctx.fillStyle='rgba(0,0,0,0.04)'; ctx.fillRect(0,sy,W,1); }

    // ── Scale ticks ──
    const SCALE_Y = H - 14, TICK_H = 5;
    ctx.font = '6px Share Tech Mono,monospace'; ctx.textAlign='center';
    majors.forEach(db => {
      if (db<DB_MIN||db>DB_MAX) return;
      const x = dbToX(db);
      ctx.strokeStyle = db===0?'rgba(255,255,255,0.5)':db>0?'rgba(255,68,68,0.5)':'rgba(0,207,255,0.25)';
      ctx.lineWidth = db===0?1.5:0.7;
      ctx.beginPath(); ctx.moveTo(x,SCALE_Y); ctx.lineTo(x,SCALE_Y+TICK_H); ctx.stroke();
      if (db%9===0||db===0||db===3||db===-3||db===-6) {
        ctx.fillStyle = db===0?'rgba(255,255,255,0.8)':db>0?'rgba(255,68,68,0.75)':'rgba(0,207,255,0.5)';
        ctx.fillText(db===0?'0':db, x, H-1);
      }
    });

    // ── Draw one channel bar — palette cyan unifiée ──
    function drawChan(label, db, pkDb, y0, barH, rmsH) {
      // Label
      ctx.font='bold 8px Orbitron,monospace'; ctx.textAlign='center';
      ctx.fillStyle=J_CYAN+'cc'; ctx.shadowColor=J_CYAN; ctx.shadowBlur=4;
      ctx.fillText(label, PAD_L/2, y0+barH*0.65+3); ctx.shadowBlur=0;

      // Groove bg
      ctx.fillStyle=J_GROOVE; ctx.fillRect(PAD_L,y0,MW,barH+rmsH+1);

      const xSig  = dbToX(db);
      const x6    = dbToX(-6);
      const x0pos = dbToX(0);

      // Safe zone — cyan gradient
      if (xSig > PAD_L) {
        const x1 = Math.min(xSig,x6);
        const gC = ctx.createLinearGradient(PAD_L,0,x6,0);
        gC.addColorStop(0,   '#001e2c');
        gC.addColorStop(0.4, '#004d6a');
        gC.addColorStop(1,   J_CYAN);
        ctx.fillStyle=gC; ctx.fillRect(PAD_L,y0,x1-PAD_L,barH);
      }
      // Warning amber
      if (xSig > x6) {
        const x1=Math.min(xSig,x0pos);
        const gA=ctx.createLinearGradient(x6,0,x0pos,0);
        gA.addColorStop(0,'#7a5800'); gA.addColorStop(1,J_AMBER);
        ctx.fillStyle=gA; ctx.fillRect(x6,y0,x1-x6,barH);
      }
      // Clip red
      if (xSig > x0pos) {
        ctx.fillStyle=J_RED; ctx.shadowColor=J_RED; ctx.shadowBlur=6;
        ctx.fillRect(x0pos,y0,xSig-x0pos,barH); ctx.shadowBlur=0;
      }
      // Unlit
      if (xSig < PAD_L+MW) {
        ctx.fillStyle=J_UNLIT; ctx.fillRect(xSig,y0,PAD_L+MW-xSig,barH);
      }
      // Segment separators
      ctx.fillStyle='rgba(5,13,26,0.65)';
      majors.filter(d=>d>DB_MIN&&d<DB_MAX).forEach(d=>{
        ctx.fillRect(dbToX(d)-0.5,y0,1,barH);
      });
      // RMS bar — cyan sombre
      const RY=y0+barH+1, xRms=dbToX(db-3);
      if (xRms>PAD_L) {
        const gR2=ctx.createLinearGradient(PAD_L,0,x6,0);
        gR2.addColorStop(0,'#001220'); gR2.addColorStop(1,'#006688');
        ctx.fillStyle=gR2; ctx.fillRect(PAD_L,RY,Math.min(xRms,x6)-PAD_L,rmsH);
        if (xRms>x6)    { ctx.fillStyle='#7a5800'; ctx.fillRect(x6,RY,Math.min(xRms,x0pos)-x6,rmsH); }
        if (xRms>x0pos) { ctx.fillStyle='#aa2222'; ctx.fillRect(x0pos,RY,xRms-x0pos,rmsH); }
      }
      ctx.fillStyle=J_UNLIT; ctx.fillRect(Math.max(PAD_L,xRms),RY,MW-Math.max(0,xRms-PAD_L),rmsH);

      // Peak hold marker
      const xPk=dbToX(pkDb);
      if (xPk>PAD_L && xPk<PAD_L+MW) {
        const pkCol=pkDb>0?J_RED:pkDb>-6?J_AMBER:'rgba(255,255,255,0.9)';
        ctx.fillStyle=pkCol; ctx.shadowColor=pkCol; ctx.shadowBlur=5;
        ctx.fillRect(xPk-1,y0-1,2,barH+rmsH+2); ctx.shadowBlur=0;
      }
    }

    // L y=2, R y=22
    drawChan('L', dbL, st.pkL, 2,  14, 4);
    drawChan('R', dbR, st.pkR, 24, 14, 4);

    // ── Balance bar ──
    const BAL_Y=44, BAL_H=8;
    const balDb=dbL-dbR, balNorm=Math.max(-1,Math.min(1,balDb/12));
    const cx=PAD_L+MW/2;
    ctx.fillStyle=J_GROOVE; ctx.fillRect(PAD_L,BAL_Y,MW,BAL_H);
    if (Math.abs(balNorm)>0.005) {
      if (balNorm>0) {
        const gL=ctx.createLinearGradient(cx-balNorm*(MW/2),0,cx,0);
        gL.addColorStop(0,'#003844'); gL.addColorStop(1,'#00cfff');
        ctx.fillStyle=gL; ctx.fillRect(cx-balNorm*(MW/2),BAL_Y,balNorm*(MW/2),BAL_H);
      } else {
        const gR=ctx.createLinearGradient(cx,0,cx+(-balNorm)*(MW/2),0);
        gR.addColorStop(0,'#004d6a'); gR.addColorStop(1,'#001e2c');
        ctx.fillStyle=gR; ctx.fillRect(cx,BAL_Y,(-balNorm)*(MW/2),BAL_H);
      }
    }
    ctx.fillStyle='rgba(255,255,255,0.4)'; ctx.fillRect(cx-0.5,BAL_Y-1,1,BAL_H+2);
    ctx.font='6px Share Tech Mono'; ctx.textAlign='center';
    ctx.fillStyle='rgba(0,207,255,0.3)'; ctx.fillText('BAL',cx,BAL_Y-1);
  }

  // ── Graduation canvas fader ──────────────────────────────────
  function _drawGrad(canvasId) {
    const cv = document.getElementById(canvasId); if (!cv) return;
    const ctx = cv.getContext('2d');
    const W = cv.width||14, H = cv.height||160;
    ctx.fillStyle='#050d18'; ctx.fillRect(0,0,W,H);
    // 0dB at 100/150 = 2/3 from top (fader 0-150, 100=unity)
    const _unityY = H * (1 - 100/150);
    const marks = [{v:150,l:'↑'},{v:120,l:'+6'},{v:100,l:'0'},{v:70,l:'-12'},{v:40,l:'-24'},{v:10,l:'-∞'}];
    marks.forEach(({v,l}) => {
      const y = H * (1 - v/150);
      ctx.fillStyle = v===100 ? 'rgba(255,255,255,0.5)' : v>100 ? 'rgba(255,189,46,0.5)' : 'rgba(0,207,255,0.3)';
      ctx.fillRect(0, y, W, v===100?1.5:0.8);
      ctx.font='6px Share Tech Mono'; ctx.textAlign='center';
      ctx.fillStyle = v===100?'rgba(255,255,255,0.7)':v>100?'rgba(255,189,46,0.6)':'rgba(0,207,255,0.4)';
      ctx.fillText(l, W/2, y-1);
    });
  }

  // ── DSP state & nodes per channel ────────────────────────────
  // dspState[id] = { eq:{enabled,low,mid,pres,high}, comp:{enabled,...}, lim:{enabled,...} }
  const _mixDsp = {};
  let _mixSelChan = null;

  function _defaultDsp() {
    return {
      eq:   { enabled:false, low:0, mid:0, pres:0, high:0 },
      comp: { enabled:false, threshold:-18, ratio:4, knee:10, attack:10, release:100, makeup:0 },
      lim:  { enabled:false, ceiling:-0.5, limrelease:100 }
    };
  }

  // Create/ensure DSP nodes for a channel
  function _ensureDspNodes(id) {
    const ac = _ac(); if (!ac) return;
    if (_mixDsp[id] && _mixDsp[id].nodes) return;
    if (!_mixDsp[id]) _mixDsp[id] = _defaultDsp();
    const d = _mixDsp[id];
    // EQ nodes (4 peaking BiquadFilters)
    const eqLow  = ac.createBiquadFilter(); eqLow.type='lowshelf';  eqLow.frequency.value=80;   eqLow.gain.value=0;
    const eqMid  = ac.createBiquadFilter(); eqMid.type='peaking';   eqMid.frequency.value=1000; eqMid.Q.value=1.0; eqMid.gain.value=0;
    const eqPres = ac.createBiquadFilter(); eqPres.type='peaking';  eqPres.frequency.value=5000;eqPres.Q.value=1.0;eqPres.gain.value=0;
    const eqHigh = ac.createBiquadFilter(); eqHigh.type='highshelf';eqHigh.frequency.value=12000;eqHigh.gain.value=0;
    // Compressor
    const comp = ac.createDynamicsCompressor();
    comp.threshold.value = d.comp.threshold;
    comp.ratio.value     = d.comp.ratio;
    comp.knee.value      = d.comp.knee;
    comp.attack.value    = d.comp.attack/1000;
    comp.release.value   = d.comp.release/1000;
    // Makeup gain (after comp)
    const makeup = ac.createGain(); makeup.gain.value = Math.pow(10, d.comp.makeup/20);
    // Limiter (compressor with high ratio + low threshold)
    const lim = ac.createDynamicsCompressor();
    lim.threshold.value = d.lim.ceiling;
    lim.ratio.value     = 20;
    lim.knee.value      = 0;
    lim.attack.value    = 0.001;
    lim.release.value   = d.lim.limrelease/1000;

    d.nodes = { eqLow, eqMid, eqPres, eqHigh, comp, makeup, lim };

    // Wire: eqLow → eqMid → eqPres → eqHigh → comp → makeup → lim
    // These nodes are inserted into the channel's gain node chain when enabled
    eqLow.connect(eqMid); eqMid.connect(eqPres); eqPres.connect(eqHigh);
    eqHigh.connect(comp); comp.connect(makeup); makeup.connect(lim);
  }

  // Insert DSP chain into a channel's signal path (between source and gainNode output)
  function _applyDspRouting(id) {
    const ac = _ac(); if (!ac) return;
    const ch = _mix.channels[id]; if (!ch || !ch.gainNode) return;
    const d  = _mixDsp[id]; if (!d || !d.nodes) return;
    const n  = d.nodes;
    const anyEnabled = d.eq.enabled || d.comp.enabled || d.lim.enabled;
    const dest = _mix.masterGain || ac.destination;
    try { ch.gainNode.disconnect(); } catch(e){/* AudioNode déjà déconnecté */}
    if (!anyEnabled) {
      ch.gainNode.connect(dest);
      return;
    }
    // Build chain: gainNode → [enabled nodes] → dest
    let firstNode = null, lastNode = null;
    if (d.eq.enabled)   { firstNode = firstNode || n.eqLow; lastNode = n.eqHigh; }
    if (d.comp.enabled) {
      if (!firstNode) { firstNode = n.comp; }
      else { try { n.eqHigh.disconnect(); } catch(e){/* chaîne rebuild — node déjà déconnecté */} n.eqHigh.connect(n.comp); }
      lastNode = n.makeup;
    }
    if (d.lim.enabled) {
      if (!firstNode) { firstNode = n.lim; }
      else { try { n.makeup.disconnect(); } catch(e){/* chaîne rebuild */}
             if (!d.comp.enabled) { try { (lastNode||n.eqHigh).disconnect(); } catch(e){/* chaîne rebuild */} (lastNode||n.eqHigh).connect(n.lim); }
             else n.makeup.connect(n.lim); }
      lastNode = n.lim;
    }
    ch.gainNode.connect(firstNode); lastNode.connect(dest);
  }

  // ── Channel select → DSP panel update ──
  window.mixSelectChannel = function(id) {
    _mixSelChan = id;
    document.querySelectorAll('.mix-strip').forEach(s => s.classList.remove('selected'));
    const el = document.getElementById('mix-strip-'+id); if(el) el.classList.add('selected');
    const nameEl = document.getElementById('mix-dsp-chan-name');
    if (nameEl) nameEl.textContent = '— ' + id.toUpperCase() + ' —';
    _ensureDspNodes(id);
    const d = _mixDsp[id] || _defaultDsp();
    // Update EQ sliders
    ['low','mid','pres','high'].forEach(k => {
      const sl = document.getElementById('mix-eq-'+k);
      const vl = document.getElementById('mix-eq-'+k+'-val');
      if (sl) sl.value = d.eq[k] || 0;
      if (vl) vl.textContent = (d.eq[k]>=0?'+':'') + parseFloat(d.eq[k]||0).toFixed(1) + ' dB';
    });
    // Comp sliders
    const compMap = {thr:'threshold','ratio':'ratio',knee:'knee',atk:'attack',rel:'release',mk:'makeup'};
    const compFmt = {threshold:v=>v+' dB',ratio:v=>v+' : 1',knee:v=>v+' dB',attack:v=>v+' ms',release:v=>v+' ms',makeup:v=>(v>=0?'+':'')+v+' dB'};
    Object.entries(compMap).forEach(([slId, param]) => {
      const sl = document.getElementById('mix-comp-'+slId);
      const vl = document.getElementById('mix-comp-'+slId+'-val');
      if (sl) sl.value = d.comp[param] ?? 0;
      if (vl) vl.textContent = compFmt[param](d.comp[param] ?? 0);
    });
    // Lim sliders
    const limCeil = document.getElementById('mix-lim-ceil');
    const limRel  = document.getElementById('mix-lim-rel');
    if (limCeil) limCeil.value = d.lim.ceiling;
    if (limRel)  limRel.value  = d.lim.limrelease;
    const limCeilV = document.getElementById('mix-lim-ceil-val');
    const limRelV  = document.getElementById('mix-lim-rel-val');
    if (limCeilV) limCeilV.textContent = d.lim.ceiling + ' dB';
    if (limRelV)  limRelV.textContent  = d.lim.limrelease + ' ms';
    // Toggle states
    _refreshDspToggles(d);
  };

  function _refreshDspToggles(d) {
    ['eq','comp','lim'].forEach(t => {
      const tog = document.getElementById('mix-dsp-'+t+'-toggle');
      if (tog) tog.classList.toggle('active', d[t].enabled);
    });
  }

  window.mixToggleDsp = function(type) {
    const id = _mixSelChan; if (!id) return;
    if (!_mixDsp[id]) _mixDsp[id] = _defaultDsp();
    _mixDsp[id][type].enabled = !_mixDsp[id][type].enabled;
    const enabled = _mixDsp[id][type].enabled;
    _refreshDspToggles(_mixDsp[id]);

    // JARVIS et DAT partagent la chaîne DSP globale
    if (id === 'jarvis' || id === 'dat') {
      const ac = _ac(); if (!ac) return;
      if (type === 'eq') {
        const nodes = [
          typeof _dspEqLow  !== 'undefined' ? _dspEqLow  : null,
          typeof _dspEqMid  !== 'undefined' ? _dspEqMid  : null,
          typeof _dspEqHigh !== 'undefined' ? _dspEqHigh : null,
          typeof _dspEqAir  !== 'undefined' ? _dspEqAir  : null,
        ];
        // Bypass EQ : remettre tous les gains à 0 ou restaurer les valeurs
        nodes.forEach(n => { if (n) n.gain.setTargetAtTime(enabled ? (n._savedGain||0) : 0, ac.currentTime, 0.02); });
        if (!enabled) nodes.forEach(n => { if (n) n._savedGain = n.gain.value; });
      }
      if (type === 'comp') {
        const comp = typeof _dspCompressor !== 'undefined' ? _dspCompressor : null;
        if (comp) {
          if (!enabled) {
            comp._savedThr = comp.threshold.value; comp._savedRatio = comp.ratio.value;
            comp.threshold.setTargetAtTime(0, ac.currentTime, 0.02);
            comp.ratio.setTargetAtTime(1,   ac.currentTime, 0.02);
          } else {
            comp.threshold.setTargetAtTime(comp._savedThr ?? -24, ac.currentTime, 0.02);
            comp.ratio.setTargetAtTime(comp._savedRatio ?? 4,     ac.currentTime, 0.02);
          }
        }
      }
      if (type === 'lim') {
        const lim = typeof _dspLimiter !== 'undefined' ? _dspLimiter : null;
        if (lim) {
          if (!enabled) {
            // Bypass : sauvegarder et rendre transparent (ratio=1, threshold=0)
            lim._savedThreshold = lim.threshold.value;
            lim._savedRatio     = lim.ratio.value;
            lim.threshold.setTargetAtTime(0,  ac.currentTime, 0.01);
            lim.ratio.setTargetAtTime(1,      ac.currentTime, 0.01);
          } else {
            // Restore
            lim.threshold.setTargetAtTime(lim._savedThreshold ?? -0.5, ac.currentTime, 0.01);
            lim.ratio.setTargetAtTime(lim._savedRatio ?? 20,            ac.currentTime, 0.01);
          }
        }
      }
      return;
    }

    // Canaux micro : routing per-canal
    _ensureDspNodes(id);
    _applyDspRouting(id);
  };

  window.mixToggleDspSection = function(type) {
    const body = document.getElementById('mix-dsp-'+type+'-body');
    const chev = document.getElementById('mix-'+type+'-chevron');
    if (body) body.classList.toggle('collapsed');
    if (chev) chev.textContent = body?.classList.contains('collapsed') ? '▸' : '▾';
  };

  window.mixSetDspParam = function(type, param, val) {
    const id = _mixSelChan; if (!id) return;
    if (!_mixDsp[id]) _mixDsp[id] = _defaultDsp();
    _ensureDspNodes(id);
    const d = _mixDsp[id]; const n = d.nodes;
    const v = parseFloat(val);
    d[type][param] = v;
    // Update label
    const labelMap = {
      low: 'mix-eq-low-val', mid: 'mix-eq-mid-val', pres: 'mix-eq-pres-val', high: 'mix-eq-high-val',
      threshold:'mix-comp-thr-val', ratio:'mix-comp-ratio-val', knee:'mix-comp-knee-val',
      attack:'mix-comp-atk-val', release:'mix-comp-rel-val', makeup:'mix-comp-mk-val',
      ceiling:'mix-lim-ceil-val', limrelease:'mix-lim-rel-val'
    };
    const fmtMap = {
      low:v=>(v>=0?'+':'')+v+' dB', mid:v=>(v>=0?'+':'')+v+' dB',
      pres:v=>(v>=0?'+':'')+v+' dB', high:v=>(v>=0?'+':'')+v+' dB',
      threshold:v=>v+' dB', ratio:v=>v+' : 1', knee:v=>v+' dB',
      attack:v=>v+' ms', release:v=>v+' ms', makeup:v=>(v>=0?'+':'')+v+' dB',
      ceiling:v=>v+' dB', limrelease:v=>v+' ms'
    };
    const lbl = document.getElementById(labelMap[param]);
    if (lbl && fmtMap[param]) lbl.textContent = fmtMap[param](v);
    // Apply to audio node
    const ac = _ac(); if (!ac || !n) return;
    if (type==='eq') {
      if (param==='low')  n.eqLow.gain.setTargetAtTime(v, ac.currentTime, 0.01);
      if (param==='mid')  n.eqMid.gain.setTargetAtTime(v, ac.currentTime, 0.01);
      if (param==='pres') n.eqPres.gain.setTargetAtTime(v, ac.currentTime, 0.01);
      if (param==='high') n.eqHigh.gain.setTargetAtTime(v, ac.currentTime, 0.01);
    }
    if (type==='comp') {
      if (param==='threshold') n.comp.threshold.setTargetAtTime(v, ac.currentTime, 0.01);
      if (param==='ratio')     n.comp.ratio.setTargetAtTime(v, ac.currentTime, 0.01);
      if (param==='knee')      n.comp.knee.setTargetAtTime(v, ac.currentTime, 0.01);
      if (param==='attack')    n.comp.attack.setTargetAtTime(v/1000, ac.currentTime, 0.01);
      if (param==='release')   n.comp.release.setTargetAtTime(v/1000, ac.currentTime, 0.01);
      if (param==='makeup')    n.makeup.gain.setTargetAtTime(Math.pow(10,v/20), ac.currentTime, 0.01);
    }
    if (type==='lim') {
      if (param==='ceiling')    n.lim.threshold.setTargetAtTime(v, ac.currentTime, 0.01);
      if (param==='limrelease') n.lim.release.setTargetAtTime(v/1000, ac.currentTime, 0.01);
    }
  };

  // ── Helpers analyseurs réels (actifs dans le graph Web Audio) ──
  function _realAnJarvis() {
    // analyserL/analyserR sont les vrais noeuds JARVIS (TTS → analyser → analyserL)
    const L = (typeof analyserL !== 'undefined' && analyserL) ? analyserL : null;
    const R = (typeof analyserR !== 'undefined' && analyserR) ? analyserR : L;
    return [L, R];
  }
  function _realAnDat() {
    // window._datAnL/R exposés par le module DAT (autre IIFE) via _datMakeAnalysers()
    const L = (window._datAnL) ? window._datAnL : null;
    const R = (window._datAnR) ? window._datAnR : L;
    return [L, R];
  }

  // ── RAF loop VU mètres ───────────────────────────────────────
  function _mixRafLoop() {
    _mix.rafId = requestAnimationFrame(_mixRafLoop);

    // JARVIS : analyseurs réels (actifs qd JARVIS parle)
    const [jL, jR] = _realAnJarvis();
    _drawMixVu('mix-vu-jarvis', jL, jR);

    // DAT : analyseurs réels (actifs qd DAT joue)
    const [dL, dR] = _realAnDat();
    _drawMixVu('mix-vu-dat', dL, dR);

    // MASTER : analyserL/R de sortie DSP
    _drawMixVu('mix-vu-master', _mix.masterAnalyserL, _mix.masterAnalyserR);

    // Canaux dynamiques (entrées micro armées)
    Object.keys(_mix.channels).forEach(id => {
      if (id==='jarvis'||id==='dat') return;
      _drawMixVu('mix-vu-'+id, _mix.channels[id]?.analyserL, _mix.channels[id]?.analyserR);
    });

    // DSP panel large VU — canal sélectionné ou MASTER par défaut
    {
      let vuL, vuR;
      const ch = _mixSelChan || 'master';
      if (ch === 'jarvis')      { [vuL, vuR] = _realAnJarvis(); }
      else if (ch === 'dat')    { [vuL, vuR] = _realAnDat(); }
      else                      { vuL = _mix.masterAnalyserL; vuR = _mix.masterAnalyserR; }
      if (!_mixSelChan && _mix.channels[ch]) {
        vuL = _mix.channels[ch].analyserL; vuR = _mix.channels[ch].analyserR;
      }
      _drawMixVuBig('mix-dsp-vu', vuL, vuR);
    }
  }

  // ── Refresh devices & build dynamic strips ───────────────────
  window.mixRefreshDevices = async function() {
    try {
      // Demande permission une seule fois
      await navigator.mediaDevices.getUserMedia({audio:true}).then(s=>s.getTracks().forEach(t=>t.stop())).catch(()=>{});
      const devices = await navigator.mediaDevices.enumerateDevices();
      _mix.devices = devices.filter(d=>d.kind==='audioinput');
      const container = document.getElementById('mix-dynamic-strips');
      if (!container) return;
      container.innerHTML = '';
      _mix.devices.forEach((dev, idx) => {
        const id = 'in'+idx;
        const label = dev.label || 'Input '+(idx+1);
        const strip = document.createElement('div');
        strip.className = 'mix-strip';
        strip.id = 'mix-strip-'+id;
        strip.setAttribute('onclick',`mixSelectChannel('${id}')`);
        strip.innerHTML = `
          <div class="mix-strip-hdr">
          <div class="mix-strip-label" title="${_esc(label)}">${_esc(label.substring(0,9))}</div>
          <div class="mix-device-id">${_esc(dev.deviceId.substring(0,6))}…</div>
          </div>
          <button class="mix-arm-btn" id="mix-arm-${id}" onclick="event.stopPropagation();mixArmInput('${id}',${JSON.stringify(dev.deviceId)})">▷ ARM</button>
          <button class="mix-btn mix-btn-agc" id="mix-agc-${id}" onclick="event.stopPropagation();mixToggleAgc('${id}')">AGC</button>
          <canvas class="mix-vu-canvas" id="mix-vu-${id}" height="80"></canvas>
          <div class="mix-fader-wrap">
            <canvas class="mix-grad-canvas" id="mix-grad-${id}" width="14" height="160"></canvas>
            <input type="range" class="mix-fader" id="mix-fader-${id}" min="0" max="150" value="100"
                   oninput="mixSetGain('${id}',this.value)">
          </div>
          <input type="range" class="mix-pan" id="mix-pan-${id}" min="-100" max="100" value="0"
                 oninput="mixSetPan('${id}',this.value)" title="Pan">
          <div class="mix-ms-row">
            <button class="mix-btn mix-btn-m" id="mix-m-${id}" onclick="mixToggleMute('${id}')">M</button>
            <button class="mix-btn mix-btn-s" id="mix-s-${id}" onclick="mixToggleSolo('${id}')">S</button>
          </div>
          <div class="mix-lcd" id="mix-lcd-${id}">0.0 dB</div>`;
        container.appendChild(strip);
        setTimeout(()=>_drawGrad('mix-grad-'+id), 50);
      });
      _mixSetStatus(_mix.devices.length + ' entrées détectées', true);
    } catch(e) { _mixSetStatus('Erreur devices: '+e.message, false); }
  };

  window.mixArmInput = function(id, deviceId) {
    const ch = _mix.channels[id];
    if (ch && ch.stream) { _disarmChannel(id); return; }
    _armInputChannel(id, deviceId);
  };

  window.mixToggleAgc = function(id) {
    const ch  = _mix.channels[id];
    const btn = document.getElementById('mix-agc-'+id);
    const active = ch ? !ch.agcActive : false;
    if (ch) {
      ch.agcActive = active;
      if (ch.agcNode) {
        if (active) {
          // AGC actif : limiteur doux -18dB threshold, ratio 8:1
          ch.agcNode.threshold.setTargetAtTime(-18, _ac().currentTime, 0.01);
          ch.agcNode.ratio.setTargetAtTime(8,    _ac().currentTime, 0.01);
          ch.agcNode.knee.setTargetAtTime(8,     _ac().currentTime, 0.01);
        } else {
          // AGC off : transparent (ratio 1 = pas de compression)
          ch.agcNode.threshold.setTargetAtTime(0, _ac().currentTime, 0.01);
          ch.agcNode.ratio.setTargetAtTime(1,     _ac().currentTime, 0.01);
          ch.agcNode.knee.setTargetAtTime(0,      _ac().currentTime, 0.01);
        }
      }
    }
    if (btn) btn.classList.toggle('active', active);
  };

  // ── Status display ───────────────────────────────────────────
  function _mixSetStatus(msg, ok) {
    const led = document.getElementById('mix-status-led');
    const lbl = document.getElementById('mix-status-lbl');
    if (led) { led.classList.remove('mix-led--ok','mix-led--err'); led.classList.add(ok ? 'mix-led--ok' : 'mix-led--err'); }
    if (lbl) { lbl.textContent=msg; lbl.classList.toggle('mix-lbl--ok', !!ok); lbl.classList.toggle('mix-lbl--err', !ok); }
    setTimeout(()=>{ if(led){ led.classList.remove('mix-led--ok','mix-led--err'); } },3000);
  }

  // ── Open / Close ─────────────────────────────────────────────
  window.openMixerModal = function() {
    const m = document.getElementById('mixer-modal'); if(!m) return;
    m.classList.add('open');
    _initMaster();
    _initJarvisChannel();
    _initDatChannel();
    // Draw static graduation canvases after layout is computed
    setTimeout(() => {
      ['jarvis','dat','master'].forEach(id => _drawGrad('mix-grad-'+id));
      // Force VU canvas width sync after modal is visible
      document.querySelectorAll('.mix-vu-canvas').forEach(cv => {
        const CW = cv.offsetWidth || cv.parentElement?.offsetWidth || 140;
        if (CW > 0) { cv.width = CW; cv.height = 80; }
      });
      // Sync DSP large VU canvas
      const dvu = document.getElementById('mix-dsp-vu');
      if (dvu) {
        const CW2 = dvu.offsetWidth || dvu.parentElement?.offsetWidth || 500;
        if (CW2 > 0) { dvu.width = CW2; dvu.height = 220; }
      }
    }, 80);
    if (!_mix.rafId) _mixRafLoop();
    mixRefreshDevices();
  };

  window.closeMixerModal = function() {
    // Ne déconnecte PAS les nœuds — reste actif en arrière-plan
    const m = document.getElementById('mixer-modal'); if(m) m.classList.remove('open');
  };

})();

// ── Polling /api/speak/queue — SOC alerts Python → Web Audio (fader + DSP + mixer) ──
(function() {
  setInterval(async function() {
    if (typeof queueSpeech !== 'function') return;
    try {
      const r = await fetch('/api/speak/queue', { cache: 'no-store' });
      if (!r.ok) return;
      const d = await r.json();
      (d.items || []).forEach(function(text) {
        if (text) queueSpeech(text);
      });
    } catch(_) { /* network error — skip speech queue poll */ }
  }, 1000);
})();
