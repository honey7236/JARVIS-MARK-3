/* ==========================================
   J.A.R.V.I.S. HUD SYSTEM CORE SCRIPT
   ========================================== */

document.addEventListener("DOMContentLoaded", () => {
    // ------------------------------------------
    // 1. Core State & Constants
    // ------------------------------------------
    const state = {
        theme: "cyan",
        isRotating: true,
        baseRotationSpeed: 0.01,
        userSpeedMultiplier: 1.0,
        model: null,
        hologramGrid: null,
        hologramRings: [],
        lights: {}
    };

    // Theme configuration mappings
    const themeConfigs = {
        cyan: {
            colorHex: 0x00f0ff,
            ambientHex: 0x002c3a,
            pointHex: 0x00d0ff,
            gridHex: 0x00f0ff
        },
        red: {
            colorHex: 0xff2a2a,
            ambientHex: 0x3a0000,
            pointHex: 0xff3a3a,
            gridHex: 0xff2a2a
        },
        gold: {
            colorHex: 0xffaa00,
            ambientHex: 0x3a2600,
            pointHex: 0xffaa00,
            gridHex: 0xffaa00
        }
    };

    // SVG Circular meter circumference (r = 40, 2 * pi * r ≈ 251.2)
    const METER_CIRCUMFERENCE = 251.2;

    // Default camera parameters for scanner reset
    const defaultCamPos = { x: 0, y: 1.2, z: 4.2 };
    const defaultCamTarget = { x: 0, y: 0.8, z: 0 };

    // ------------------------------------------
    // 2. Initialize UI Components (Clock, HUD)
    // ------------------------------------------
    function initClock() {
        const timeEl = document.getElementById("hud-time");
        const dateEl = document.getElementById("hud-date");

        function update() {
            const now = new Date();

            // Format time: hh:mm:ss AM/PM
            let hours = now.getHours();
            const minutes = String(now.getMinutes()).padStart(2, "0");
            const seconds = String(now.getSeconds()).padStart(2, "0");
            const ampm = hours >= 12 ? "PM" : "AM";
            hours = hours % 12;
            hours = hours ? hours : 12; // 0 should be 12
            const hoursStr = String(hours).padStart(2, "0");

            if (timeEl) {
                timeEl.textContent = `${hoursStr}:${minutes}:${seconds} ${ampm}`;
            }

            // Format date: Day, DD Mon YYYY
            const options = { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' };
            if (dateEl) {
                dateEl.textContent = now.toLocaleDateString('en-US', options).toUpperCase();
            }
        }

        update();
        setInterval(update, 1000);
    }

    initClock();

    // ------------------------------------------
    // 3. Three.js Scene Setup
    // ------------------------------------------
    const container = document.getElementById("canvas-container");
    const scene = new THREE.Scene();

    // Create Camera
    const camera = new THREE.PerspectiveCamera(
        45,
        container.clientWidth / container.clientHeight,
        0.1,
        100
    );
    camera.position.set(defaultCamPos.x, defaultCamPos.y, defaultCamPos.z);

    // Create Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 2.2; // Further boosted exposure from 1.5 to 2.2
    container.appendChild(renderer.domElement);

    // Orbit Controls
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 + 0.1; // Limit panning below the ground
    controls.minDistance = 2.0;
    controls.maxDistance = 8.0;
    controls.target.set(defaultCamTarget.x, defaultCamTarget.y, defaultCamTarget.z);

    // ------------------------------------------
    // 4. Lights Setup
    // ------------------------------------------
    // Hemisphere Light - fills in dark shadows and metallic reflections evenly (boosted to 4.0)
    state.lights.hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 4.0);
    scene.add(state.lights.hemiLight);

    // Ambient light - base HUD fill glow
    state.lights.ambient = new THREE.AmbientLight(
        themeConfigs.cyan.ambientHex,
        1.5
    );
    scene.add(state.lights.ambient);

    // Directional Light 1 - primary spotlight highlights (boosted to 5.0)
    state.lights.dirLight1 = new THREE.DirectionalLight(0xffffff, 5.0);
    state.lights.dirLight1.position.set(2, 4, 5);
    scene.add(state.lights.dirLight1);

    // Directional Light 2 - secondary backing highlights (boosted to 3.0)
    state.lights.dirLight2 = new THREE.DirectionalLight(0xffffff, 3.0);
    state.lights.dirLight2.position.set(-2, 2, -3);
    scene.add(state.lights.dirLight2);

    // Glowing point light - simulating Arc Reactor core reflection
    state.lights.reactorGlow = new THREE.PointLight(
        themeConfigs.cyan.pointHex,
        4,
        5
    );
    state.lights.reactorGlow.position.set(0, 1.1, 0.5);
    scene.add(state.lights.reactorGlow);

    // ------------------------------------------
    // 5. Holographic Landing Pad (Grid & Rings)
    // ------------------------------------------
    function createHologramBase() {
        const baseGroup = new THREE.Group();
        baseGroup.position.y = -0.8;

        // 1. Grid Helper
        const size = 3.5;
        const divisions = 16;
        const gridColor = new THREE.Color(themeConfigs.cyan.gridHex);
        state.hologramGrid = new THREE.GridHelper(size, divisions, gridColor, gridColor);
        state.hologramGrid.material.transparent = true;
        state.hologramGrid.material.opacity = 0.15;
        baseGroup.add(state.hologramGrid);

        // 2. Holographic Radar Rings (Wireframe Circle/Ring)
        const ringMaterial = new THREE.MeshBasicMaterial({
            color: themeConfigs.cyan.gridHex,
            transparent: true,
            opacity: 0.4,
            side: THREE.DoubleSide,
            wireframe: true
        });

        // Outer rotating ring
        const outerRingGeo = new THREE.RingGeometry(1.2, 1.4, 30, 2);
        const outerRing = new THREE.Mesh(outerRingGeo, ringMaterial);
        outerRing.rotation.x = Math.PI / 2;
        baseGroup.add(outerRing);
        state.hologramRings.push({ mesh: outerRing, speed: -0.003 });

        // Inner rotating ring
        const innerRingGeo = new THREE.RingGeometry(0.7, 0.8, 20, 1);
        const innerRing = new THREE.Mesh(innerRingGeo, ringMaterial);
        innerRing.rotation.x = Math.PI / 2;
        baseGroup.add(innerRing);
        state.hologramRings.push({ mesh: innerRing, speed: 0.006 });

        scene.add(baseGroup);
    }
    createHologramBase();

    // ------------------------------------------
    // 6. GLTF Model Loader (Iron Man)
    // ------------------------------------------
    const loader = new THREE.GLTFLoader();

    // UI Elements for Loading Progress
    const loadingScreen = document.getElementById("loading-screen");
    const progressBarFill = document.getElementById("loader-progress-bar");
    const progressPercentage = document.getElementById("loader-percentage");

    loader.load(
        "assets/iron_man.glb",
        (gltf) => {
            // Model Load Success
            const modelScene = gltf.scene;
            state.model = modelScene;

            // Enhance metallic textures/materials
            modelScene.traverse((child) => {
                if (child.isMesh) {
                    child.material.roughness = Math.min(child.material.roughness, 0.3);
                    child.material.metalness = Math.max(child.material.metalness, 0.8);

                    // Add subtle emissive texture glows if available or map color tinting
                    if (child.name.toLowerCase().includes("eye") || child.name.toLowerCase().includes("reactor")) {
                        child.material.emissive = new THREE.Color(0xffffff);
                        child.material.emissiveIntensity = 2;
                    }
                }
            });

            // Center and scale the model automatically using bounding box
            const box = new THREE.Box3().setFromObject(modelScene);
            const size = box.getSize(new THREE.Vector3());
            const center = box.getCenter(new THREE.Vector3());

            // Normalize size (target height of ~2.2 units)
            const targetHeight = 2.2;
            const scaleFactor = targetHeight / size.y;
            modelScene.scale.set(scaleFactor, scaleFactor, scaleFactor);

            // Re-adjust position so feet stand on the holographic pad (y = -0.8)
            // Model pivot center adjustment
            modelScene.position.x = -center.x * scaleFactor;
            modelScene.position.z = -center.z * scaleFactor;
            modelScene.position.y = -0.8 - (box.min.y * scaleFactor);

            // Add model to the scene
            scene.add(modelScene);

            // Complete loading bar animation and dismiss overlay
            if (progressBarFill) progressBarFill.style.width = "100%";
            if (progressPercentage) progressPercentage.textContent = "100%";

            setTimeout(() => {
                if (loadingScreen) {
                    loadingScreen.classList.add("fade-out");
                }
            }, 600);
        },
        (xhr) => {
            // Loading Progress
            if (xhr.total > 0) {
                const percent = Math.round((xhr.loaded / xhr.total) * 100);
                if (progressBarFill) progressBarFill.style.width = `${percent}%`;
                if (progressPercentage) progressPercentage.textContent = `${percent}%`;
            }
        },
        (error) => {
            console.error("Error loading 3D model GLB:", error);
            // Dismiss loading screen anyway so the dashboard remains visible
            if (loadingScreen) loadingScreen.classList.add("fade-out");
        }
    );

    // ------------------------------------------
    // 7. Render & Animation Loop
    // ------------------------------------------
    function animate() {
        requestAnimationFrame(animate);

        // Slow rotate the Iron Man model
        if (state.model && state.isRotating) {
            state.model.rotation.y += state.baseRotationSpeed * state.userSpeedMultiplier;
        }

        // Counter-rotate the holographic radar rings for mechanical contrast
        state.hologramRings.forEach((ring) => {
            ring.mesh.rotation.z += ring.speed;
        });

        // Pulsate the point light slightly to simulate active power core
        const time = Date.now() * 0.003;
        state.lights.reactorGlow.intensity = 2.5 + Math.sin(time) * 0.5;

        // Update controls
        controls.update();

        // Render scene
        renderer.render(scene, camera);
    }
    animate();

    // Handle Window Resizing
    window.addEventListener("resize", () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });

    // ------------------------------------------
    // 8. Bottom Control Deck Bindings
    // ------------------------------------------
    const btnPlayPause = document.getElementById("btn-play-pause");
    const speedSlider = document.getElementById("rotation-speed");
    const speedDisplay = document.getElementById("speed-display");
    const btnResetCam = document.getElementById("btn-reset-cam");

    // Play/Pause toggle
    if (btnPlayPause) {
        btnPlayPause.addEventListener("click", () => {
            state.isRotating = !state.isRotating;
            if (state.isRotating) {
                btnPlayPause.textContent = "PAUSE";
                btnPlayPause.classList.add("btn-active");
            } else {
                btnPlayPause.textContent = "ROTATE";
                btnPlayPause.classList.remove("btn-active");
            }
        });
    }

    // Rotation speed slider
    if (speedSlider) {
        speedSlider.addEventListener("input", (e) => {
            const val = parseFloat(e.target.value);
            state.userSpeedMultiplier = val / 10.0;
            if (speedDisplay) {
                speedDisplay.textContent = `${state.userSpeedMultiplier.toFixed(1)}x`;
            }
        });
    }

    // Microphone Toggle System
    const btnToggleMic = document.getElementById("btn-toggle-mic");
    let isMuted = false;

    if (btnToggleMic) {
        // Fetch current mic state from python on initialization
        try {
            eel.get_mic_state()((muted) => {
                isMuted = muted;
                updateMicUI();
            });
        } catch (e) {
            console.error("Failed to fetch initial mic state:", e);
        }

        btnToggleMic.addEventListener("click", () => {
            isMuted = !isMuted;
            try {
                // Call python function to toggle mic state
                eel.toggle_mic(isMuted)((muted) => {
                    isMuted = muted;
                    updateMicUI();
                });
            } catch (e) {
                console.error("Failed to toggle mic:", e);
                // Fallback local UI update if python not initialized
                updateMicUI();
            }
        });

        function updateMicUI() {
            if (isMuted) {
                btnToggleMic.textContent = "MIC: MUTED";
                btnToggleMic.classList.remove("mic-unmuted");
                btnToggleMic.classList.add("mic-muted");
            } else {
                btnToggleMic.textContent = "MIC: ON";
                btnToggleMic.classList.remove("mic-muted");
                btnToggleMic.classList.add("mic-unmuted");
            }
        }
    }

    // Align Scanner (Reset camera view)
    if (btnResetCam) {
        btnResetCam.addEventListener("click", () => {
            // Smoothly animate camera controls back to default
            let steps = 30;
            let currentStep = 0;

            const startX = camera.position.x;
            const startY = camera.position.y;
            const startZ = camera.position.z;

            const startTarX = controls.target.x;
            const startTarY = controls.target.y;
            const startTarZ = controls.target.z;

            function lerpCamera() {
                if (currentStep >= steps) {
                    camera.position.set(defaultCamPos.x, defaultCamPos.y, defaultCamPos.z);
                    controls.target.set(defaultCamTarget.x, defaultCamTarget.y, defaultCamTarget.z);
                    return;
                }

                currentStep++;
                const t = currentStep / steps;
                // Ease-in-out curve
                const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

                camera.position.x = startX + (defaultCamPos.x - startX) * ease;
                camera.position.y = startY + (defaultCamPos.y - startY) * ease;
                camera.position.z = startZ + (defaultCamPos.z - startZ) * ease;

                controls.target.x = startTarX + (defaultCamTarget.x - startTarX) * ease;
                controls.target.y = startTarY + (defaultCamTarget.y - startTarY) * ease;
                controls.target.z = startTarZ + (defaultCamTarget.z - startTarZ) * ease;

                requestAnimationFrame(lerpCamera);
            }
            lerpCamera();
        });
    }

    // ------------------------------------------
    // 9. Theme / Energy Matrix Switching
    // ------------------------------------------
    const themeButtons = document.querySelectorAll(".theme-buttons button");

    themeButtons.forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const selectedTheme = e.target.getAttribute("data-theme");

            // 1. Update active state button in UI
            themeButtons.forEach((b) => b.classList.remove("active"));
            e.target.classList.add("active");

            // 2. Shift CSS variables class on body
            document.body.className = `theme-${selectedTheme}`;
            state.theme = selectedTheme;

            // 3. Update Three.js lighting and grid colors
            const cfg = themeConfigs[selectedTheme];
            if (cfg) {
                // Animate light colors
                state.lights.ambient.color.setHex(cfg.ambientHex);
                state.lights.reactorGlow.color.setHex(cfg.pointHex);

                // Update grid helper colors
                if (state.hologramGrid) {
                    scene.remove(state.hologramGrid.parent); // We can just reconstruct or update materials
                    createHologramBase();
                }
            }
        });
    });

    // Re-create hologram components to update color dynamically
    function createHologramBase() {
        // Clear old ones
        if (state.hologramGrid) {
            scene.remove(state.hologramGrid.parent);
        }
        state.hologramRings.forEach((r) => scene.remove(r.mesh));
        state.hologramRings = [];

        const baseGroup = new THREE.Group();
        baseGroup.position.y = -0.8;

        const cfg = themeConfigs[state.theme];
        const gridColor = new THREE.Color(cfg.gridHex);

        // Grid
        state.hologramGrid = new THREE.GridHelper(3.5, 16, gridColor, gridColor);
        state.hologramGrid.material.transparent = true;
        state.hologramGrid.material.opacity = 0.15;
        baseGroup.add(state.hologramGrid);

        // Ring Material
        const ringMaterial = new THREE.MeshBasicMaterial({
            color: cfg.gridHex,
            transparent: true,
            opacity: 0.4,
            side: THREE.DoubleSide,
            wireframe: true
        });

        // Outer ring
        const outerRingGeo = new THREE.RingGeometry(1.2, 1.4, 30, 2);
        const outerRing = new THREE.Mesh(outerRingGeo, ringMaterial);
        outerRing.rotation.x = Math.PI / 2;
        baseGroup.add(outerRing);
        state.hologramRings.push({ mesh: outerRing, speed: -0.003 });

        // Inner ring
        const innerRingGeo = new THREE.RingGeometry(0.7, 0.8, 20, 1);
        const innerRing = new THREE.Mesh(innerRingGeo, ringMaterial);
        innerRing.rotation.x = Math.PI / 2;
        baseGroup.add(innerRing);
        state.hologramRings.push({ mesh: innerRing, speed: 0.006 });

        scene.add(baseGroup);
    }

    // ------------------------------------------
    // 10. Eel Python Integration & Live Data
    // ------------------------------------------

    // Helper to update progress ring SVGs
    function updateProgressRing(elementId, textId, percentValue) {
        const ring = document.getElementById(elementId);
        const text = document.getElementById(textId);
        if (!ring) return;

        // Ensure percent is a clean integer between 0 and 100
        const percent = Math.min(Math.max(parseInt(percentValue) || 0, 0), 100);

        // Calculate stroke offset
        const offset = METER_CIRCUMFERENCE - (METER_CIRCUMFERENCE * percent / 100);
        ring.style.strokeDashoffset = offset;

        if (text) {
            text.textContent = `${percent}%`;
        }
    }

    // Fallback Mock Data in case Eel is running offline/without python connection
    function runMockStats() {
        console.log("Eel not detected. Initiating offline HUD telemetry simulation.");
        setInterval(() => {
            const cpu = Math.floor(Math.random() * 25) + 15;
            const ram = Math.floor(Math.random() * 5) + 40;
            const disk = 68;

            updateProgressRing("cpu-ring", "cpu-percent-text", cpu);
            updateProgressRing("ram-ring", "ram-percent-text", ram);
            updateProgressRing("disk-ring", "disk-percent-text", disk);

            const ramUsed = (16 * ram / 100).toFixed(1);
            document.getElementById("ram-details-text").textContent = `${ramUsed}/16.0 GB`;
            document.getElementById("disk-details-text").textContent = `312 GB Free`;
        }, 3000);

        // Mock Weather
        function fetchMockWeather() {
            const btn = document.getElementById("btn-refresh-weather");
            if (btn) btn.classList.add("refreshing");
            setTimeout(() => {
                const temps = ["24°C", "26°C", "27°C", "25°C", "28°C"];
                const descs = ["PARTLY CLOUDY", "CLEAR SKY", "OVERCAST CLOUDS", "LIGHT RAIN"];
                const humidities = ["58%", "62%", "65%", "60%"];
                const winds = ["3.8 m/s", "4.2 m/s", "5.1 m/s", "2.9 m/s"];
                
                const tempEl = document.getElementById("weather-temp");
                const descEl = document.getElementById("weather-desc");
                const cityEl = document.getElementById("weather-city");
                const humidityEl = document.getElementById("weather-humidity");
                const windEl = document.getElementById("weather-wind");

                if (tempEl) tempEl.textContent = temps[Math.floor(Math.random() * temps.length)];
                if (descEl) descEl.textContent = descs[Math.floor(Math.random() * descs.length)];
                if (cityEl) cityEl.textContent = "MALIBU";
                if (humidityEl) humidityEl.textContent = humidities[Math.floor(Math.random() * humidities.length)];
                if (windEl) windEl.textContent = winds[Math.floor(Math.random() * winds.length)];

                if (btn) btn.classList.remove("refreshing");
            }, 600);
        }

        // Mock News
        function fetchMockNews() {
            const btn = document.getElementById("btn-refresh-news");
            if (btn) btn.classList.add("refreshing");
            setTimeout(() => {
                const newsPool = [
                    "Arc Reactor output stabilized at 100%.",
                    "Satellite link established with Stark Industries Orbiters.",
                    "House Party Protocol modules running diagnostic checks...",
                    "Mark LXXXV nanotech shell integrity verified.",
                    "Friday AI assistant diagnostic report: Optimal.",
                    "Deep Space telemetry scanning sector 4-B.",
                    "Stark Tower mainframe firewall upgraded.",
                    "Nanoparticle distribution flow: 99.8% precision."
                ];
                const shuffled = newsPool.sort(() => 0.5 - Math.random());
                const selected = shuffled.slice(0, 4);
                const container = document.getElementById("news-container");
                if (container) {
                    container.innerHTML = "";
                    selected.forEach(item => {
                        const div = document.createElement("div");
                        div.className = "news-item";
                        div.textContent = item;
                        container.appendChild(div);
                    });
                }
                if (btn) btn.classList.remove("refreshing");
            }, 600);
        }

        // Initial mock load
        fetchMockWeather();
        fetchMockNews();

        // Bind refresh button click events
        const refWeatherBtn = document.getElementById("btn-refresh-weather");
        if (refWeatherBtn) {
            refWeatherBtn.addEventListener("click", fetchMockWeather);
        }
        const refNewsBtn = document.getElementById("btn-refresh-news");
        if (refNewsBtn) {
            refNewsBtn.addEventListener("click", fetchMockNews);
        }
    }

    // Check if running inside Eel environment
    if (typeof eel !== "undefined") {
        console.log("J.A.R.V.I.S. linked successfully with Python core.");

        // A. Expose updateNetwork function to python to receive push speed updates
        eel.expose(updateNetwork);
        function updateNetwork(data) {
            const netStatus = document.getElementById("net-status");
            const netPing = document.getElementById("net-ping");
            const netDownload = document.getElementById("net-download");
            const netUpload = document.getElementById("net-upload");

            if (netStatus) {
                netStatus.textContent = (data.status || "OFFLINE").toUpperCase();
                if (data.status === "Connected") {
                    netStatus.style.color = "var(--theme-color)";
                } else {
                    netStatus.style.color = "#ff3333";
                }
            }
            if (netPing) netPing.textContent = data.ping;
            if (netDownload) netDownload.textContent = data.download;
            if (netUpload) netUpload.textContent = data.upload;
        }

        // Expose updateStatus function to python to receive core state updates
        eel.expose(updateStatus);
        function updateStatus(status) {
            console.log("[Eel] J.A.R.V.I.S. Core State transition:", status);
            const statusEl = document.getElementById("sys-core-status");
            if (statusEl) {
                statusEl.textContent = status.toUpperCase();
                // Clear existing state classes
                statusEl.classList.remove("listening", "thinking", "answering", "translating", "active", "muted");
                // Add the new state class
                statusEl.classList.add(status.toLowerCase().replace("...", "").trim());
            }

            // Sync 3D Hologram characteristics with system state
            const stateKey = status.toLowerCase().replace("...", "").trim();
            if (state.lights && state.lights.reactorGlow) {
                if (stateKey === "listening") {
                    state.baseRotationSpeed = 0.025; // Speed up rotation to show attention
                    state.lights.reactorGlow.color.setHex(0x00ffaa); // Glowing cyan-green
                } else if (stateKey === "thinking" || stateKey === "translating") {
                    state.baseRotationSpeed = 0.05; // Spin rapidly to represent heavy computation
                    state.lights.reactorGlow.color.setHex(0xffaa00); // Glowing amber
                } else if (stateKey === "answering") {
                    state.baseRotationSpeed = 0.005; // Slow down during vocal reply
                    state.lights.reactorGlow.color.setHex(0xff2a2a); // Stark red warning/attention core
                } else if (stateKey === "muted") {
                    state.baseRotationSpeed = 0.002; // Very slow rotation to indicate standby
                    state.lights.reactorGlow.color.setHex(0x555555); // Glowing dim grey
                } else {
                    // Reset to active/idle state defaults
                    state.baseRotationSpeed = 0.01;
                    const currentThemeCfg = themeConfigs[state.theme] || themeConfigs.cyan;
                    state.lights.reactorGlow.color.setHex(currentThemeCfg.pointHex);
                }
            }
        }

        // B. Poll System diagnostics periodically
        async function fetchSystemDiagnostics() {
            try {
                // In Eel, calling an exposed python function returns a promise
                const stats = await eel.display_system_info_data()();
                if (stats) {
                    // Extract CPU percentage as number
                    const cpuPercent = parseInt(stats.cpu.replace("%", "")) || 0;
                    const ramPercent = parseInt(stats.ram_percent.replace("%", "")) || 0;
                    const diskPercent = parseInt(stats.disk_percent.replace("%", "")) || 0;

                    updateProgressRing("cpu-ring", "cpu-percent-text", cpuPercent);
                    updateProgressRing("ram-ring", "ram-percent-text", ramPercent);
                    updateProgressRing("disk-ring", "disk-percent-text", diskPercent);

                    const ramDetails = document.getElementById("ram-details-text");
                    const diskDetails = document.getElementById("disk-details-text");

                    if (ramDetails) ramDetails.textContent = stats.ram_details;
                    if (diskDetails) diskDetails.textContent = stats.disk_details;
                }
            } catch (err) {
                console.error("Error polling system stats from python:", err);
            }
        }

        // C. Fetch Environmental weather and global news
        async function fetchWeatherData() {
            const btn = document.getElementById("btn-refresh-weather");
            if (btn) btn.classList.add("refreshing");
            try {
                // Fetch weather
                const weatherData = await eel.display_weather_data()();
                const tempEl = document.getElementById("weather-temp");
                const descEl = document.getElementById("weather-desc");
                const cityEl = document.getElementById("weather-city");
                const humidityEl = document.getElementById("weather-humidity");
                const windEl = document.getElementById("weather-wind");

                if (weatherData && typeof weatherData === "object") {
                    if (tempEl) tempEl.textContent = weatherData.temp || "--°C";
                    if (descEl) descEl.textContent = (weatherData.description || "UNKNOWN").toUpperCase();
                    if (cityEl) cityEl.textContent = (weatherData.city || "MALIBU").toUpperCase();
                    if (humidityEl) humidityEl.textContent = weatherData.humidity || "--%";
                    if (windEl) windEl.textContent = weatherData.wind || "-- m/s";
                } else if (typeof weatherData === "string") {
                    if (descEl) descEl.textContent = weatherData.toUpperCase();
                }
            } catch (err) {
                console.error("Error fetching weather data from python:", err);
            } finally {
                setTimeout(() => {
                    if (btn) btn.classList.remove("refreshing");
                }, 600);
            }
        }

        async function fetchNewsData() {
            const btn = document.getElementById("btn-refresh-news");
            if (btn) btn.classList.add("refreshing");
            try {
                // Fetch news feeds
                const newsString = await eel.get_news_data()();
                const newsContainer = document.getElementById("news-container");
                if (newsString && newsContainer) {
                    const headlines = newsString.split("\n");
                    newsContainer.innerHTML = "";
                    headlines.forEach((line) => {
                        if (line.trim()) {
                            const item = document.createElement("div");
                            item.className = "news-item";
                            // Remove number prefixes from headlines if they exist e.g. "1. Headline"
                            item.textContent = line.replace(/^\d+\.\s+/, "");
                            newsContainer.appendChild(item);
                        }
                    });
                }
            } catch (err) {
                console.error("Error fetching news data from python:", err);
            } finally {
                setTimeout(() => {
                    if (btn) btn.classList.remove("refreshing");
                }, 600);
            }
        }

        // Start Polling loops
        fetchSystemDiagnostics();
        fetchWeatherData();
        fetchNewsData();

        setInterval(fetchSystemDiagnostics, 4000);   // Poll system info every 4 seconds

        // Bind refresh button click events
        const refWeatherBtn = document.getElementById("btn-refresh-weather");
        if (refWeatherBtn) {
            refWeatherBtn.addEventListener("click", fetchWeatherData);
        }
        const refNewsBtn = document.getElementById("btn-refresh-news");
        if (refNewsBtn) {
            refNewsBtn.addEventListener("click", fetchNewsData);
        }

    } else {
        // Fallback to simulation mode if opened directly in browser without Eel backend
        runMockStats();
    }

    // ------------------------------------------
    // 11. Custom Settings Panels, Profiles, Chat & Onboarding Flow
    // ------------------------------------------
    let currentChatLogJson = "";
    
    // UI Elements for settings and profile
    const settingsModal = document.getElementById("settings-modal");
    const onboardingScreen = document.getElementById("onboarding-screen");
    
    const btnOpenSettings = document.getElementById("btn-open-settings");
    const btnCloseSettings = document.getElementById("close-settings-modal");
    
    const profileBadge = document.getElementById("user-profile-badge");
    const profileDropdown = document.getElementById("profile-dropdown");
    const btnEditIdentity = document.getElementById("btn-edit-identity");
    
    // Modal Open/Close helpers with smooth display + opacity transition
    function showModal(modal) {
        if (!modal) return;
        modal.style.display = "flex";
        // Trigger reflow
        modal.offsetHeight;
        modal.classList.add("active");
    }
    
    function hideModal(modal) {
        if (!modal) return;
        modal.classList.remove("active");
        setTimeout(() => {
            if (!modal.classList.contains("active")) {
                modal.style.display = "none";
            }
        }, 300); // Wait for transition fade-out (300ms)
    }

    if (btnOpenSettings) {
        btnOpenSettings.addEventListener("click", () => {
            // Load both forms
            loadPersonalInfoForm();
            loadApiKeysForm();
            // Switch to default tab (Personal info)
            switchTab("tab-personal");
            showModal(settingsModal);
        });
    }
    
    if (btnCloseSettings) {
        btnCloseSettings.addEventListener("click", () => {
            hideModal(settingsModal);
        });
    }
    
    // Profile badge hover/click toggles
    if (profileBadge && profileDropdown) {
        profileBadge.addEventListener("click", (e) => {
            e.stopPropagation();
            profileDropdown.classList.toggle("active");
        });
        
        // Close dropdown when clicking outside
        document.addEventListener("click", () => {
            profileDropdown.classList.remove("active");
        });
        
        profileDropdown.addEventListener("click", (e) => {
            e.stopPropagation();
        });
    }
    
    if (btnEditIdentity) {
        btnEditIdentity.addEventListener("click", () => {
            if (profileDropdown) profileDropdown.classList.remove("active");
            loadPersonalInfoForm();
            loadApiKeysForm();
            switchTab("tab-personal");
            showModal(settingsModal);
        });
    }

    // Modal Tabs Navigation binding
    const tabButtons = document.querySelectorAll(".modal-tabs .tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    
    function switchTab(targetId) {
        tabButtons.forEach(btn => {
            if (btn.getAttribute("data-target") === targetId) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });
        
        tabContents.forEach(content => {
            if (content.id === targetId) {
                content.style.display = "block";
                content.classList.add("active");
            } else {
                content.style.display = "none";
                content.classList.remove("active");
            }
        });
    }
    
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-target");
            switchTab(target);
        });
    });

    // Dynamically manage Groq API key rows in API configuration panel
    const groqContainer = document.getElementById("groq-keys-container");
    const btnAddGroqKey = document.getElementById("btn-add-groq-key");
    
    function createGroqKeyRow(val = "") {
        const row = document.createElement("div");
        row.className = "key-input-row";
        
        const input = document.createElement("input");
        input.type = "password";
        input.className = "hud-input groq-key-input";
        input.placeholder = "Enter Groq API Key";
        input.value = val;
        
        const btnRemove = document.createElement("button");
        btnRemove.className = "btn-remove-key";
        btnRemove.textContent = "REMOVE";
        btnRemove.addEventListener("click", () => {
            row.remove();
        });
        
        row.appendChild(input);
        row.appendChild(btnRemove);
        return row;
    }
    
    if (btnAddGroqKey) {
        btnAddGroqKey.addEventListener("click", () => {
            if (groqContainer) {
                groqContainer.appendChild(createGroqKeyRow());
            }
        });
    }
    
    // Load and render API configuration keys
    async function loadApiKeysForm() {
        if (typeof eel === "undefined") return;
        try {
            const keys = await eel.get_api_keys()();
            if (groqContainer) {
                groqContainer.innerHTML = "";
                const groqKeys = keys.GroqAPIKeys || [];
                if (groqKeys.length === 0) {
                    groqContainer.appendChild(createGroqKeyRow());
                } else {
                    groqKeys.forEach(k => {
                        groqContainer.appendChild(createGroqKeyRow(k));
                    });
                }
            }
            
            const cohereInput = document.getElementById("input-cohere");
            const hfInput = document.getElementById("input-hf");
            const weatherInput = document.getElementById("input-weather");
            const gnewsInput = document.getElementById("input-gnews");
            
            if (cohereInput) cohereInput.value = keys.cohere || "";
            if (hfInput) hfInput.value = keys.HuggingFaceAPIKey || "";
            if (weatherInput) weatherInput.value = keys.OpenWeatherAPIKey || "";
            if (gnewsInput) gnewsInput.value = keys.GNewsAPIKey || "";
        } catch (err) {
            console.error("Error loading API keys:", err);
        }
    }
    
    // Save API configuration keys
    const btnSaveApi = document.getElementById("btn-save-api");
    if (btnSaveApi) {
        btnSaveApi.addEventListener("click", async () => {
            if (typeof eel === "undefined") return;
            
            // Gather Groq keys
            const groqInputs = document.querySelectorAll(".groq-key-input");
            const groqKeys = [];
            groqInputs.forEach(input => {
                const val = input.value.trim ? input.value.trim() : input.value;
                if (val) groqKeys.push(val);
            });
            
            const cohereVal = document.getElementById("input-cohere") ? document.getElementById("input-cohere").value.trim() : "";
            const hfVal = document.getElementById("input-hf") ? document.getElementById("input-hf").value.trim() : "";
            const weatherVal = document.getElementById("input-weather") ? document.getElementById("input-weather").value.trim() : "";
            const gnewsVal = document.getElementById("input-gnews") ? document.getElementById("input-gnews").value.trim() : "";
            
            const updatedKeys = {
                GroqAPIKeys: groqKeys,
                cohere: cohereVal,
                HuggingFaceAPIKey: hfVal,
                OpenWeatherAPIKey: weatherVal,
                GNewsAPIKey: gnewsVal
            };
            
            btnSaveApi.textContent = "SAVING...";
            try {
                const res = await eel.save_api_keys(updatedKeys)();
                if (res && res.success) {
                    btnSaveApi.textContent = "SAVED SUCCESS";
                    setTimeout(() => {
                        btnSaveApi.textContent = "SAVE CONFIGURATION";
                        hideModal(settingsModal);
                        updateProfileWidgets();
                    }, 800);
                } else {
                    btnSaveApi.textContent = "ERROR SAVING";
                    alert("Error saving: " + (res.error || "Unknown error"));
                    setTimeout(() => { btnSaveApi.textContent = "SAVE CONFIGURATION"; }, 1500);
                }
            } catch (err) {
                console.error("Error saving API keys:", err);
                btnSaveApi.textContent = "ERROR";
                setTimeout(() => { btnSaveApi.textContent = "SAVE CONFIGURATION"; }, 1500);
            }
        });
    }
    
    // Load and render Personal Info configuration
    async function loadPersonalInfoForm() {
        if (typeof eel === "undefined") return;
        try {
            const info = await eel.get_personal_info()();
            const usernameInput = document.getElementById("input-username");
            const assistantInput = document.getElementById("input-assistantname");
            
            if (usernameInput) usernameInput.value = info.Username || "";
            if (assistantInput) assistantInput.value = info.Assistantname || "";
        } catch (err) {
            console.error("Error loading personal info:", err);
        }
    }
    
    // Save Personal Info configuration
    const btnSavePersonal = document.getElementById("btn-save-personal");
    if (btnSavePersonal) {
        btnSavePersonal.addEventListener("click", async () => {
            if (typeof eel === "undefined") return;
            
            const usernameVal = document.getElementById("input-username") ? document.getElementById("input-username").value.trim() : "";
            const assistantVal = document.getElementById("input-assistantname") ? document.getElementById("input-assistantname").value.trim() : "";
            
            if (!usernameVal || !assistantVal) {
                alert("Username and Assistant Core name cannot be empty.");
                return;
            }
            
            const info = {
                Username: usernameVal,
                Assistantname: assistantVal
            };
            
            btnSavePersonal.textContent = "UPDATING...";
            try {
                const res = await eel.save_personal_info(info)();
                if (res && res.success) {
                    btnSavePersonal.textContent = "UPDATE SUCCESS";
                    setTimeout(() => {
                        btnSavePersonal.textContent = "UPDATE IDENTITY";
                        hideModal(settingsModal);
                        updateProfileWidgets();
                    }, 800);
                } else {
                    btnSavePersonal.textContent = "ERROR UPDATING";
                    alert("Error: " + (res.error || "Unknown error"));
                    setTimeout(() => { btnSavePersonal.textContent = "UPDATE IDENTITY"; }, 1500);
                }
            } catch (err) {
                console.error("Error updating identity info:", err);
                btnSavePersonal.textContent = "ERROR";
                setTimeout(() => { btnSavePersonal.textContent = "UPDATE IDENTITY"; }, 1500);
            }
        });
    }
    
    // Update profile badge and Secure User card dropdown
    async function updateProfileWidgets() {
        if (typeof eel === "undefined") return;
        try {
            const info = await eel.get_personal_info()();
            const keys = await eel.get_api_keys()();
            
            const profileUsername = document.getElementById("profile-username");
            const cardUsername = document.getElementById("card-username");
            const cardAssistantname = document.getElementById("card-assistantname");
            const cardKeysStatus = document.getElementById("card-keys-status");
            
            if (profileUsername) profileUsername.textContent = info.Username || "USER";
            if (cardUsername) cardUsername.textContent = info.Username || "---";
            if (cardAssistantname) cardAssistantname.textContent = info.Assistantname || "---";
            
            // Build keys text (e.g. "3 GROQ / WEATHER")
            let keyTextParts = [];
            const numGroq = (keys.GroqAPIKeys || []).length;
            if (numGroq > 0) keyTextParts.push(`${numGroq} GROQ`);
            if (keys.cohere) keyTextParts.push("COHERE");
            if (keys.HuggingFaceAPIKey) keyTextParts.push("HF");
            if (keys.OpenWeatherAPIKey) keyTextParts.push("WEATHER");
            if (keys.GNewsAPIKey) keyTextParts.push("GNEWS");
            
            if (cardKeysStatus) {
                cardKeysStatus.textContent = keyTextParts.join(" / ") || "NO KEYS MOUNTED";
            }
        } catch (err) {
            console.error("Error updating profile widgets:", err);
        }
    }
    
    // Onboarding login setup logic
    const btnInitSystem = document.getElementById("btn-initialize-system");
    if (btnInitSystem) {
        btnInitSystem.addEventListener("click", async () => {
            if (typeof eel === "undefined") {
                alert("Offline mode: Python backend not linked.");
                if (onboardingScreen) onboardingScreen.style.display = "none";
                return;
            }
            
            const obUsername = document.getElementById("ob-username") ? document.getElementById("ob-username").value.trim() : "";
            const obAssistant = document.getElementById("ob-assistantname") ? document.getElementById("ob-assistantname").value.trim() : "";
            const obGroq = document.getElementById("ob-groq-key") ? document.getElementById("ob-groq-key").value.trim() : "";
            const obCohere = document.getElementById("ob-cohere-key") ? document.getElementById("ob-cohere-key").value.trim() : "";
            const obHf = document.getElementById("ob-hf-key") ? document.getElementById("ob-hf-key").value.trim() : "";
            
            if (!obUsername || !obAssistant || !obGroq) {
                alert("Please fill in Username, Assistant name, and a primary Groq API Key.");
                return;
            }
            
            btnInitSystem.textContent = "INITIALIZING CORE...";
            try {
                // Save personal info
                const infoRes = await eel.save_personal_info({ Username: obUsername, Assistantname: obAssistant })();
                // Save api keys
                const apiRes = await eel.save_api_keys({
                    GroqAPIKeys: [obGroq],
                    cohere: obCohere,
                    HuggingFaceAPIKey: obHf,
                    OpenWeatherAPIKey: "",
                    GNewsAPIKey: ""
                })();
                
                if (infoRes && infoRes.success && apiRes && apiRes.success) {
                    btnInitSystem.textContent = "CORE PROTOCOL ONLINE";
                    setTimeout(() => {
                        if (onboardingScreen) {
                            onboardingScreen.style.transition = "opacity 1s ease";
                            onboardingScreen.style.opacity = 0;
                            setTimeout(() => {
                                onboardingScreen.style.display = "none";
                            }, 1000);
                        }
                        if (profileBadge) profileBadge.style.display = "flex";
                        updateProfileWidgets();
                        // Trigger weather and news fetches now that we have keys
                        if (typeof fetchWeatherData === "function") fetchWeatherData();
                        if (typeof fetchNewsData === "function") fetchNewsData();
                    }, 1000);
                } else {
                    btnInitSystem.textContent = "INITIALIZATION FAILED";
                    const errMsg = (!infoRes || !infoRes.success) ? (infoRes.error || "Personal info error") : (apiRes.error || "API key error");
                    alert("Initialization error: " + errMsg);
                    setTimeout(() => { btnInitSystem.textContent = "INITIALIZE CORE PROTOCOL"; }, 1500);
                }
            } catch (err) {
                console.error("Error initializing core onboarding:", err);
                btnInitSystem.textContent = "ERROR INITIALIZING";
                setTimeout(() => { btnInitSystem.textContent = "INITIALIZE CORE PROTOCOL"; }, 1500);
            }
        });
    }
    
    // Check login status at boot
    async function checkLoginStatus() {
        if (typeof eel === "undefined") {
            // Render simulation state for local browser previews
            if (profileBadge) profileBadge.style.display = "flex";
            return;
        }
        
        try {
            const res = await eel.check_login_status()();
            if (res && res.logged_in) {
                // Already logged in - bypass onboarding, show profile badge
                if (onboardingScreen) onboardingScreen.style.display = "none";
                if (profileBadge) profileBadge.style.display = "flex";
                updateProfileWidgets();
            } else {
                // Not logged in - show onboarding screen, hide profile badge
                if (onboardingScreen) onboardingScreen.style.display = "flex";
                if (profileBadge) profileBadge.style.display = "none";
            }
        } catch (err) {
            console.error("Error checking login status:", err);
            // Default show onboarding just in case
            if (onboardingScreen) onboardingScreen.style.display = "flex";
        }
    }
    
    checkLoginStatus();
    
    // Real-time Chat log polling and incremental rendering
    const chatLogContainer = document.getElementById("sidebar-chat-log");
    
    async function pollChatLog() {
        if (typeof eel === "undefined") {
            // Simulated messages in offline mode
            if (chatLogContainer && chatLogContainer.children.length === 0) {
                chatLogContainer.innerHTML = `
                    <div class="chat-bubble system-bubble">DIAGNOSTIC CHANNEL CONNECTED</div>
                    <div class="chat-bubble assistant-bubble">Greeting User. Telemetry matrices online. Ready for command.</div>
                `;
            }
            return;
        }
        
        try {
            const messages = await eel.get_chat_log()();
            const serialized = JSON.stringify(messages);
            if (serialized !== currentChatLogJson) {
                currentChatLogJson = serialized;
                renderChatLog(messages);
            }
        } catch (err) {
            console.error("Error polling chat log:", err);
        }
    }
    
    function renderChatLog(messages) {
        if (!chatLogContainer) return;
        chatLogContainer.innerHTML = "";
        
        if (!messages || messages.length === 0) {
            const systemLog = document.createElement("div");
            systemLog.className = "chat-bubble system-bubble";
            systemLog.textContent = "NO RECENT CHAT LOGS DETECTED";
            chatLogContainer.appendChild(systemLog);
            return;
        }
        
        messages.forEach(msg => {
            const bubble = document.createElement("div");
            const role = (msg.role || "").toLowerCase();
            const content = msg.content || "";
            
            if (role === "user") {
                bubble.className = "chat-bubble user-bubble";
            } else if (role === "assistant" || role === "friday" || role === "jarvis") {
                bubble.className = "chat-bubble assistant-bubble";
            } else {
                bubble.className = "chat-bubble system-bubble";
            }
            
            bubble.textContent = content;
            chatLogContainer.appendChild(bubble);
        });
        
        // Auto-scroll chat log to bottom
        chatLogContainer.scrollTop = chatLogContainer.scrollHeight;
    }
    
    // Poll chat log every 1.5 seconds
    pollChatLog();
    setInterval(pollChatLog, 1500);
});
