// ══════════════════════════════════════════════════════════════
// DSP AUDIO SYSTEM — Chaîne de traitement audio (UI)
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// Système DSP audio côté UI : init/sync de la chaîne de traitement
// (gain, compresseur, limiteur, EQ bandes), push des paramètres vers
// le backend Python, dessin du canvas DSP. Fichier .js classique
// (scope global). Chargé APRÈS jarvis_main.js.

let _dspInited    = false;
let _dspRafId     = null;
let _eqPanelOn    = true;  // false quand le panel EQ est bypassed (⏻)
let _dspAnalyser  = null;
let _dspDataArray = null;
let _dspEqLow     = null;
let _dspEqMid     = null;
let _dspEqHigh    = null;
let _dspEqAir     = null;
let _dspCompressor= null;
let _dspGainNode   = null;
let _jarvisPreGain = null; // gain JARVIS uniquement (avant _dspAnalyser)
let _dspLimiter    = null; // limiteur global (après compresseur)
let _dspVoiceBypass   = null; // bypass voix DSP → destination (découplage voix/DSP)
let _dspVoiceDecoupled = false; // true = voix JARVIS bypass DSP
let _dspPlaybackRate = 1.0;
let _dspPitchSemi = 0;
let _dspVolume    = 1.0;
let _fxConvolver   = null;  // ConvolverNode WebAudio (reverb/echo/delay IR — normalize=true)
let _fxDryGain     = null;  // chemin direct (dry) vers destination
let _fxWetGain     = null;  // gain wet final (equal-power crossfade)
let _masterLimiter = null;  // brick-wall limiter final (-0.3 dBFS) — sécurité unique
let _haasDelayNode = null;  // noeud delay persistant mono→stéréo (Haas effect canal R)
let _haasGainNode  = null;  // gain canal R = stereo_width (0=mono, 1=max largeur)
let _stereoWidth   = 85;    // valeur courante en pourcents
let _specColorTable = null; // table couleurs barres spectrum (160 entrées, freq → [r,g,b])
let _specBinMap     = null; // mapping barres → plages bins FFT (160 entrées)
let _rackSpecMode   = 'mirror'; // mode affichage rack-spectrum-canvas
let _scopeGain      = 1.0;      // auto-gain oscilloscope (lissé)

const DSP_PROFILES = {
  flat:      { low:0,  mid:0,  high:0,  air:0,  thresh:-24, ratio:4,  attack:3,  release:250, gain:0 },
  clair:     { low:-2, mid:1,  high:3,  air:2,  thresh:-20, ratio:3,  attack:5,  release:200, gain:0 },
  studio:    { low:2,  mid:0,  high:2,  air:3,  thresh:-24, ratio:4,  attack:3,  release:250, gain:1 },
  robotic:   { low:-6, mid:8,  high:2,  air:0,  thresh:-30, ratio:8,  attack:2,  release:100, gain:0 },
  broadcast: { low:3,  mid:2,  high:4,  air:3,  thresh:-18, ratio:5,  attack:4,  release:200, gain:2 },
  jarvis:    { low:4,  mid:-1, high:5,  air:4,  thresh:-28, ratio:6,  attack:3,  release:300, gain:1 },
  deep:      { low:8,  mid:2,  high:-2, air:-3, thresh:-20, ratio:4,  attack:5,  release:300, gain:0 },
};

