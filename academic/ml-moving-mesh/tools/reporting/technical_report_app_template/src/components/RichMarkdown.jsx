import {
  $convertFromMarkdownString, $convertToMarkdownString, BOLD_ITALIC_STAR, BOLD_STAR, CHECK_LIST,
  HEADING, INLINE_CODE, ITALIC_STAR, LINK, ORDERED_LIST, QUOTE, UNORDERED_LIST,
} from "@lexical/markdown";
import { LexicalComposer } from "@lexical/react/LexicalComposer";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import { CheckListPlugin } from "@lexical/react/LexicalCheckListPlugin";
import { ContentEditable } from "@lexical/react/LexicalContentEditable";
import { LexicalErrorBoundary } from "@lexical/react/LexicalErrorBoundary";
import { HistoryPlugin } from "@lexical/react/LexicalHistoryPlugin";
import { LinkPlugin } from "@lexical/react/LexicalLinkPlugin";
import { ListPlugin } from "@lexical/react/LexicalListPlugin";
import { MarkdownShortcutPlugin } from "@lexical/react/LexicalMarkdownShortcutPlugin";
import { OnChangePlugin } from "@lexical/react/LexicalOnChangePlugin";
import { RichTextPlugin } from "@lexical/react/LexicalRichTextPlugin";
import { LinkNode } from "@lexical/link";
import { ListItemNode, ListNode } from "@lexical/list";
import { HeadingNode, QuoteNode } from "@lexical/rich-text";
import { COMMAND_PRIORITY_HIGH, KEY_ESCAPE_COMMAND } from "lexical";
import React, { useEffect, useMemo, useState } from "react";
import Markdown from "react-markdown";
import remarkMath from "remark-math";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

import { useDataAppShell } from "../DataAppContext.jsx";
import { sourcePreviewForHref } from "../source-preview.js";
import { RichTextFormatToolbar } from "./RichTextFormatToolbar.jsx";
import { SourcePreviewLink } from "./SourcePreviewLink.jsx";
import { Button } from "./ui.jsx";

const transformers = [
  HEADING, QUOTE, CHECK_LIST, UNORDERED_LIST, ORDERED_LIST, BOLD_ITALIC_STAR, BOLD_STAR,
  ITALIC_STAR, INLINE_CODE, LINK,
];
const theme = {
  heading: { h1: "markdown-h1", h2: "markdown-h2", h3: "markdown-h3", h4: "markdown-h4" },
  link: "markdown-link",
  list: { listitem: "markdown-list-item", ol: "markdown-list", ul: "markdown-list" },
  quote: "markdown-quote",
  text: { bold: "markdown-bold", italic: "markdown-italic", code: "markdown-code" },
};

