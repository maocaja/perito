const sharp = require("sharp");

const W = 2000, H = 1125;
const INK = "#0E0F13";
const LIME = "#C8F250";

// Fine technical grid (blueprint feel), very subtle
function grid(step, color, opacity, width) {
  let lines = "";
  for (let x = step; x < W; x += step) lines += `<line x1="${x}" y1="0" x2="${x}" y2="${H}" stroke="${color}" stroke-opacity="${opacity}" stroke-width="${width}"/>`;
  for (let y = step; y < H; y += step) lines += `<line x1="0" y1="${y}" x2="${W}" y2="${y}" stroke="${color}" stroke-opacity="${opacity}" stroke-width="${width}"/>`;
  return lines;
}

function svg({ glowX, glowY, glowR, glowOp }) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <defs>
      <radialGradient id="glow" cx="${glowX}" cy="${glowY}" r="${glowR}" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="${LIME}" stop-opacity="${glowOp}"/>
        <stop offset="60%" stop-color="${LIME}" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="vig" cx="50%" cy="42%" r="75%">
        <stop offset="55%" stop-color="#000000" stop-opacity="0"/>
        <stop offset="100%" stop-color="#000000" stop-opacity="0.55"/>
      </radialGradient>
    </defs>
    <rect width="${W}" height="${H}" fill="${INK}"/>
    <g>${grid(50, "#FFFFFF", 0.018, 1)}</g>
    <g>${grid(250, LIME, 0.04, 1)}</g>
    <rect width="${W}" height="${H}" fill="url(#glow)"/>
    <rect width="${W}" height="${H}" fill="url(#vig)"/>
  </svg>`;
}

async function make(name, opts) {
  await sharp(Buffer.from(svg(opts))).png().toFile(`img/${name}.png`);
  console.log("wrote img/" + name + ".png");
}

(async () => {
  // Main content background: faint glow bottom-right
  await make("bg-main", { glowX: 1750, glowY: 1000, glowR: 900, glowOp: 0.10 });
  // Hero background (title/closing): stronger glow, lower-left
  await make("bg-hero", { glowX: 250, glowY: 950, glowR: 1150, glowOp: 0.16 });
  // Demo background: glow center-ish, dim
  await make("bg-demo", { glowX: 1000, glowY: 560, glowR: 1100, glowOp: 0.09 });
})();
