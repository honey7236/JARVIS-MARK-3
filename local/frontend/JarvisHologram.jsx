import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

/**
 * JarvisHologram React Component
 * 3D Holographic Cybernetic Sphere & Gyroscopic Circular Fusion Core powered by Three.js.
 * Ultra-high fidelity, locked 60-120 FPS performance with independent multi-axis rotations.
 */
export default function JarvisHologram({ className = '', style = {} }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 3000);
    camera.position.set(0, 0, 480);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.toneMapping = THREE.LinearToneMapping;
    container.appendChild(renderer.domElement);

    // UNIFIED ELECTRIC AMBER-ORANGE PALETTE
    const PALETTE = {
      coreWhite:   0xffffff,
      hotGold:     0xfff0aa,
      amberBright: 0xffa600,
      amberMid:    0xff8000,
      amberDeep:   0xee5500,
      amberGlow:   0xd84500,
      amberFaint:  0x993000
    };

    function createParticleTexture() {
      const c = document.createElement('canvas');
      c.width = 64; c.height = 64;
      const ctx = c.getContext('2d');
      const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 30);
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
      const c = document.createElement('canvas');
      c.width = size; c.height = size;
      const ctx = c.getContext('2d');
      const half = size / 2;
      const g = ctx.createRadialGradient(half, half, 0, half, half, half * 0.96);
      stops.forEach(([pos, col]) => g.addColorStop(pos, col));
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(half, half, half * 0.96, 0, Math.PI * 2); ctx.fill();
      return new THREE.CanvasTexture(c);
    }

    const particleTexture = createParticleTexture();

    const coreHotTexture = createGlowTexture(256, [
      [0.00, 'rgba(255,255,255,1.0)'],
      [0.10, 'rgba(255,245,160,0.98)'],
      [0.28, 'rgba(255,165,25,0.85)'],
      [0.55, 'rgba(240,95,5,0.45)'],
      [1.00, 'rgba(0,0,0,0)']
    ]);

    const coreMidTexture = createGlowTexture(256, [
      [0.00, 'rgba(255,195,45,0.90)'],
      [0.35, 'rgba(255,120,10,0.55)'],
      [0.70, 'rgba(215,65,0,0.22)'],
      [1.00, 'rgba(0,0,0,0)']
    ]);

    const coreAmbientTexture = createGlowTexture(256, [
      [0.00, 'rgba(255,140,20,0.50)'],
      [0.45, 'rgba(225,80,5,0.22)'],
      [0.80, 'rgba(160,40,0,0.08)'],
      [1.00, 'rgba(0,0,0,0)']
    ]);

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
    const rng = sfc32(0x9E3779B9, 0x243F6A88, 0xB7E15162, 2026);

    function sphericalToVec3(radius, phi, theta) {
      const sinPhi = Math.sin(phi);
      return new THREE.Vector3(
        radius * sinPhi * Math.cos(theta),
        radius * Math.cos(phi),
        radius * sinPhi * Math.sin(theta)
      );
    }

    function createRingLine(radius, colorHex, opacity, segments = 180) {
      const geom = new THREE.BufferGeometry();
      const pts = [];
      for (let i = 0; i <= segments; i++) {
        const a = (i / segments) * Math.PI * 2;
        pts.push(Math.cos(a) * radius, Math.sin(a) * radius, 0);
      }
      geom.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
      return new THREE.Line(geom, new THREE.LineBasicMaterial({
        color: colorHex, transparent: true, opacity, blending: THREE.AdditiveBlending
      }));
    }

    function createBroadRingBand(innerR, outerR, colorHex, opacity, segments = 120) {
      const geom = new THREE.RingGeometry(innerR, outerR, segments);
      const mat = new THREE.MeshBasicMaterial({
        color: colorHex, transparent: true, opacity, side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending, depthWrite: false
      });
      return new THREE.Mesh(geom, mat);
    }

    const hologramRoot = new THREE.Group();
    scene.add(hologramRoot);

    // 1. OUTER SPHERE SHELL (Decreased size: 138)
    const outerSphereGroup = new THREE.Group();
    hologramRoot.add(outerSphereGroup);
    const SPHERE_RADIUS = 138;

    outerSphereGroup.add(new THREE.Mesh(
      new THREE.SphereGeometry(SPHERE_RADIUS, 54, 54),
      new THREE.MeshBasicMaterial({ color: PALETTE.amberGlow, transparent: true, opacity: 0.05, side: THREE.BackSide, blending: THREE.AdditiveBlending })
    ));

    outerSphereGroup.add(createRingLine(SPHERE_RADIUS, PALETTE.amberBright, 0.70));
    outerSphereGroup.add(createRingLine(SPHERE_RADIUS + 2, PALETTE.hotGold, 0.95));
    outerSphereGroup.add(createRingLine(SPHERE_RADIUS + 4, PALETTE.amberMid, 0.45));

    const circuitLinePositions = [];

    // 28 hubs
    for (let h = 0; h < 28; h++) {
      const hubPhi = 0.20 + rng() * (Math.PI - 0.40);
      const hubTheta = rng() * Math.PI * 2;
      const branches = 7 + Math.floor(rng() * 7);
      for (let b = 0; b < branches; b++) {
        let curPhi = hubPhi, curTheta = hubTheta;
        const steps = 4 + Math.floor(rng() * 5);
        for (let s = 0; s < steps; s++) {
          const p1 = sphericalToVec3(SPHERE_RADIUS, curPhi, curTheta);
          if (s % 2 === 0) curTheta += (rng() - 0.5) * 0.30;
          else curPhi = Math.max(0.10, Math.min(Math.PI - 0.10, curPhi + (rng() - 0.5) * 0.25));
          const p2 = sphericalToVec3(SPHERE_RADIUS, curPhi, curTheta);
          circuitLinePositions.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);
        }
      }
    }

    // 40 lightning traces
    for (let z = 0; z < 40; z++) {
      let zphi = 0.25 + rng() * (Math.PI - 0.50);
      let ztheta = rng() * Math.PI * 2;
      for (let zs = 0; zs < 5 + Math.floor(rng() * 6); zs++) {
        const zp1 = sphericalToVec3(SPHERE_RADIUS, zphi, ztheta);
        zphi = Math.max(0.10, Math.min(Math.PI - 0.10, zphi + (rng() - 0.5) * 0.22));
        ztheta += (rng() - 0.5) * 0.22;
        const zp2 = sphericalToVec3(SPHERE_RADIUS, zphi, ztheta);
        circuitLinePositions.push(zp1.x, zp1.y, zp1.z, zp2.x, zp2.y, zp2.z);
      }
    }

    // Latitude arcs
    [-0.80, -0.65, -0.50, -0.35, -0.20, -0.07, 0.07, 0.20, 0.35, 0.50, 0.65, 0.80].forEach((latFrac) => {
      const latPhi = Math.PI / 2 + latFrac * (Math.PI / 2.2);
      for (let ls = 0; ls < 5 + Math.floor(rng() * 6); ls++) {
        const startTheta = rng() * Math.PI * 2;
        const arcSpan = 0.35 + rng() * 0.85;
        for (let li = 0; li < 30; li++) {
          const lt1 = startTheta + (li / 30) * arcSpan;
          const lt2 = startTheta + ((li + 1) / 30) * arcSpan;
          const la1 = sphericalToVec3(SPHERE_RADIUS, latPhi, lt1);
          const la2 = sphericalToVec3(SPHERE_RADIUS, latPhi, lt2);
          circuitLinePositions.push(la1.x, la1.y, la1.z, la2.x, la2.y, la2.z);
        }
      }
    });

    // Continuous latitude circles
    [0.20, 0.38, 0.58, 0.72, 0.88].forEach((lrFrac) => {
      [-1, 1].forEach((lrSign) => {
        const lrPhi = Math.PI / 2 + lrSign * lrFrac * (Math.PI / 2.4);
        for (let lri = 0; lri < 90; lri++) {
          const lrt1 = (lri / 90) * Math.PI * 2;
          const lrt2 = ((lri + 1) / 90) * Math.PI * 2;
          const lrp1 = sphericalToVec3(SPHERE_RADIUS, lrPhi, lrt1);
          const lrp2 = sphericalToVec3(SPHERE_RADIUS, lrPhi, lrt2);
          circuitLinePositions.push(lrp1.x, lrp1.y, lrp1.z, lrp2.x, lrp2.y, lrp2.z);
        }
      });
    });

    // Longitude meridians
    for (let m = 0; m < 24; m++) {
      const mTheta = (m / 24) * Math.PI * 2 + (rng() - 0.5) * 0.10;
      const mStartPhi = 0.25 + rng() * 0.35;
      const mPhiSpan = 0.55 + rng() * 1.40;
      for (let mi = 0; mi < 32; mi++) {
        const mp1 = sphericalToVec3(SPHERE_RADIUS, mStartPhi + (mi / 32) * mPhiSpan, mTheta);
        const mp2 = sphericalToVec3(SPHERE_RADIUS, mStartPhi + ((mi + 1) / 32) * mPhiSpan, mTheta);
        circuitLinePositions.push(mp1.x, mp1.y, mp1.z, mp2.x, mp2.y, mp2.z);
      }
    }

    // 70 micro chips
    for (let cp = 0; cp < 70; cp++) {
      const cPhi = 0.25 + rng() * (Math.PI - 0.50);
      const cTheta = rng() * Math.PI * 2;
      const dPhi = 0.035 + rng() * 0.055;
      const dTheta = 0.04 + rng() * 0.075;
      const cc1 = sphericalToVec3(SPHERE_RADIUS, cPhi, cTheta);
      const cc2 = sphericalToVec3(SPHERE_RADIUS, cPhi + dPhi, cTheta);
      const cc3 = sphericalToVec3(SPHERE_RADIUS, cPhi + dPhi, cTheta + dTheta);
      const cc4 = sphericalToVec3(SPHERE_RADIUS, cPhi, cTheta + dTheta);
      circuitLinePositions.push(cc1.x, cc1.y, cc1.z, cc2.x, cc2.y, cc2.z);
      circuitLinePositions.push(cc2.x, cc2.y, cc2.z, cc3.x, cc3.y, cc3.z);
      circuitLinePositions.push(cc3.x, cc3.y, cc3.z, cc4.x, cc4.y, cc4.z);
      circuitLinePositions.push(cc4.x, cc4.y, cc4.z, cc1.x, cc1.y, cc1.z);
    }

    const circuitGeom = new THREE.BufferGeometry();
    circuitGeom.setAttribute('position', new THREE.Float32BufferAttribute(circuitLinePositions, 3));
    outerSphereGroup.add(new THREE.LineSegments(circuitGeom, new THREE.LineBasicMaterial({
      color: PALETTE.amberBright, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending
    })));

    // 1400 Surface Nodes
    const nodePositions = [];
    const nodeColors = [];
    const colorBright = new THREE.Color(PALETTE.hotGold);
    const colorMid = new THREE.Color(PALETTE.amberBright);
    const colorDeep = new THREE.Color(PALETTE.amberMid);
    for (let ni = 0; ni < 1400; ni++) {
      const nphi = Math.acos(2 * rng() - 1);
      const ntheta = rng() * Math.PI * 2;
      const nv = sphericalToVec3(SPHERE_RADIUS + (rng() - 0.5) * 3.5, nphi, ntheta);
      nodePositions.push(nv.x, nv.y, nv.z);
      const npick = rng();
      const nc = npick > 0.65 ? colorBright : npick > 0.30 ? colorMid : colorDeep;
      nodeColors.push(nc.r, nc.g, nc.b);
    }
    const nodeGeom = new THREE.BufferGeometry();
    nodeGeom.setAttribute('position', new THREE.Float32BufferAttribute(nodePositions, 3));
    nodeGeom.setAttribute('color', new THREE.Float32BufferAttribute(nodeColors, 3));
    const nodeMat = new THREE.PointsMaterial({
      size: 7.5, vertexColors: true, map: particleTexture,
      transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false
    });
    outerSphereGroup.add(new THREE.Points(nodeGeom, nodeMat));

    // 100 BROAD RADIAL SPIKES
    const pinPositions = [], pinTipPositions = [], pinTipColors = [];
    const pinCount = 100;
    const spikeWidth = 0.010;

    for (let pi = 0; pi < pinCount; pi++) {
      const pang = rng() * Math.PI * 2;
      const pr1 = SPHERE_RADIUS - 2;
      const spikeLen = 14 + rng() * 26;
      const pr2 = SPHERE_RADIUS + spikeLen;
      const ppz = (rng() - 0.5) * 35;

      const cosL = Math.cos(pang - spikeWidth), sinL = Math.sin(pang - spikeWidth);
      const cosR = Math.cos(pang + spikeWidth), sinR = Math.sin(pang + spikeWidth);
      const cosM = Math.cos(pang), sinM = Math.sin(pang);

      pinPositions.push(cosL * pr1, sinL * pr1, ppz, cosL * pr2, sinL * pr2, ppz);
      pinPositions.push(cosR * pr1, sinR * pr1, ppz, cosR * pr2, sinR * pr2, ppz);
      pinPositions.push(cosM * pr1, sinM * pr1, ppz, cosM * pr2, sinM * pr2, ppz);
      pinPositions.push(cosL * pr2, sinL * pr2, ppz, cosR * pr2, sinR * pr2, ppz);

      pinTipPositions.push(cosM * pr2, sinM * pr2, ppz);
      pinTipColors.push(colorBright.r, colorBright.g, colorBright.b);
    }
    const pinGeom = new THREE.BufferGeometry();
    pinGeom.setAttribute('position', new THREE.Float32BufferAttribute(pinPositions, 3));
    outerSphereGroup.add(new THREE.LineSegments(pinGeom, new THREE.LineBasicMaterial({
      color: PALETTE.amberBright, transparent: true, opacity: 0.88, blending: THREE.AdditiveBlending
    })));
    const pinTipGeom = new THREE.BufferGeometry();
    pinTipGeom.setAttribute('position', new THREE.Float32BufferAttribute(pinTipPositions, 3));
    pinTipGeom.setAttribute('color', new THREE.Float32BufferAttribute(pinTipColors, 3));
    outerSphereGroup.add(new THREE.Points(pinTipGeom, new THREE.PointsMaterial({
      size: 9.5, vertexColors: true, map: particleTexture,
      transparent: true, opacity: 1.0, blending: THREE.AdditiveBlending, depthWrite: false
    })));

    outerSphereGroup.rotation.x = 0.38;
    outerSphereGroup.rotation.z = -0.15;

    // 2. INNER GYROSCOPIC RINGS — BROADER BANDS
    const innerGyroGroup = new THREE.Group();
    hologramRoot.add(innerGyroGroup);

    const coronaGroup = new THREE.Group();
    innerGyroGroup.add(coronaGroup);
    const CORONA_R = 104;

    coronaGroup.add(createBroadRingBand(CORONA_R - 9, CORONA_R + 9, PALETTE.amberGlow, 0.20, 140));
    coronaGroup.add(createBroadRingBand(CORONA_R - 4, CORONA_R + 4, PALETTE.amberMid, 0.28, 140));

    coronaGroup.add(createRingLine(CORONA_R - 10, PALETTE.amberGlow, 0.45));
    coronaGroup.add(createRingLine(CORONA_R - 6, PALETTE.amberDeep, 0.72));
    coronaGroup.add(createRingLine(CORONA_R - 3, PALETTE.amberMid, 0.85));
    coronaGroup.add(createRingLine(CORONA_R, PALETTE.hotGold, 1.00));
    coronaGroup.add(createRingLine(CORONA_R + 3, PALETTE.amberBright, 0.90));
    coronaGroup.add(createRingLine(CORONA_R + 6, PALETTE.amberMid, 0.75));
    coronaGroup.add(createRingLine(CORONA_R + 10, PALETTE.amberGlow, 0.45));

    // Corona teeth (360)
    const teethPositions = [];
    for (let ti = 0; ti < 360; ti++) {
      const ta = (ti / 360) * Math.PI * 2;
      const tLen = ti % 8 === 0 ? 10.0 : 5.5;
      teethPositions.push(
        Math.cos(ta) * (CORONA_R - tLen), Math.sin(ta) * (CORONA_R - tLen), 0,
        Math.cos(ta) * (CORONA_R + tLen), Math.sin(ta) * (CORONA_R + tLen), 0
      );
    }
    const teethGeom = new THREE.BufferGeometry();
    teethGeom.setAttribute('position', new THREE.Float32BufferAttribute(teethPositions, 3));
    coronaGroup.add(new THREE.LineSegments(teethGeom, new THREE.LineBasicMaterial({
      color: PALETTE.amberMid, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending
    })));

    // Gyro Rings 1, 2, 3 (Broad Bands)
    const gyroRing1 = new THREE.Group();
    innerGyroGroup.add(gyroRing1);
    gyroRing1.rotation.x = 0.55; gyroRing1.rotation.y = -0.35;
    gyroRing1.add(createBroadRingBand(74, 84, PALETTE.amberGlow, 0.18, 120));
    gyroRing1.add(createRingLine(74, PALETTE.amberDeep, 0.55));
    gyroRing1.add(createRingLine(77, PALETTE.amberMid, 0.72));
    gyroRing1.add(createRingLine(81, PALETTE.amberBright, 0.92));
    gyroRing1.add(createRingLine(85, PALETTE.hotGold, 0.85));

    const gyroRing2 = new THREE.Group();
    innerGyroGroup.add(gyroRing2);
    gyroRing2.rotation.x = -0.45; gyroRing2.rotation.z = 0.65;
    gyroRing2.add(createBroadRingBand(55, 65, PALETTE.amberGlow, 0.20, 100));
    gyroRing2.add(createRingLine(55, PALETTE.amberDeep, 0.60));
    gyroRing2.add(createRingLine(58, PALETTE.amberMid, 0.80));
    gyroRing2.add(createRingLine(62, PALETTE.amberBright, 0.95));
    gyroRing2.add(createRingLine(65, PALETTE.hotGold, 0.90));

    const gyroRing3 = new THREE.Group();
    innerGyroGroup.add(gyroRing3);
    gyroRing3.rotation.x = 0.25; gyroRing3.rotation.z = -0.80;
    gyroRing3.add(createBroadRingBand(44, 52, PALETTE.amberGlow, 0.18, 90));
    gyroRing3.add(createRingLine(44, PALETTE.amberDeep, 0.65));
    gyroRing3.add(createRingLine(48, PALETTE.amberBright, 0.88));
    gyroRing3.add(createRingLine(52, PALETTE.hotGold, 0.82));

    // 3. CENTRAL FUSION CORE — 3D CIRCULAR SPHERICAL CORE
    const coreGroup = new THREE.Group();
    hologramRoot.add(coreGroup);

    const coreSphereCage = new THREE.Group();
    coreGroup.add(coreSphereCage);

    const CORE_SPHERE_R = 36;
    const coreSphereWireGeom = new THREE.WireframeGeometry(new THREE.SphereGeometry(CORE_SPHERE_R, 18, 12));
    coreSphereCage.add(new THREE.LineSegments(coreSphereWireGeom, new THREE.LineBasicMaterial({
      color: PALETTE.amberBright, transparent: true, opacity: 0.70, blending: THREE.AdditiveBlending
    })));

    function create3DCircularRing(radius, rotX, rotY, rotZ, colorHex, opacity) {
      const g = new THREE.BufferGeometry();
      const pts = [];
      for (let i = 0; i <= 120; i++) {
        const a = (i / 120) * Math.PI * 2;
        pts.push(Math.cos(a) * radius, Math.sin(a) * radius, 0);
      }
      g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
      const l = new THREE.Line(g, new THREE.LineBasicMaterial({
        color: colorHex, transparent: true, opacity, blending: THREE.AdditiveBlending
      }));
      l.rotation.set(rotX, rotY, rotZ);
      return l;
    }

    coreSphereCage.add(create3DCircularRing(CORE_SPHERE_R + 1, Math.PI / 2, 0, 0, PALETTE.hotGold, 0.95));
    coreSphereCage.add(create3DCircularRing(CORE_SPHERE_R + 1, 0, Math.PI / 2, 0, PALETTE.amberBright, 0.90));
    coreSphereCage.add(create3DCircularRing(CORE_SPHERE_R + 1, Math.PI / 4, Math.PI / 4, 0, PALETTE.amberMid, 0.75));
    coreSphereCage.add(create3DCircularRing(CORE_SPHERE_R + 1, -Math.PI / 4, Math.PI / 4, 0, PALETTE.amberMid, 0.75));

    // Circular Vernier Ticks (r=42)
    const coreVernierPositions = [];
    for (let cvi = 0; cvi < 64; cvi++) {
      const cva = (cvi / 64) * Math.PI * 2;
      const cvLen = cvi % 8 === 0 ? 4.5 : 2.5;
      coreVernierPositions.push(
        Math.cos(cva) * (42 - cvLen), Math.sin(cva) * (42 - cvLen), 0,
        Math.cos(cva) * (42 + cvLen), Math.sin(cva) * (42 + cvLen), 0
      );
    }
    const coreVernierGeom = new THREE.BufferGeometry();
    coreVernierGeom.setAttribute('position', new THREE.Float32BufferAttribute(coreVernierPositions, 3));
    coreGroup.add(new THREE.LineSegments(coreVernierGeom, new THREE.LineBasicMaterial({
      color: PALETTE.hotGold, transparent: true, opacity: 0.88, blending: THREE.AdditiveBlending
    })));

    // Concentric Circular Rings
    coreGroup.add(createRingLine(4, PALETTE.coreWhite, 1.00));
    coreGroup.add(createRingLine(9, PALETTE.hotGold, 0.95));
    coreGroup.add(createRingLine(16, PALETTE.hotGold, 0.90));
    coreGroup.add(createRingLine(24, PALETTE.amberBright, 0.85));
    coreGroup.add(createRingLine(32, PALETTE.amberMid, 0.70));
    coreGroup.add(createRingLine(42, PALETTE.hotGold, 0.92));
    coreGroup.add(createRingLine(48, PALETTE.amberDeep, 0.50));

    // Volumetric multi-layer glow sprites
    function makeGlowSprite(texture, colorHex, scale, opacity) {
      const mat = new THREE.SpriteMaterial({
        map: texture, color: colorHex, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false
      });
      const sprite = new THREE.Sprite(mat);
      sprite.scale.set(scale, scale, 1);
      return sprite;
    }

    coreGroup.add(makeGlowSprite(coreHotTexture, PALETTE.coreWhite, 55, 1.00));
    coreGroup.add(makeGlowSprite(coreHotTexture, PALETTE.hotGold, 110, 0.88));
    coreGroup.add(makeGlowSprite(coreMidTexture, PALETTE.amberBright, 180, 0.70));
    coreGroup.add(makeGlowSprite(coreMidTexture, PALETTE.amberDeep, 270, 0.45));
    coreGroup.add(makeGlowSprite(coreAmbientTexture, PALETTE.amberGlow, 380, 0.28));
    coreGroup.add(makeGlowSprite(coreAmbientTexture, 0x4a1800, 520, 0.20));

    // 4. FLOATING EMBER PARTICLES
    const EMBER_COUNT = 320;
    const emberPositions = new Float32Array(EMBER_COUNT * 3);
    const emberVelocities = [];
    const emberColors = new Float32Array(EMBER_COUNT * 3);
    const emberLife = new Float32Array(EMBER_COUNT);

    function resetEmber(i) {
      const ephi = Math.acos(2 * rng() - 1);
      const etheta = rng() * Math.PI * 2;
      const espeed = 0.3 + rng() * 1.2;
      emberVelocities[i] = {
        vx: Math.sin(ephi) * Math.cos(etheta) * espeed,
        vy: Math.cos(ephi) * espeed,
        vz: Math.sin(ephi) * Math.sin(etheta) * espeed
      };
      emberPositions[i * 3] = (rng() - 0.5) * 20;
      emberPositions[i * 3 + 1] = (rng() - 0.5) * 20;
      emberPositions[i * 3 + 2] = (rng() - 0.5) * 20;
      emberLife[i] = rng() * 200;
      const et = rng();
      const ec = et > 0.6 ? colorBright : et > 0.25 ? colorMid : colorDeep;
      emberColors[i * 3] = ec.r;
      emberColors[i * 3 + 1] = ec.g;
      emberColors[i * 3 + 2] = ec.b;
    }

    for (let ei = 0; ei < EMBER_COUNT; ei++) resetEmber(ei);

    const emberGeom = new THREE.BufferGeometry();
    emberGeom.setAttribute('position', new THREE.BufferAttribute(emberPositions, 3));
    emberGeom.setAttribute('color', new THREE.BufferAttribute(emberColors, 3));
    const emberPoints = new THREE.Points(emberGeom, new THREE.PointsMaterial({
      size: 5.5, vertexColors: true, map: particleTexture, transparent: true, opacity: 0.88, blending: THREE.AdditiveBlending, depthWrite: false
    }));
    hologramRoot.add(emberPoints);

    // 5. ANIMATION & CONTROLS
    let animId = null;
    const clock = new THREE.Clock();
    let isDragging = false;
    let prevMouseX = 0, prevMouseY = 0;
    const targetRootRotation = { x: 0, y: 0 };

    const onPointerDown = (e) => { isDragging = true; prevMouseX = e.clientX; prevMouseY = e.clientY; };
    const onPointerMove = (e) => {
      if (isDragging) {
        targetRootRotation.y += (e.clientX - prevMouseX) * 0.006;
        targetRootRotation.x += (e.clientY - prevMouseY) * 0.006;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
      }
    };
    const onPointerUp = () => { isDragging = false; };

    window.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    };
    window.addEventListener('resize', onResize);

    function animate() {
      animId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const t = clock.getElapsedTime();

      outerSphereGroup.rotation.y += delta * 0.22;
      coronaGroup.rotation.z += delta * 0.14;
      gyroRing1.rotation.y += delta * 0.28;
      gyroRing1.rotation.x += delta * 0.06;
      gyroRing2.rotation.z -= delta * 0.32;
      gyroRing2.rotation.x -= delta * 0.08;
      gyroRing3.rotation.y += delta * 0.18;
      gyroRing3.rotation.z -= delta * 0.14;

      coreSphereCage.rotation.y += delta * 0.45;
      coreSphereCage.rotation.x += delta * 0.22;

      const pulse = 1 + Math.sin(t * 3.5) * 0.07 + Math.sin(t * 11.3) * 0.02;
      coreGroup.scale.set(pulse, pulse, pulse);
      coreGroup.rotation.z -= delta * 0.12;

      hologramRoot.rotation.y += (targetRootRotation.y - hologramRoot.rotation.y) * 0.08;
      hologramRoot.rotation.x += (targetRootRotation.x - hologramRoot.rotation.x) * 0.08;
      if (!isDragging) targetRootRotation.y += delta * 0.04;

      const epos = emberGeom.attributes.position;
      for (let ei2 = 0; ei2 < EMBER_COUNT; ei2++) {
        const ev = emberVelocities[ei2];
        const ex = emberPositions[ei2 * 3], ey = emberPositions[ei2 * 3 + 1], ez = emberPositions[ei2 * 3 + 2];
        if (ex * ex + ey * ey + ez * ez > 14400 || emberLife[ei2] <= 0) {
          resetEmber(ei2);
        } else {
          emberPositions[ei2 * 3] += ev.vx;
          emberPositions[ei2 * 3 + 1] += ev.vy;
          emberPositions[ei2 * 3 + 2] += ev.vz;
          emberLife[ei2]--;
        }
      }
      epos.needsUpdate = true;

      renderer.render(scene, camera);
    }
    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('resize', onResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      className={className}
      style={{
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        background: '#000000',
        position: 'relative',
        ...style
      }}
    >
      <div ref={containerRef} style={{ width: '100%', height: '100%', cursor: 'grab' }} />
    </div>
  );
}