// Match the checklist syntax emitted by Lexical, leaving ordinary Markdown
// (including escaped markers and inline code) to react-markdown's parser.
function remarkChecklists() {
  return (tree, file) => {
    function visit(node) {
      const paragraph = node.type === "listItem" ? node.children?.[0] : null;
      const text = paragraph?.type === "paragraph" ? paragraph.children?.[0] : null;
      const marker = text?.type === "text" && /^\[([ xX])\](?:[ \t]+|$)/u.exec(text.value);
      if (marker && typeof text.position?.start.offset === "number"
        && String(file.value).slice(text.position.start.offset).startsWith(marker[0])) {
        node.checked = marker[1].toLowerCase() === "x";
        text.value = text.value.slice(marker[0].length);
      }
      node.children?.forEach(visit);
    }
    visit(tree);
  };
}
const markdownPlugins = [remarkGfm, remarkMath, remarkChecklists];
const mathPlugins = [[rehypeKatex, { strict: false, throwOnError: false }]];
const noteUrlTransform = (url) => /^data:image\/(?:png|jpeg|gif|webp|svg\+xml|avif|bmp);base64,/iu.test(url)
  ? url : /^(?:https?:|mailto:|#|\/|\.\/|\.\.\/)/iu.test(url) || !/^[a-z][a-z\d+.-]*:/iu.test(url) ? url : "";

function MarkdownSourceEditor({ value, onSave, onCancel, label }) {
  const [draft, setDraft] = useState(value);
  return <div className="note-source-editor">
    <label>{label}<textarea aria-label={label} value={draft} spellCheck={false}
      onChange={(event) => setDraft(event.target.value)} rows={18} /></label>
    <div className="actions">
      <Button onClick={() => onSave(draft)}>保存正文</Button>
      <Button variant="ghost" onClick={onCancel}>取消</Button>
    </div>
  </div>;
}

function EditorEvents({ onChange, onCancel }) {
  const [editor] = useLexicalComposerContext();

  useEffect(() => editor.registerCommand(KEY_ESCAPE_COMMAND, () => {
    onCancel();
    return true;
  }, COMMAND_PRIORITY_HIGH), [editor, onCancel]);

  return <OnChangePlugin ignoreSelectionChange onChange={(state) => state.read(() => {
    onChange($convertToMarkdownString(transformers).trim());
  })} />;
}

export function RichMarkdown({ value, editing, onEditingChange, onSave, label = "Markdown text" }) {
  const [draft, setDraft] = useState(value);
  const initialConfig = useMemo(() => ({
    namespace: "DataAppMarkdown",
    nodes: [HeadingNode, QuoteNode, ListNode, ListItemNode, LinkNode],
    theme,
    onError(error) { throw error; },
    editorState: () => $convertFromMarkdownString(value, transformers),
  }), [value]);

  function cancel() {
    setDraft(value);
    onEditingChange(false);
  }

  if (!editing) {
    return <div className="notes" role="button" tabIndex={0} onDoubleClick={() => onEditingChange(true)}
      onKeyDown={(event) => { if (event.key === "Enter") onEditingChange(true); }}>
      <Markdown remarkPlugins={markdownPlugins} rehypePlugins={mathPlugins} urlTransform={noteUrlTransform}>{value}</Markdown>
    </div>;
  }

  return (
    <div className="markdown-editor">
      <LexicalComposer initialConfig={initialConfig} key={value}>
        <RichTextPlugin contentEditable={<ContentEditable className="markdown-editable" aria-label={label} />}
          placeholder={<span className="markdown-placeholder">Write Markdown…</span>}
          ErrorBoundary={LexicalErrorBoundary} />
        <HistoryPlugin />
        <ListPlugin />
        <CheckListPlugin />
        <LinkPlugin />
        <RichTextFormatToolbar />
        <MarkdownShortcutPlugin transformers={transformers} />
        <EditorEvents onChange={setDraft} onCancel={cancel} />
      </LexicalComposer>
      <div className="actions">
        <Button onClick={() => { onSave(draft); onEditingChange(false); }}>Save</Button>
        <Button variant="ghost" onClick={cancel}>Cancel</Button>
      </div>
    </div>
  );
}

export function RichNarrative({ id, value, sourcePreviews, sourceEditing = false, className = "", label = "Narrative", ...attributes }) {
  const { canEdit, mode, narrativeEdits, setNarrativeEdit } = useDataAppShell();
  const [sourceOpen, setSourceOpen] = useState(false);
  if (typeof id !== "string" || !id.trim()) {
    throw new Error("RichNarrative requires a non-empty stable narrative id.");
  }
  const authoredMarkdown = narrativeEdits[id] ?? value;
  const markdown = authoredMarkdown;
  const initialConfig = useMemo(() => ({
    namespace: `DataAppNarrative:${id}`,
    nodes: [HeadingNode, QuoteNode, ListNode, ListItemNode, LinkNode],
    theme,
    onError(error) { throw error; },
    editorState: () => $convertFromMarkdownString(markdown, transformers),
  }), [id, markdown]);
  const editing = canEdit && mode === "edit";
  const markdownComponents = useMemo(() => sourcePreviews ? {
    a: ({ node: _node, href, children, ...props }) => {
      const preview = sourcePreviewForHref(sourcePreviews, href);
      return preview ? <SourcePreviewLink {...props} preview={preview}>{children}</SourcePreviewLink>
        : <a {...props} href={href}>{children}</a>;
    },
  } : undefined, [sourcePreviews]);

  return <div {...attributes} className={["rich-narrative", className].filter(Boolean).join(" ")}
    data-rich-narrative data-editable-narrative data-editable-id={id}>
    {editing && sourceEditing ? <>
      {sourceOpen ? <MarkdownSourceEditor key={markdown} value={markdown} label="Markdown / LaTeX 源码"
        onSave={(next) => { setNarrativeEdit(id, next); setSourceOpen(false); }}
        onCancel={() => setSourceOpen(false)} /> : <>
        <div className="rich-narrative-content"><Markdown remarkPlugins={markdownPlugins} rehypePlugins={mathPlugins}
          urlTransform={noteUrlTransform} components={markdownComponents}>{markdown}</Markdown></div>
        <Button onClick={() => setSourceOpen(true)}>编辑 Markdown / LaTeX</Button>
      </>}
    </> : editing ? <LexicalComposer initialConfig={initialConfig} key={id}>
      <RichTextPlugin contentEditable={<ContentEditable className="report-rich-editable" aria-label={label} />}
        placeholder={<span className="markdown-placeholder">Write narrative…</span>}
        ErrorBoundary={LexicalErrorBoundary} />
      <HistoryPlugin />
      <ListPlugin />
      <CheckListPlugin />
      <LinkPlugin />
      <RichTextFormatToolbar />
      <MarkdownShortcutPlugin transformers={transformers} />
      <OnChangePlugin ignoreSelectionChange onChange={(state) => state.read(() => {
        const next = $convertToMarkdownString(transformers).trim();
        if (next !== markdown) setNarrativeEdit(id, next);
      })} />
    </LexicalComposer> : <div className="rich-narrative-content"><Markdown remarkPlugins={markdownPlugins} rehypePlugins={mathPlugins}
      urlTransform={noteUrlTransform} components={markdownComponents}>{markdown}</Markdown></div>}
  </div>;
}
