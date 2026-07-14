const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { FaUserCheck, FaBalanceScale, FaShieldAlt } = require("react-icons/fa");

// ---------- palette ----------
// Perito brand palette (dashboard dark theme): near-black bg, navy, red-orange accent
const INK = "0B0D12", PAPER = "E7EAEF", MUTE = "949CAA", FAINT = "5C6472";
const ACCENT = "F2492F", CARD = "161B24", BORDER = "2E3745", DIMACCENT = "B33A26";
const MUTE2 = "C4C9D0", SRC = "8A929E";
const NAVY = "1A2C49", ACCENTWEAK = "2A1512"; // navy depth / dark-red highlight fill
const SANS = "Arial", MONO = "Courier New";

// ---------- icons -> base64 png ----------
async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

(async () => {
  const ICON = {
    hitl: await icon(FaUserCheck, ACCENT),
    rules: await icon(FaBalanceScale, ACCENT),
    pii: await icon(FaShieldAlt, ACCENT),
  };

  const pres = new pptxgen();
  pres.defineLayout({ name: "W", width: 10, height: 5.625 });
  pres.layout = "W";
  const MX = 0.55, CW = 10 - 2 * MX;

  // ---------- reusable pieces ----------
  const bg = (s, which) => { s.background = { path: `img/${which}.png` }; };
  const shadow = () => ({ type: "outer", color: "000000", blur: 10, offset: 3, angle: 90, opacity: 0.35 });

  function tick(s, x = MX, y = 0.5) {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.1, h: 0.1, fill: { color: ACCENT }, line: { color: ACCENT } });
  }
  function footer(s, n) {
    s.addShape(pres.shapes.LINE, { x: MX, y: 5.16, w: CW, h: 0, line: { color: BORDER, width: 1 } });
    s.addText("PERITO", { x: MX, y: 5.2, w: 3, h: 0.3, fontFace: MONO, fontSize: 8.5, color: FAINT, charSpacing: 2, align: "left", valign: "middle" });
    s.addText("TRIAGE DE SINIESTROS · IA", { x: 3, y: 5.2, w: 4, h: 0.3, fontFace: MONO, fontSize: 8.5, color: FAINT, align: "center", valign: "middle" });
    s.addText(String(n).padStart(2, "0"), { x: 10 - MX - 1, y: 5.2, w: 1, h: 0.3, fontFace: MONO, fontSize: 8.5, color: FAINT, align: "right", valign: "middle" });
  }
  function lead(s, text, y = 0.62, size = 23, w = CW) {
    tick(s, MX, y + 0.06);
    s.addText(text, { x: MX + 0.24, y, w: w - 0.24, h: 0.95, fontFace: SANS, fontSize: size, bold: true, color: PAPER, align: "left", valign: "top", lineSpacingMultiple: 1.02 });
  }
  // rich text runs helper (highlight words in lime)
  const run = (t, o = {}) => ({ text: t, options: o });

  // ============================================================ S1 · HOOK
  {
    const s = pres.addSlide(); bg(s, "bg-hero");
    s.addImage({ path: "img/logo.png", x: MX, y: 0.46, w: 1.85, h: 0.75 });
    s.addText([
      run("Es 23 de diciembre.\n", { color: PAPER }),
      run("Entran tres avisos de siniestro por minuto.\n", { color: PAPER }),
      run("Diana ", { color: ACCENT }), run("tiene dos manos.", { color: PAPER }),
    ], { x: MX, y: 1.7, w: 8.7, h: 2.1, fontFace: SANS, fontSize: 34, bold: true, align: "left", valign: "top", lineSpacingMultiple: 1.08 });
    s.addText("Una historia sobre por qué las personas no deberían pasar el día transcribiendo datos.",
      { x: MX, y: 4.15, w: 7.6, h: 0.7, fontFace: SANS, fontSize: 14, color: MUTE, italic: true, valign: "top" });
    footer(s, 1);
  }

  // ============================================================ S2 · SCALE (stats)
  {
    const s = pres.addSlide(); bg(s, "bg-main");
    lead(s, "El problema no es Diana. Es el volumen.");
    const stats = [
      { n: "$27,6", u: "billones COP", d: "en siniestros pagados por las aseguradoras del país en 2025 (+8% vs. 2024).", src: "Fasecolda, 2025" },
      { n: "2 M+", u: "reclamaciones/año", d: "es lo que reciben las aseguradoras del país cada año.", src: "Fasecolda" },
      { n: "+20%", u: "en diciembre", d: "sube la accidentalidad vial — y otra vez en cada puente festivo.", src: "ACIS / Mintransporte" },
    ];
    const gap = 0.3, cwid = (CW - gap * 2) / 3, y = 1.9, ch = 2.6;
    stats.forEach((st, i) => {
      const x = MX + i * (cwid + gap);
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: cwid, h: ch, fill: { color: CARD }, line: { color: BORDER, width: 1 }, shadow: shadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: cwid, h: 0.06, fill: { color: ACCENT }, line: { color: ACCENT } });
      s.addText(st.n, { x: x + 0.22, y: y + 0.26, w: cwid - 0.44, h: 0.85, fontFace: SANS, fontSize: 44, bold: true, color: ACCENT, align: "left", valign: "middle" });
      s.addText(st.u, { x: x + 0.24, y: y + 1.1, w: cwid - 0.44, h: 0.3, fontFace: MONO, fontSize: 11, color: PAPER, align: "left" });
      s.addText(st.d, { x: x + 0.24, y: y + 1.44, w: cwid - 0.46, h: 0.8, fontFace: SANS, fontSize: 12.5, color: MUTE2, align: "left", valign: "top", lineSpacingMultiple: 1.05 });
      s.addText(st.src, { x: x + 0.24, y: y + ch - 0.34, w: cwid - 0.44, h: 0.28, fontFace: MONO, fontSize: 8, color: SRC, align: "left" });
    });
    footer(s, 2);
  }

  // ============================================================ S3 · SEASONALITY
  {
    const s = pres.addSlide(); bg(s, "bg-main");
    lead(s, "Y no llegan repartidos. Llegan casi todos el mismo día.");
    s.addText("Diciembre, Semana Santa, los puentes, los domingos. La siniestralidad no es una línea plana: es una montaña rusa. Cuando sube la ola, el analista se ahoga — y los tiempos de respuesta se disparan justo cuando más importan.",
      { x: MX, y: 1.75, w: 4.35, h: 2.4, fontFace: SANS, fontSize: 15, color: MUTE, align: "left", valign: "top", lineSpacingMultiple: 1.18 });
    // human-stakes stat
    s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 3.85, w: 4.35, h: 1.05, fill: { color: CARD }, line: { color: BORDER, width: 1 } });
    s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 3.85, w: 0.06, h: 1.05, fill: { color: ACCENT }, line: { color: ACCENT } });
    s.addText([run("8.266 ", { color: ACCENT, bold: true, fontSize: 22 }), run("muertes viales en 2024", { color: PAPER, fontSize: 14, bold: true })],
      { x: MX + 0.25, y: 3.98, w: 4.0, h: 0.4, fontFace: SANS, valign: "middle" });
    s.addText("+44% sobre el promedio de 5 años · ANSV",
      { x: MX + 0.25, y: 4.42, w: 4.0, h: 0.35, fontFace: MONO, fontSize: 9, color: MUTE2, valign: "middle" });
    // index chart
    const cx = MX + 4.9, cw = CW - 4.9;
    s.addText("ÍNDICE DE ACCIDENTALIDAD · MES PROM. = 100", { x: cx, y: 1.78, w: cw, h: 0.3, fontFace: MONO, fontSize: 9, color: SRC, charSpacing: 0.5 });
    s.addChart(pres.charts.BAR, [{ name: "Índice", labels: ["Mes promedio", "Diciembre"], values: [100, 120] }], {
      x: cx - 0.1, y: 2.1, w: cw + 0.1, h: 2.85, barDir: "col",
      chartColors: ["3E4652", ACCENT], chartColorsOpacity: [100, 100],
      showLegend: false, showTitle: false,
      catAxisLabelColor: PAPER, catAxisLabelFontFace: SANS, catAxisLabelFontSize: 12,
      valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
      valAxisMinVal: 0, valAxisMaxVal: 140,
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: PAPER, dataLabelFontFace: SANS, dataLabelFontSize: 13, dataLabelFontBold: true,
      barGapWidthPct: 60,
    });
    footer(s, 3);
  }

  // ============================================================ S4 · THE USER
  {
    const s = pres.addSlide(); bg(s, "bg-main");
    lead(s, "Conozcamos a Diana.");
    s.addText([
      run("Es analista de admisión en una aseguradora. Su día empieza con la bandeja llena. Un correo dice: ", { color: MUTE }),
      run("«choqué el carro, la póliza es POL-1001, creo que son unos 5 millones».", { color: PAPER, italic: true }),
      run("  Ni fechas exactas, ni placa clara, ni cifras confiables.", { color: MUTE }),
    ], { x: MX, y: 1.7, w: CW, h: 1.0, fontFace: SANS, fontSize: 15, align: "left", valign: "top", lineSpacingMultiple: 1.18 });
    // manual steps chips
    const steps = ["Transcribe los datos a mano", "Busca la póliza campo por campo", "Verifica la cobertura", "Intenta oler el fraude sin tiempo para mirar"];
    const gap = 0.22, cwid = (CW - gap * 3) / 4, y = 2.95, ch = 0.95;
    steps.forEach((t, i) => {
      const x = MX + i * (cwid + gap);
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: cwid, h: ch, fill: { color: CARD }, line: { color: BORDER, width: 1 } });
      s.addText(String(i + 1).padStart(2, "0"), { x: x + 0.16, y: y + 0.12, w: cwid - 0.3, h: 0.3, fontFace: MONO, fontSize: 11, color: ACCENT, bold: true });
      s.addText(t, { x: x + 0.16, y: y + 0.38, w: cwid - 0.32, h: 0.5, fontFace: SANS, fontSize: 11, color: PAPER, valign: "top", lineSpacingMultiple: 1.0 });
    });
    // pull quote
    s.addText([run("“Quítame la transcripción mecánica. No me quites el criterio ni el control.”", {})],
      { x: MX, y: 4.25, w: CW, h: 0.7, fontFace: SANS, fontSize: 17, italic: true, bold: true, color: ACCENT, align: "left", valign: "middle" });
    footer(s, 4);
  }

  // ============================================================ S5 · THE TURN
  {
    const s = pres.addSlide(); bg(s, "bg-hero");
    lead(s, "¿Y si el caso ya estuviera armado cuando Diana lo abre?", 0.9, 26);
    s.addText([
      run("Perito ", { color: ACCENT, bold: true }),
      run("no decide por ella. Le entrega el caso ya estructurado, con cada dato enlazado a su origen y un dictamen de cobertura ", { color: MUTE }),
      run("ya calculado", { color: PAPER, bold: true }),
      run(" — con el deducible y la cláusula citada.", { color: MUTE }),
    ], { x: MX, y: 2.25, w: 8.4, h: 1.3, fontFace: SANS, fontSize: 19, align: "left", valign: "top", lineSpacingMultiple: 1.2 });
    s.addText([run("Ella revisa. Ella firma.  ", { color: PAPER, bold: true }), run("En segundos, no en minutos.", { color: ACCENT, bold: true })],
      { x: MX, y: 3.7, w: CW, h: 0.5, fontFace: SANS, fontSize: 19, valign: "middle" });
    s.addText("→  Mejor te lo muestro.", { x: MX, y: 4.45, w: CW, h: 0.4, fontFace: MONO, fontSize: 13, color: MUTE });
    footer(s, 5);
  }

  // ============================================================ S6 · DEMO
  {
    const s = pres.addSlide(); bg(s, "bg-demo");
    s.addText("● EN VIVO", { x: MX, y: 0.55, w: 3, h: 0.35, fontFace: MONO, fontSize: 11, color: ACCENT, bold: true, charSpacing: 2 });
    s.addText("DEMO", { x: MX, y: 0.95, w: CW, h: 1.0, fontFace: SANS, fontSize: 60, bold: true, color: PAPER, charSpacing: 1 });
    // framed screen area
    s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 2.2, w: 4.5, h: 2.56, fill: { color: "101216" }, line: { color: ACCENT, width: 1.5, dashType: "dash" } });
    s.addText("▶", { x: MX, y: 3.0, w: 4.5, h: 0.7, fontFace: SANS, fontSize: 34, color: ACCENT, align: "center" });
    // cue list
    const cues = [
      ["01", "La bandeja se llena sola", "los correos de siniestro llegan a Gmail y se procesan solos."],
      ["02", "Abrimos un caso", "se ve qué hizo cada agente, con la evidencia enlazada."],
      ["03", "El dictamen", "CUBIERTO, deducible calculado y la cláusula citada."],
      ["04", "Diana revisa y firma", "en ~40 s. El humano tiene la última palabra."],
    ];
    const lx = MX + 4.9, lw = CW - 4.9; let cy = 2.36;
    cues.forEach(([n, t, d]) => {
      s.addText(n, { x: lx, y: cy, w: 0.5, h: 0.6, fontFace: MONO, fontSize: 14, color: ACCENT, bold: true, valign: "top" });
      s.addText([run(t + "  ", { color: PAPER, bold: true, fontSize: 13.5 }), run("— " + d, { color: MUTE2, fontSize: 12 })],
        { x: lx + 0.5, y: cy, w: lw - 0.5, h: 0.6, fontFace: SANS, valign: "top", lineSpacingMultiple: 1.05 });
      cy += 0.63;
    });
    footer(s, 6);
  }

  // ============================================================ S7 · UNDER THE HOOD (pipeline)
  {
    const s = pres.addSlide(); bg(s, "bg-main");
    lead(s, "Detrás, el caso pasa por una posta de agentes.");
    const nodes = [
      ["Correo", "del cliente"], ["Extrae", "Haiku"], ["Verifica", "Sonnet"], ["Póliza", "grounding"],
      ["Reglas", "R1–R5"], ["Fraude", "señales"], ["Listo", "para firmar"],
    ];
    const N = nodes.length, y = 2.55, r = 0.52;
    const first = MX + r / 2 + 0.15, last = 10 - MX - r / 2 - 0.15;
    const spanline = last - first;
    // connecting line
    s.addShape(pres.shapes.LINE, { x: first, y: y + r / 2, w: spanline, h: 0, line: { color: BORDER, width: 1.5 } });
    nodes.forEach(([t, sub], i) => {
      const cxc = first + (spanline * i) / (N - 1);
      const x = cxc - r / 2;
      const last = i === N - 1;
      s.addShape(pres.shapes.OVAL, { x, y, w: r, h: r, fill: { color: last ? ACCENT : CARD }, line: { color: last ? ACCENT : BORDER, width: 1.5 } });
      s.addText(String(i + 1), { x, y, w: r, h: r, fontFace: MONO, fontSize: 13, bold: true, color: last ? INK : ACCENT, align: "center", valign: "middle" });
      s.addText(t, { x: cxc - 0.7, y: y + r + 0.08, w: 1.4, h: 0.28, fontFace: SANS, fontSize: 11.5, bold: true, color: PAPER, align: "center" });
      s.addText(sub, { x: cxc - 0.7, y: y + r + 0.34, w: 1.4, h: 0.26, fontFace: MONO, fontSize: 8.5, color: SRC, align: "center" });
    });
    s.addText([run("Hoy: ", { color: ACCENT, bold: true }), run("lee el texto del correo y enlaza cada campo a su origen. Los PDF y las fotos se cargan y quedan adjuntos al caso — su análisis automático es el siguiente paso, no esta versión.", { color: MUTE2 })],
      { x: MX, y: 4.3, w: CW, h: 0.7, fontFace: SANS, fontSize: 13, align: "left", valign: "top", lineSpacingMultiple: 1.12 });
    footer(s, 7);
  }

  // ============================================================ S8 · NON-NEGOTIABLES
  {
    const s = pres.addSlide(); bg(s, "bg-main");
    lead(s, "Tres reglas que el sistema no puede romper.");
    const cards = [
      [ICON.hitl, "El humano firma, siempre", "Perito propone y prepara. Nunca cierra ni aprueba un caso solo: la última palabra es humana."],
      [ICON.rules, "La cobertura la deciden reglas", "Un motor determinístico dictamina y cita la cláusula. La IA solo llena los campos."],
      [ICON.pii, "Datos personales, protegidos", "Cédula, teléfono y correo se redactan antes de tocar el modelo. Habeas Data (Ley 1581)."],
    ];
    const gap = 0.3, cwid = (CW - gap * 2) / 3, y = 1.7, ch = 2.78;
    cards.forEach(([ic, t, d], i) => {
      const x = MX + i * (cwid + gap);
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: cwid, h: ch, fill: { color: CARD }, line: { color: BORDER, width: 1 }, shadow: shadow() });
      s.addImage({ data: ic, x: x + 0.28, y: y + 0.3, w: 0.48, h: 0.48 });
      s.addText(t, { x: x + 0.28, y: y + 0.95, w: cwid - 0.5, h: 0.6, fontFace: SANS, fontSize: 15, bold: true, color: PAPER, valign: "top", lineSpacingMultiple: 1.0 });
      s.addText(d, { x: x + 0.28, y: y + 1.55, w: cwid - 0.52, h: 1.1, fontFace: SANS, fontSize: 11.5, color: MUTE2, valign: "top", lineSpacingMultiple: 1.14 });
    });
    s.addText([run("Solo el 7% de las aseguradoras logra escalar IA: ", { color: PAPER, bold: true }), run("el freno es la confianza, no el modelo. (BCG 2025)", { color: MUTE })],
      { x: MX, y: 4.62, w: CW, h: 0.3, fontFace: SANS, fontSize: 11, align: "left", valign: "middle" });
    footer(s, 8);
  }

  // ============================================================ S9 · HOW BUILT WITH AI
  {
    const s = pres.addSlide(); bg(s, "bg-main");
    lead(s, "No escribí este código a mano.\nTampoco dejé que la IA lo escribiera sola.", 0.6, 22);
    const pts = [
      ["Definí el qué", "con una metodología (AI-DLC): requisitos, historias de usuario y unidades de trabajo antes de una línea de código."],
      ["Orquesté el cómo con un harness", "usé OpenSymphony para coordinar agentes: cada uno revisaba, validaba y abría su pull request en un espacio aislado. Yo aprobaba antes de integrar."],
      ["Repartí por costo", "un modelo barato extrae, uno intermedio hace el grueso, el más potente solo entra en lo ambiguo."],
    ];
    let y = 1.82;
    pts.forEach(([t, d], i) => {
      s.addText(String(i + 1).padStart(2, "0"), { x: MX, y, w: 0.6, h: 0.5, fontFace: MONO, fontSize: 16, bold: true, color: ACCENT, valign: "top" });
      s.addText([run(t + ".  ", { color: PAPER, bold: true }), run(d, { color: MUTE2 })],
        { x: MX + 0.65, y, w: 5.25, h: 1.0, fontFace: SANS, fontSize: 13, valign: "top", lineSpacingMultiple: 1.12 });
      y += 1.0;
    });
    // honest pull-quote card on the right
    const qx = MX + 6.1, qw = CW - 6.1;
    s.addShape(pres.shapes.RECTANGLE, { x: qx, y: 1.9, w: qw, h: 2.4, fill: { color: CARD }, line: { color: BORDER, width: 1 } });
    s.addShape(pres.shapes.RECTANGLE, { x: qx, y: 1.9, w: 0.06, h: 2.4, fill: { color: ACCENT }, line: { color: ACCENT } });
    s.addText("LA LECCIÓN", { x: qx + 0.28, y: 2.1, w: qw - 0.5, h: 0.3, fontFace: MONO, fontSize: 9, color: ACCENT, charSpacing: 2 });
    s.addText("“El agente decía «listo, verificado» sin verificar. La barrera real no fue escribir el código: fue revisarlo.”",
      { x: qx + 0.28, y: 2.45, w: qw - 0.55, h: 1.7, fontFace: SANS, fontSize: 14.5, italic: true, bold: true, color: PAPER, valign: "top", lineSpacingMultiple: 1.15 });
    footer(s, 9);
  }

  // ============================================================ S10 · RESULTS
  {
    const s = pres.addSlide(); bg(s, "bg-main");
    lead(s, "¿El resultado?");
    const stats = [
      ["≈ USD 0,02", "procesar 4–5 casos de punta a punta con IA real (~1 centavo por correo)."],
      ["100%", "de los dictámenes de cobertura citan la cláusula exacta que aplicaron."],
      ["≈ 40 s", "tarda el analista en revisar y firmar un caso que ya llega armado."],
      ["0", "ciclos infinitos: la terminación siempre está acotada (frameworks así se cuelgan el 33,8%)."],
    ];
    const gap = 0.28, cwid = (CW - gap) / 2, ch = 1.32, y0 = 1.72;
    stats.forEach(([n, d], i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = MX + col * (cwid + gap), y = y0 + row * (ch + 0.22);
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: cwid, h: ch, fill: { color: CARD }, line: { color: BORDER, width: 1 } });
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.06, h: ch, fill: { color: ACCENT }, line: { color: ACCENT } });
      s.addText(n, { x: x + 0.28, y: y + 0.12, w: cwid - 0.5, h: 0.55, fontFace: SANS, fontSize: 28, bold: true, color: ACCENT, valign: "middle" });
      s.addText(d, { x: x + 0.29, y: y + 0.68, w: cwid - 0.55, h: 0.58, fontFace: SANS, fontSize: 11.5, color: MUTE2, valign: "top", lineSpacingMultiple: 1.08 });
    });
    s.addText("Métricas medidas en la demo real. No prometo ahorros de tiempo que no haya validado.",
      { x: MX, y: 4.82, w: CW, h: 0.3, fontFace: MONO, fontSize: 9, color: SRC });
    footer(s, 10);
  }

  // ============================================================ S11 · COST/TIME
  {
    const s = pres.addSlide(); bg(s, "bg-main");
    lead(s, "¿Cuánto costaría construir esto en una fábrica de software?");
    const gap = 0.3, cwid = (CW - gap) / 2, y = 1.85, ch = 2.35;
    // left card - agency
    const lx = MX;
    s.addShape(pres.shapes.RECTANGLE, { x: lx, y, w: cwid, h: ch, fill: { color: CARD }, line: { color: BORDER, width: 1 } });
    s.addText("UNA FÁBRICA DE SOFTWARE (estimado)", { x: lx + 0.28, y: y + 0.25, w: cwid - 0.5, h: 0.3, fontFace: MONO, fontSize: 10, color: MUTE, charSpacing: 1 });
    s.addText("≈ USD 80.000", { x: lx + 0.28, y: y + 0.6, w: cwid - 0.5, h: 0.7, fontFace: SANS, fontSize: 34, bold: true, color: PAPER, valign: "middle" });
    s.addText("≈ $320 millones COP", { x: lx + 0.28, y: y + 1.28, w: cwid - 0.5, h: 0.3, fontFace: MONO, fontSize: 11, color: MUTE });
    s.addText([run("~4 personas", { color: PAPER }), run("  ·  3–4 meses  ·  ~2.000 horas  ·  tarifa mixta ≈ USD 40/h", { color: MUTE })],
      { x: lx + 0.28, y: y + 1.72, w: cwid - 0.5, h: 0.5, fontFace: SANS, fontSize: 12, valign: "top", lineSpacingMultiple: 1.1 });
    // right card - this
    const rx = MX + cwid + gap;
    s.addShape(pres.shapes.RECTANGLE, { x: rx, y, w: cwid, h: ch, fill: { color: ACCENTWEAK }, line: { color: ACCENT, width: 1.5 } });
    s.addText("LO QUE TOMÓ AQUÍ", { x: rx + 0.28, y: y + 0.25, w: cwid - 0.5, h: 0.3, fontFace: MONO, fontSize: 10, color: ACCENT, charSpacing: 1 });
    s.addText("120 horas", { x: rx + 0.28, y: y + 0.6, w: cwid - 0.5, h: 0.7, fontFace: SANS, fontSize: 34, bold: true, color: ACCENT, valign: "middle" });
    s.addText("20 días · 6 h/día · 1 persona + IA", { x: rx + 0.28, y: y + 1.28, w: cwid - 0.5, h: 0.3, fontFace: MONO, fontSize: 11, color: PAPER });
    s.addText([run("Costo de modelo e infraestructura: ", { color: MUTE }), run("centavos.", { color: PAPER, bold: true })],
      { x: rx + 0.28, y: y + 1.72, w: cwid - 0.5, h: 0.5, fontFace: SANS, fontSize: 12, valign: "top" });
    // punchline strip
    s.addText([run("~16× menos horas.  ", { color: ACCENT, bold: true }), run("Semanas en vez de meses.", { color: PAPER, bold: true })],
      { x: MX, y: 4.45, w: CW, h: 0.4, fontFace: SANS, fontSize: 18, align: "center", valign: "middle" });
    s.addText("Estimación ilustrativa · supuestos: alcance MVP comparable, tarifa de agencia LATAM, USD ≈ 4.000 COP.",
      { x: MX, y: 4.9, w: CW, h: 0.25, fontFace: MONO, fontSize: 8, color: FAINT, align: "center" });
    footer(s, 11);
  }

  // ============================================================ S12 · WHO I AM
  {
    const s = pres.addSlide(); bg(s, "bg-hero");
    s.addText("QUIÉN HAY DETRÁS", { x: MX, y: 0.6, w: CW, h: 0.35, fontFace: MONO, fontSize: 11, color: ACCENT, charSpacing: 3 });
    s.addText([
      run("Me obsesionan los procesos repetitivos que aburren a la gente.\n", { color: PAPER }),
      run("Busco, con tecnología, que las empresas ganen tiempo y dinero — y que las personas dejen de copiar y pegar datos para dedicarse a lo que ", { color: MUTE2 }),
      run("de verdad rinde.", { color: ACCENT }),
    ], { x: MX, y: 1.6, w: 8.6, h: 2.6, fontFace: SANS, fontSize: 25, bold: true, align: "left", valign: "top", lineSpacingMultiple: 1.18 });
    footer(s, 12);
  }

  // ============================================================ S13 · WHAT'S NEXT
  {
    const s = pres.addSlide(); bg(s, "bg-main");
    lead(s, "Lo que sigue no es un roadmap de cinco años.");
    // concrete next step
    s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 1.55, w: CW, h: 1.15, fill: { color: CARD }, line: { color: BORDER, width: 1 }, shadow: shadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 1.55, w: 0.08, h: 1.15, fill: { color: ACCENT }, line: { color: ACCENT } });
    s.addText("EL PASO CONCRETO", { x: MX + 0.35, y: 1.72, w: CW - 0.7, h: 0.28, fontFace: MONO, fontSize: 9.5, color: ACCENT, charSpacing: 2 });
    s.addText([
      run("Conectar Perito al correo real de una aseguradora y correr un ", { color: PAPER }),
      run("piloto de dos semanas", { color: ACCENT, bold: true }),
      run(": pasar de casos sintéticos a reales y medir cuánto acelera el triage.", { color: PAPER }),
    ], { x: MX + 0.35, y: 2.02, w: CW - 0.75, h: 0.6, fontFace: SANS, fontSize: 15.5, align: "left", valign: "top", lineSpacingMultiple: 1.1 });
    // where it grows
    s.addText("Y HACIA DÓNDE CRECE", { x: MX, y: 2.95, w: CW, h: 0.3, fontFace: MONO, fontSize: 9.5, color: SRC, charSpacing: 2 });
    const grow = [
      ["Métricas a la medida", "Paneles con lo que cada aseguradora necesita medir: costo por caso, % escalado, tiempos por ramo."],
      ["Inteligencia del historial", "Perito señala a quienes se siniestran de forma recurrente: insumo para suscribir y renovar mejor. Sugiere; decide el humano."],
    ];
    const gp = 0.3, gw = (CW - gp) / 2, gy = 3.24, gh = 1.66;
    grow.forEach(([t, d], i) => {
      const x = MX + i * (gw + gp);
      s.addShape(pres.shapes.RECTANGLE, { x, y: gy, w: gw, h: gh, fill: { color: CARD }, line: { color: BORDER, width: 1 } });
      s.addText(t, { x: x + 0.28, y: gy + 0.2, w: gw - 0.5, h: 0.4, fontFace: SANS, fontSize: 15, bold: true, color: PAPER });
      s.addText(d, { x: x + 0.28, y: gy + 0.62, w: gw - 0.52, h: 0.95, fontFace: SANS, fontSize: 11.5, color: MUTE2, valign: "top", lineSpacingMultiple: 1.12 });
    });
    footer(s, 13);
  }

  // ============================================================ S14 · CLOSING
  {
    const s = pres.addSlide(); bg(s, "bg-hero");
    s.addImage({ path: "img/logo.png", x: MX, y: 0.5, w: 1.85, h: 0.75 });
    s.addText([
      run("Perito no reemplaza al analista.\n", { color: PAPER }),
      run("Le devuelve el criterio.", { color: ACCENT }),
    ], { x: MX, y: 1.95, w: 9, h: 1.8, fontFace: SANS, fontSize: 38, bold: true, align: "left", valign: "top", lineSpacingMultiple: 1.1 });
    s.addShape(pres.shapes.LINE, { x: MX, y: 4.35, w: 2.2, h: 0, line: { color: ACCENT, width: 2 } });
    s.addText([run("Gracias.   ", { color: PAPER, bold: true }), run("Mauricio Cajamarca  ·  lmauriciocajamarca@gmail.com", { color: MUTE })],
      { x: MX, y: 4.55, w: CW, h: 0.4, fontFace: SANS, fontSize: 14, valign: "middle" });
    footer(s, 14);
  }

  await pres.writeFile({ fileName: "Perito-pitch.pptx" });
  console.log("wrote Perito-pitch.pptx");
})();
