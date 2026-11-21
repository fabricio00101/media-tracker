// Verifica que csvEscape() de app.js neutraliza la inyección de fórmulas CSV.
// Se ejecuta desde tests/test_frontend.py; sale con código != 0 si algo falla.
const fs = require("fs");
const path = require("path");

const appJsPath = path.join(__dirname, "..", "static", "js", "app.js");
const src = fs.readFileSync(appJsPath, "utf8");

const DECL = "const csvEscape =";
const start = src.indexOf(DECL);
if (start === -1) {
    console.error("FAIL: no se encontró csvEscape en app.js");
    process.exit(1);
}

const end = src.indexOf("\n};", start);
if (end === -1) {
    console.error("FAIL: no se pudo delimitar el cuerpo de csvEscape");
    process.exit(1);
}

const declaration = src.slice(start, end + 3).replace(/;\s*$/, "");
const csvEscape = eval(declaration.slice(DECL.length).trim());

if (typeof csvEscape !== "function") {
    console.error("FAIL: csvEscape no es una función");
    process.exit(1);
}

const casos = [
    { valor: "=cmd|'/C calc'!A1", prefijo: true },
    { valor: "+cmd|'/C calc'!A1", prefijo: true },
    { valor: "-1+1", prefijo: true },
    { valor: "@SUM(A1:A9)", prefijo: true },
    { valor: "titulo normal", prefijo: false },
    { valor: 'un "comilla" doble', prefijo: false },
];

let failed = 0;
for (const caso of casos) {
    const out = csvEscape(caso.valor);
    const problemas = [];

    if (!out.startsWith('"') || !out.endsWith('"')) {
        problemas.push("falta el entrecomillado CSV");
    }
    if (caso.prefijo && !out.startsWith('"\'')) {
        problemas.push("fórmula sin neutralizar");
    }
    if (!caso.prefijo && out.startsWith('"\'')) {
        problemas.push("valor normal prefijado por error");
    }
    if (caso.valor.includes('"') && !out.includes('""')) {
        problemas.push("comillas sin duplicar");
    }

    if (problemas.length) {
        failed += 1;
        console.log(`FAIL ${JSON.stringify(caso.valor)} -> ${out}: ${problemas.join(", ")}`);
    } else {
        console.log(`OK   ${JSON.stringify(caso.valor)} -> ${out}`);
    }
}

process.exit(failed ? 1 : 0);
