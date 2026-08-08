/**
 * GestureHome booth: browser HandConnect visuals + gesture to /command API
 */

const API = window.location.origin;
const HOLD_S = 3.0;
const FAN_HOLD_S = 2.0;
const DOOR_HOLD_S = 2.0;
const SEC_HOLD_S = 2.0;
const COOLDOWN_S = 0.5;
const WAVE_WINDOW = 24;
const WAVE_MIN_AMP = 0.07;
const WAVE_MIN_SWINGS = 3;

const LM = {
  WRIST: 0,
  THUMB_TIP: 4,
  INDEX_MCP: 5,
  INDEX_TIP: 8,
  MIDDLE_MCP: 9,
  MIDDLE_TIP: 12,
  RING_MCP: 13,
  RING_TIP: 16,
  PINKY_MCP: 17,
  PINKY_TIP: 20,
};
const FINGER_PAIRS = [
  [LM.INDEX_TIP, LM.INDEX_MCP],
  [LM.MIDDLE_TIP, LM.MIDDLE_MCP],
  [LM.RING_TIP, LM.RING_MCP],
  [LM.PINKY_TIP, LM.PINKY_MCP],
];
const FINGER_TIPS = [4, 8, 12, 16, 20];

const video = document.querySelector(".input_video");
const canvas = document.getElementById("mainCanvas");
const ctx = canvas.getContext("2d");

let width = 0;
let height = 0;
let lastCommandAt = 0;
let waveHistory = [];

const state = {
  lightsOn: false,
  fanSpeed: 0,
  doorOpen: false,
  securityArmed: false,
  fistSince: null,
  palmSince: null,
  fanSince: null,
  fanPose: null,
  doorSince: null,
  securitySince: null,
};

const ui = {
  gesture: document.getElementById("gestureLine"),
  timer: document.getElementById("timerLine"),
  usb: document.getElementById("stUsb"),
  light: document.getElementById("stLight"),
  fan: document.getElementById("stFan"),
  door: document.getElementById("stDoor"),
  sec: document.getElementById("stSec"),
  alarm: document.getElementById("stAlarm"),
};

function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function isFist(lm) {
  const wrist = lm[LM.WRIST];
  let curled = 0;
  for (const [tip, mcp] of FINGER_PAIRS) {
    if (dist(lm[tip], wrist) < dist(lm[mcp], wrist)) curled += 1;
  }
  return curled >= 4;
}

function isOpenPalm(lm) {
  const wrist = lm[LM.WRIST];
  let extended = 0;
  for (const [tip, mcp] of FINGER_PAIRS) {
    if (dist(lm[tip], wrist) > dist(lm[mcp], wrist) * 1.02) extended += 1;
  }
  const thumbOpen =
    dist(lm[LM.THUMB_TIP], wrist) > dist(lm[LM.INDEX_MCP], wrist) * 0.85;
  return extended >= 4 && thumbOpen;
}

function countExtended(lm) {
  const wrist = lm[LM.WRIST];
  let n = 0;
  for (const [tip, mcp] of FINGER_PAIRS) {
    if (dist(lm[tip], wrist) > dist(lm[mcp], wrist) * 1.02) n += 1;
  }
  return n;
}

function isThumbsUp(lm) {
  const wrist = lm[LM.WRIST];
  const thumb = lm[LM.THUMB_TIP];
  const indexMcp = lm[LM.INDEX_MCP];
  if (thumb.y >= wrist.y - 0.04) return false;
  if (thumb.y >= indexMcp.y - 0.02) return false;
  let curled = 0;
  for (const [tip, mcp] of FINGER_PAIRS) {
    if (dist(lm[tip], wrist) < dist(lm[mcp], wrist)) curled += 1;
  }
  return curled >= 3;
}

function isTenFingers(hands) {
  return hands.length >= 2 && isOpenPalm(hands[0]) && isOpenPalm(hands[1]);
}

