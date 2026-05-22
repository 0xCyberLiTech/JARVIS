/* =============================================================================
   VOICE PRINT v2 — Analyse empreinte vocale pro (librosa back-end)
   Sélecteur vocal — sélection graphique de portion audio
   ============================================================================= */
(function() {
  'use strict';

  var _vpData      = null;
  var _vpMicRec    = null;
  var _vpMicChunks = [];
  var _vpParams    = { fmin:50, fmax:800, n_mels:32 };

  /* Selector / playback state */
  var _vpAudioBuffer = null;
  var _vpAudioCtx    = null;
  var _vpPlaySource  = null;
  var _vpSelStart    = 0;
  var _vpSelEnd      = 0;

  /* ─── Init ─────────────────────────────────────────────────── */
  function _vpInit() {
    _vpInitDrop();
    _vpInitSelector();
    _vpDrawPlaceholders();
    _vpRenderEqBands({ low:0, lomid:0, mid:0, himid:0, air:0 });
    _vpRenderProfileList();
    _vpLoadLibrary();
    _vpLoadPrints();
  }

  function _vpInitDrop() {
    var zone = document.getElementById('vp-drop-zone');
    var inp  = document.getElementById('vp-file-input');
    if (!zone || !inp) return;
    zone.addEventListener('dragover', function(e){ e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', function(){ zone.classList.remove('drag-over'); });
    zone.addEventListener('drop', function(e){
      e.preventDefault(); zone.classList.remove('drag-over');
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) _vpAnalyse(f);
    });
    zone.addEventListener('click', function(){ inp.click(); });
    inp.addEventListener('change', function(){
      if (inp.files && inp.files[0]) { _vpAnalyse(inp.files[0]); inp.value=''; }
    });
  }

  /* ─── Placeholder canvases ──────────────────────────────────── */
  function _vpDrawPlaceholders() {
    requestAnimationFrame(function(){
      _vpPlaceholder('vp-waveform', '#00cfff', '— EN ATTENTE —');
      _vpPlaceholder('vp-pitch',    '#00ff88', 'PITCH F0 — EN ATTENTE');
      _vpPlaceholder('vp-spectrum', '#00aaff', 'SPECTRE MEL — EN ATTENTE');
    });
  }

  function _vpPlaceholder(id, color, label) {
    var c = document.getElementById(id); if (!c) return;
    var w = c.offsetWidth || 400; c.width = w;
    var ctx = c.getContext('2d');
    ctx.fillStyle = '#000d14'; ctx.fillRect(0,0,w,c.height);
    ctx.strokeStyle = color+'10'; ctx.lineWidth = 1;
    for (var y=0; y<=c.height; y+=c.height/4){
      ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(w,y); ctx.stroke();
    }
    for (var x=0; x<=w; x+=w/8){
      ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,c.height); ctx.stroke();
    }
    ctx.fillStyle = color+'22'; ctx.font = '9px Share Tech Mono,monospace';
    ctx.textAlign = 'center';
    ctx.fillText(label, w/2, c.height/2+4);
    ctx.textAlign = 'left';
  }

  /* ─── EQ preview ────────────────────────────────────────────── */
  function _vpRenderEqBands(eq) {
    var prev = document.getElementById('vp-eq-preview'); if (!prev) return;
    var bands = [
      { lbl:'LOW',    hz:'80',   val: eq.low   || 0 },
      { lbl:'LO-MID', hz:'400',  val: eq.lomid || 0 },
      { lbl:'MID',    hz:'2.5k', val: eq.mid   || 0 },
      { lbl:'HI-MID', hz:'6k',   val: eq.himid || 0 },
      { lbl:'AIR',    hz:'14k',  val: eq.air   || 0 },
    ];
    prev.innerHTML = bands.map(function(b){
      var bw  = Math.min(Math.abs(b.val)*4, 50);
      var sgn = b.val > 0 ? '+' : '';
      var mod = b.val > 0 ? 'pos' : (b.val < 0 ? 'neg' : 'zero');
      var ml  = b.val >= 0 ? '50%' : (50+b.val*4)+'%';
      return '<div class="vp-eq-band">'
        +'<span class="vp-eq-lbl">'+b.lbl+'</span>'
        +'<div class="vp-eq-bar-wrap">'
          +'<div class="vp-eq-bar-fill vp-eq-bar-fill--'+mod+'" style="width:'+bw+'%;margin-left:'+ml+'"></div>'
          +'<div class="vp-eq-bar-mid"></div>'
        +'</div>'
        +'<span class="vp-eq-val vp-eq-val--'+mod+'">'+(b.val===0?'0':sgn+b.val)+' dB</span>'
        +'<span class="vp-eq-hz">'+b.hz+'</span>'
        +'</div>';
    }).join('');
  }

  /* ─── Status helpers ────────────────────────────────────────── */
  function _vpSetInfo(msg, err) {
    var el = document.getElementById('vp-file-info');
    if (el) { el.textContent = msg; el.classList.toggle('vp-msg-err', !!err); el.classList.toggle('vp-msg-ok', !err); }
  }
  function _vpShowSpinner(on) {
    var s = document.getElementById('vp-spinner');
    _disp(s, on, 'flex');
  }

  /* ─── Analysis ──────────────────────────────────────────────── */
  async function _vpAnalyse(file) {
    _vpSetInfo('◈ '+file.name+' — '+(file.size/1024).toFixed(0)+' Ko');
    _vpShowSpinner(true);
    _vpDecodeFileForSelector(file);
    var fd = new FormData();
    fd.append('audio', file);
    fd.append('fmin',   _vpParams.fmin);
    fd.append('fmax',   _vpParams.fmax);
    fd.append('n_mels', _vpParams.n_mels);
    try {
      var r = await fetch('/api/voice/analyse', { method:'POST', body:fd });
      if (!r.ok) {
        var txt = await r.text();
        var detail = r.status===413 ? '— fichier trop volumineux · max 200 Mo · utiliser un sample 3–30s'
                   : r.status===404 ? '— route introuvable · redémarrer JARVIS'
                   : txt.startsWith('<') ? '— erreur serveur · redémarrer JARVIS'
                   : '— '+txt.slice(0,80);
        throw new Error('HTTP '+r.status+' '+detail);
      }
      var d = await r.json();
      _vpShowSpinner(false);
      if (!d.ok) { _vpSetInfo('⚠ '+(d.error||'Erreur analyse'), true); return; }
      _vpData = d;
      _vpRender(d);
      _vpSetInfo('◈ Analyse OK — '+d.duration+'s · '+d.sr+' Hz');
    } catch(e) {
      _vpShowSpinner(false);
      _vpSetInfo('⚠ '+e.message, true);
    }
  }

  /* ─── Render results ────────────────────────────────────────── */
  function _vpRender(d) {
    _vpUpdateMetrics(d);
    _vpUpdateProfile(d);
    _vpRenderEqBands(d.eq_preset || {});
    requestAnimationFrame(function(){
      _vpDrawWaveform(d.waveform);
      _vpDrawPitch(d.pitch_curve, (d.params||{}).fmin||50, (d.params||{}).fmax||800);
      _vpDrawSpectrum(d.spectrum);
    });
  }

  function _vpUpdateMetrics(d) {
    var m = d.metrics || {};
    function s(id,v){ var el=document.getElementById(id); if(el) el.textContent=v; }
    s('vpm-type',    m.voice_type || '—');
    s('vpm-pitch',   m.pitch_median ? m.pitch_median+' Hz  ('+m.pitch_min+'–'+m.pitch_max+')' : '—');
    s('vpm-centroid',m.spectral_centroid ? Math.round(m.spectral_centroid)+' Hz — '+m.brightness : '—');
    s('vpm-rolloff', m.rolloff_hz ? Math.round(m.rolloff_hz)+' Hz' : '—');
    s('vpm-voicing', m.voicing || '—');
    s('vpm-timbre',  m.breathiness || '—');
    s('vpm-dynamic', m.dynamic_range_db != null ? m.dynamic_range_db+' dB' : '—');
    s('vpm-dur',     d.duration ? d.duration+'s · '+d.sr+' Hz' : '—');
    var badge = document.getElementById('vp-voice-badge');
    if (badge) badge.textContent = m.voice_type || '—';
  }

  function _vpUpdateProfile(d) {
    var m = d.metrics || {};
    function s(id,v){ var el=document.getElementById(id); if(el) el.textContent=v; }
    s('vpp-timbre',  m.brightness  || '—');
    s('vpp-texture', m.breathiness || '—');
    s('vpp-voicing', m.voicing     || '—');
    s('vpp-dynamic', m.dynamic_range_db != null ? m.dynamic_range_db+' dB' : '—');
  }

  /* ─── Canvas drawing ────────────────────────────────────────── */
  function _vpDrawWaveform(wf) {
    var c = document.getElementById('vp-waveform'); if (!c || !wf || !wf.length) return;
    var w = c.offsetWidth || 400; c.width = w;
    var h = c.height, mid = h / 2;
    var ctx = c.getContext('2d');
    ctx.fillStyle = '#000d14'; ctx.fillRect(0, 0, w, h);
    /* grid */
    ctx.strokeStyle = '#00cfff0d'; ctx.lineWidth = 1;
    [0.25, 0.5, 0.75].forEach(function(t) {
      var gy = Math.round(h * t) + 0.5;
      ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke();
    });
    ctx.strokeStyle = '#00cfff22'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, mid); ctx.lineTo(w, mid); ctx.stroke();
    /* downsample to pixel columns */
    var scale = 0.90, step = wf.length / w;
    var pts = [];
    for (var xi = 0; xi < w; xi++) {
      var i0 = Math.floor(xi * step), i1 = Math.min(wf.length, Math.ceil((xi + 1) * step));
      var peak = 0;
      for (var k = i0; k < i1; k++) { var av = Math.abs(wf[k]); if (av > peak) peak = av; }
      pts.push(peak);
    }
    /* mirrored gradient fill */
    var fillGrad = ctx.createLinearGradient(0, 0, 0, h);
    fillGrad.addColorStop(0,    'rgba(0,207,255,0.04)');
    fillGrad.addColorStop(0.42, 'rgba(0,207,255,0.22)');
    fillGrad.addColorStop(0.5,  'rgba(0,207,255,0.32)');
    fillGrad.addColorStop(0.58, 'rgba(0,207,255,0.22)');
    fillGrad.addColorStop(1,    'rgba(0,207,255,0.04)');
    ctx.fillStyle = fillGrad;
    ctx.beginPath();
    ctx.moveTo(0, mid);
    for (var xi = 0; xi < w; xi++) ctx.lineTo(xi, mid - pts[xi] * mid * scale);
    for (var xi = w - 1; xi >= 0; xi--) ctx.lineTo(xi, mid + pts[xi] * mid * scale);
    ctx.closePath(); ctx.fill();
    /* top edge stroke */
    var strokeGrad = ctx.createLinearGradient(0, 0, 0, h);
    strokeGrad.addColorStop(0,   'rgba(0,207,255,0.35)');
    strokeGrad.addColorStop(0.5, 'rgba(0,207,255,1.00)');
    strokeGrad.addColorStop(1,   'rgba(0,207,255,0.35)');
    ctx.strokeStyle = strokeGrad; ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (var xi = 0; xi < w; xi++) {
      var y = mid - pts[xi] * mid * scale;
      xi === 0 ? ctx.moveTo(xi, y) : ctx.lineTo(xi, y);
    }
    ctx.stroke();
    /* bottom mirror stroke */
    ctx.beginPath();
    for (var xi = 0; xi < w; xi++) {
      var y = mid + pts[xi] * mid * scale;
      xi === 0 ? ctx.moveTo(xi, y) : ctx.lineTo(xi, y);
    }
    ctx.stroke();
    /* RMS envelope glow */
    var rmsSum = 0;
    wf.forEach(function(v) { rmsSum += v * v; });
    var rms = Math.sqrt(rmsSum / wf.length);
    var rmsY = mid - rms * mid * scale;
    ctx.strokeStyle = 'rgba(0,255,180,0.25)'; ctx.lineWidth = 1; ctx.setLineDash([3, 6]);
    ctx.beginPath(); ctx.moveTo(0, rmsY); ctx.lineTo(w, rmsY); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, h - rmsY); ctx.lineTo(w, h - rmsY); ctx.stroke();
    ctx.setLineDash([]);
  }

  function _vpDrawPitch(pts, fmin, fmax) {
    var c = document.getElementById('vp-pitch'); if (!c || !pts || !pts.length) return;
    var w = c.offsetWidth || 400; c.width = w; fmin = fmin || 50; fmax = fmax || 800;
    var h = c.height, pad = 3;
    var ctx = c.getContext('2d');
    ctx.fillStyle = '#000d14'; ctx.fillRect(0, 0, w, h);
    /* grid lines */
    ctx.lineWidth = 1;
    [0.25, 0.5, 0.75].forEach(function(t) {
      var fy = fmin + (fmax - fmin) * t;
      var gy = Math.round(h - ((fy - fmin) / (fmax - fmin)) * (h - pad * 2) - pad) + 0.5;
      ctx.strokeStyle = 'rgba(0,255,136,0.07)';
      ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke();
      ctx.fillStyle = 'rgba(0,255,136,0.3)'; ctx.font = '7px Share Tech Mono,monospace';
      ctx.fillText(Math.round(fy) + 'Hz', 4, gy - 2);
    });
    /* collect voiced segments */
    var step = w / pts.length;
    function _pitchY(v) { return h - ((v - fmin) / (fmax - fmin)) * (h - pad * 2) - pad; }
    function _pitchColor(v) {
      var t = Math.max(0, Math.min(1, (v - fmin) / (fmax - fmin)));
      var r = Math.round(0 + t * 255), g = Math.round(255 - t * 100), b = Math.round(255 - t * 255);
      return 'rgb(' + r + ',' + g + ',' + b + ')';
    }
    /* area fill under curve per voiced segment */
    var segStart = -1;
    pts.forEach(function(v, i) {
      var voiced = v >= fmin && v <= fmax;
      if (voiced && segStart < 0) segStart = i;
      if ((!voiced || i === pts.length - 1) && segStart >= 0) {
        var segEnd = voiced ? i : i - 1;
        if (segEnd < segStart) { segStart = -1; return; }
        var gFill = ctx.createLinearGradient(0, 0, 0, h);
        gFill.addColorStop(0, 'rgba(0,220,255,0.18)');
        gFill.addColorStop(1, 'rgba(0,220,255,0.02)');
        ctx.fillStyle = gFill;
        ctx.beginPath();
        ctx.moveTo(segStart * step, h);
        for (var k = segStart; k <= segEnd; k++) ctx.lineTo(k * step, _pitchY(pts[k]));
        ctx.lineTo(segEnd * step, h);
        ctx.closePath(); ctx.fill();
        segStart = -1;
      }
    });
    /* stroke curve with gradient color per segment */
    var inSeg = false;
    ctx.lineWidth = 1.8;
    pts.forEach(function(v, i) {
      var voiced = v >= fmin && v <= fmax;
      if (!voiced) { if (inSeg) { ctx.stroke(); } inSeg = false; return; }
      ctx.strokeStyle = _pitchColor(v);
      if (!inSeg) { ctx.beginPath(); ctx.moveTo(i * step, _pitchY(v)); inSeg = true; }
      else ctx.lineTo(i * step, _pitchY(v));
    });
    if (inSeg) ctx.stroke();
    /* voiced dots */
    pts.forEach(function(v, i) {
      if (v < fmin || v > fmax) return;
      var x = i * step, y = _pitchY(v);
      ctx.fillStyle = _pitchColor(v);
      ctx.beginPath(); ctx.arc(x, y, 1.5, 0, Math.PI * 2); ctx.fill();
    });
    /* Hz axis labels */
    ctx.fillStyle = 'rgba(0,255,136,0.45)'; ctx.font = '7px Share Tech Mono,monospace';
    ctx.fillText(Math.round(fmax) + 'Hz', 4, 9);
    ctx.fillText(Math.round(fmin) + 'Hz', 4, h - 2);
  }

  function _vpDrawSpectrum(spec) {
    var c = document.getElementById('vp-spectrum'); if (!c || !spec || !spec.length) return;
    var w = c.offsetWidth || 400; c.width = w;
    var h = c.height;
    var ctx = c.getContext('2d');
    ctx.fillStyle = '#000d14'; ctx.fillRect(0, 0, w, h);
    var n = spec.length;
    var minV = spec[0], maxV = spec[0];
    for (var i = 1; i < n; i++) { if (spec[i] < minV) minV = spec[i]; if (spec[i] > maxV) maxV = spec[i]; }
    var range = (maxV - minV) || 1;
    /* heatmap colormap: black→blue→cyan→green→yellow→white */
    function _heatColor(t) {
      var stops = [
        [0,    0,   0,  0  ],
        [0.15, 0,  50, 180 ],
        [0.35, 0, 200, 220 ],
        [0.55, 0, 220,  60 ],
        [0.75, 220,220,  0 ],
        [0.90, 255,140,  0 ],
        [1.0,  255,255, 255]
      ];
      for (var s = 1; s < stops.length; s++) {
        if (t <= stops[s][0]) {
          var lo = stops[s-1], hi = stops[s], f = (t - lo[0]) / (hi[0] - lo[0]);
          var r = Math.round(lo[1] + (hi[1]-lo[1])*f);
          var g = Math.round(lo[2] + (hi[2]-lo[2])*f);
          var b = Math.round(lo[3] + (hi[3]-lo[3])*f);
          return 'rgb('+r+','+g+','+b+')';
        }
      }
      return 'rgb(255,255,255)';
    }
    var barW = w / n;
    for (var i = 0; i < n; i++) {
      var norm = (spec[i] - minV) / range;
      var bh = Math.max(2, norm * (h - 2));
      var x = i * barW, bx = Math.floor(x), bw = Math.max(1, Math.ceil(barW) - (barW > 2 ? 1 : 0));
      /* column gradient: heatmap color at top → dark at bottom */
      var colTop = _heatColor(norm);
      var grad = ctx.createLinearGradient(0, h - bh, 0, h);
      grad.addColorStop(0, colTop);
      grad.addColorStop(0.6, _heatColor(norm * 0.5));
      grad.addColorStop(1,   'rgba(0,20,40,0.6)');
      ctx.fillStyle = grad;
      ctx.fillRect(bx, h - bh, bw, bh);
      /* peak tick */
      if (norm > 0.15) {
        ctx.fillStyle = 'rgba(255,255,255,0.55)';
        ctx.fillRect(bx, h - bh, bw, 1);
      }
    }
    /* faint frequency axis labels */
    ctx.fillStyle = 'rgba(0,207,255,0.35)'; ctx.font = '7px Share Tech Mono,monospace';
    ctx.fillText('0', 3, h - 3);
    ctx.fillText('8k', Math.floor(w * 0.5) - 4, h - 3);
    ctx.fillText('16k', w - 18, h - 3);
  }

  /* ─── Selector ──────────────────────────────────────────────── */
  function _vpGetAudioCtx() {
    if (!_vpAudioCtx || _vpAudioCtx.state === 'closed') {
      _vpAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return _vpAudioCtx;
  }

  function _vpDecodeFileForSelector(file) {
    var reader = new FileReader();
    reader.onload = function(ev) {
      var ctx = _vpGetAudioCtx();
      ctx.decodeAudioData(ev.target.result, function(buf) {
        _vpAudioBuffer = buf;
        _vpSelStart = 0;
        _vpSelEnd = 0;
        var sel = document.getElementById('vp-selector');
        _disp(sel, true);
        _vpUpdateSelInfo();
        requestAnimationFrame(_vpDrawSelector);
      }, function(err) {
      });
    };
    reader.readAsArrayBuffer(file);
  }

  function _vpInitSelector() {
    var c = document.getElementById('vp-sel-canvas');
    if (!c) return;
    var dragging = false, dragT0 = 0;

    function px2t(x) {
      if (!_vpAudioBuffer) return 0;
      return Math.max(0, Math.min(_vpAudioBuffer.duration, (x / (c.offsetWidth || 1)) * _vpAudioBuffer.duration));
    }

    c.addEventListener('mousedown', function(e) {
      if (!_vpAudioBuffer) return;
      e.preventDefault();
      dragging = true;
      dragT0 = px2t(e.offsetX);
      _vpSelStart = dragT0; _vpSelEnd = dragT0;
      requestAnimationFrame(_vpDrawSelector); _vpUpdateSelInfo();
    });
    c.addEventListener('mousemove', function(e) {
      if (!dragging || !_vpAudioBuffer) return;
      var t = px2t(e.offsetX);
      if (t < dragT0) { _vpSelStart = t; _vpSelEnd = dragT0; }
      else { _vpSelStart = dragT0; _vpSelEnd = t; }
      requestAnimationFrame(_vpDrawSelector); _vpUpdateSelInfo();
    });
    window.addEventListener('mouseup', function() { dragging = false; });
    c.addEventListener('touchstart', function(e) {
      if (!_vpAudioBuffer) return;
      e.preventDefault();
      dragging = true;
      var rect = c.getBoundingClientRect();
      dragT0 = px2t(e.touches[0].clientX - rect.left);
      _vpSelStart = dragT0; _vpSelEnd = dragT0;
      requestAnimationFrame(_vpDrawSelector); _vpUpdateSelInfo();
    }, { passive:false });
    c.addEventListener('touchmove', function(e) {
      if (!dragging || !_vpAudioBuffer) return;
      e.preventDefault();
      var rect = c.getBoundingClientRect();
      var t = px2t(e.touches[0].clientX - rect.left);
      if (t < dragT0) { _vpSelStart = t; _vpSelEnd = dragT0; }
      else { _vpSelStart = dragT0; _vpSelEnd = t; }
      requestAnimationFrame(_vpDrawSelector); _vpUpdateSelInfo();
    }, { passive:false });
    c.addEventListener('touchend', function() { dragging = false; });
  }

  function _vpDrawSelRegion(ctx, rms, w, h, ymid, dur) {
    if (!(_vpSelEnd > _vpSelStart + 0.01)) return;
    var x1 = Math.floor((_vpSelStart / dur) * w);
    var x2 = Math.ceil((_vpSelEnd / dur) * w);
    ctx.fillStyle = '#cc88ff0c';
    ctx.fillRect(x1, 0, x2-x1, h);
    ctx.save();
    ctx.beginPath(); ctx.rect(x1, 0, x2-x1, h); ctx.clip();
    for (var i = x1; i <= x2 && i < w; i++) {
      if (i < 0) continue;
      var bh = Math.max(1, rms[i] * (h - 4));
      ctx.fillStyle = '#cc88ffaa';
      ctx.fillRect(i, ymid - bh, 1, bh * 2);
    }
    ctx.restore();
    var g1 = ctx.createLinearGradient(x1, 0, x1+4, 0);
    g1.addColorStop(0, '#cc88ffcc'); g1.addColorStop(1, '#cc88ff00');
    ctx.fillStyle = g1; ctx.fillRect(x1, 0, 4, h);
    var g2 = ctx.createLinearGradient(x2-4, 0, x2, 0);
    g2.addColorStop(0, '#cc88ff00'); g2.addColorStop(1, '#cc88ffcc');
    ctx.fillStyle = g2; ctx.fillRect(x2-4, 0, 4, h);
    var selDur = _vpSelEnd - _vpSelStart;
    if (x2 - x1 > 60) {
      ctx.fillStyle = '#cc88ffcc'; ctx.font = 'bold 9px Share Tech Mono,monospace';
      ctx.textAlign = 'center';
      ctx.fillText(selDur.toFixed(2)+'s', (x1+x2)/2, ymid + 5);
      ctx.textAlign = 'left';
    }
  }

  function _vpDrawSelector() {
    var c = document.getElementById('vp-sel-canvas');
    if (!c || !_vpAudioBuffer) return;
    var w = c.offsetWidth || 600; c.width = w;
    var h = c.height;
    var ctx = c.getContext('2d');
    var ch = _vpAudioBuffer.getChannelData(0);
    var dur = _vpAudioBuffer.duration;
    var step = Math.max(1, Math.floor(ch.length / w));
    var ymid = h / 2;
    var rms = new Float32Array(w);
    for (var i = 0; i < w; i++) {
      var base = i * step, s = 0;
      for (var j = 0; j < step && (base+j) < ch.length; j++) s += ch[base+j]*ch[base+j];
      rms[i] = Math.sqrt(s / step);
    }
    ctx.fillStyle = '#000d14';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = '#00cfff08'; ctx.lineWidth = 1;
    [0.25, 0.5, 0.75].forEach(function(t) {
      ctx.beginPath(); ctx.moveTo(0, h*t); ctx.lineTo(w, h*t); ctx.stroke();
    });
    for (var i = 0; i < w; i++) {
      var bh = Math.max(1, rms[i] * (h - 4));
      ctx.fillStyle = '#00cfff2a';
      ctx.fillRect(i, ymid - bh, 1, bh * 2);
    }
    ctx.strokeStyle = '#00cfff18'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, ymid); ctx.lineTo(w, ymid); ctx.stroke();
    _vpDrawSelRegion(ctx, rms, w, h, ymid, dur);
    var tickCount = Math.min(10, Math.ceil(dur));
    ctx.fillStyle = '#00cfff33'; ctx.font = '8px Share Tech Mono,monospace';
    for (var t = 0; t <= tickCount; t++) {
      var tx = Math.floor((t / tickCount) * w);
      ctx.fillText((dur * t / tickCount).toFixed(1)+'s', tx + 2, h - 3);
    }
  }

  function _vpUpdateSelInfo() {
    var s1   = document.getElementById('vp-sel-start-lbl');
    var s2   = document.getElementById('vp-sel-end-lbl');
    var sd   = document.getElementById('vp-sel-dur-lbl');
    var btnS = document.getElementById('vp-btn-play-sel');
    var btnC = document.getElementById('vp-btn-capture');
    var hasSel = _vpSelEnd > _vpSelStart + 0.1;
    if (s1) s1.textContent = _vpSelStart.toFixed(2)+'s';
    if (s2) s2.textContent = (_vpAudioBuffer ? _vpSelEnd : 0).toFixed(2)+'s';
    if (sd) sd.textContent = hasSel ? 'DURÉE: '+(_vpSelEnd-_vpSelStart).toFixed(2)+'s' : '— glisser pour sélectionner —';
    if (btnS) btnS.disabled = !hasSel;
    if (btnC) btnC.disabled = !hasSel;
  }

  /* ─── Playback ──────────────────────────────────────────────── */
  function _vpStopSource() {
    if (_vpPlaySource) {
      try { _vpPlaySource.stop(); } catch(e) {}
      _vpPlaySource = null;
    }
  }

  function _vpBtnPlaying(btnId, label) {
    var b = document.getElementById(btnId);
    if (b) { b.textContent = label; b.classList.add('playing'); }
  }
  function _vpBtnIdle(btnId, label) {
    var b = document.getElementById(btnId);
    if (b) { b.textContent = label; b.classList.remove('playing'); }
  }
  function _vpResetPlayBtns() {
    _vpBtnIdle('vp-btn-play-all', '▶ TOUT');
    _vpBtnIdle('vp-btn-play-sel', '▶ SÉLECTION');
  }

  function _vpPlayAudio(offset, duration, btnId) {
    _vpStopSource(); _vpResetPlayBtns();
    var ctx = _vpGetAudioCtx();
    if (ctx.state === 'suspended') ctx.resume();
    var src = ctx.createBufferSource();
    src.buffer = _vpAudioBuffer;
    src.connect(ctx.destination);
    src.start(0, offset, duration);
    _vpPlaySource = src;
    _vpBtnPlaying(btnId, '■ EN COURS');
    src.onended = function() {
      if (_vpPlaySource === src) { _vpPlaySource = null; _vpResetPlayBtns(); }
    };
  }

  window.vpPlayAll = function() {
    if (!_vpAudioBuffer) { _vpSetInfo('⚠ Charger un sample d\'abord', true); return; }
    _vpPlayAudio(0, undefined, 'vp-btn-play-all');
  };

  window.vpPlaySel = function() {
    if (!_vpAudioBuffer) return;
    if (_vpSelEnd <= _vpSelStart + 0.05) { _vpSetInfo('⚠ Sélectionner une région d\'abord', true); return; }
    _vpPlayAudio(_vpSelStart, _vpSelEnd - _vpSelStart, 'vp-btn-play-sel');
  };

  window.vpStopPlay = function() { _vpStopSource(); _vpResetPlayBtns(); };

  /* ─── VP Modal plein écran (pattern code-modal — enfant body) ── */
  window.vpToggleModal = function() {
    var modal   = document.getElementById('vp-modal');
    var content = document.getElementById('vp-modal-content');
    var rack    = document.getElementById('rack-unit-vp');
    var btn     = document.getElementById('vp-expand-btn');
    if (!modal || !content || !rack) return;

    var isOpen = modal.classList.toggle('open');
    if (btn) {
      btn.textContent = isOpen ? '✕ FERMER' : '⤢ MODAL';
      btn.classList.toggle('active', isOpen);
    }

    var body = rack.querySelector('.rack-unit-body');
    if (!body) return;

    if (isOpen) {
      content.appendChild(body);           // déplace le corps VP dans le modal
      setTimeout(function() {
        var canvas = document.getElementById('vp-sel-canvas');
        if (canvas) {
          var w = canvas.parentElement ? canvas.parentElement.clientWidth : 0;
          if (w > 0 && w !== canvas.width) canvas.width = w;
          if (typeof _vpDrawSelector === 'function') _vpDrawSelector();
        }
      }, 60);
    } else {
      rack.appendChild(body);              // remet le corps VP dans le rack
    }
  };

  /* ─── Public actions ────────────────────────────────────────── */
  window.vpOpenFile = function(){ document.getElementById('vp-file-input').click(); };

  window.vpStartMic = function(){
    var btn=document.getElementById('vp-mic-btn');
    if (_vpMicRec && _vpMicRec.state==='recording'){
      _vpMicRec.stop();
      if(btn){btn.textContent='⏺ MIC';btn.classList.remove('active');}
      return;
    }
    if (!navigator.mediaDevices){_vpSetInfo('⚠ MediaDevices non disponible',true);return;}
    navigator.mediaDevices.getUserMedia({audio:true}).then(function(stream){
      _vpMicChunks=[];
      _vpMicRec=new MediaRecorder(stream);
      _vpMicRec.ondataavailable=function(e){_vpMicChunks.push(e.data);};
      _vpMicRec.onstop=function(){
        stream.getTracks().forEach(function(t){t.stop();});
        _vpAnalyse(new File(_vpMicChunks,'mic.webm',{type:'audio/webm'}));
      };
      _vpMicRec.start();
      if(btn){btn.textContent='■ STOP';btn.classList.add('active');}
      _vpSetInfo('⏺ Enregistrement… cliquer STOP');
    }).catch(function(e){_vpSetInfo('⚠ Micro: '+e.message,true);});
  };

  window.vpParamUpdate = function(id){
    var el=document.getElementById(id); if(!el) return;
    var val=+el.value;
    var map={'vp-fmin':'vp-fmin-v','vp-fmax':'vp-fmax-v','vp-mels':'vp-mels-v'};
    var lbl=document.getElementById(map[id]);
    if(lbl) lbl.textContent=val+(id==='vp-mels'?'':' Hz');
    if(id==='vp-fmin') _vpParams.fmin=val;
    else if(id==='vp-fmax') _vpParams.fmax=val;
    else if(id==='vp-mels') _vpParams.n_mels=val;
  };

  window.vpApplyPreset = function(){
    if (!_vpData || !_vpData.eq_preset){
      _vpSetInfo('⚠ Aucune analyse — charger un sample',true); return;
    }
    var eq = _vpData.eq_preset;
    setEqBand('low',  +((eq.low  || 0).toFixed(1)));
    setEqBand('mid',  +(((( eq.lomid || 0) + (eq.mid || 0)) / 2).toFixed(1)));
    setEqBand('high', +((eq.himid || 0).toFixed(1)));
    setEqBand('air',  +((eq.air   || 0).toFixed(1)));
    drawEqCurve();
    _dspSchedulePush();
    _vpSetInfo('◈ Preset EQ Voice Print appliqué au DSP');
  };

  window.vpExportPreset = function(){
    if(!_vpData){_vpSetInfo('⚠ Aucune analyse',true);return;}
    var p={source:'JARVIS VOICE PRINT v2',date:new Date().toISOString(),metrics:_vpData.metrics,eq_preset:_vpData.eq_preset,duration:_vpData.duration,sr:_vpData.sr};
    var url=URL.createObjectURL(new Blob([JSON.stringify(p,null,2)],{type:'application/json'}));
    var a=document.createElement('a'); a.href=url; a.download='voice_print_'+Date.now()+'.json'; a.click();
    URL.revokeObjectURL(url);
  };

  window.vpClone = function(engine){
    var st=document.getElementById('vp-clone-status');
    if(!_vpData){if(st)st.textContent='⚠ Charger un sample d\'abord';return;}
    var msgs={
      chatterbox: '⬡ Chatterbox (Resemble AI) — pip install chatterbox-tts · prosody+émotion · RTX5080',
      f5:         '⬡ F5-TTS — pip install f5-tts · diffusion flow-matching · très haute qualité',
    };
    if(st){st.textContent=msgs[engine]||'?';st.className=(st.className.replace(/\bvp-capture-ok\b/g,'')+' vp-clone-info').trim();}
  };

  window.vpSaveProfile = function(){
    if(!_vpData){_vpSetInfo('⚠ Aucune analyse à sauvegarder',true);return;}
    var nameEl=document.getElementById('vp-profile-name');
    var name=(nameEl&&nameEl.value||'').trim();
    if(!name){if(nameEl)nameEl.focus();return;}
    var profiles=JSON.parse(localStorage.getItem('vp_profiles')||'[]');
    var idx=profiles.findIndex(function(p){return p.name===name;});
    var entry={name:name,date:new Date().toISOString().slice(0,10),metrics:_vpData.metrics,eq_preset:_vpData.eq_preset};
    if(idx>=0) profiles[idx]=entry; else profiles.push(entry);
    localStorage.setItem('vp_profiles',JSON.stringify(profiles));
    if(nameEl) nameEl.value='';
    _vpRenderProfileList();
    _vpSetInfo('◈ Profil "'+name+'" sauvegardé');
  };

  window.vpLoadProfile = function(idx){
    var profiles=JSON.parse(localStorage.getItem('vp_profiles')||'[]');
    var p=profiles[+idx]; if(!p) return;
    _vpData={metrics:p.metrics,eq_preset:p.eq_preset,duration:0,sr:0};
    _vpUpdateMetrics(_vpData);
    _vpUpdateProfile(_vpData);
    _vpRenderEqBands(p.eq_preset);
    _vpDrawPlaceholders();
    _vpSetInfo('◈ Profil "'+p.name+'" chargé ('+p.date+')');
  };

  window.vpDeleteProfile = function(idx){
    var profiles=JSON.parse(localStorage.getItem('vp_profiles')||'[]');
    profiles.splice(+idx,1);
    localStorage.setItem('vp_profiles',JSON.stringify(profiles));
    _vpRenderProfileList();
  };

  function _vpRenderProfileList(){
    var list=document.getElementById('vp-profiles-list'); if(!list) return;
    var profiles=JSON.parse(localStorage.getItem('vp_profiles')||'[]');
    if(!profiles.length){list.innerHTML='<span class="vp-profiles-empty">Aucun profil sauvegardé</span>';return;}
    list.innerHTML=profiles.map(function(p,i){
      return '<div class="vp-profile-item">'
        +'<span class="vp-profile-item-name">'+p.name+'</span>'
        +'<span class="vp-profile-item-type">'+(p.metrics&&p.metrics.voice_type||'?')+'</span>'
        +'<button class="vp-profile-item-load" data-action="vpLoadProfile" data-args=\'["'+i+'"]\'>CHARGER</button>'
        +'<button class="vp-profile-item-del"  data-action="vpDeleteProfile" data-args=\'["'+i+'"]\'>✕</button>'
        +'</div>';
    }).join('');
  }

  /* ─── Voix capturées (Voice Prints) ──────────────────────────── */
  function _vpLoadPrints() {
    var list = document.getElementById('vp-prints-list');
    if (!list) return;
    fetch('/api/voice/prints')
      .then(function(r) { return r.json(); })
      .then(function(prints) {
        if (!prints.length) {
          list.innerHTML = '<span class="vp-profiles-empty">Aucune voix capturée</span>';
          return;
        }
        list.innerHTML = prints.map(function(p) {
          return '<div class="vp-print-item">'
            +'<span class="vp-print-name">'+p.name+'</span>'
            +'<span class="vp-print-dur">'+p.duration+'s</span>'
            +'<button class="vp-print-load" title="Charger dans le sélecteur"'
            +' data-action="vpLoadPrintInSelector" data-args=\'["'+p.name+'"]\'>▶</button>'
            +'<button class="vp-print-del" title="Supprimer" data-action="vpDeletePrint" data-args=\'["'+p.name+'"]\'>✕</button>'
            +'</div>';
        }).join('');
      })
      .catch(function() {});
  }

  window.vpLoadPrintInSelector = function(name) {
    var url = '/api/voice/print/audio/' + encodeURIComponent(name);
    fetch(url)
      .then(function(r) {
        if (!r.ok) { _vpSetInfo('⚠ Fichier introuvable', true); return null; }
        return r.blob();
      })
      .then(function(blob) {
        if (!blob) return;
        var file = new File([blob], name + '.wav', { type: 'audio/wav' });
        // Marquer l'item actif dans la liste
        document.querySelectorAll('#vp-prints-list .vp-print-item').forEach(function(el) {
          el.classList.toggle('active', el.querySelector('.vp-print-name') && el.querySelector('.vp-print-name').textContent === name);
        });
        _vpAnalyse(file);
      })
      .catch(function(e) { _vpSetInfo('⚠ ' + e.message, true); });
  };

  window.vpDeletePrint = function(name) {
    if (!name) return;
    if (!confirm('Supprimer voice_prints/'+name+'.wav ?')) return;
    fetch('/api/voice/print/delete', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name: name})
    })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.ok) { _vpSetInfo('◈ Voix "'+name+'" supprimée'); _vpLoadPrints(); }
        else _vpSetInfo('⚠ '+(d.error||'Erreur'), true);
      })
      .catch(function(e) { _vpSetInfo('⚠ '+e.message, true); });
  };

  /* ─── Bibliothèque samples ──────────────────────────────────── */
  function _vpLoadLibrary() {
    var list = document.getElementById('vp-lib-list');
    if (!list) return;
    fetch('/api/voice/samples')
      .then(function(r) { return r.json(); })
      .then(function(samples) {
        if (!samples.length) {
          list.innerHTML = '<span class="vp-profiles-empty">Aucun sample dans voice_samples/</span>';
          return;
        }
        list.innerHTML = samples.map(function(s, i) {
          return '<div class="vp-lib-item" data-url="'+s.url+'" data-name="'+s.file+'" data-idx="'+i+'">'
            +'<span class="vp-lib-lang">'+s.lang+'</span>'
            +'<span class="vp-lib-name">'+s.name+'</span>'
            +'<span class="vp-lib-sz">'+s.size_kb+'Ko</span>'
            +'</div>';
        }).join('');
        list.querySelectorAll('.vp-lib-item').forEach(function(el) {
          el.addEventListener('click', function() {
            list.querySelectorAll('.vp-lib-item').forEach(function(x){x.classList.remove('active');});
            el.classList.add('active');
            _vpLoadSampleUrl(el.dataset.url, el.dataset.name);
          });
        });
      })
      .catch(function() {
        if (list) list.innerHTML = '<span class="vp-profiles-empty">Erreur chargement bibliothèque</span>';
      });
  }

  function _vpLoadSampleUrl(url, name) {
    _vpSetInfo('◈ Chargement '+name+'…');
    _vpShowSpinner(true);
    fetch(url)
      .then(function(r) {
        if (!r.ok) throw new Error('HTTP '+r.status);
        return r.blob();
      })
      .then(function(blob) {
        var file = new File([blob], name, { type: blob.type || 'audio/wav' });
        _vpAnalyse(file);
      })
      .catch(function(e) {
        _vpShowSpinner(false);
        _vpSetInfo('⚠ '+e.message, true);
      });
  }

  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',_vpInit);
  else _vpInit();
})();
