/**
 * timeline-shim.js — Zero-dependency animation timeline engine for HyperFrames.
 *
 * API:
 *   new SimpleTimeline({ totalDur })      → creates timeline
 *   .to(sel, props, time)                → animate from CSS to props
 *   .from(sel, props, time)              → animate from props to CSS
 *   .fromTo(sel, from, to, time)         → animate between explicit states
 *   .set(sel, props, time)               → snap to props at time
 *   .progress(p)                         → seek to p∈[0,1] — 
 *
 * Supported CSS props: opacity, y, x, scale, rotation, scaleX, width, innerText
 * Supported easings: power2.out, power3.out, power2.in, power2.inOut,
 *                    power3.inOut, sine.inOut, sine.in, expo.out, linear
 */

(function () {
  'use strict';

  // ── Easing functions ──
  var E = {
    'power2.out':     function (t) { return t * (2 - t); },
    'power3.out':     function (t) { var a = 1 - t; return 1 - a * a * a; },
    'power2.in':      function (t) { return t * t; },
    'power2.inOut':   function (t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; },
    'power3.inOut':   function (t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; },
    'sine.inOut':     function (t) { return -(Math.cos(Math.PI * t) - 1) / 2; },
    'sine.in':        function (t) { return 1 - Math.cos(t * Math.PI / 2); },
    'expo.out':       function (t) { return t === 1 ? 1 : 1 - Math.pow(2, -10 * t); },
    'linear':         function (t) { return t; },
    'power2.in':      function (t) { return t * t; },
  };

  function lerp(a, b, t) { return a + (b - a) * t; }

  // ── Parse a CSS-props string like "y:20,opacity:0,duration:0.4" ──
  function parseProps(str) {
    var out = {}, parts = str.split(',');
    for (var i = 0; i < parts.length; i++) {
      var kv = parts[i].split(':');
      if (kv.length < 2) continue;
      var key = kv[0].trim(), val = kv[1].trim();
      // numeric values
      var num = parseFloat(val);
      if (!isNaN(num)) { out[key] = num; continue; }
      // quoted or string values
      out[key] = val.replace(/"/g, '').replace(/'/g, '');
    }
    return out;
  }

  // ── CSS properties that affect transform ──
  var TRANSFORM_PROPS = { y: 1, x: 1, scale: 1, rotation: 1, scaleX: 1 };

  function buildTransform(vals) {
    var parts = [];
    if (vals.y !== undefined) parts.push('translateY(' + vals.y + 'px)');
    if (vals.x !== undefined) parts.push('translateX(' + vals.x + 'px)');
    if (vals.scale !== undefined) parts.push('scale(' + vals.scale + ')');
    if (vals.rotation !== undefined) parts.push('rotate(' + vals.rotation + 'deg)');
    if (vals.scaleX !== undefined) parts.push('scaleX(' + vals.scaleX + ')');
    return parts.join(' ');
  }

  // ── Apply a props map to a DOM element ──
  function applyProps(el, props) {
    if (!el || !props) return;
    var tf = {};
    for (var key in props) {
      if (key === 'duration' || key === 'ease' || key === 'stagger' || key === 'transformOrigin') continue;
      if (key === 'innerText') { el.innerText = props[key]; continue; }
      if (key === 'visibility') { el.style.visibility = props[key]; continue; }
      if (key === 'backgroundPosition') { el.style.backgroundPosition = props[key]; continue; }
      if (TRANSFORM_PROPS[key]) { tf[key] = props[key]; continue; }
      if (key === 'opacity') { el.style.opacity = props[key]; continue; }
      // fallback: set as style property
      try { el.style[key] = props[key]; } catch (e) {}
    }
    var tfs = buildTransform(tf);
    if (tfs) { el.style.transform = tfs; }
    if (props.transformOrigin) { el.style.transformOrigin = props.transformOrigin; }
  }

  // ── Interpolate between two prop maps ──
  function interpolateProps(from, to, t, out) {
    out = out || {};
    for (var key in to) {
      if (key === 'duration' || key === 'ease' || key === 'stagger' || key === 'transformOrigin') continue;
      var fv = from[key] !== undefined ? from[key] : 0;
      var tv = to[key];
      if (typeof tv === 'number') {
        out[key] = lerp(fv, tv, t);
      } else {
        out[key] = tv;
      }
    }
    return out;
  }

  // ── Track ──
  function Track(type, selector, a, b, time, dur, ease, stagger) {
    this.type = type;
    this.selector = selector;
    this.a = a || {};   // from state (or empty for 'to')
    this.b = b || {};   // to state
    this.time = time;
    this.dur = dur || 0.3;
    this.ease = ease || 'power2.out';
    this.stagger = stagger || 0;
  }

  Track.prototype.resolveElements = function () {
    if (!this._els) {
      this._els = [].slice.call(document.querySelectorAll(this.selector));
    }
    return this._els;
  };

  // ── SimpleTimeline ──
  window.SimpleTimeline = function (opts) {
    opts = opts || {};
    this._tracks = [];
    this._totalDur = opts.totalDur || 60;
    this._spriteUpdate = null;   // fn(t) for runner sprite
    this._spriteCycle = 1.2;
    this._spriteFrames = 9;
  };

  SimpleTimeline.prototype = {
    to: function (sel, props, time) {
      var dur = props.duration || 0.4, ease = props.ease || 'power2.out', stag = props.stagger || 0;
      this._tracks.push(new Track('to', sel, {}, props, time, dur, ease, stag));
    },
    from: function (sel, props, time) {
      var dur = props.duration || 0.4, ease = props.ease || 'power2.out', stag = props.stagger || 0;
      this._tracks.push(new Track('from', sel, props, {}, time, dur, ease, stag));
    },
    fromTo: function (sel, from, to, time) {
      var dur = to.duration || from.duration || 0.45, ease = to.ease || 'power2.out', stag = 0;
      this._tracks.push(new Track('fromTo', sel, from, to, time, dur, ease, stag));
    },
    set: function (sel, props, time) {
      this._tracks.push(new Track('set', sel, props, {}, time, 0));
    },
    // Called by HyperFrames for each rendered frame
    progress: function (p) {
      this._lastP = p;
      var t = p * this._totalDur;
      this._lastTime = t;
      var i, j, track, els, el, localT, eased, fromState, toState;

      // Phase 1: Reset all tracked elements to CSS natural state
      for (i = 0; i < this._tracks.length; i++) {
        track = this._tracks[i];
        els = track.resolveElements();
        for (j = 0; j < els.length; j++) {
          el = els[j];
          if (!el._stReset) el._stReset = {};
          // Only reset once per element
          if (!el._stReset[track.selector]) {
            el._stReset[track.selector] = true;
            // Clear animation-set inline styles (keep base CSS)
            // We only reset what we might have set
            el.style.opacity = '';
            el.style.transform = '';
            el.style.transformOrigin = '';
            el.style.visibility = '';
          }
        }
      }

      // Phase 2: Apply active animations
      for (i = 0; i < this._tracks.length; i++) {
        track = this._tracks[i];
        els = track.resolveElements();

        if (track.type === 'set') {
          // set is "instant" at its time
          if (t >= track.time) {
            for (j = 0; j < els.length; j++) {
              applyProps(els[j], track.a);
            }
          }
          continue;
        }

        // Handle stagger: each element gets offset delay
        for (j = 0; j < els.length; j++) {
          el = els[j];
          var effectiveTime = track.time + j * (track.stagger || 0);

          if (track.type === 'from') {
            // Before start: show from-state
            if (t < effectiveTime) {
              applyProps(el, track.a);
              continue;
            }
            // After start: interpolate from from-state to {}(empty=natural)
            localT = Math.min((t - effectiveTime) / track.dur, 1);
            eased = (E[track.ease] || E['power2.out'])(localT);
            fromState = track.a;
            toState = {};
            // Build interpolated state: for each prop in 'from', interpolate to 0
            var interp = {};
            for (var key in fromState) {
              if (key === 'duration' || key === 'ease' || key === 'stagger' || key === 'transformOrigin') continue;
              if (typeof fromState[key] === 'number') {
                interp[key] = lerp(fromState[key], 0, eased);
              }
            }
            // For opacity, interpolate from 0 to 1
            if (interp.opacity === undefined && fromState.opacity !== undefined) {
              interp.opacity = lerp(fromState.opacity, 1, eased);
            }
            if (interp.y === undefined && fromState.y !== undefined) {
              interp.y = lerp(fromState.y, 0, eased);
            }
            if (interp.x === undefined && fromState.x !== undefined) {
              interp.x = lerp(fromState.x, 0, eased);
            }
            applyProps(el, interp);

          } else if (track.type === 'to') {
            // Before start: natural state (already reset)
            if (t < effectiveTime) continue;
            localT = Math.min((t - effectiveTime) / track.dur, 1);
            eased = (E[track.ease] || E['power2.out'])(localT);
            var toVals = {};
            for (var k in track.b) {
              if (k === 'duration' || k === 'ease' || k === 'stagger' || k === 'transformOrigin') continue;
              if (typeof track.b[k] === 'number') {
                toVals[k] = lerp(0, track.b[k], eased);
              }
            }
            if (toVals.opacity === undefined && track.b.opacity !== undefined) {
              toVals.opacity = lerp(1, track.b.opacity, eased);
            }
            if (toVals.scale === undefined && track.b.scale !== undefined) {
              toVals.scale = lerp(1, track.b.scale, eased);
            }
            applyProps(el, toVals);

          } else if (track.type === 'fromTo') {
            if (t < effectiveTime) {
              applyProps(el, track.a);
              continue;
            }
            localT = Math.min((t - effectiveTime) / track.dur, 1);
            eased = (E[track.ease] || E['power2.out'])(localT);
            applyProps(el, interpolateProps(track.a, track.b, eased));
          }
        }
      }

      // Phase 3: Update progress bar
      var pf = document.getElementById('pf');
      if (pf) pf.style.width = (p * 100) + '%';

      // Phase 4: Update sprite runner
      if (this._spriteUpdate) {
        this._spriteUpdate(t);
      }
    },

    _setSprite: function (cycle, frames) {
      this._spriteCycle = cycle;
      this._spriteFrames = frames;
      var self = this;
      this._spriteUpdate = function (t) {
        var pr = document.getElementById('pr');
        if (!pr) return;
        var f = Math.floor((t % self._spriteCycle) / self._spriteCycle * self._spriteFrames);
        pr.style.backgroundPosition = '-' + (f * 60) + 'px 0px';
        // Left position: progress-based
        if (self._totalDur > 0) {
          pr.style.left = 'calc(' + (t / self._totalDur * 100) + '% - 30px)';
        }
      };
    }

    // GSAP compatibility methods
    totalDuration: function () { return this._totalDur; },
    duration: function () { return this._totalDur; },
    time: function () {
        // Return current time based on last progress call
        return this._lastTime || 0;
    },
    // Allow HyperFrames to seek via time() as well
    seek: function (t) {
        this.progress(t / this._totalDur);
    },

  };
})();