function updateWaveHistory(lm) {
  waveHistory.push(lm[LM.WRIST].x);
  if (waveHistory.length > WAVE_WINDOW) waveHistory.shift();
}

function isWaving() {
  if (waveHistory.length < WAVE_WINDOW) return false;
  const minX = Math.min(...waveHistory);
  const maxX = Math.max(...waveHistory);
  if (maxX - minX < WAVE_MIN_AMP) return false;
  let swings = 0;
  for (let i = 2; i < waveHistory.length; i++) {
    const d1 = waveHistory[i - 1] - waveHistory[i - 2];
    const d2 = waveHistory[i] - waveHistory[i - 1];
    if (d1 * d2 < 0 && Math.abs(d1) > 0.008 && Math.abs(d2) > 0.008) swings += 1;
  }
  return swings >= WAVE_MIN_SWINGS;
}

function isSecurityGesture(hands) {
  if (isTenFingers(hands)) return true;
  if (hands.length >= 1) {
    updateWaveHistory(hands[0]);
    return isWaving();
  }
  return false;
}

function detectSinglePose(lm) {
  if (isThumbsUp(lm)) return "thumb_stop";
  const fist = isFist(lm);
  const palm = isOpenPalm(lm);
  if (fist && !palm) return "fist";
  if (palm && !fist) return "palm";
  const n = countExtended(lm);
  if (n === 1) return "fan1";
  if (n === 2) return "fan2";
  if (n === 3) return "fan3";
  return null;
}

