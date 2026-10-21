import React from "react";

import {
  ChartRenderer, DataComponent, DataTable, MetricCard, ReportSection,
  RichNarrative, useDataApp,
} from "../../data-app-public.jsx";

function rowsFor(reviewedPeriodRows, queryId) {
  return queryId ? reviewedPeriodRows(queryId) : [];
}

function NarrativeBlock({ block, rows, reviewedPeriodRows }) {
  if (!block.queryId) {
    return <RichNarrative id={`report:${block.id}`} label={`编辑 ${block.id}`} value={block.markdown} sourceEditing={block.sourceEditing} />;
  }
  return <ReportSection id={block.id} queryId={block.queryId} queryIds={block.queryIds} sourceRows={rows}
    sourceRowsByQuery={block.queryIds ? Object.fromEntries(block.queryIds.map((id) => [id, reviewedPeriodRows(id)])) : undefined} showHeading={false}>
      <RichNarrative id={`${block.id}:body`} label={`编辑 ${block.id}`} value={block.markdown} sourceEditing={block.sourceEditing} />
  </ReportSection>;
}

function ReportBlock({ block, reviewedPeriodRows, chartOverrides, chartProps }) {
  const rows = rowsFor(reviewedPeriodRows, block.queryId);
  if (block.kind === "narrative") return <NarrativeBlock block={block} rows={rows} reviewedPeriodRows={reviewedPeriodRows} />;
  if (block.kind === "metrics") {
    return <div className="report-facts" aria-label={block.title ?? "关键指标"}>
      {block.metrics.map((metric) => <MetricCard key={metric.id} id={metric.id} title={metric.title}
        queryId={block.queryId} sourceRows={rows} value={metric.value} comparison={metric.comparison}
        negative={metric.negative} description={metric.description} />)}
    </div>;
  }
  if (block.kind === "chart") {
    const chart = chartOverrides[block.id] ?? block.spec;
    return <DataComponent id={block.id} title={block.title} kind="chart" queryId={block.queryId}
      sourceRows={rows} chart={chart} description={block.description}>
      <ChartRenderer spec={chart} rows={rows} height={block.height ?? 340} {...chartProps(block.id)} />
    </DataComponent>;
  }
  if (block.kind === "table") {
    return <DataComponent id={block.id} title={block.title} kind="table" queryId={block.queryId}
      sourceRows={rows} displayRows={rows}>
      <DataTable rows={rows} columns={block.columns ?? []} searchable={block.searchable ?? false}
        pageSize={block.pageSize ?? 12} />
    </DataComponent>;
  }
  throw new Error(`Unsupported report block kind: ${block.kind}`);
}

export function ReportContent() {
  const { snapshot, reviewedPeriodRows, chartOverrides, chartProps, canEdit, mode, appTitle, setAppTitle,
    narrativeEdits, setNarrativeEdit } = useDataApp();
  const layout = snapshot.report?.layout;
  if (!layout) return <article className="report-content"><p>报告布局尚未配置。</p></article>;
  const noteBlock = snapshot.noteImport ? layout.blocks[0] : null;
  function downloadNote() {
    const text = narrativeEdits[`report:${noteBlock.id}`] ?? noteBlock.markdown;
    const url = URL.createObjectURL(new Blob([`# ${appTitle}\n\n${text}\n`], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${appTitle.replace(/[<>:"/\\|?*]/g, "_")}.md`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <article className="report-content" aria-label="技术数值报告">
    {snapshot.status !== "ready" && <p role="status">{snapshot.noteImport ? "笔记整理稿" : `报告状态：${snapshot.status === "needs_revision" ? "检查未通过，需修订" : "草稿，尚未通过验证"}`}</p>}
    <header className="report-hero">
      <h1 data-data-app-title contentEditable={canEdit && mode === "edit"} suppressContentEditableWarning
        onBlur={canEdit && mode === "edit" ? (event) => setAppTitle(event.currentTarget.textContent.trim() || appTitle) : undefined}
        onKeyDown={canEdit && mode === "edit" ? (event) => {
          if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); }
        } : undefined}>{appTitle}</h1>
      {layout.intro && <RichNarrative id="report:introduction" className="report-deck" label="编辑报告导语" value={layout.intro} />}
    </header>
    {noteBlock && canEdit && mode === "edit" && <div className="actions note-document-actions">
      <button type="button" className="button" onClick={downloadNote}>下载当前 Markdown</button>
      <button type="button" className="button ghost"
        onClick={() => setNarrativeEdit(`report:${noteBlock.id}`, noteBlock.markdown)}>还原导入正文</button>
    </div>}
    {layout.blocks.map((block) => <ReportBlock key={block.id} block={block}
      reviewedPeriodRows={reviewedPeriodRows} chartOverrides={chartOverrides} chartProps={chartProps} />)}
  </article>;
}
