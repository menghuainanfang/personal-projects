const fs = require("node:fs");
const path = require("node:path");
for (const name of ["cmaps", "standard_fonts", "wasm"])
  fs.cpSync(
    path.join("node_modules/pdfjs-dist", name),
    path.join("dist/pdf", name),
    { recursive: true },
  );
