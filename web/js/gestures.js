/**
 * GestureHome Phase 1 - browser script
 * Watches your hands via webcam and asks the Python bridge to turn the LED on/off.
 */

// Import MediaPipe hand-tracking tools from the internet (CDN)
import {
  FilesetResolver,   // Loads MediaPipe WASM runtime files
  HandLandmarker,    // AI model that finds hands in video
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";

// Map of MediaPipe hand point indices we care about
const LM = {
  WRIST: 0,       // Point 0 = wrist (where hand meets arm)
  INDEX_TIP: 8,   // Point 8 = index fingertip (reserved for later phases)
};

// Pairs of point indices - used to draw green skeleton lines on hands
const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],           // thumb bones
  [0, 5], [5, 6], [6, 7], [7, 8],           // index finger bones
  [5, 9], [9, 10], [10, 11], [11, 12],     // middle finger bones
  [9, 13], [13, 14], [14, 15], [15, 16],   // ring finger bones
  [13, 17], [17, 18], [18, 19], [19, 20],  // pinky bones
  [0, 17],                                  // wrist to pinky side
];

const LOAD_TIMEOUT_MS = 20000;  // Max wait (ms) for MediaPipe to download
const COOLDOWN_MS = 1500;       // Min gap (ms) between commands to bridge
const STABLE_FRAMES = 4;        // Frames to hold gesture before sending
const HANDS_UP_Y = 0.42;        // Wrist Y below this = hands "up" (0=top, 1=bottom)
const HANDS_DOWN_Y = 0.58;      // Wrist Y above this = hands "down"

// URL of Python bridge - use page origin if http, else fallback localhost:8090
const BRIDGE_BASE =
  window.location.protocol.startsWith("http")
    ? window.location.origin
    : "http://127.0.0.1:8090";

const videoEl = document.getElementById("webcam");           // Hidden <video> for camera
const canvas = document.getElementById("sceneCanvas");       // Visible canvas you see
const ctx = canvas.getContext("2d");                         // 2D drawing pen for canvas

const statusDot = document.getElementById("statusDot");      // Header coloured dot
const statusText = document.getElementById("statusText");    // Header status words
const loadingOverlay = document.getElementById("loadingOverlay"); // Full-screen loader
const loaderText = document.getElementById("loaderText");    // Loader message
const loaderRetry = document.getElementById("loaderRetry");  // Retry button
const errorBanner = document.getElementById("errorBanner");  // Red error bar
const ledIcon = document.getElementById("ledIcon");          // Fake LED circle
const ledState = document.getElementById("ledState");        // "On" / "Off" label
const bridgeLine = document.getElementById("bridgeLine");    // USB/bridge status
const btnOn = document.getElementById("btnOn");              // Manual lights on
const btnOff = document.getElementById("btnOff");            // Manual lights off

let handLandmarker = null;   // MediaPipe AI; null until download finishes
let lightsOn = false;        // Our memory: is light supposed to be on?
let lastCommandAt = 0;       // Timestamp of last POST to bridge (cooldown)
let stableUp = 0;            // Count of consecutive "hands up" frames
let stableDown = 0;          // Count of consecutive "hands down" frames

function setLedUi(on) {
  lightsOn = on;                              // Save state in memory
  ledIcon.classList.toggle("on", on);         // CSS yellow glow when on
  ledState.textContent = on ? "On" : "Off";   // Update label text
}

function withTimeout(promise, ms, message) {
  let timer;                                  // Holds setTimeout id
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(message)), ms); // Fail after ms
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer)); // Race + cleanup
}

async function initWebcam() {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" }, // Ask for 720p front cam
    audio: false,                               // No microphone
  });
  videoEl.srcObject = stream;                   // Connect stream to <video>
  await new Promise((resolve) => {
    videoEl.onloadedmetadata = () => {
      videoEl.play();                           // Play once dimensions known
      resolve();                                // Continue boot()
    };
  });
  canvas.width = videoEl.videoWidth;            // Canvas pixels match video width
  canvas.height = videoEl.videoHeight;          // Canvas pixels match video height
  fitCanvasToStage();                           // Size canvas on screen
}