async function sendCommand(cmd) {
  try {
    const res = await fetch(`${API}/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cmd }),
    });
    if (!res.ok) {
      const err = await res.json();
      console.warn("command failed", err);
      return false;
    }
    lastCommandAt = Date.now() / 1000;
    return true;
  } catch (e) {
    console.warn("command error", e);
    return false;
  }
}

async function pollHouse() {
  try {
    const res = await fetch(`${API}/house-status`);
    if (!res.ok) return;
    const data = await res.json();
    ui.usb.textContent = data.connected ? "OK" : "-";
    const s = data.status || {};
    if (s.lights) {
      state.lightsOn = s.lights === "ON";
      ui.light.textContent = s.lights;
    }
    if (s.fan !== undefined) {
      state.fanSpeed = s.fan;
      ui.fan.textContent = s.fan === 0 ? "OFF" : String(s.fan);
    }
    if (s.door) {
      state.doorOpen = s.door === "OPEN";
      ui.door.textContent = s.door;
    }
    if (s.security) {
      state.securityArmed = s.security === "ON";
      ui.sec.textContent = s.security;
    }
    if (s.alarm) ui.alarm.textContent = s.alarm;
  } catch (e) {
    ui.usb.textContent = "err";
  }
}

function cooledDown() {
  return Date.now() / 1000 - lastCommandAt >= COOLDOWN_S;
}

function resetHolds() {
  state.fistSince = null;
  state.palmSince = null;
  state.fanSince = null;
  state.fanPose = null;
  state.doorSince = null;
  state.securitySince = null;
}

async function processGestures(hands) {
  const now = Date.now() / 1000;
  if (hands.length < 1) {
    resetHolds();
    waveHistory = [];
    ui.gesture.textContent = "Show your hand(s) to the camera";
    ui.timer.textContent = "";
    return;
  }

  if (hands.length >= 2 && isFist(hands[0]) && isFist(hands[1])) {
    resetHolds();
    waveHistory = [];
    if (state.doorSince === null) state.doorSince = now;
    const held = now - state.doorSince;
    const next = state.doorOpen ? "CLOSE" : "OPEN";
    ui.gesture.textContent = `2 fists → door ${next}`;
    ui.timer.textContent = `${held.toFixed(1)}s / ${DOOR_HOLD_S}s`;
    if (held >= DOOR_HOLD_S && cooledDown()) {
      if (await sendCommand("DOOR_TOGGLE")) {
        state.doorOpen = !state.doorOpen;
        state.doorSince = null;
        ui.gesture.textContent = `Door ${state.doorOpen ? "OPEN" : "CLOSE"}!`;
        pollHouse();
      }
    }
    return;
  }

  if (isSecurityGesture(hands)) {
    resetHolds();
    state.doorSince = null;
    if (state.securitySince === null) state.securitySince = now;
    const held = now - state.securitySince;
    const hint = isTenFingers(hands) ? "10 fingers" : "wave";
    const next = state.securityArmed ? "OFF" : "ON";
    ui.gesture.textContent = `${hint} → security ${next}`;
    ui.timer.textContent = `${held.toFixed(1)}s / ${SEC_HOLD_S}s`;
    if (held >= SEC_HOLD_S && cooledDown()) {
      const cmd = state.securityArmed ? "SECURITY_OFF" : "SECURITY_ON";
      if (await sendCommand(cmd)) {
        state.securityArmed = !state.securityArmed;
        state.securitySince = null;
        waveHistory = [];
        ui.gesture.textContent = `Security ${state.securityArmed ? "ON" : "OFF"}!`;
        pollHouse();
      }
    }
    return;
  }

  state.doorSince = null;
  state.securitySince = null;
  waveHistory = [];

  const lm = hands[0];
  const pose = detectSinglePose(lm);

  if (pose === "fist") {
    state.palmSince = null;
    state.fanSince = null;
    state.fanPose = null;
    if (state.fistSince === null) state.fistSince = now;
    const held = now - state.fistSince;
    ui.gesture.textContent = "Fist → lights ON";
    ui.timer.textContent = `${held.toFixed(1)}s / ${HOLD_S}s`;
    if (held >= HOLD_S && cooledDown() && !state.lightsOn) {
      if (await sendCommand("LIGHTS_ON")) {
        state.lightsOn = true;
        state.fistSince = null;
        ui.gesture.textContent = "Lights ON!";
        pollHouse();
      }
    }
    return;
  }

  if (pose === "palm") {
    state.fistSince = null;
    state.fanSince = null;
    state.fanPose = null;
    if (state.palmSince === null) state.palmSince = now;
    const held = now - state.palmSince;
    ui.gesture.textContent = "Open palm → lights OFF";
    ui.timer.textContent = `${held.toFixed(1)}s / ${HOLD_S}s`;
    if (held >= HOLD_S && cooledDown() && state.lightsOn) {
      if (await sendCommand("LIGHTS_OFF")) {
        state.lightsOn = false;
        state.palmSince = null;
        ui.gesture.textContent = "Lights OFF!";
        pollHouse();
      }
    }
    return;
  }

  if (pose === "thumb_stop" || pose?.startsWith("fan")) {
    state.fistSince = null;
    state.palmSince = null;
    if (state.fanPose !== pose) {
      state.fanPose = pose;
      state.fanSince = now;
    }
    const held = now - (state.fanSince || now);
    if (pose === "thumb_stop") {
      ui.gesture.textContent = "Thumbs up → fan STOP";
      ui.timer.textContent = `${held.toFixed(1)}s / ${FAN_HOLD_S}s`;
      if (held >= FAN_HOLD_S && cooledDown() && state.fanSpeed !== 0) {
        if (await sendCommand("FAN_STOP")) {
          state.fanSpeed = 0;
          state.fanSince = null;
          state.fanPose = null;
          ui.gesture.textContent = "Fan STOP!";
          pollHouse();
        }
      }
    } else {
      const target = parseInt(pose.slice(-1), 10);
      ui.gesture.textContent = `${target} finger(s) → fan ${target}`;
      ui.timer.textContent = `${held.toFixed(1)}s / ${FAN_HOLD_S}s`;
      if (held >= FAN_HOLD_S && cooledDown() && state.fanSpeed !== target) {
        if (await sendCommand(`FAN_SPEED_${target}`)) {
          state.fanSpeed = target;
          state.fanSince = null;
          state.fanPose = null;
          ui.gesture.textContent = `Fan speed ${target}!`;
          pollHouse();
        }
      }
    }
    return;
  }

  resetHolds();
  ui.gesture.textContent = "See cheat sheet →";
  ui.timer.textContent = "";
}

function drawNeonHands(results) {
  ctx.clearRect(0, 0, width, height);
  const hands = results.multiHandLandmarks || [];
  if (!hands.length) return;

  const t = Date.now() / 1000;

  for (const lm of hands) {
    for (const [tip, mcp] of FINGER_PAIRS) {
      const a = lm[mcp];
      const b = lm[tip];
      ctx.strokeStyle = `hsl(${(t * 80 + tip * 40) % 360}, 100%, 65%)`;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(a.x * width, a.y * height);
      ctx.lineTo(b.x * width, b.y * height);
      ctx.stroke();
    }
    for (const i of FINGER_TIPS) {
      ctx.fillStyle = "#61d4c3";
      ctx.beginPath();
      ctx.arc(lm[i].x * width, lm[i].y * height, 5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  if (hands.length >= 2) {
    const h0 = hands[0];
    const h1 = hands[1];
    for (let i = 0; i < FINGER_TIPS.length; i++) {
      const a = h0[FINGER_TIPS[i]];
      const b = h1[FINGER_TIPS[i]];
      const hue = (t * 100 + i * 50) % 360;
      const grad = ctx.createLinearGradient(
        a.x * width,
        a.y * height,
        b.x * width,
        b.y * height
      );
      grad.addColorStop(0, `hsl(${hue}, 100%, 60%)`);
      grad.addColorStop(1, `hsl(${(hue + 120) % 360}, 100%, 60%)`);
      ctx.strokeStyle = grad;
      ctx.lineWidth = 4;
      ctx.shadowBlur = 12;
      ctx.shadowColor = `hsl(${hue}, 100%, 50%)`;
      ctx.beginPath();
      ctx.moveTo(a.x * width, a.y * height);
      ctx.lineTo(b.x * width, b.y * height);
      ctx.stroke();
      ctx.shadowBlur = 0;
    }
  }
}

function resize() {
  width = window.innerWidth;
  height = window.innerHeight;
  canvas.width = width;
  canvas.height = height;
}

window.addEventListener("resize", resize);
resize();

const hands = new Hands({
  locateFile: (file) =>
    `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
});
hands.setOptions({
  maxNumHands: 2,
  modelComplexity: 1,
  minDetectionConfidence: 0.6,
  minTrackingConfidence: 0.6,
});

hands.onResults((results) => {
  drawNeonHands(results);
  const landmarks = results.multiHandLandmarks || [];
  processGestures(landmarks);
});

const camera = new Camera(video, {
  onFrame: async () => {
    await hands.send({ image: video });
  },
  width: 1280,
  height: 720,
});

function cameraHelpMessage() {
  if (!window.isSecureContext) {
    return (
      "Camera on phones needs HTTPS.\n\n" +
      "Scan the projector QR again and open the https:// link.\n" +
      "On iPhone: tap Advanced → Proceed, then Start camera."
    );
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return (
      "This browser cannot access the camera here.\n\n" +
      "Use Safari with the https:// booth link from the projector QR."
    );
  }
  return "Could not start the camera. Check permissions and try again.";
}

document.getElementById("startBtn").addEventListener("click", async () => {
  if (!window.isSecureContext) {
    alert(cameraHelpMessage());
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    alert(cameraHelpMessage());
    return;
  }
  try {
    document.getElementById("startOverlay").classList.add("hidden");
    await camera.start();
    pollHouse();
    setInterval(pollHouse, 2000);
  } catch (err) {
    console.error(err);
    document.getElementById("startOverlay").classList.remove("hidden");
    alert(cameraHelpMessage());
  }
});