function _initDspApplyAudioParams(p){
  if(p.gain!==undefined){
    setDspGain(p.gain);
    const rg=document.getElementById('rack-gain');
    if(rg){rg.value=p.gain;_syncRangeSlider(rg);}
  }
  [['threshold',p.comp_threshold],['ratio',p.comp_ratio],
   ['attack',Math.round((p.comp_attack||0.003)*1000)],
   ['release',Math.round((p.comp_release||0.25)*1000)]
  ].forEach(function(pair){
    var param=pair[0],val=pair[1]; if(val===undefined) return;
    setDspCompressor(param,val);
    var rackId={threshold:'rack-comp-thresh',ratio:'rack-comp-ratio',attack:'rack-comp-att',release:'rack-comp-rel'};
    var rs2=document.getElementById(rackId[param]); if(rs2){rs2.value=val;_syncRangeSlider(rs2);}
  });
  ['low','mid','high','air'].forEach(function(id){
    var g=p['eq_'+id],sl=document.getElementById('eq-'+id);
    if(g!==undefined&&sl){sl.value=g;setEqBand(id,g);}
    if(p['eq_'+id+'_freq']) eqSetFreq(id,p['eq_'+id+'_freq']);
    if(p['eq_'+id+'_q'])    eqSetQ(id,p['eq_'+id+'_q']);
    if(p['eq_'+id+'_type']) eqSetType(id,p['eq_'+id+'_type']);
    if(p['eq_'+id+'_byp'])  eqToggleBypass(id);
  });
  ['sub','bass','mids','treble'].forEach(function(id){
    var g=p['dat_eq_'+id],sl=document.getElementById('dat-eq-'+id);
    if(g!==undefined&&sl){sl.value=g;setDatEqBand(id,g);}
    if(p['dat_eq_'+id+'_freq']) datEqSetFreq(id,p['dat_eq_'+id+'_freq']);
    if(p['dat_eq_'+id+'_q'])    datEqSetQ(id,p['dat_eq_'+id+'_q']);
    if(p['dat_eq_'+id+'_type']) datEqSetType(id,p['dat_eq_'+id+'_type']);
    if(p['dat_eq_'+id+'_byp'])  datEqToggleBypass(id);
  });
}
function _initDspApplyUiParams(p){
  const mt=document.getElementById('dsp-master-toggle');
  if(mt) mt.classList.toggle('on',!!p.enabled);
  _updateDspChainStatus(!!p.enabled);
  const dfOn=!!p.df_enabled, dfBtn=document.getElementById('rack-df-bypass');
  if(dfBtn){dfBtn.classList.toggle('on',dfOn);dfBtn.classList.toggle('off',!dfOn);}
  document.getElementById('rack-unit-df')?.classList.toggle('bypassed',!dfOn);
  document.getElementById('rsp-df')?.classList.toggle('active',dfOn);
  const swEl=document.getElementById('rack-stereo-width'), hdEl=document.getElementById('rack-haas-delay');
  const stereoOn=p.stereo_enabled!==false;
  if(swEl){swEl.value=Math.round((p.stereo_width??0.85)*100);rackSyncStereoWidth(swEl.value);}
  if(hdEl){hdEl.value=p.haas_delay_ms??18;rackSyncHaasDelay(hdEl.value);}
  const sBtn=document.getElementById('rack-stereo-bypass');
  if(sBtn){sBtn.classList.toggle('on',stereoOn);sBtn.classList.toggle('off',!stereoOn);}
  document.getElementById('rack-unit-stereo')?.classList.toggle('bypassed',!stereoOn);
  document.getElementById('rsp-stereo')?.classList.toggle('active',stereoOn);
  const sTag=document.getElementById('rack-stereo-tag');
  if(sTag){sTag.textContent=stereoOn?'L + R':'MONO';sTag.className='rack-unit-tag '+(stereoOn?'tag-ok':'');}
  const fxOn=!!p.fx_enabled; _fxActive=fxOn;
  const fxBtn=document.getElementById('rack-fx-bypass'), fxUnit=document.getElementById('rack-unit-fx');
  const fxNode=document.getElementById('rsp-fx'), fxLabel=document.getElementById('fx-proc-label');
  if(fxBtn){fxBtn.classList.toggle('on',fxOn);fxBtn.classList.toggle('off',!fxOn);}
  if(fxUnit) fxUnit.classList.toggle('bypassed',!fxOn);
  if(fxNode){fxNode.classList.toggle('active',fxOn);fxNode.classList.toggle('fx-bypass-node',!fxOn);}
  if(fxLabel) fxLabel.textContent=fxOn?'◉ ACTIF':'BYPASS';
  if(_fxDryGain&&_fxWetGain&&_fxConvolver){
    const fxType=p.fx_type||'reverb'; _fx2Type=fxType; _fxType=fxType;
    const savedVals={};
    if(_FX2[fxType]){_FX2[fxType].params.forEach(function(pm){if(p[pm.key]!==undefined)savedVals[pm.key]=p[pm.key];});}
    if(!_fx2Vals[fxType]) _fx2Vals[fxType]=savedVals;
    const wet=p.fx_wet!==undefined?p.fx_wet:0.4;
    if(!_fx2Vals[fxType].fx_wet) _fx2Vals[fxType].fx_wet=wet;
    if (typeof _fxRefreshIr === 'function') _fxRefreshIr(fxType, _fx2Vals[fxType]);
    if(fxOn) _fxSetWetDry(wet, false);
  }
  const srEl=document.getElementById('rack-stereo-sr');
  if(srEl) srEl.textContent=(audioCtx.sampleRate||_SAMPLE_RATE)+' Hz';
  document.querySelectorAll('.rack-fader').forEach(f=>{
    const pct=((parseFloat(f.value)-parseFloat(f.min))/(parseFloat(f.max)-parseFloat(f.min))*100).toFixed(1);
    f.style.setProperty('--f-pct',pct+'%');
  });
}
function _initDspCreateNodes(){
  _dspAnalyser = audioCtx.createAnalyser();
  _dspAnalyser.fftSize = 2048;
  _dspAnalyser.smoothingTimeConstant = 0.82;
  _dspDataArray = new Uint8Array(_dspAnalyser.frequencyBinCount);
  const _eqNodes = [null, null, null, null];
  [_dspEqLow, _dspEqMid, _dspEqHigh, _dspEqAir] = [0,1,2,3].map(i => {
    const f = audioCtx.createBiquadFilter();
    f.type = _eqState[i].type; f.frequency.value = _eqState[i].freq;
    f.Q.value = _eqState[i].q; f.gain.value = 0;
    return f;
  });
  window._dspEqLow=_dspEqLow; window._dspEqMid=_dspEqMid;
  window._dspEqHigh=_dspEqHigh; window._dspEqAir=_dspEqAir;
  // ── COMPRESSEUR VOIX — réglage doux type broadcast vocal ──
  // Threshold haut + ratio doux = peu d'action sauf pics > -12 dBFS
  // Compensation par makeup gain ci-dessous (sinon signal écrasé sans récupération)
  _dspCompressor = audioCtx.createDynamicsCompressor();
  _dspCompressor.threshold.value = -12;   // était -24 (trop bas → écrasement permanent)
  _dspCompressor.ratio.value     = 2;     // était 4:1 (trop agressif)
  _dspCompressor.attack.value    = 0.010; // 10ms — laisse passer transitoires courtes
  _dspCompressor.release.value   = 0.150; // 150ms — récupération naturelle
  _dspCompressor.knee.value      = 6;
  // Makeup gain compensatoire — restaure le niveau perçu après compression
  _dspGainNode = audioCtx.createGain();
  _dspGainNode.gain.value = 1.5;          // +3.5 dB — compense les ~3 dB de gain reduction max
  // ── LIMITER VOIX — brick-wall plus haut, laisse de la place au mix ──
  _dspLimiter = audioCtx.createDynamicsCompressor();
  _dspLimiter.threshold.value = -1.5;     // était -0.5 (trop proche du clip, déclenchait sur peanuts)
  _dspLimiter.ratio.value     = 20;
  _dspLimiter.attack.value    = 0.002;
  _dspLimiter.release.value   = 0.080;
  _dspLimiter.knee.value      = 0;
  // ── BUS FX SIMPLE — dry direct + wet via convolver, plus de routing intermédiaire ──
  _fxConvolver = audioCtx.createConvolver();
  _fxConvolver.normalize = true;       // Web Audio normalise l'IR nativement
  _fxConvolver.buffer = null;          // pas d'IR initiale → wet path silencieux jusqu'à activation FX
  _fxDryGain = audioCtx.createGain();  _fxDryGain.gain.value = 1.0;
  _fxWetGain = audioCtx.createGain();  _fxWetGain.gain.value = 0.0;

  // ── BRICK-WALL LIMITER FINAL (sécurité absolue, capture wet+dry en sortie) ──
  _masterLimiter = audioCtx.createDynamicsCompressor();
  _masterLimiter.threshold.value = -0.3;
  _masterLimiter.ratio.value     = 20;
  _masterLimiter.attack.value    = 0.001;
  _masterLimiter.release.value   = 0.05;
  _masterLimiter.knee.value      = 0;

  window._fxDryGain=_fxDryGain; window._fxWetGain=_fxWetGain; window._fxConvolver=_fxConvolver;
  window._masterLimiter=_masterLimiter;
}
function _initDspWireChain(){
  // ─────────────────────────────────────────────────────────────────────────
  // CHAÎNE AUDIO SIMPLIFIÉE — minimal routing, anti-bug duplication
  //
  // analyser → preGain → dspAnalyser → EQ4b → comp → voice limiter → outGain
  //                                                                     │
  //                                              ┌──────────────────────┤
  //                                              │                      │
  //                                              ▼                      ▼
  //                                         _fxDryGain (1.0)      _fxConvolver
  //                                              │                      │
  //                                              │                      ▼
  //                                              │               _fxWetGain (0.0 init)
  //                                              │                      │
  //                                              └──→ _masterLimiter ◄──┘
  //                                                          │
  //                                                          ▼
  //                                                  audioCtx.destination
  // ─────────────────────────────────────────────────────────────────────────
  _dspCompressor.connect(_dspLimiter); _dspLimiter.connect(_dspGainNode);

  // Sortie voice channel → DRY direct + WET via convolver
  _dspGainNode.connect(_fxDryGain);
  _dspGainNode.connect(_fxConvolver);
  _fxConvolver.connect(_fxWetGain);

  // Sommation finale : dry + wet → master limiter → destination (un seul path par signal)
  _fxDryGain.connect(_masterLimiter);
  _fxWetGain.connect(_masterLimiter);
  _masterLimiter.connect(audioCtx.destination);
  window._dspAnalyser=_dspAnalyser; window._dspCompressor=_dspCompressor;
  if(window._datPreDsp){
    try{window._datPreDsp.disconnect();}catch(e){}
    if(window._datEqSub&&window._datEqSub.context===audioCtx){
      try{window._datEqTreble.disconnect();}catch(e){}
      try{window._datEqTreble.connect(_dspCompressor);}catch(e){}
      try{window._datPreDsp.connect(window._datEqSub);}catch(e){}
    }else{try{window._datPreDsp.connect(_dspCompressor);}catch(e){}}
  }
  _jarvisPreGain=audioCtx.createGain(); _jarvisPreGain.gain.value=1.0;
  analyser.connect(_jarvisPreGain); _jarvisPreGain.connect(_dspAnalyser);
  _dspAnalyser.connect(_dspEqLow); _dspEqLow.connect(_dspEqMid);
  _dspEqMid.connect(_dspEqHigh); _dspEqHigh.connect(_dspEqAir); _dspEqAir.connect(_dspCompressor);
  try{analyser.disconnect(audioCtx.destination);}catch(e){}
  _dspVoiceBypass=audioCtx.createGain(); _dspVoiceBypass.gain.value=0;
  analyser.connect(_dspVoiceBypass); _dspVoiceBypass.connect(audioCtx.destination);
  window._dspVoiceBypass=_dspVoiceBypass;
}
function initDsp() {
  if (_dspInited) return;
  if (!_ensureAudioCtx()) return;
  _dspInited = true;
  _initDspCreateNodes();
  _initDspWireChain();
  syncDspVoices();
  document.querySelectorAll('.dsp-hslider').forEach(sl => updateSliderPct(sl));
  setTimeout(drawEqCurve, _EQ_REDRAW_MS);
  _updateEqCoupleBadges();
  startDspDraw();
  _fetchDspParams().then(p=>{
    if(!p) return;
    _initDspApplyAudioParams(p);
    _initDspApplyUiParams(p);
    // Pré-génération IR du type FX courant — 1er toggle ON instantané
    if (_fx2Type && typeof _fxRefreshIr === 'function') {
      _fxRefreshIr(_fx2Type, _fx2Vals[_fx2Type] || {});
    }
  }).catch(()=>{});
  rackInitFaders();
}