function fitCanvasToStage() {
  const stage = document.getElementById("stage");     // Black camera box
  const vw = stage.clientWidth;                       // Stage width in CSS pixels
  const vh = stage.clientHeight;                      // Stage height in CSS pixels
  const aspect = canvas.width / canvas.height;        // Video aspect ratio
  const containerAspect = vw / vh;                    // Stage aspect ratio
  let cssW, cssH;                                     // Display size we'll apply
  if (containerAspect > aspect) {                     // Stage wider than video
    cssW = vw;                                        // Use full width
    cssH = vw / aspect;                               // Height from ratio
  } else {                                            // Stage taller than video
    cssH = vh;                                        // Use full height
    cssW = vh * aspect;                               // Width from ratio
  }
  canvas.style.width = `${cssW}px`;                   // Apply display width
  canvas.style.height = `${cssH}px`;                  // Apply display height
}

window.addEventListener("resize", fitCanvasToStage);  // Refit on window resize

async function initHandLandmarker() {
  const vision = await withTimeout(
    FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm" // WASM runtime URL
    ),
    LOAD_TIMEOUT_MS,
    "Timed out loading MediaPipe WASM."
  );

  const opts = {
    baseOptions: {
      modelAssetPath:
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task", // ~10MB model
      delegate: "GPU",                                // Try GPU first (faster)
    },
    runningMode: "video",                           // Live video mode (not single photo)
    numHands: 2,                                    // Track up to 2 hands
    minHandDetectionConfidence: 0.6,              // 60% to detect new hand
    minHandPresenceConfidence: 0.6,               // 60% to believe hand still there
    minTrackingConfidence: 0.6,                   // 60% to keep tracking
  };

  try {
    return await withTimeout(
      HandLandmarker.createFromOptions(vision, opts), // Build landmarker with GPU
      LOAD_TIMEOUT_MS,
      "Timed out loading hand model (GPU)."
    );
  } catch {
    opts.baseOptions.delegate = "CPU";              // GPU failed - use CPU
    return await withTimeout(
      HandLandmarker.createFromOptions(vision, opts), // Build landmarker with CPU
      LOAD_TIMEOUT_MS,
      "Timed out loading hand model (CPU)."
    );
  }
}

function mirrorX(lm) {
  return { x: 1 - lm.x, y: lm.y };                  // Flip X for mirror view
}

function drawVideoFrame() {
  ctx.save();                                       // Save canvas transform state
  ctx.scale(-1, 1);                                 // Flip horizontally
  ctx.drawImage(videoEl, -canvas.width, 0, canvas.width, canvas.height); // Draw mirrored frame
  ctx.restore();                                    // Undo flip transform
}

function drawHandSkeleton(landmarks) {
  const pts = landmarks.map((lm) => {               // Each landmark → pixel coords
    const m = mirrorX(lm);                          // Mirror point
    return { x: m.x * canvas.width, y: m.y * canvas.height }; // 0–1 → pixels
  });

  ctx.strokeStyle = "rgba(61, 214, 195, 0.85)";    // Teal skeleton lines
  ctx.lineWidth = 2;
  for (const [a, b] of HAND_CONNECTIONS) {          // Each bone pair
    ctx.beginPath();
    ctx.moveTo(pts[a].x, pts[a].y);                 // Start at point a
    ctx.lineTo(pts[b].x, pts[b].y);                 // Line to point b
    ctx.stroke();                                   // Draw line
  }

  ctx.fillStyle = "#3dd6c3";                        // Teal joint dots
  for (const p of pts) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);           // Small circle at joint
    ctx.fill();
  }
}

function averageWristY(landmarksList) {
  let sum = 0;                                      // Running total of wrist Y
  for (const lm of landmarksList) {
    sum += lm[LM.WRIST].y;                          // Add wrist Y for each hand
  }
  return sum / landmarksList.length;                // Average height of both wrists
}

async function sendCommand(cmd) {
  const now = performance.now();                    // Current time in ms
  if (now - lastCommandAt < COOLDOWN_MS) return;    // Skip if cooldown active

  try {
    const res = await fetch(`${BRIDGE_BASE}/command`, {
      method: "POST",                               // Send data to bridge
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cmd }),                // e.g. {"cmd":"LIGHTS_ON"}
    });
    const data = await res.json();                  // Parse JSON response
    if (!res.ok || data.ok === false) {             // HTTP or logical error
      const msg = data.error || data.detail || `HTTP ${res.status}`;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    lastCommandAt = now;                            // Start cooldown timer
    stableUp = 0;                                   // Reset gesture counters
    stableDown = 0;
    if (cmd === "LIGHTS_ON") setLedUi(true);        // Update on-screen LED
    if (cmd === "LIGHTS_OFF") setLedUi(false);
    statusText.textContent = `Sent ${cmd}`;         // Show success message
  } catch (err) {
    statusText.textContent = `Bridge error: ${err.message}`; // Show fetch error
  }
}

