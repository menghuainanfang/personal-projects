import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve, extname } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const input = JSON.parse(readFileSync(0, "utf8"));
const require = createRequire(resolve(process.argv[2], "package.json"));
const { unified } = await import(pathToFileURL(require.resolve("unified")));
const { default: remarkParse } = await import(pathToFileURL(require.resolve("remark-parse")));
const { default: remarkMath } = await import(pathToFileURL(require.resolve("remark-math")));
const { default: remarkGfm } = await import(pathToFileURL(require.resolve("remark-gfm")));

// Leave code spans and fenced examples unchanged when normalizing TeX delimiters.
let markdown = input.markdown.replace(/```[^]*?```|~~~[^]*?~~~|`[^`\n]*`|\\\[([^]*?)\\\]|\\\(([^]*?)\\\)/gu,
  (match, display, inline) => display !== undefined ? `\n$$\n${display.trim()}\n$$\n`
    : inline !== undefined ? `$${inline}$` : match);
const tree = unified().use(remarkParse).use(remarkGfm).use(remarkMath).parse(markdown);
const replacements = [];
const assets = [];
const referencedImages = new Set();
let title = input.title || "";
const plainText = (node) => node.value ?? node.children?.map(plainText).join("") ?? "";
const first = tree.children[0];
if (first?.type === "heading" && first.depth === 1) {
  if (!title) title = plainText(first);
  replacements.push({ start: first.position.start.offset, end: first.position.end.offset, value: "" });
}
function walk(node, visitor) {
  visitor(node);
  node.children?.forEach((child) => walk(child, visitor));
}
walk(tree, (node) => {
  if (node.type === "imageReference") referencedImages.add(node.identifier);
});
const mime = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
  ".webp": "image/webp", ".svg": "image/svg+xml", ".avif": "image/avif", ".bmp": "image/bmp" };
walk(tree, (node) => {
  if (node.type !== "image" && !(node.type === "definition" && referencedImages.has(node.identifier))) return;
  if (node.url.startsWith("data:image/")) return;
  if (/^https?:/iu.test(node.url)) throw new Error(`请将图片下载到笔记旁，再使用相对路径：${node.url}`);
  const url = node.url.startsWith("file:") ? fileURLToPath(node.url) : decodeURIComponent(node.url.split("#")[0]);
  const path = resolve(input.baseDir, url);
  const type = mime[extname(path).toLowerCase()];
  if (!type) throw new Error(`不支持的图片格式：${node.url}`);
  const data = `data:${type};base64,${readFileSync(path).toString("base64")}`;
  assets.push(path);
  const quote = node.title ? ` ${JSON.stringify(node.title)}` : "";
  const value = node.type === "image" ? `![${(node.alt ?? "").replace(/[\[\]]/gu, "\\$&")}](${data}${quote})`
    : `[${node.label ?? node.identifier}]: ${data}${quote}`;
  replacements.push({ start: node.position.start.offset, end: node.position.end.offset, value });
});
// Image nodes within a removed title do not require a second replacement.
for (const item of replacements.filter((item, i, all) => !all.some((other, j) => i !== j
  && other.start <= item.start && other.end >= item.end)).sort((a, b) => b.start - a.start)) {
  markdown = markdown.slice(0, item.start) + item.value + markdown.slice(item.end);
}
process.stdout.write(JSON.stringify({ title: title || input.fallbackTitle, markdown: markdown.trim(), assets: [...new Set(assets)] }));
