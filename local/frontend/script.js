/**
 * JARVIS Holographic 3D Cybernetic Sphere & Gyroscopic HUD Engine
 * Ultra-High Fidelity 3D WebGL
 *
 * Updates:
 * - Decreased outer orb size: SPHERE_RADIUS = 138 (down from 164)
 * - Spikes preserved at full length (~18-38) and made broader with radial tapered pin geometry & glowing heads
 * - Inner rings made significantly broader with concentric multi-track bands & luminous ring discs
 * - 3D circular spherical core with pure spherical geometry
 * - Unified electric amber-orange color palette
 */

(function () {
  'use strict';

  if (typeof THREE === 'undefined') {
    console.error('Three.js library is required.');
    return;
  }

  var container = document.getElementById('webgl-container');
  if (!container) return;

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 3000);
  camera.position.set(0, 0, 480);

  var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.LinearToneMapping;
  container.appendChild(renderer.domElement);

  // --------------------------------------------------------------------------
  // UNIFIED ELECTRIC AMBER-ORANGE PALETTE
  // --------------------------------------------------------------------------
  var PALETTE = {
    coreWhite:   0xffffff,
    hotGold:     0xfff0aa,
    amberBright: 0xffa600,
    amberMid:    0xff8000,
    amberDeep:   0xee5500,
    amberGlow:   0xd84500,
    amberFaint:  0x993000
  };

  // --------------------------------------------------------------------------
  // Texture factories
  // --------------------------------------------------------------------------
  function createParticleTexture() {
    var c = document.createElement('canvas');
    c.width = 64; c.height = 64;
    var ctx = c.getContext('2d');
    var g = ctx.createRadialGradient(32, 32, 0, 32, 32, 30);
    g.addColorStop(0.00, 'rgba(255,255,255,1.0)');
    g.addColorStop(0.18, 'rgba(255,235,130,0.98)');
    g.addColorStop(0.48, 'rgba(255,145,15,0.65)');
    g.addColorStop(0.78, 'rgba(230,75,0,0.25)');
    g.addColorStop(1.00, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(32, 32, 30, 0, Math.PI * 2); ctx.fill();
    return new THREE.CanvasTexture(c);
  }

  function createGlowTexture(size, stops) {
    var c = document.createElement('canvas');
    c.width = size; c.height = size;
    var ctx = c.getContext('2d');
    var half = size / 2;
    var g = ctx.createRadialGradient(half, half, 0, half, half, half * 0.96);
    stops.forEach(function(s) { g.addColorStop(s[0], s[1]); });
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(half, half, half * 0.96, 0, Math.PI * 2); ctx.fill();
    return new THREE.CanvasTexture(c);
  }

  var particleTexture = createParticleTexture();

  var coreHotTexture = createGlowTexture(256, [
    [0.00, 'rgba(255,255,255,1.0)'],
    [0.10, 'rgba(255,245,160,0.98)'],
    [0.28, 'rgba(255,165,25,0.85)'],
    [0.55, 'rgba(240,95,5,0.45)'],
    [1.00, 'rgba(0,0,0,0)']
  ]);

  var coreMidTexture = createGlowTexture(256, [
    [0.00, 'rgba(255,195,45,0.90)'],
    [0.35, 'rgba(255,120,10,0.55)'],
    [0.70, 'rgba(215,65,0,0.22)'],
    [1.00, 'rgba(0,0,0,0)']
  ]);

  var coreAmbientTexture = createGlowTexture(256, [
    [0.00, 'rgba(255,140,20,0.50)'],
    [0.45, 'rgba(225,80,5,0.22)'],
    [0.80, 'rgba(160,40,0,0.08)'],
    [1.00, 'rgba(0,0,0,0)']
  ]);

  // Seeded RNG
  function sfc32(a, b, c, d) {
    return function () {
      a >>>= 0; b >>>= 0; c >>>= 0; d >>>= 0;
      let t = (a + b | 0) + d | 0;
      d = d + 1 | 0;
      a = b ^ b >>> 9;
      b = c + (c << 3) | 0;
      c = (c << 21 | c >>> 11);
      c = c + t | 0;
      return (t >>> 0) / 4294967296;
    };
  }
  var rng = sfc32(0x9E3779B9, 0x243F6A88, 0xB7E15162, 2026);

  function sphericalToVec3(radius, phi, theta) {
    var sinPhi = Math.sin(phi);
    return new THREE.Vector3(
      radius * sinPhi * Math.cos(theta),
      radius * Math.cos(phi),
      radius * sinPhi * Math.sin(theta)
    );
  }

  function createRingLine(radius, colorHex, opacity, segments) {
    segments = segments || 180;
    var geom = new THREE.BufferGeometry();
    var pts = [];
    for (var i = 0; i <= segments; i++) {
      var a = (i / segments) * Math.PI * 2;
      pts.push(Math.cos(a) * radius, Math.sin(a) * radius, 0);
    }
    geom.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    return new THREE.Line(geom, new THREE.LineBasicMaterial({
      color: colorHex, transparent: true, opacity: opacity,
      blending: THREE.AdditiveBlending
    }));
  }

  // Broad ring disc helper
  function createBroadRingBand(innerR, outerR, colorHex, opacity, segments) {
    segments = segments || 120;
    var geom = new THREE.RingGeometry(innerR, outerR, segments);
    var mat = new THREE.MeshBasicMaterial({
      color: colorHex,
      transparent: true,
      opacity: opacity,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    return new THREE.Mesh(geom, mat);
  }

  var hologramRoot = new THREE.Group();
  scene.add(hologramRoot);

  // ==========================================================================
  // 1. OUTER SPHERE SHELL (Decreased size: 164 -> 138)
  // ==========================================================================
  var outerSphereGroup = new THREE.Group();
  hologramRoot.add(outerSphereGroup);
  var SPHERE_RADIUS = 138;

  outerSphereGroup.add(new THREE.Mesh(
    new THREE.SphereGeometry(SPHERE_RADIUS, 54, 54),
    new THREE.MeshBasicMaterial({
      color: PALETTE.amberGlow, transparent: true, opacity: 0.05,
      side: THREE.BackSide, blending: THREE.AdditiveBlending
    })
  ));

  outerSphereGroup.add(createRingLine(SPHERE_RADIUS,     PALETTE.amberBright, 0.70));
  outerSphereGroup.add(createRingLine(SPHERE_RADIUS + 2, PALETTE.hotGold,     0.95));
  outerSphereGroup.add(createRingLine(SPHERE_RADIUS + 4, PALETTE.amberMid,    0.45));

  var circuitLinePositions = [];

  // 28 major hubs on the smaller sphere
  var hubCount = 28;
  for (var h = 0; h < hubCount; h++) {
    var hubPhi   = 0.20 + rng() * (Math.PI - 0.40);
    var hubTheta = rng() * Math.PI * 2;
    var branches = 7 + Math.floor(rng() * 7);
    for (var b = 0; b < branches; b++) {
      var curPhi = hubPhi, curTheta = hubTheta;
      var steps = 4 + Math.floor(rng() * 5);
      for (var s = 0; s < steps; s++) {
        var p1 = sphericalToVec3(SPHERE_RADIUS, curPhi, curTheta);
        if (s % 2 === 0) { curTheta += (rng() - 0.5) * 0.30; }
        else { curPhi = Math.max(0.10, Math.min(Math.PI - 0.10, curPhi + (rng() - 0.5) * 0.25)); }
        var p2 = sphericalToVec3(SPHERE_RADIUS, curPhi, curTheta);
        circuitLinePositions.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);
      }
    }
  }

  // 40 lightning zigzag traces
  for (var z = 0; z < 40; z++) {
    var zphi = 0.25 + rng() * (Math.PI - 0.50);
    var ztheta = rng() * Math.PI * 2;
    var zsegs = 5 + Math.floor(rng() * 6);
    for (var zs = 0; zs < zsegs; zs++) {
      var zp1 = sphericalToVec3(SPHERE_RADIUS, zphi, ztheta);
      zphi   = Math.max(0.10, Math.min(Math.PI - 0.10, zphi   + (rng() - 0.5) * 0.22));
      ztheta = ztheta + (rng() - 0.5) * 0.22;
      var zp2 = sphericalToVec3(SPHERE_RADIUS, zphi, ztheta);
      circuitLinePositions.push(zp1.x, zp1.y, zp1.z, zp2.x, zp2.y, zp2.z);
    }
  }

  // Dense latitude arcs (12 bands)
  var latFracs = [-0.80, -0.65, -0.50, -0.35, -0.20, -0.07, 0.07, 0.20, 0.35, 0.50, 0.65, 0.80];
  for (var lf = 0; lf < latFracs.length; lf++) {
    var latPhi = Math.PI / 2 + latFracs[lf] * (Math.PI / 2.2);
    var lsegs = 5 + Math.floor(rng() * 6);
    for (var ls = 0; ls < lsegs; ls++) {
      var startTheta = rng() * Math.PI * 2;
      var arcSpan = 0.35 + rng() * 0.85;
      for (var li = 0; li < 30; li++) {
        var lt1 = startTheta + (li / 30) * arcSpan;
        var lt2 = startTheta + ((li + 1) / 30) * arcSpan;
        var la1 = sphericalToVec3(SPHERE_RADIUS, latPhi, lt1);
        var la2 = sphericalToVec3(SPHERE_RADIUS, latPhi, lt2);
        circuitLinePositions.push(la1.x, la1.y, la1.z, la2.x, la2.y, la2.z);
      }
    }
  }

  // Full continuous latitude circles (5 rings, both hemispheres)
  var latRings = [0.20, 0.38, 0.58, 0.72, 0.88];
  for (var lr = 0; lr < latRings.length; lr++) {
    var lrFrac = latRings[lr];
    for (var lrSign = -1; lrSign <= 1; lrSign += 2) {
      var lrPhi = Math.PI / 2 + lrSign * lrFrac * (Math.PI / 2.4);
      for (var lri = 0; lri < 90; lri++) {
        var lrt1 = (lri / 90) * Math.PI * 2;
        var lrt2 = ((lri + 1) / 90) * Math.PI * 2;
        var lrp1 = sphericalToVec3(SPHERE_RADIUS, lrPhi, lrt1);
        var lrp2 = sphericalToVec3(SPHERE_RADIUS, lrPhi, lrt2);
        circuitLinePositions.push(lrp1.x, lrp1.y, lrp1.z, lrp2.x, lrp2.y, lrp2.z);
      }
    }
  }

  // 24 longitude meridians
  for (var m = 0; m < 24; m++) {
    var mTheta = (m / 24) * Math.PI * 2 + (rng() - 0.5) * 0.10;
    var mStartPhi = 0.25 + rng() * 0.35;
    var mPhiSpan  = 0.55 + rng() * 1.40;
    for (var mi = 0; mi < 32; mi++) {
      var mp1 = sphericalToVec3(SPHERE_RADIUS, mStartPhi + (mi / 32) * mPhiSpan, mTheta);
      var mp2 = sphericalToVec3(SPHERE_RADIUS, mStartPhi + ((mi + 1) / 32) * mPhiSpan, mTheta);
      circuitLinePositions.push(mp1.x, mp1.y, mp1.z, mp2.x, mp2.y, mp2.z);
    }
  }

  // 70 chip micro-panels
  for (var cp = 0; cp < 70; cp++) {
    var cPhi   = 0.25 + rng() * (Math.PI - 0.50);
    var cTheta = rng() * Math.PI * 2;
    var dPhi   = 0.035 + rng() * 0.055;
    var dTheta = 0.04  + rng() * 0.075;
    var cc1 = sphericalToVec3(SPHERE_RADIUS, cPhi,        cTheta);
    var cc2 = sphericalToVec3(SPHERE_RADIUS, cPhi + dPhi, cTheta);
    var cc3 = sphericalToVec3(SPHERE_RADIUS, cPhi + dPhi, cTheta + dTheta);
    var cc4 = sphericalToVec3(SPHERE_RADIUS, cPhi,        cTheta + dTheta);
    circuitLinePositions.push(cc1.x, cc1.y, cc1.z, cc2.x, cc2.y, cc2.z);
    circuitLinePositions.push(cc2.x, cc2.y, cc2.z, cc3.x, cc3.y, cc3.z);
    circuitLinePositions.push(cc3.x, cc3.y, cc3.z, cc4.x, cc4.y, cc4.z);
    circuitLinePositions.push(cc4.x, cc4.y, cc4.z, cc1.x, cc1.y, cc1.z);
    if (rng() > 0.45) {
      var cm1 = sphericalToVec3(SPHERE_RADIUS, cPhi + dPhi * 0.5, cTheta);
      var cm2 = sphericalToVec3(SPHERE_RADIUS, cPhi + dPhi * 0.5, cTheta + dTheta);
      circuitLinePositions.push(cm1.x, cm1.y, cm1.z, cm2.x, cm2.y, cm2.z);
    }
  }

  var circuitGeom = new THREE.BufferGeometry();
  circuitGeom.setAttribute('position', new THREE.Float32BufferAttribute(circuitLinePositions, 3));
  outerSphereGroup.add(new THREE.LineSegments(circuitGeom, new THREE.LineBasicMaterial({
    color: PALETTE.amberBright, transparent: true, opacity: 0.85,
    blending: THREE.AdditiveBlending
  })));

  // Accent layer (brighter hot gold traces)
  var accentPositions = [];
  for (var ah = 0; ah < 14; ah++) {
    var ahPhi   = 0.30 + rng() * (Math.PI - 0.60);
    var ahTheta = rng() * Math.PI * 2;
    for (var ab = 0; ab < 5; ab++) {
      var ap = ahPhi, at = ahTheta;
      var asteps = 3 + Math.floor(rng() * 3);
      for (var as = 0; as < asteps; as++) {
        var ap1 = sphericalToVec3(SPHERE_RADIUS, ap, at);
        if (as % 2 === 0) at += (rng() - 0.5) * 0.22;
        else ap = Math.max(0.12, Math.min(Math.PI - 0.12, ap + (rng() - 0.5) * 0.18));
        var ap2 = sphericalToVec3(SPHERE_RADIUS, ap, at);
        accentPositions.push(ap1.x, ap1.y, ap1.z, ap2.x, ap2.y, ap2.z);
      }
    }
  }
  var accentGeom = new THREE.BufferGeometry();
  accentGeom.setAttribute('position', new THREE.Float32BufferAttribute(accentPositions, 3));
  outerSphereGroup.add(new THREE.LineSegments(accentGeom, new THREE.LineBasicMaterial({
    color: PALETTE.hotGold, transparent: true, opacity: 0.95,
    blending: THREE.AdditiveBlending
  })));

  // 1400 surface nodes
  var nodeCount = 1400;
  var nodePositions = [], nodeColors = [];
  var colorBright = new THREE.Color(PALETTE.hotGold);
  var colorMid    = new THREE.Color(PALETTE.amberBright);
  var colorDeep   = new THREE.Color(PALETTE.amberMid);
  for (var ni = 0; ni < nodeCount; ni++) {
    var nphi   = Math.acos(2 * rng() - 1);
    var ntheta = rng() * Math.PI * 2;
    var nv     = sphericalToVec3(SPHERE_RADIUS + (rng() - 0.5) * 3.5, nphi, ntheta);
    nodePositions.push(nv.x, nv.y, nv.z);
    var npick = rng();
    var nc = npick > 0.65 ? colorBright : npick > 0.30 ? colorMid : colorDeep;
    nodeColors.push(nc.r, nc.g, nc.b);
  }
  var nodeGeom = new THREE.BufferGeometry();
  nodeGeom.setAttribute('position', new THREE.Float32BufferAttribute(nodePositions, 3));
  nodeGeom.setAttribute('color',    new THREE.Float32BufferAttribute(nodeColors, 3));
  var nodeMat = new THREE.PointsMaterial({
    size: 7.5, vertexColors: true, map: particleTexture,
    transparent: true, opacity: 0.95,
    blending: THREE.AdditiveBlending, depthWrite: false
  });
  outerSphereGroup.add(new THREE.Points(nodeGeom, nodeMat));

  // --------------------------------------------------------------------------
  // BROAD RADIAL SPIKES (Radial orientation, same length ~14-38, broader profile)
  // --------------------------------------------------------------------------
  var pinPositions = [], pinTipPositions = [], pinTipColors = [];
  var pinCount = 100;
  var spikeWidth = 0.010; // Natural radial wedge width

  for (var pi = 0; pi < pinCount; pi++) {
    var pang = rng() * Math.PI * 2;
    var pr1  = SPHERE_RADIUS - 2;
    var spikeLen = 14 + rng() * 26; // Same absolute spike length
    var pr2  = SPHERE_RADIUS + spikeLen;
    var ppz  = (rng() - 0.5) * 35;

    // Dual radial rails from base to tip
    var cosL = Math.cos(pang - spikeWidth), sinL = Math.sin(pang - spikeWidth);
    var cosR = Math.cos(pang + spikeWidth), sinR = Math.sin(pang + spikeWidth);
    var cosM = Math.cos(pang), sinM = Math.sin(pang);

    // Left rail
    pinPositions.push(cosL * pr1, sinL * pr1, ppz, cosL * pr2, sinL * pr2, ppz);
    // Right rail
    pinPositions.push(cosR * pr1, sinR * pr1, ppz, cosR * pr2, sinR * pr2, ppz);
    // Center bright beam
    pinPositions.push(cosM * pr1, sinM * pr1, ppz, cosM * pr2, sinM * pr2, ppz);
    // Tip crossbar
    pinPositions.push(cosL * pr2, sinL * pr2, ppz, cosR * pr2, sinR * pr2, ppz);

    // Glowing tip bead
    pinTipPositions.push(cosM * pr2, sinM * pr2, ppz);
    pinTipColors.push(colorBright.r, colorBright.g, colorBright.b);
  }

  var pinGeom = new THREE.BufferGeometry();
  pinGeom.setAttribute('position', new THREE.Float32BufferAttribute(pinPositions, 3));
  outerSphereGroup.add(new THREE.LineSegments(pinGeom, new THREE.LineBasicMaterial({
    color: PALETTE.amberBright, transparent: true, opacity: 0.88,
    blending: THREE.AdditiveBlending
  })));

  var pinTipGeom = new THREE.BufferGeometry();
  pinTipGeom.setAttribute('position', new THREE.Float32BufferAttribute(pinTipPositions, 3));
  pinTipGeom.setAttribute('color',    new THREE.Float32BufferAttribute(pinTipColors, 3));
  var pinTipMat = new THREE.PointsMaterial({
    size: 9.5, vertexColors: true, map: particleTexture,
    transparent: true, opacity: 1.0,
    blending: THREE.AdditiveBlending, depthWrite: false
  });
  outerSphereGroup.add(new THREE.Points(pinTipGeom, pinTipMat));

  outerSphereGroup.rotation.x =  0.38;
  outerSphereGroup.rotation.z = -0.15;

  // ==========================================================================
  // 2. INNER GYROSCOPIC RINGS — BROADER BANDS
  // ==========================================================================
  var innerGyroGroup = new THREE.Group();
  hologramRoot.add(innerGyroGroup);

  // 2a. Broad Corona Equator Ring (Span across radius 96 - 114)
  var coronaGroup = new THREE.Group();
  innerGyroGroup.add(coronaGroup);
  var CORONA_R = 104;

  // Broad glowing disc band for corona
  coronaGroup.add(createBroadRingBand(CORONA_R - 9, CORONA_R + 9, PALETTE.amberGlow, 0.20, 140));
  coronaGroup.add(createBroadRingBand(CORONA_R - 4, CORONA_R + 4, PALETTE.amberMid,  0.28, 140));

  // Multi-track boundary lines spanning 18 radius units wide
  coronaGroup.add(createRingLine(CORONA_R - 10, PALETTE.amberGlow,   0.45));
  coronaGroup.add(createRingLine(CORONA_R - 6,  PALETTE.amberDeep,   0.72));
  coronaGroup.add(createRingLine(CORONA_R - 3,  PALETTE.amberMid,    0.85));
  coronaGroup.add(createRingLine(CORONA_R,      PALETTE.hotGold,     1.00));
  coronaGroup.add(createRingLine(CORONA_R + 3,  PALETTE.amberBright, 0.90));
  coronaGroup.add(createRingLine(CORONA_R + 6,  PALETTE.amberMid,    0.75));
  coronaGroup.add(createRingLine(CORONA_R + 10, PALETTE.amberGlow,   0.45));

  // Extended vernier teeth across the full band
  var teethPositions = [];
  for (var ti = 0; ti < 360; ti++) {
    var ta = (ti / 360) * Math.PI * 2;
    var isMajor = ti % 8 === 0;
    var tLen = isMajor ? 10.0 : 5.5; // Broader teeth reach
    teethPositions.push(
      Math.cos(ta) * (CORONA_R - tLen), Math.sin(ta) * (CORONA_R - tLen), 0,
      Math.cos(ta) * (CORONA_R + tLen), Math.sin(ta) * (CORONA_R + tLen), 0
    );
  }
  var teethGeom = new THREE.BufferGeometry();
  teethGeom.setAttribute('position', new THREE.Float32BufferAttribute(teethPositions, 3));
  coronaGroup.add(new THREE.LineSegments(teethGeom, new THREE.LineBasicMaterial({
    color: PALETTE.amberMid, transparent: true, opacity: 0.85,
    blending: THREE.AdditiveBlending
  })));

  // Digital square wave along broad band
  var wavePositions = [];
  for (var wi = 0; wi <= 140; wi++) {
    var wa = (wi / 140) * Math.PI * 2;
    var wr = CORONA_R + (wi % 2 === 0 ? 7.5 : -7.5);
    wavePositions.push(Math.cos(wa) * wr, Math.sin(wa) * wr, 0);
  }
  var waveGeom = new THREE.BufferGeometry();
  waveGeom.setAttribute('position', new THREE.Float32BufferAttribute(wavePositions, 3));
  coronaGroup.add(new THREE.Line(waveGeom, new THREE.LineBasicMaterial({
    color: PALETTE.hotGold, transparent: true, opacity: 0.92,
    blending: THREE.AdditiveBlending
  })));

  // Spark beads along broad corona
  var sparkPositions = [], sparkColors = [];
  for (var si = 0; si < 100; si++) {
    var sa = (si / 100) * Math.PI * 2;
    var sr = CORONA_R + ((si * 13) % 23) - 11;
    sparkPositions.push(Math.cos(sa) * sr, Math.sin(sa) * sr, (rng() - 0.5) * 10);
    sparkColors.push(colorBright.r, colorBright.g, colorBright.b);
  }
  var sparkGeom = new THREE.BufferGeometry();
  sparkGeom.setAttribute('position', new THREE.Float32BufferAttribute(sparkPositions, 3));
  sparkGeom.setAttribute('color',    new THREE.Float32BufferAttribute(sparkColors, 3));
  coronaGroup.add(new THREE.Points(sparkGeom, new THREE.PointsMaterial({
    size: 9.5, vertexColors: true, map: particleTexture,
    transparent: true, opacity: 0.98,
    blending: THREE.AdditiveBlending, depthWrite: false
  })));

  // 2b. Broad Gyro Ring 1 (Radius ~80, width ~12)
  var gyroRing1 = new THREE.Group();
  innerGyroGroup.add(gyroRing1);
  gyroRing1.rotation.x =  0.55;
  gyroRing1.rotation.y = -0.35;
  gyroRing1.add(createBroadRingBand(74, 84, PALETTE.amberGlow, 0.18, 120));
  gyroRing1.add(createRingLine(74, PALETTE.amberDeep,   0.55));
  gyroRing1.add(createRingLine(77, PALETTE.amberMid,    0.72));
  gyroRing1.add(createRingLine(81, PALETTE.amberBright, 0.92));
  gyroRing1.add(createRingLine(85, PALETTE.hotGold,     0.85));

  var spoke1Pos = [];
  for (var spi = 0; spi < 36; spi++) {
    var spa = (spi / 36) * Math.PI * 2;
    spoke1Pos.push(Math.cos(spa) * 28, Math.sin(spa) * 28, 0,
                   Math.cos(spa) * 85, Math.sin(spa) * 85, 0);
  }
  var spoke1Geom = new THREE.BufferGeometry();
  spoke1Geom.setAttribute('position', new THREE.Float32BufferAttribute(spoke1Pos, 3));
  gyroRing1.add(new THREE.LineSegments(spoke1Geom, new THREE.LineBasicMaterial({
    color: PALETTE.amberDeep, transparent: true, opacity: 0.45,
    blending: THREE.AdditiveBlending
  })));

  // 2c. Broad Gyro Ring 2 (Radius ~60, width ~10)
  var gyroRing2 = new THREE.Group();
  innerGyroGroup.add(gyroRing2);
  gyroRing2.rotation.x = -0.45;
  gyroRing2.rotation.z =  0.65;
  gyroRing2.add(createBroadRingBand(55, 65, PALETTE.amberGlow, 0.20, 100));
  gyroRing2.add(createRingLine(55, PALETTE.amberDeep,   0.60));
  gyroRing2.add(createRingLine(58, PALETTE.amberMid,    0.80));
  gyroRing2.add(createRingLine(62, PALETTE.amberBright, 0.95));
  gyroRing2.add(createRingLine(65, PALETTE.hotGold,     0.90));

  // 2d. Broad Gyro Ring 3 (Radius ~48, width ~8)
  var gyroRing3 = new THREE.Group();
  innerGyroGroup.add(gyroRing3);
  gyroRing3.rotation.x =  0.25;
  gyroRing3.rotation.z = -0.80;
  gyroRing3.add(createBroadRingBand(44, 52, PALETTE.amberGlow, 0.18, 90));
  gyroRing3.add(createRingLine(44, PALETTE.amberDeep,   0.65));
  gyroRing3.add(createRingLine(48, PALETTE.amberBright, 0.88));
  gyroRing3.add(createRingLine(52, PALETTE.hotGold,     0.82));

  // 2e. Broader Sweeping 3D Orbital Ribbon Band (width 11.0)
  var ribbonSegments = 70;
  var ribbonCurvePts = [];
  for (var ri = 0; ri <= ribbonSegments; ri++) {
    var ru = ri / ribbonSegments;
    var rtheta = 0.35 * Math.PI + ru * 1.55 * Math.PI;
    var rr = 68 + Math.sin(ru * Math.PI) * 15;
    ribbonCurvePts.push(new THREE.Vector3(
      Math.cos(rtheta) * rr,
      Math.sin(rtheta) * (rr * 0.75),
      Math.sin(ru * Math.PI) * 32 - 14
    ));
  }
  var ribbonVerts = [], ribbonIndices = [];
  var ribbonWidth = 11.0;
  for (var rvi = 0; rvi <= ribbonSegments; rvi++) {
    var rpt   = ribbonCurvePts[rvi];
    var rnorm = rpt.clone().normalize();
    var rup   = new THREE.Vector3(0, 0, 1);
    var rbin  = new THREE.Vector3().crossVectors(rnorm, rup).normalize();
    var rpO   = rpt.clone().addScaledVector(rbin,  ribbonWidth / 2);
    var rpI   = rpt.clone().addScaledVector(rbin, -ribbonWidth / 2);
    ribbonVerts.push(rpO.x, rpO.y, rpO.z, rpI.x, rpI.y, rpI.z);
    if (rvi < ribbonSegments) {
      var ra = rvi * 2;
      ribbonIndices.push(ra, ra + 1, ra + 2, ra + 1, ra + 3, ra + 2);
    }
  }
  var ribbonMeshGeom = new THREE.BufferGeometry();
  ribbonMeshGeom.setAttribute('position', new THREE.Float32BufferAttribute(ribbonVerts, 3));
  ribbonMeshGeom.setIndex(ribbonIndices);
  ribbonMeshGeom.computeVertexNormals();
  var ribbonMesh = new THREE.Mesh(ribbonMeshGeom, new THREE.MeshBasicMaterial({
    color: PALETTE.amberBright, side: THREE.DoubleSide,
    transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending
  }));
  innerGyroGroup.add(ribbonMesh);

  // Ribbon rails
  var railOuterPts = [], railInnerPts = [];
  for (var rii = 0; rii <= ribbonSegments; rii++) {
    railOuterPts.push(ribbonVerts[rii * 6],     ribbonVerts[rii * 6 + 1], ribbonVerts[rii * 6 + 2]);
    railInnerPts.push(ribbonVerts[rii * 6 + 3], ribbonVerts[rii * 6 + 4], ribbonVerts[rii * 6 + 5]);
  }
  var railOGeom = new THREE.BufferGeometry();
  railOGeom.setAttribute('position', new THREE.Float32BufferAttribute(railOuterPts, 3));
  innerGyroGroup.add(new THREE.Line(railOGeom, new THREE.LineBasicMaterial({
    color: PALETTE.hotGold, transparent: true, opacity: 0.98,
    blending: THREE.AdditiveBlending
  })));
  var railIGeom = new THREE.BufferGeometry();
  railIGeom.setAttribute('position', new THREE.Float32BufferAttribute(railInnerPts, 3));
  innerGyroGroup.add(new THREE.Line(railIGeom, new THREE.LineBasicMaterial({
    color: PALETTE.amberBright, transparent: true, opacity: 0.88,
    blending: THREE.AdditiveBlending
  })));

  // Sweeping tail arc
  var tailPts = [];
  for (var tli = 0; tli <= 40; tli++) {
    var tlu = tli / 40;
    tailPts.push(-18 + tlu * 70, Math.sin(tlu * Math.PI * 0.85) * 20 - tlu * 11, (1 - tlu) * 16);
  }
  var tailGeom = new THREE.BufferGeometry();
  tailGeom.setAttribute('position', new THREE.Float32BufferAttribute(tailPts, 3));
  innerGyroGroup.add(new THREE.Line(tailGeom, new THREE.LineBasicMaterial({
    color: PALETTE.hotGold, transparent: true, opacity: 0.95,
    blending: THREE.AdditiveBlending
  })));

  // ==========================================================================
  // 3. CENTRAL FUSION CORE — 3D CIRCULAR SPHERE CORE
  // ==========================================================================
  var coreGroup = new THREE.Group();
  hologramRoot.add(coreGroup);

  var coreSphereCage = new THREE.Group();
  coreGroup.add(coreSphereCage);

  var CORE_SPHERE_R = 36;
  var coreSphereWireGeom = new THREE.WireframeGeometry(
    new THREE.SphereGeometry(CORE_SPHERE_R, 18, 12)
  );
  var coreSphereWireMat = new THREE.LineBasicMaterial({
    color: PALETTE.amberBright,
    transparent: true,
    opacity: 0.70,
    blending: THREE.AdditiveBlending
  });
  coreSphereCage.add(new THREE.LineSegments(coreSphereWireGeom, coreSphereWireMat));

  function create3DCircularRing(radius, rotX, rotY, rotZ, colorHex, opacity) {
    var g = new THREE.BufferGeometry();
    var pts = [];
    var segs = 120;
    for (var i = 0; i <= segs; i++) {
      var a = (i / segs) * Math.PI * 2;
      pts.push(Math.cos(a) * radius, Math.sin(a) * radius, 0);
    }
    g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    var l = new THREE.Line(g, new THREE.LineBasicMaterial({
      color: colorHex, transparent: true, opacity: opacity,
      blending: THREE.AdditiveBlending
    }));
    l.rotation.set(rotX, rotY, rotZ);
    return l;
  }

  coreSphereCage.add(create3DCircularRing(CORE_SPHERE_R + 1,  Math.PI / 2, 0, 0, PALETTE.hotGold, 0.95));
  coreSphereCage.add(create3DCircularRing(CORE_SPHERE_R + 1,  0, Math.PI / 2, 0, PALETTE.amberBright, 0.90));
  coreSphereCage.add(create3DCircularRing(CORE_SPHERE_R + 1,  Math.PI / 4, Math.PI / 4, 0, PALETTE.amberMid, 0.75));
  coreSphereCage.add(create3DCircularRing(CORE_SPHERE_R + 1, -Math.PI / 4, Math.PI / 4, 0, PALETTE.amberMid, 0.75));

  // Rotating Nodes on Core Sphere Surface (60 points)
  var coreNodePositions = [];
  var coreNodeColors = [];
  for (var cni = 0; cni < 60; cni++) {
    var cphi   = Math.acos(2 * rng() - 1);
    var ctheta = rng() * Math.PI * 2;
    var cnv    = sphericalToVec3(CORE_SPHERE_R, cphi, ctheta);
    coreNodePositions.push(cnv.x, cnv.y, cnv.z);
    var ccol = rng() > 0.5 ? colorBright : colorMid;
    coreNodeColors.push(ccol.r, ccol.g, ccol.b);
  }
  var coreNodeGeom = new THREE.BufferGeometry();
  coreNodeGeom.setAttribute('position', new THREE.Float32BufferAttribute(coreNodePositions, 3));
  coreNodeGeom.setAttribute('color',    new THREE.Float32BufferAttribute(coreNodeColors, 3));
  var coreNodePoints = new THREE.Points(coreNodeGeom, new THREE.PointsMaterial({
    size: 7.0, vertexColors: true, map: particleTexture,
    transparent: true, opacity: 0.95,
    blending: THREE.AdditiveBlending, depthWrite: false
  }));
  coreSphereCage.add(coreNodePoints);

  // Circular vernier reticle with tick marks (r=42)
  var coreVernierPositions = [];
  for (var cvi = 0; cvi < 64; cvi++) {
    var cva = (cvi / 64) * Math.PI * 2;
    var cvLen = cvi % 8 === 0 ? 4.5 : 2.5;
    coreVernierPositions.push(
      Math.cos(cva) * (42 - cvLen), Math.sin(cva) * (42 - cvLen), 0,
      Math.cos(cva) * (42 + cvLen), Math.sin(cva) * (42 + cvLen), 0
    );
  }
  var coreVernierGeom = new THREE.BufferGeometry();
  coreVernierGeom.setAttribute('position', new THREE.Float32BufferAttribute(coreVernierPositions, 3));
  coreGroup.add(new THREE.LineSegments(coreVernierGeom, new THREE.LineBasicMaterial({
    color: PALETTE.hotGold, transparent: true, opacity: 0.88,
    blending: THREE.AdditiveBlending
  })));

  // Circular segmented perimeter arcs (4 quadrants)
  for (var cqi = 0; cqi < 4; cqi++) {
    var qStart = (cqi * Math.PI / 2) + 0.12;
    var qSpan  = (Math.PI / 2) - 0.24;
    var qGeom = new THREE.BufferGeometry();
    var qPts = [];
    for (var qj = 0; qj <= 20; qj++) {
      var qa = qStart + (qj / 20) * qSpan;
      qPts.push(Math.cos(qa) * 46, Math.sin(qa) * 46, 0);
    }
    qGeom.setAttribute('position', new THREE.Float32BufferAttribute(qPts, 3));
    coreGroup.add(new THREE.Line(qGeom, new THREE.LineBasicMaterial({
      color: PALETTE.amberBright, transparent: true, opacity: 0.95,
      blending: THREE.AdditiveBlending
    })));
  }

  // Circular Crosshair Ticks (0, 90, 180, 270 deg)
  var crosshairPositions = [
    46, 0, 0,  54, 0, 0,
   -46, 0, 0, -54, 0, 0,
    0, 46, 0,   0, 54, 0,
    0,-46, 0,   0,-54, 0
  ];
  var crosshairGeom = new THREE.BufferGeometry();
  crosshairGeom.setAttribute('position', new THREE.Float32BufferAttribute(crosshairPositions, 3));
  coreGroup.add(new THREE.LineSegments(crosshairGeom, new THREE.LineBasicMaterial({
    color: PALETTE.hotGold, transparent: true, opacity: 1.0,
    blending: THREE.AdditiveBlending
  })));

  // Concentric Circular Core Boundary Rings
  coreGroup.add(createRingLine( 4,  PALETTE.coreWhite,   1.00));
  coreGroup.add(createRingLine( 9,  PALETTE.hotGold,     0.95));
  coreGroup.add(createRingLine(16,  PALETTE.hotGold,     0.90));
  coreGroup.add(createRingLine(24,  PALETTE.amberBright, 0.85));
  coreGroup.add(createRingLine(32,  PALETTE.amberMid,    0.70));
  coreGroup.add(createRingLine(42,  PALETTE.hotGold,     0.92));
  coreGroup.add(createRingLine(48,  PALETTE.amberDeep,   0.50));

  // Archimedean Spiral Core Singularity
  var spiralPts = [];
  for (var svi = 0; svi <= 80; svi++) {
    var svu = svi / 80;
    var svth = svu * Math.PI * 4;
    var svr  = 2 + svu * 26;
    spiralPts.push(Math.cos(svth) * svr, Math.sin(svth) * svr, 0);
  }
  var spiralGeom = new THREE.BufferGeometry();
  spiralGeom.setAttribute('position', new THREE.Float32BufferAttribute(spiralPts, 3));
  coreGroup.add(new THREE.Line(spiralGeom, new THREE.LineBasicMaterial({
    color: PALETTE.hotGold, transparent: true, opacity: 0.95,
    blending: THREE.AdditiveBlending
  })));

  // Volumetric multi-layer core glow
  function makeGlowSprite(texture, colorHex, scale, opacity) {
    var mat = new THREE.SpriteMaterial({
      map: texture, color: colorHex,
      transparent: true, opacity: opacity,
      blending: THREE.AdditiveBlending, depthWrite: false
    });
    var sprite = new THREE.Sprite(mat);
    sprite.scale.set(scale, scale, 1);
    return sprite;
  }

  coreGroup.add(makeGlowSprite(coreHotTexture,     PALETTE.coreWhite,   55,  1.00));
  coreGroup.add(makeGlowSprite(coreHotTexture,     PALETTE.hotGold,    110,  0.88));
  coreGroup.add(makeGlowSprite(coreMidTexture,     PALETTE.amberBright, 180, 0.70));
  coreGroup.add(makeGlowSprite(coreMidTexture,     PALETTE.amberDeep,  270,  0.45));
  coreGroup.add(makeGlowSprite(coreAmbientTexture, PALETTE.amberGlow,  380,  0.28));
  coreGroup.add(makeGlowSprite(coreAmbientTexture, 0x4a1800,           520,  0.20));

  coreGroup.add(new THREE.Mesh(
    new THREE.SphereGeometry(50, 24, 24),
    new THREE.MeshBasicMaterial({
      color: PALETTE.amberDeep, transparent: true, opacity: 0.08,
      blending: THREE.AdditiveBlending, depthWrite: false
    })
  ));
  coreGroup.add(new THREE.Mesh(
    new THREE.SphereGeometry(78, 24, 24),
    new THREE.MeshBasicMaterial({
      color: PALETTE.amberGlow, transparent: true, opacity: 0.05,
      blending: THREE.AdditiveBlending, depthWrite: false
    })
  ));

  // ==========================================================================
  // 4. FLOATING EMBER PARTICLES
  // ==========================================================================
  var EMBER_COUNT = 320;
  var emberPositions = new Float32Array(EMBER_COUNT * 3);
  var emberVelocities = [];
  var emberColors = new Float32Array(EMBER_COUNT * 3);
  var emberLife = new Float32Array(EMBER_COUNT);

  function resetEmber(i) {
    var ephi   = Math.acos(2 * rng() - 1);
    var etheta = rng() * Math.PI * 2;
    var espeed = 0.3 + rng() * 1.2;
    emberVelocities[i] = {
      vx: Math.sin(ephi) * Math.cos(etheta) * espeed,
      vy: Math.cos(ephi) * espeed,
      vz: Math.sin(ephi) * Math.sin(etheta) * espeed
    };
    emberPositions[i * 3]     = (rng() - 0.5) * 20;
    emberPositions[i * 3 + 1] = (rng() - 0.5) * 20;
    emberPositions[i * 3 + 2] = (rng() - 0.5) * 20;
    emberLife[i] = rng() * 200;
    var et = rng();
    var ec = et > 0.6 ? colorBright : et > 0.25 ? colorMid : colorDeep;
    emberColors[i * 3]     = ec.r;
    emberColors[i * 3 + 1] = ec.g;
    emberColors[i * 3 + 2] = ec.b;
  }

  for (var ei = 0; ei < EMBER_COUNT; ei++) resetEmber(ei);

  var emberGeom = new THREE.BufferGeometry();
  emberGeom.setAttribute('position', new THREE.BufferAttribute(emberPositions, 3));
  emberGeom.setAttribute('color',    new THREE.BufferAttribute(emberColors, 3));
  var emberPoints = new THREE.Points(emberGeom, new THREE.PointsMaterial({
    size: 5.5, vertexColors: true, map: particleTexture,
    transparent: true, opacity: 0.88,
    blending: THREE.AdditiveBlending, depthWrite: false
  }));
  hologramRoot.add(emberPoints);

  // ==========================================================================
  // 5. INTERACTIVE CONTROLS
  // ==========================================================================
  var isDragging = false, prevMouseX = 0, prevMouseY = 0;
  var targetRootRotation = { x: 0, y: 0 };

  window.addEventListener('pointerdown', function(e) {
    isDragging = true; prevMouseX = e.clientX; prevMouseY = e.clientY;
  });
  window.addEventListener('pointermove', function(e) {
    if (isDragging) {
      targetRootRotation.y += (e.clientX - prevMouseX) * 0.006;
      targetRootRotation.x += (e.clientY - prevMouseY) * 0.006;
      prevMouseX = e.clientX; prevMouseY = e.clientY;
    } else {
      var nx = (e.clientX - window.innerWidth / 2)  / (window.innerWidth / 2);
      var ny = (e.clientY - window.innerHeight / 2) / (window.innerHeight / 2);
      hologramRoot.position.x += (nx * 12 - hologramRoot.position.x) * 0.05;
      hologramRoot.position.y += (-ny * 12 - hologramRoot.position.y) * 0.05;
    }
  });
  window.addEventListener('pointerup',     function() { isDragging = false; });
  window.addEventListener('pointercancel', function() { isDragging = false; });
  window.addEventListener('resize', function() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  });

  // ==========================================================================
  // 6. ANIMATION LOOP
  // ==========================================================================
  // ==========================================================================
  // 6. ANIMATION LOOP & REACTIVE CORE DYNAMICS
  // ==========================================================================
  var clock = new THREE.Clock();
  var currentStatus = "standby";

  // Real-time audio pitch/amplitude level (0.0 = silent/steady, 1.0 = peak speech pitch)
  var audioPitchLevel = 0.0;
  var smoothAudioLevel = 0.0;

  function setAudioLevel(level) {
    audioPitchLevel = Math.max(0.0, Math.min(1.0, level || 0.0));
  }

  function animate() {
    requestAnimationFrame(animate);
    var delta = clock.getDelta();
    var t     = clock.getElapsedTime();

    // Smoothly interpolate audio level (fast attack, smooth exponential decay)
    if (audioPitchLevel > smoothAudioLevel) {
      smoothAudioLevel += (audioPitchLevel - smoothAudioLevel) * 0.45;
    } else {
      smoothAudioLevel += (audioPitchLevel - smoothAudioLevel) * 0.12;
    }

    // Steady, smooth, uniform rotation speeds (no jarring speed spikes)
    var speedMult = 1.0;

    // 1. Outer Sphere Shell — steady planetary axis rotation
    outerSphereGroup.rotation.y += delta * 0.18 * speedMult;

    // 2. Inner Gyroscopic Rings — independent smooth multi-axis rotation
    coronaGroup.rotation.z += delta * 0.12 * speedMult;
    gyroRing1.rotation.y   += delta * 0.22 * speedMult;
    gyroRing1.rotation.x   += delta * 0.05 * speedMult;
    gyroRing2.rotation.z   -= delta * 0.26 * speedMult;
    gyroRing2.rotation.x   -= delta * 0.06 * speedMult;
    gyroRing3.rotation.y   += delta * 0.15 * speedMult;
    gyroRing3.rotation.z   -= delta * 0.11 * speedMult;
    ribbonMesh.rotation.z  += delta * 0.07 * speedMult;

    // 3. 3D Spherical Core Cage Rotation (smooth and steady)
    coreSphereCage.rotation.y += delta * 0.35 * speedMult;
    coreSphereCage.rotation.x += delta * 0.18 * speedMult;

    // 4. Central Core Scale — completely steady (1.0) with zero idle bouncing;
    // reacts dynamically ONLY when JARVIS speaks proportionally to audio pitch/energy
    var speechScale = 1.0 + smoothAudioLevel * 0.28;
    coreGroup.scale.set(speechScale, speechScale, speechScale);
    coreGroup.rotation.z -= delta * 0.10 * speedMult;

    // 5. Inertia damping
    hologramRoot.rotation.y += (targetRootRotation.y - hologramRoot.rotation.y) * 0.08;
    hologramRoot.rotation.x += (targetRootRotation.x - hologramRoot.rotation.x) * 0.08;
    if (!isDragging) targetRootRotation.y += delta * 0.03 * speedMult;

    // 6. Embers update
    var epos = emberGeom.attributes.position;
    for (var ei2 = 0; ei2 < EMBER_COUNT; ei2++) {
      var ev = emberVelocities[ei2];
      var ex = emberPositions[ei2 * 3], ey = emberPositions[ei2 * 3 + 1], ez = emberPositions[ei2 * 3 + 2];
      if (ex * ex + ey * ey + ez * ez > 14400 || emberLife[ei2] <= 0) {
        resetEmber(ei2);
      } else {
        emberPositions[ei2 * 3]     += ev.vx * speedMult;
        emberPositions[ei2 * 3 + 1] += ev.vy * speedMult;
        emberPositions[ei2 * 3 + 2] += ev.vz * speedMult;
        emberLife[ei2]--;
      }
    }
    epos.needsUpdate = true;

    renderer.render(scene, camera);
  }

  animate();

  // ==========================================================================
  // 7. HOLOGRAPHIC HUD CONTROLLER & EEL INTEGRATION
  // ==========================================================================

  // Live Clock & Date Telemetry (if present in DOM)
  function initClock() {
    var clockEl = document.getElementById('hud-clock');
    var dateEl  = document.getElementById('hud-date');
    if (!clockEl && !dateEl) return;

    function update() {
      var now = new Date();
      var hours = now.getHours();
      var minutes = String(now.getMinutes()).padStart(2, '0');
      var seconds = String(now.getSeconds()).padStart(2, '0');
      var ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12 || 12;
      var hoursStr = String(hours).padStart(2, '0');

      if (clockEl) {
        clockEl.textContent = hoursStr + ':' + minutes + ':' + seconds + ' ' + ampm;
      }
      if (dateEl) {
        var options = { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' };
        dateEl.textContent = now.toLocaleDateString('en-US', options).toUpperCase();
      }
    }
    update();
    setInterval(update, 1000);
  }
  initClock();

  // HUD Dialogue Updates
  function setDialogue(speaker, text) {
    var textEl = document.getElementById('dialogue-text');
    var cardEl = document.getElementById('dialogue-card');

    if (textEl) {
      textEl.textContent = text;
    }
    if (cardEl) {
      cardEl.style.transform = 'scale(1.01)';
      setTimeout(function() { cardEl.style.transform = 'scale(1.0)'; }, 180);
    }
  }

  // Assistant State Update
  function onStatusChange(status) {
    currentStatus = (status || "standby").toLowerCase();
    var statusTextEl = document.getElementById('status-text');
    var statusDotEl  = document.getElementById('status-dot');

    if (statusTextEl) {
      statusTextEl.textContent = status;
    }

    // The green dot indicates Online / Ready
    if (statusDotEl) {
      if (currentStatus.indexOf("offline") !== -1 || currentStatus.indexOf("disconnected") !== -1) {
        statusDotEl.classList.add('offline');
        statusDotEl.title = "JARVIS Offline";
      } else {
        statusDotEl.classList.remove('offline');
        statusDotEl.title = "JARVIS Online";
      }
    }
  }

  // Microphone Toggle UI
  var isMuted = false;
  var micBtn = document.getElementById('btn-mic');
  var micText = document.getElementById('mic-text');

  function updateMicUI(muted) {
    isMuted = muted;
    if (micBtn) {
      if (muted) {
        micBtn.classList.add('mic-muted');
        micBtn.classList.remove('mic-on');
        if (micText) micText.textContent = "VOICE MUTED";
      } else {
        micBtn.classList.remove('mic-muted');
        micBtn.classList.add('mic-on');
        if (micText) micText.textContent = "VOICE ACTIVE";
      }
    }
  }

  if (micBtn) {
    micBtn.addEventListener('click', function() {
      var nextState = !isMuted;
      updateMicUI(nextState);
      if (typeof eel !== "undefined" && eel.toggle_mic) {
        eel.toggle_mic(nextState)(function(res) {
          updateMicUI(res);
        });
      }
    });
  }

  // Text Command Input Submission
  var inputForm = document.getElementById('hud-input-form');
  var inputField = document.getElementById('hud-input');
  var submitBtn = document.getElementById('btn-submit');

  function submitUserQuery() {
    if (!inputField) return;
    var query = inputField.value.trim();
    if (!query) return;

    // Display query on HUD
    setDialogue("USER", query);
    inputField.value = "";

    // Send to Python backend
    if (typeof eel !== "undefined" && eel.user_text_query) {
      onStatusChange("Thinking...");
      eel.user_text_query(query)();
    }
  }

  if (inputForm) {
    inputForm.addEventListener('submit', function(e) {
      e.preventDefault();
      submitUserQuery();
    });
  }

  if (submitBtn) {
    submitBtn.addEventListener('click', function(e) {
      e.preventDefault();
      submitUserQuery();
    });
  }

  // Eel API Integration
  if (typeof eel !== "undefined") {
    console.log("[HUD] J.A.R.V.I.S. Eel bridge linked successfully.");

    // Expose functions for Python backend to call
    eel.expose(updateStatus);
    function updateStatus(status) {
      onStatusChange(status);
    }

    eel.expose(displayUserTranscript);
    function displayUserTranscript(speaker, text) {
      setDialogue(speaker || "USER", text);
    }

    eel.expose(displayAssistantResponse);
    function displayAssistantResponse(speaker, text) {
      setDialogue(speaker || "JARVIS", text);
    }

    // Expose audio pitch / energy receiver for voice speech playback
    eel.expose(updateAudioLevel);
    function updateAudioLevel(level) {
      setAudioLevel(level);
    }

    // Fetch initial state from Python
    if (eel.get_initial_state) {
      eel.get_initial_state()(function(state) {
        if (state) {
          if (typeof state.is_muted !== "undefined") updateMicUI(state.is_muted);
          if (state.status) onStatusChange(state.status);
          if (state.dialogue) setDialogue(state.dialogue.speaker, state.dialogue.text);
        }
      });
    }
  } else {
    console.log("[HUD] Running standalone preview mode (without Eel).");
  }

})();