function updateSliderPct(sl) {
  if (!sl) return;
  const min = parseFloat(sl.min), max = parseFloat(sl.max), val = parseFloat(sl.value);
  const raw = (val - min) / (max - min);
  const w = sl.offsetWidth;
  const isDatEq = sl.classList.contains('dat-eq-slider');
  if (w > 20) {
    const pct = ((raw * (w - 18) + 9) / w * 100).toFixed(2);
    sl.style.setProperty('--pct', pct + '%');
    if (isDatEq) {
      const cRaw = (-min) / (max - min);
      const cPct = ((cRaw * (w - 18) + 9) / w * 100);
      const p = parseFloat(pct);
      const diff = Math.abs(p - cPct);
      if (diff < 0.8) {
        sl.style.setProperty('--fill-s', '49.3%');
        sl.style.setProperty('--fill-e', '50.7%');
      } else {
        sl.style.setProperty('--fill-s', Math.min(p, cPct).toFixed(2) + '%');
        sl.style.setProperty('--fill-e', Math.max(p, cPct).toFixed(2) + '%');
      }
    }
  } else {
    sl.dataset.rawPct = raw.toFixed(4);
    sl.style.setProperty('--pct', (raw * 100).toFixed(1) + '%');
    if (isDatEq) {
      sl.style.setProperty('--fill-s', '49.3%');
      sl.style.setProperty('--fill-e', '50.7%');
    }
  }
}

// Recalcule tous les curseurs DSP quand le tab devient visible
function _refreshDspSliders() {
  document.querySelectorAll('.dsp-hslider').forEach(sl => {
    if (sl.dataset.rawPct !== undefined && sl.offsetWidth > 20) {
      const raw = parseFloat(sl.dataset.rawPct);
      const w   = sl.offsetWidth;
      sl.style.setProperty('--pct', ((raw * (w - 18) + 9) / w * 100).toFixed(2) + '%');
      delete sl.dataset.rawPct;
    } else {
      updateSliderPct(sl);
    }
  });
}
