import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import worker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import "pdfjs-dist/web/pdf_viewer.css";
import type { Annotation } from "../domain";
pdfjs.GlobalWorkerOptions.workerSrc = worker;
export type Selection = { anchor: string; text: string };
export type ReaderProps = {
  bytes: Uint8Array;
  annotations: Annotation[];
  location: string;
  tool: string;
  color: string;
  width: number;
  zoom: number;
  onLocation: (s: string) => void;
  onSelection: (s: Selection | null) => void;
  onDraw: (kind: string, anchor: string, text?: string) => void;
  onErase: (id: string) => void;
  onToc: (toc: { label: string; location: string }[]) => void;
  onError: (s: string) => void;
};
export function PdfReader(p: ReaderProps) {
  const [doc, setDoc] = useState<pdfjs.PDFDocumentProxy | null>(null);
  const [size, setSize] = useState({ width: 600, height: 800 });
  const canvas = useRef<HTMLCanvasElement>(null),
    text = useRef<HTMLDivElement>(null),
    pageRef = useRef<HTMLDivElement>(null),
    scrollRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState<number[][]>([]);
  const points = useRef<number[][]>([]);
  let loc: { page: number; scroll?: number };
  try {
    loc = JSON.parse(p.location);
  } catch {
    loc = { page: Number(p.location) || 1 };
  }
  const page = Math.max(1, Math.min(doc?.numPages || 1, loc?.page || 1));
  const latest = useRef(p);
  latest.current = p;
  useEffect(() => {
    const base = new URL("./pdf/", window.location.href).href;
    const task = pdfjs.getDocument({
      data: p.bytes.slice(),
      cMapUrl: base + "cmaps/",
      cMapPacked: true,
      standardFontDataUrl: base + "standard_fonts/",
      wasmUrl: base + "wasm/",
      isEvalSupported: false,
    });
    let alive = true;
    task.promise
      .then(async (d) => {
        if (!alive) return;
        setDoc(d);
        const outline = await d.getOutline();
        const toc = [];
        const walk = async (items: any[]) => {
          for (const item of items) {
            try {
              const dest =
                typeof item.dest === "string"
                  ? await d.getDestination(item.dest)
                  : item.dest;
              const n =
                typeof dest?.[0] === "number"
                  ? dest[0]
                  : await d.getPageIndex(dest[0]);
              toc.push({
                label: item.title,
                location: JSON.stringify({ page: n + 1 }),
              });
            } catch {}
            if (item.items) await walk(item.items);
          }
        };
        if (outline) await walk(outline);
        else
          for (let n = 1; n <= d.numPages; n++)
            toc.push({
              label: "第 " + n + " 页",
              location: JSON.stringify({ page: n }),
            });
        if (alive) latest.current.onToc(toc);
      })
      .catch(
        (e) => alive && latest.current.onError("PDF 无法打开：" + e.message),
      );
    return () => {
      alive = false;
      void task.destroy();
    };
  }, [p.bytes]);
  useEffect(() => {
    if (!doc) return;
    let cancelled = false,
      render: pdfjs.RenderTask | undefined,
      layer: pdfjs.TextLayer | undefined;
    (async () => {
      const pg = await doc.getPage(page);
      if (cancelled) return;
      const vp = pg.getViewport({ scale: p.zoom });
      setSize({ width: vp.width, height: vp.height });
      const c = canvas.current!,
        t = text.current!;
      const ratio = window.devicePixelRatio || 1;
      c.width = Math.floor(vp.width * ratio);
      c.height = Math.floor(vp.height * ratio);
      c.style.width = vp.width + "px";
      c.style.height = vp.height + "px";
      t.replaceChildren();
      t.style.setProperty("--scale-factor", String(p.zoom));
      t.style.setProperty("--total-scale-factor", String(p.zoom));
      render = pg.render({
        canvas: c,
        canvasContext: c.getContext("2d")!,
        viewport: vp,
        transform: ratio === 1 ? undefined : [ratio, 0, 0, ratio, 0, 0],
      });
      await render.promise;
      if (cancelled) return;
      layer = new pdfjs.TextLayer({
        textContentSource: await pg.getTextContent(),
        container: t,
        viewport: vp,
      });
      await layer.render();
      if (!cancelled && scrollRef.current)
        scrollRef.current.scrollTop =
          (loc.scroll || 0) *
          Math.max(
            0,
            scrollRef.current.scrollHeight - scrollRef.current.clientHeight,
          );
    })().catch((e) => {
      if (!cancelled && e.name !== "RenderingCancelledException")
        latest.current.onError("页面渲染失败：" + e.message);
    });
    return () => {
      cancelled = true;
      render?.cancel();
      layer?.cancel();
    };
  }, [doc, page, p.zoom]);
  const point = (e: React.PointerEvent) => {
    const r = pageRef.current!.getBoundingClientRect();
    return [
      Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)),
      Math.max(0, Math.min(1, (e.clientY - r.top) / r.height)),
    ];
  };
  const selection = () => {
    if (p.tool !== "select") return;
    const s = window.getSelection();
    if (
      !s?.rangeCount ||
      !s.toString().trim() ||
      !text.current?.contains(s.anchorNode) ||
      !text.current?.contains(s.focusNode)
    ) {
      p.onSelection(null);
      return;
    }
    const r = pageRef.current!.getBoundingClientRect();
    const rects = Array.from(s.getRangeAt(0).getClientRects())
      .filter((v) => v.width > 0 && v.height > 0)
      .map((v) => [
        (v.x - r.x) / r.width,
        (v.y - r.y) / r.height,
        v.width / r.width,
        v.height / r.height,
      ]);
    p.onSelection({
      text: s.toString(),
      anchor: JSON.stringify({ page, rects }),
    });
  };
  const draw = (a: Annotation) => {
    let anchor: any;
    try {
      anchor = JSON.parse(a.anchor);
    } catch {
      return null;
    }
    if (anchor.page !== page) return null;
    const common = {
      stroke: a.color,
      strokeWidth: a.width * p.zoom,
      fill: "none",
      onPointerDown: () => {
        if (p.tool === "erase") p.onErase(a.id);
      },
      style: {
        pointerEvents: p.tool === "erase" ? "auto" : "none",
      } as React.CSSProperties,
      "data-annotation": a.id,
    };
    if (a.kind === "highlight")
      return (
        <g key={a.id}>
          {anchor.rects?.map((r: number[], i: number) => (
            <rect
              key={i}
              data-annotation={a.id}
              onPointerDown={() => p.tool === "erase" && p.onErase(a.id)}
              x={r[0] * size.width}
              y={r[1] * size.height}
              width={r[2] * size.width}
              height={r[3] * size.height}
              fill={a.color}
              opacity="0.32"
              style={{ pointerEvents: p.tool === "erase" ? "auto" : "none" }}
            />
          ))}
        </g>
      );
    const pts = anchor.points || [];
    if (!pts.length) return null;
    if (a.kind === "textbox")
      return (
        <text
          key={a.id}
          {...common}
          fill={a.color}
          stroke="none"
          fontSize={16 * p.zoom}
          x={pts[0][0] * size.width}
          y={pts[0][1] * size.height}
        >
          {a.text}
        </text>
      );
    if (a.kind === "circle")
      return (
        <ellipse
          key={a.id}
          {...common}
          cx={((pts[0][0] + pts[pts.length - 1][0]) / 2) * size.width}
          cy={((pts[0][1] + pts[pts.length - 1][1]) / 2) * size.height}
          rx={(Math.abs(pts[0][0] - pts[pts.length - 1][0]) / 2) * size.width}
          ry={(Math.abs(pts[0][1] - pts[pts.length - 1][1]) / 2) * size.height}
        />
      );
    return (
      <polyline
        key={a.id}
        {...common}
        strokeLinecap="round"
        strokeLinejoin="round"
        points={(a.kind === "line" ? [pts[0], pts[pts.length - 1]] : pts)
          .map((v: number[]) => v[0] * size.width + "," + v[1] * size.height)
          .join(" ")}
      />
    );
  };
  return (
    <div className="pdf-reader">
      <div className="page-nav">
        <button
          disabled={page <= 1}
          onClick={() => p.onLocation(JSON.stringify({ page: page - 1 }))}
        >
          上一页
        </button>
        <label>
          页码{" "}
          <input
            aria-label="PDF 页码"
            type="number"
            min={1}
            max={doc?.numPages || 1}
            value={page}
            onChange={(e) =>
              p.onLocation(
                JSON.stringify({ page: Number(e.target.value) || 1 }),
              )
            }
          />
        </label>
        <span>/ {doc?.numPages || "…"}</span>
        <button
          disabled={!doc || page >= doc.numPages}
          onClick={() => p.onLocation(JSON.stringify({ page: page + 1 }))}
        >
          下一页
        </button>
      </div>
      <div
        className="pdf-scroll"
        ref={scrollRef}
        onScroll={(e) => {
          const el = e.currentTarget;
          if (doc)
            latest.current.onLocation(
              JSON.stringify({
                page,
                scroll:
                  el.scrollTop / Math.max(1, el.scrollHeight - el.clientHeight),
              }),
            );
        }}
      >
        <div
          className="pdf-page"
          ref={pageRef}
          style={{ width: size.width, height: size.height }}
          onMouseUp={selection}
        >
          <canvas ref={canvas} />
          <div
            ref={text}
            className="textLayer"
            style={{ pointerEvents: p.tool === "select" ? "auto" : "none" }}
          />
          <svg
            className="annotation-layer"
            width={size.width}
            height={size.height}
            style={{
              pointerEvents: p.tool === "select" ? "none" : "auto",
              touchAction: "none",
            }}
            onPointerDown={(e) => {
              if (e.button !== 0 || p.tool === "select" || p.tool === "erase")
                return;
              e.preventDefault();
              e.currentTarget.setPointerCapture(e.pointerId);
              points.current = [point(e)];
              setDraft(points.current);
            }}
            onPointerMove={(e) => {
              if (!points.current.length) return;
              points.current = [...points.current, point(e)];
              setDraft(points.current);
            }}
            onPointerCancel={() => {
              points.current = [];
              setDraft([]);
            }}
            onPointerUp={(e) => {
              if (!points.current.length) return;
              const ps = [...points.current, point(e)];
              points.current = [];
              setDraft([]);
              p.onDraw(
                p.tool,
                JSON.stringify({
                  page,
                  points: p.tool === "ink" ? ps : [ps[0], ps[ps.length - 1]],
                }),
              );
            }}
          >
            {p.annotations.map(draw)}
            {draft.length > 0 &&
              draw({
                id: "draft",
                asset_id: "",
                kind: p.tool,
                anchor: JSON.stringify({ page, points: draft }),
                color: p.color,
                width: p.width,
                text: "",
                comment: "",
              })}
          </svg>
        </div>
      </div>
      <div className="reader-progress">
        <span style={{ width: (page / (doc?.numPages || 1)) * 100 + "%" }} />
      </div>
    </div>
  );
}
