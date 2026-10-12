const fs = require("node:fs"),
  path = require("node:path");
const lock = JSON.parse(fs.readFileSync("package-lock.json", "utf8"));
let out =
  "ReadingOS third-party notices\n\nElectron also ships LICENSE and LICENSES.chromium.html alongside the executable.\n\n";
for (const [key, entry] of Object.entries(lock.packages).sort()) {
  if (
    !key ||
    entry.dev ||
    entry.optional ||
    !fs.existsSync(path.join(key, "package.json"))
  )
    continue;
  const pkg = JSON.parse(
    fs.readFileSync(path.join(key, "package.json"), "utf8"),
  );
  out +=
    "\n============================================================\n" +
    pkg.name +
    " " +
    pkg.version +
    "\nLicense: " +
    (typeof pkg.license === "string"
      ? pkg.license
      : JSON.stringify(pkg.license)) +
    "\nRepository: " +
    (typeof pkg.repository === "string"
      ? pkg.repository
      : pkg.repository?.url || "") +
    "\n";
  const files = fs
    .readdirSync(key)
    .filter((n) => /^(licen[sc]e|copying|notice)(\.|$)/i.test(n));
  for (const file of files)
    if (fs.statSync(path.join(key, file)).isFile())
      out +=
        "\n" +
        file +
        "\n" +
        fs.readFileSync(path.join(key, file), "utf8") +
        "\n";
}
fs.writeFileSync("THIRD_PARTY_NOTICES.txt", out);
