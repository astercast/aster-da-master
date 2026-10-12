/* assets/js/tx-audio.js — Transmission layer 2: the audio dimension.
 *
 * Honest Web Audio sound for the broadcast: band-limited static bursts on
 * era transitions, a short retune zip, a soft two-tone "SIGNAL FOUND" land.
 * Everything is synthesized live (no samples, no fetches); every sound is
 * under half a second and sits at a low master gain.
 *
 * Rules, stated plainly:
 *  - Sound is OFF by default. Nothing creates an AudioContext until the
 *    listener presses the sound toggle (or Begin / Resume / a tuner station,
 *    which only prime the context — they never unmute).
 *  - The toggle is a real persisted choice (localStorage
 *    "adm.transmission.sound" = "on"/"off"); the button always shows the
 *    current state via aria-pressed.
 *  - Reduced-motion users get the same narrative without motion — audio is
 *    not motion, so the toggle is available to everyone, and every sound is
 *    optional, never required.
 *  - No AudioContext in the browser → every call no-ops. A blocked or
 *    missing script can never break the broadcast (transmission.js guards
 *    with `window.TxAudio &&` before every call).
 */
(function () {
  "use strict";

  var STORE = "adm.transmission.sound";
  var MASTER_GAIN = 0.06;

  var ctx = null;
  var master = null;
  var muted = true;

  try {
    muted = (localStorage.getItem(STORE) || "off") !== "on";
  } catch (e) { /* private mode: stay muted, stay silent */ }

  function ensure() {
    if (ctx) return true;
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    try {
      ctx = new AC();
      master = ctx.createGain();
      master.gain.value = MASTER_GAIN;
      master.connect(ctx.destination);
    } catch (e) {
      ctx = null;
      return false;
    }
    return true;
  }

  /* Call from inside a user gesture so mobile browsers let the context run. */
  function prime() {
    if (!ensure()) return;
    if (ctx.state === "suspended") {
      try { ctx.resume(); } catch (e) { /* noop */ }
    }
  }

  function noiseBuffer(dur) {
    var sr = ctx.sampleRate;
    var len = Math.max(1, Math.floor(sr * dur));
    var buf = ctx.createBuffer(1, len, sr);
    var d = buf.getChannelData(0);
    for (var i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    return buf;
  }

  function audible() {
    return !muted && ensure();
  }

  /* Signal loss: band-limited static burst, filter sweeping up as the
     interference peaks, then an exponential decay into silence. */
  function playStatic(durMs) {
    if (!audible()) return;
    prime();
    var dur = (durMs || 380) / 1000;
    var t = ctx.currentTime;
    var src = ctx.createBufferSource();
    src.buffer = noiseBuffer(dur + 0.05);
    var bp = ctx.createBiquadFilter();
    bp.type = "bandpass";
    bp.Q.value = 0.8;
    bp.frequency.setValueAtTime(500, t);
    bp.frequency.exponentialRampToValueAtTime(2600, t + dur);
    var g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(1.0, t + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(bp);
    bp.connect(g);
    g.connect(master);
    src.start(t);
    src.stop(t + dur + 0.05);
  }

  /* The retune zip: a short sawtooth glide, 180 → 920 Hz in 0.22 s. */
  function playTune() {
    if (!audible()) return;
    prime();
    var t = ctx.currentTime;
    var dur = 0.22;
    var o = ctx.createOscillator();
    o.type = "sawtooth";
    o.frequency.setValueAtTime(180, t);
    o.frequency.exponentialRampToValueAtTime(920, t + dur);
    var g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.5, t + 0.03);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g);
    g.connect(master);
    o.start(t);
    o.stop(t + dur + 0.02);
  }

  /* Signal found: two soft sine blips, 880 then 1318.5 Hz. */
  function playLand() {
    if (!audible()) return;
    prime();
    var t = ctx.currentTime;
    var freqs = [880, 1318.5];
    for (var i = 0; i < freqs.length; i++) {
      (function (f, i) {
        var o = ctx.createOscillator();
        o.type = "sine";
        o.frequency.value = f;
        var g = ctx.createGain();
        var s = t + i * 0.09;
        g.gain.setValueAtTime(0.0001, s);
        g.gain.exponentialRampToValueAtTime(0.6, s + 0.015);
        g.gain.exponentialRampToValueAtTime(0.0001, s + 0.09);
        o.connect(g);
        g.connect(master);
        o.start(s);
        o.stop(s + 0.1);
      })(freqs[i], i);
    }
  }

  function setMuted(m) {
    muted = !!m;
    try { localStorage.setItem(STORE, muted ? "off" : "on"); } catch (e) { /* noop */ }
  }

  window.TxAudio = {
    prime: prime,
    static: playStatic,
    tune: playTune,
    land: playLand,
    setMuted: setMuted,
    isMuted: function () { return muted; }
  };
})();
