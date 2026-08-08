const API = window.location.origin;

const ui = {
  phoneUrl: document.getElementById("phoneUrl"),
  usbBadge: document.getElementById("usbBadge"),
  usb: document.getElementById("stUsb"),
  light: document.getElementById("stLight"),
  fan: document.getElementById("stFan"),
  door: document.getElementById("stDoor"),
  sec: document.getElementById("stSec"),
  alarm: document.getElementById("stAlarm"),
  driverLink: document.getElementById("driverLink"),
};

let qrRendered = false;

async function loadBoothInfo() {
  const res = await fetch(`${API}/booth-info`);
  if (!res.ok) throw new Error("booth-info failed");
  return res.json();
}

function renderQr(url) {
  const el = document.getElementById("qrcode");
  el.innerHTML = "";
  if (typeof QRCode === "undefined") {
    el.textContent = "QR library missing";
    return;
  }
  new QRCode(el, {
    text: url,
    width: 280,
    height: 280,
    colorDark: "#000000",
    colorLight: "#ffffff",
    correctLevel: QRCode.CorrectLevel.M,
  });
  qrRendered = true;
}

async function init() {
  try {
    const info = await loadBoothInfo();
    const phoneUrl = info.phone_url || `${API}/booth.html`;
    ui.phoneUrl.textContent = phoneUrl;
    ui.driverLink.href = info.booth_url || "/booth.html";
    if (!qrRendered) renderQr(phoneUrl);

    if (info.serial_connected) {
      ui.usbBadge.textContent = `USB connected (${info.port || "serial"})`;
      ui.usbBadge.className = "badge ok";
    } else {
      ui.usbBadge.textContent = "USB not connected (preview only)";
      ui.usbBadge.className = "badge warn";
    }
  } catch (err) {
    ui.phoneUrl.textContent = "Could not reach booth bridge";
    ui.usbBadge.textContent = "Bridge offline";
    ui.usbBadge.className = "badge warn";
    console.error(err);
  }
}

async function pollStatus() {
  try {
    const health = await fetch(`${API}/health`).then((r) => r.json());
    ui.usb.textContent = health.serial_connected ? "OK" : "OFF";

    const house = await fetch(`${API}/house-status`).then((r) => r.json());
    const st = house.status || {};
    ui.light.textContent = st.lights || "-";
    ui.fan.textContent = st.fan !== undefined ? String(st.fan) : "-";
    ui.door.textContent = st.door || "-";
    ui.sec.textContent = st.security || "-";
    ui.alarm.textContent = st.alarm || "-";
  } catch {
    ui.usb.textContent = "ERR";
  }
}

init();
setInterval(pollStatus, 2000);
pollStatus();
