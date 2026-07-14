const sharp = require("sharp");
const fs = require("fs");

const W = 2000, H = 1125;
const INK = "#0B0D12";       // Perito dark bg
const ACCENT = "#F2492F";    // Perito brand (dark theme)
const NAVY = "#1A2C49";      // Perito navy (lifted for grid visibility)

function grid(step, color, opacity, width) {
  let lines = "";
  for (let x = step; x < W; x += step) lines += `<line x1="${x}" y1="0" x2="${x}" y2="${H}" stroke="${color}" stroke-opacity="${opacity}" stroke-width="${width}"/>`;
  for (let y = step; y < H; y += step) lines += `<line x1="0" y1="${y}" x2="${W}" y2="${y}" stroke="${color}" stroke-opacity="${opacity}" stroke-width="${width}"/>`;
  return lines;
}

function bgSvg({ glowX, glowY, glowR, glowOp }) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <defs>
      <radialGradient id="glow" cx="${glowX}" cy="${glowY}" r="${glowR}" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="${ACCENT}" stop-opacity="${glowOp}"/>
        <stop offset="60%" stop-color="${ACCENT}" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="vig" cx="50%" cy="42%" r="75%">
        <stop offset="55%" stop-color="#000000" stop-opacity="0"/>
        <stop offset="100%" stop-color="#000000" stop-opacity="0.55"/>
      </radialGradient>
    </defs>
    <rect width="${W}" height="${H}" fill="${INK}"/>
    <g>${grid(50, "#FFFFFF", 0.015, 1)}</g>
    <g>${grid(250, NAVY, 0.14, 1)}</g>
    <rect width="${W}" height="${H}" fill="url(#glow)"/>
    <rect width="${W}" height="${H}" fill="url(#vig)"/>
  </svg>`;
}

// Perito logo, recolored for dark backgrounds (navy -> light, red -> brand)
const LIGHT = "#E7EAEF";
const logoDark = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 236 96">
  <rect x="4"  y="30" width="26" height="7" rx="3.5" fill="${ACCENT}"/>
  <rect x="0"  y="43" width="19" height="7" rx="3.5" fill="${ACCENT}"/>
  <rect x="8"  y="56" width="26" height="7" rx="3.5" fill="${ACCENT}"/>
  <path d="M42 14h30a26 26 0 0 1 0 52H58v22H42z" fill="${LIGHT}"/>
  <rect x="50" y="66" width="8" height="20" rx="4" transform="rotate(45 54 76)" fill="${LIGHT}"/>
  <circle cx="72" cy="40" r="20" fill="#10151d"/>
  <circle cx="72" cy="40" r="20" fill="none" stroke="${LIGHT}" stroke-width="4"/>
  <path d="M63 40l7 7 12-14" fill="none" stroke="${ACCENT}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="112" y="66" font-family="'Arial',sans-serif" font-size="46" font-weight="700" fill="${LIGHT}">perito</text>
</svg>`;

(async () => {
  await sharp(Buffer.from(bgSvg({ glowX: 1750, glowY: 1000, glowR: 900, glowOp: 0.11 }))).png().toFile("img/bg-main.png");
  await sharp(Buffer.from(bgSvg({ glowX: 250, glowY: 950, glowR: 1150, glowOp: 0.18 }))).png().toFile("img/bg-hero.png");
  await sharp(Buffer.from(bgSvg({ glowX: 1000, glowY: 560, glowR: 1100, glowOp: 0.10 }))).png().toFile("img/bg-demo.png");
  await sharp(Buffer.from(logoDark)).resize(720).png().toFile("img/logo.png");
  console.log("assets regenerated (bg + logo)");
})();
