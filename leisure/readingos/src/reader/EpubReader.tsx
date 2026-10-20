import { useEffect, useRef, useState } from "react";
import ePub from "epubjs";
import type { Rendition, Book } from "epubjs";
import DOMPurify from "dompurify";
import type { ReaderProps } from "./PdfReader";
import { textRange } from "./epubSelection";
export function EpubReader(
  p: ReaderProps & { fontSize: number; lineHeight: number; theme: string; background:string; foreground:string },
) {
  const host = useRef<HTMLDivElement>(null),
    rendition = useRef<Rendition | null>(null),
    book = useRef<Book | null>(null);
  const latest = useRef(p);
  latest.current = p;
  const applied = useRef<string[]>([]);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let alive = true;
    const b = ePub(p.bytes.slice().buffer as ArrayBuffer, {
      replacements: "blobUrl",
    });
    book.current = b;
    b.spine.hooks.serialize.register((output: string, section: any) => {
      section.output = DOMPurify.sanitize(output, {
        WHOLE_DOCUMENT: true,
        ADD_TAGS: ["link"],
        ADD_ATTR: ["epub:type"],
        FORBID_TAGS: ["script", "object", "embed", "form"],
        FORBID_ATTR: ["srcdoc"],
      });
    });
    const r = b.renderTo(host.current!, {
      width: "100%",
      height: "100%",
      flow: "paginated",
      spread: "none",
      allowScriptedContent: false,
    });
    rendition.current = r;
    r.themes.default({
      body: {
        "font-family": 'Georgia, "Microsoft YaHei", serif',
        "line-height": String(p.lineHeight),
        padding: "24px !important",
      },
      p: { "margin-bottom": "0.8em" },
    });
    r.themes.fontSize(p.fontSize + "px");
    r.on("selected", (cfi: string, contents: any) => {
      try {
        const selection = contents.document.defaultView?.getSelection();
        const range = textRange(
          selection?.rangeCount ? selection.getRangeAt(0) : contents.range(cfi),
        );
        const anchor = contents.cfiFromRange(range);
        latest.current.onSelection({
          anchor: JSON.stringify({ cfi: anchor }),
          text: range.toString(),
        });
      } catch {}
    });
    r.on("relocated", (loc: any) => {
      if (alive) latest.current.onLocation(loc.start.cfi);
    });
    r.on("displayError", (e: Error) =>
      latest.current.onError("EPUB 页面无法显示：" + e.message),
    );
    b.loaded.navigation
      .then((nav) => {
        const toc: { label: string; location: string }[] = [];
        const walk = (items: any[]) =>
          items.forEach((item) => {
            toc.push({ label: item.label.trim(), location: item.href });
            if (item.subitems) walk(item.subitems);
          });
        walk(nav.toc);
        if (alive) latest.current.onToc(toc);
      })
      .catch((e) => latest.current.onError(e.message));
    r.display(p.location || undefined)
      .then(() => {
        if (alive) setReady(true);
      })
      .catch(
        (e) => alive && latest.current.onError("EPUB 无法打开：" + e.message),
      );
    const observer = new ResizeObserver(() => {
      if (alive && (r as any).manager)
        r.resize(host.current!.clientWidth, host.current!.clientHeight);
    });
    observer.observe(host.current!);
    return () => {
      alive = false;
      observer.disconnect();
      r.destroy();
      b.destroy();
      rendition.current = null;
      applied.current = [];
    };
  }, [p.bytes]);
  useEffect(() => {
    const r = rendition.current;
    if (!r || !ready) return;
    r.themes.fontSize(p.fontSize + "px");
    r.themes.override("line-height", String(p.lineHeight));
    r.themes.override("color", p.foreground);
    r.themes.override("background", p.background);
  }, [p.fontSize, p.lineHeight, p.background, p.foreground, ready]);
  useEffect(() => {
    const r = rendition.current;
    if (!r || !ready) return;
    for (const cfi of applied.current) r.annotations.remove(cfi, "highlight");
    applied.current = [];
    for (const a of p.annotations)
      try {
        const { cfi } = JSON.parse(a.anchor);
        r.annotations.highlight(
          cfi,
          { id: a.id },
          () => latest.current.onSelection({ anchor: a.anchor, text: a.text }),
          "readingos-highlight",
          {
            fill: a.color,
            "fill-opacity": "0.35",
            "mix-blend-mode": "multiply",
          },
        );
        applied.current.push(cfi);
      } catch {}
  }, [p.annotations, p.bytes, ready]);
  useEffect(() => {
    const r = rendition.current;
    if (
      r &&
      ready &&
      p.location &&
      p.location !== (r.currentLocation() as any)?.start?.cfi
    )
      r.display(p.location).catch((e) =>
        latest.current.onError("无法定位到此段落：" + e.message),
      );
  }, [p.location, ready]);
  return (
    <div className="epub-reader">
      <div className="page-nav">
        <button onClick={() => void rendition.current?.prev()}>上一页</button>
        <span>EPUB · 文字随窗口自动排版</span>
        <button onClick={() => void rendition.current?.next()}>下一页</button>
      </div>
      <div className="epub-host" ref={host} />
    </div>
  );
}
