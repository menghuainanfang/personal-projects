const { PDFDocument, StandardFonts, rgb } = require("pdf-lib");
const JSZip = require("jszip");
const fs = require("node:fs");
const path = require("node:path");
async function fixtures(root) {
  fs.mkdirSync(root, { recursive: true });
  const pdf = await PDFDocument.create();
  pdf.setTitle("The Art of Slow Reading");
  pdf.setAuthor("ReadingOS");
  const font = await pdf.embedFont(StandardFonts.TimesRoman);
  for (let i = 1; i <= 3; i++) {
    const pg = pdf.addPage([595, 842]);
    pg.drawText("The Art of Slow Reading", {
      x: 65,
      y: 740,
      size: 28,
      font,
      color: rgb(0.23, 0.35, 0.26),
    });
    pg.drawText("Chapter " + i + " - Read, reflect, practice", {
      x: 65,
      y: 680,
      size: 17,
      font,
    });
    for (let n = 0; n < 15; n++)
      pg.drawText("Reading invites us to pause and make an idea our own.", {
        x: 65,
        y: 635 - n * 26,
        size: 14,
        font,
      });
    pg.drawText("Original test document. CC0. Page " + i, {
      x: 65,
      y: 55,
      size: 10,
      font,
    });
  }
  fs.writeFileSync(path.join(root, "sample.pdf"), await pdf.save());
  const zip = new JSZip();
  zip.file("mimetype", "application/epub+zip", { compression: "STORE" });
  zip.file(
    "META-INF/container.xml",
    '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
  );
  zip.file(
    "OEBPS/content.opf",
    '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">readingos-original-test</dc:identifier><dc:title>A Small Book of Reflection</dc:title><dc:creator>ReadingOS</dc:creator><dc:language>en</dc:language><meta property="dcterms:modified">2026-10-11T00:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="c1" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/></spine></package>',
  );
  zip.file(
    "OEBPS/nav.xhtml",
    '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head><body><nav epub:type="toc"><h1>Contents</h1><ol><li><a href="chapter.xhtml">A moment to reflect</a></li></ol></nav></body></html>',
  );
  zip.file(
    "OEBPS/chapter.xhtml",
    '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>A moment to reflect</title></head><body><h1>A moment to reflect</h1>' +
      Array.from(
        { length: 25 },
        (_, n) =>
          "<p>Paragraph " +
          n +
          ". Reading invites us to pause and make an idea our own. We read slowly, reflect honestly, and practice a little each day.</p>",
      ).join("") +
      "</body></html>",
  );
  fs.writeFileSync(
    path.join(root, "sample.epub"),
    await zip.generateAsync({ type: "nodebuffer" }),
  );
  fs.writeFileSync(path.join(root, "malformed.pdf"), "not a pdf");
  zip.remove("OEBPS/chapter.xhtml");
  fs.writeFileSync(
    path.join(root, "malformed.epub"),
    await zip.generateAsync({ type: "nodebuffer" }),
  );
  return root;
}
module.exports = { fixtures };
if (require.main === module) fixtures(path.resolve("test-results/fixtures"));
