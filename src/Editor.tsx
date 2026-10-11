import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import DOMPurify from "dompurify";
import { useEffect, useRef, useState } from "react";
export function Editor({
  value,
  version,
  onSave,
  label,
}: {
  value: string;
  version?: string;
  onSave: (value: string) => Promise<void>;
  label: string;
}) {
  const [status, setStatus] = useState("已保存");
  const saver = useRef(onSave);
  saver.current = onSave;
  const generation = useRef(0);
  const editor = useEditor({
    extensions: [StarterKit.configure({ link: { openOnClick: false } })],
    content: DOMPurify.sanitize(value),
    editorProps: { attributes: { "aria-label": label, role: "textbox" } },
    onUpdate: ({ editor }) => {
      const html = editor.getHTML(),
        version = ++generation.current;
      setStatus("保存中…");
      void saver
        .current(html)
        .then(() => {
          if (version === generation.current) setStatus("已保存");
        })
        .catch((e) => setStatus("保存失败：" + e.message));
    },
  });
  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(DOMPurify.sanitize(value), {
        emitUpdate: false,
      });
    }
  }, [value, version, editor]);
  if (!editor) return null;
  return (
    <div className="rich-editor">
      <div className="format-bar">
        <button
          type="button"
          aria-label="加粗"
          className={editor.isActive("bold") ? "active" : ""}
          onClick={() => editor.chain().focus().toggleBold().run()}
        >
          <b>B</b>
        </button>
        <button
          type="button"
          aria-label="斜体"
          onClick={() => editor.chain().focus().toggleItalic().run()}
        >
          <i>I</i>
        </button>
        <button
          type="button"
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 2 }).run()
          }
        >
          标题
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        >
          列表
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
        >
          引用
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().undo().run()}
        >
          撤销
        </button>
        <span role="status">{status}</span>
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}