function processGestures(landmarksList) {
  if (landmarksList.length < 2) {                   // Need both hands
    stableUp = 0;
    stableDown = 0;
    statusDot.className = "brand-dot live";         // Green dot
    statusText.textContent = "Show both hands";
    return;                                         // Stop this frame
  }

  const avgY = averageWristY(landmarksList);        // How high are hands?
  const cooledDown = performance.now() - lastCommandAt >= COOLDOWN_MS; // Cooldown over?

  if (avgY < HANDS_UP_Y) {                          // Hands are UP
    stableDown = 0;
    stableUp += 1;                                  // Count stable up frames
    statusDot.className = "brand-dot armed";        // Orange dot
    statusText.textContent =
      stableUp >= STABLE_FRAMES && cooledDown
        ? "Lights on!"
        : `Hands up (${stableUp}/${STABLE_FRAMES})`;
    if (stableUp >= STABLE_FRAMES && cooledDown && !lightsOn) {
      sendCommand("LIGHTS_ON");                     // Tell bridge to turn on
    }
  } else if (avgY > HANDS_DOWN_Y) {                 // Hands are DOWN
    stableUp = 0;
    stableDown += 1;                                // Count stable down frames
    statusDot.className = "brand-dot armed";
    statusText.textContent =
      stableDown >= STABLE_FRAMES && cooledDown
        ? "Lights off!"
        : `Hands down (${stableDown}/${STABLE_FRAMES})`;
    if (stableDown >= STABLE_FRAMES && cooledDown && lightsOn) {
      sendCommand("LIGHTS_OFF");                    // Tell bridge to turn off
    }
  } else {                                          // Middle zone - neutral
    stableUp = 0;
    stableDown = 0;
    statusDot.className = "brand-dot live";
    statusText.textContent = "Neutral - raise or lower both hands";
  }
}

async function pollBridgeHealth() {
  try {
    const res = await fetch(`${BRIDGE_BASE}/health`); // GET bridge status
    const data = await res.json();
    if (data.serial_connected) {                    // USB open?
      bridgeLine.textContent = `Serial OK (${data.port || "connected"})`;
      bridgeLine.style.color = "var(--accent)";     // Teal text
    } else {
      bridgeLine.textContent = "Bridge up, serial not connected";
      bridgeLine.style.color = "var(--warn)";       // Orange text
    }
    if (data.last_command === "LIGHTS_ON") setLedUi(true);  // Sync UI from bridge
    if (data.last_command === "LIGHTS_OFF") setLedUi(false);
  } catch {
    bridgeLine.textContent = `Cannot reach bridge at ${BRIDGE_BASE}`;
    bridgeLine.style.color = "var(--danger)";       // Red text
  }
}

function renderLoop() {
  if (videoEl.readyState >= 2 && handLandmarker) {  // Video ready + AI loaded
    drawVideoFrame();                               // Paint camera frame
    const result = handLandmarker.detectForVideo(videoEl, performance.now()); // Find hands
    const hands = result.landmarks || [];           // List of hands (or empty)
    for (const lm of hands) {
      drawHandSkeleton(lm);                         // Draw each hand skeleton
    }
    processGestures(hands);                         // Check up/down rules
  }
  requestAnimationFrame(renderLoop);                // Call self again next frame
}

function showError(message) {
  errorBanner.textContent = message;                // Set error text
  errorBanner.classList.remove("hidden");           // Show red banner
}

async function boot() {
  loaderRetry?.addEventListener("click", () => window.location.reload()); // Retry = reload page
  btnOn.addEventListener("click", () => sendCommand("LIGHTS_ON"));        // Button → ON
  btnOff.addEventListener("click", () => sendCommand("LIGHTS_OFF"));      // Button → OFF

  try {
    await initWebcam();                             // Step 1: camera
    handLandmarker = await initHandLandmarker();    // Step 2: hand AI
    loadingOverlay.classList.add("hidden");         // Hide loading screen
    statusText.textContent = "Raise both hands to turn lights on";
    pollBridgeHealth();                             // Check bridge once
    setInterval(pollBridgeHealth, 5000);            // Check bridge every 5s
    requestAnimationFrame(renderLoop);              // Start animation loop
  } catch (err) {
    loaderText.textContent = err.message || String(err);  // Show error on loader
    loaderText.style.color = "#e0533d";                   // Red text
    loaderRetry?.classList.remove("hidden");              // Show retry button
    showError(err.message || String(err));                // Show error banner
  }
}

boot();  // Start the app when script loads
