// Verifica que el escapeHtml() de app.js neutraliza payloads XSS.
// Se ejecuta desde tests/test_frontend.py; sale con código != 0 si algo falla.
const fs = require("fs");
const path = require("path");

const appJsPath = path.join(__dirname, "..", "static", "js", "app.js");
const src = fs.readFileSync(appJsPath, "utf8");

// Extrae la declaración real de escapeHtml desde app.js
const DECL = "const escapeHtml =";
const start = src.indexOf(DECL);
if (start === -1) {
    console.error("FAIL: no se encontró escapeHtml en app.js");
    process.exit(1);
}

const marker = "&#39;\");";
const end = src.indexOf(marker, start);
if (end === -1) {
    console.error("FAIL: no se pudo delimitar el cuerpo de escapeHtml");
    process.exit(1);
}

const declaration = src.slice(start, end + marker.length).replace(/;\s*$/, "");
const escapeHtml = eval(declaration.slice(DECL.length).trim());

if (typeof escapeHtml !== "function") {
    console.error("FAIL: escapeHtml no es una función");
    process.exit(1);
}

const payloads = [
    '"><img src=x onerror=alert(1)>',
    "<script>alert(document.cookie)</script>",
    "'; alert(1); //",
    'x" onmouseover="alert(1)',
    "a & b",
    "it's",
    "O'Neil & Sons <b>bold</b>",
];

let failed = 0;

for (const payload of payloads) {
    const out = escapeHtml(payload);
    const problemas = [];

    if (out.includes("<")) problemas.push("< sin escapar");
    if (out.includes(">")) problemas.push("> sin escapar");
    if (out.includes('"')) problemas.push('" sin escapar');
    if (out.includes("'")) problemas.push("' sin escapar");

    // El & debe escaparse primero: si quedara suelto, las entidades generadas
    // a continuación no podrían distinguirse de las del contenido original.
    if (payload.includes("&") && !out.includes("&amp;")) {
        problemas.push("& sin escapar");
    }

    if (problemas.length) {
        failed += 1;
        console.log(
            `FAIL ${JSON.stringify(payload)} -> ${JSON.stringify(out)}: ${problemas.join(", ")}`
        );
    } else {
        console.log(`OK   ${JSON.stringify(payload)} -> ${JSON.stringify(out)}`);
    }
}

// Verificación inversa: lo que produce escapeHtml debe ser HTML inocuo
const roundTrip = escapeHtml('<img src=x onerror="alert(1)">');
const entidades = ["&lt;", "&gt;", "&quot;"];
for (const e of entidades) {
    if (!roundTrip.includes(e)) {
        failed += 1;
        console.log(`FAIL: falta la entidad ${e} en ${JSON.stringify(roundTrip)}`);
    }
}

process.exit(failed ? 1 : 0);
