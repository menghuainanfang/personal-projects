const { _electron: electron } = require("playwright");
const { expect } = require("playwright/test");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const { fixtures } = require("./fixtures.cjs");
const root = path.resolve(
  "test-results/desktop-" +
    (process.env.READINGOS_EXECUTABLE ? "packaged" : "development"),
);
fs.mkdirSync(root, { recursive: true });
if (!root.startsWith(path.resolve("test-results") + path.sep))
  throw Error("Invalid test output directory");
fs.rmSync(path.join(root, "data"), { recursive: true, force: true });
let app, page;
const results = [];
const errors = [];
let blockedScripts = 0;
async function launch() {
  const opts = {
    env: {
      ...process.env,
      READINGOS_TEST_DATA: path.join(root, "data"),
      READINGOS_TEST_HEADLESS: "1",
    },
  };
  if (process.env.READINGOS_EXECUTABLE) {
    opts.executablePath = path.resolve(process.env.READINGOS_EXECUTABLE);
    opts.args = [];
  } else opts.args = [path.resolve(".")];
  app = await electron.launch(opts);
  page = await app.firstWindow();
  await app.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows()[0].webContents.setBackgroundThrottling(false),
  );
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") {
      if (m.text().startsWith("Blocked script execution in 'about:srcdoc'"))
        blockedScripts++;
      else errors.push(m.text());
    }
  });
  await expect(page.getByRole("heading", { name: "我的书库" })).toBeVisible();
}
async function step(name, fn) {
  await fn();
  results.push(name);
  console.log("PASS " + name);
}
async function snapshot() {
  return page.evaluate(() => window.readingos.snapshot());
}
async function capture(name) {
  const base64 = await app.evaluate(async ({ BrowserWindow }) => {
    const window = BrowserWindow.getAllWindows()[0];
    window.showInactive();
    await new Promise((resolve) => setTimeout(resolve, 300));
    const image = await window.webContents.capturePage(undefined, {
      stayHidden: true,
      stayAwake: true,
    });
    window.hide();
    return image.toPNG().toString("base64");
  });
  fs.writeFileSync(path.join(root, name), Buffer.from(base64, "base64"));
}
async function waitSaved() {
  const status = (await page.locator(".modal .format-bar span").count())
    ? page.locator(".modal .format-bar span")
    : (await page.locator(".reader-header small").count())
      ? page.locator(".reader-header small")
      : page.locator(".format-bar span").first();
  await expect(status).toHaveText("已保存");
}
async function chooseImport(file) {
  await app.evaluate(({ dialog }, p) => {
    dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [p] });
  }, file);
  await page
    .getByRole("button", { name: "导入电子书", exact: true })
    .first()
    .click();
}
async function selectPdf() {
  await page
    .locator(".textLayer span")
    .filter({ hasText: "Reading invites" })
    .first()
    .waitFor();
  await page.evaluate(() => {
    const span = [...document.querySelectorAll(".textLayer span")].find((e) =>
      e.textContent.includes("Reading invites"),
    );
    const range = document.createRange();
    range.selectNodeContents(span);
    const s = window.getSelection();
    s.removeAllRanges();
    s.addRange(range);
    span.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
  });
  await expect(page.getByRole("button", { name: "高亮选文" })).toBeEnabled();
}
async function selectEpub() {
  const frame = page.frameLocator("iframe");
  await frame.locator("p").first().waitFor();
  await frame
    .locator("p")
    .first()
    .evaluate((p) => {
      const r = document.createRange();
      r.selectNodeContents(p);
      const s = window.getSelection();
      s.removeAllRanges();
      s.addRange(r);
      p.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    });
  await expect(page.getByRole("button", { name: "高亮选文" })).toBeEnabled();
  return frame;
}
(async () => {
  await fixtures(path.join(root, "fixtures"));
  await launch();
  await step(
    "First launch: empty local library and isolated renderer",
    async () => {
      await expect(
        page.getByRole("heading", { name: "你的第一本书，等你打开" }),
      ).toBeVisible();
      assert.equal(await page.evaluate(() => typeof require), "undefined");
      assert.equal(
        await page.evaluate(() => typeof window.readingos),
        "object",
      );
    },
  );
  await step(
    "Physical book, editable metadata and rich reflection autosave",
    async () => {
      await page.getByRole("button", { name: "添加纸质书" }).first().click();
      await page
        .getByRole("textbox", { name: "书名", exact: true })
        .fill("纸质书测试");
      await page
        .getByRole("textbox", { name: "作者", exact: true })
        .fill("测试作者");
      await page.getByRole("button", { name: "保存", exact: true }).click();
      await page
        .getByRole("button")
        .filter({ has: page.getByRole("heading", { name: "纸质书测试" }) })
        .click();
      const text = "理解从阅读开始。".repeat(300);
      await page
        .getByRole("textbox", { name: "主读后感", exact: true })
        .fill(text);
      await waitSaved();
      assert.ok((await snapshot()).summaries[0].content.includes(text));
      await page
        .getByRole("textbox", { name: "主读后感", exact: true })
        .fill(text + "实践是下一步。");
      await waitSaved();
      assert.equal((await snapshot()).summary_revisions.length, 2);
      await page.getByRole("button", { name: /版本记录/ }).click();
      await expect(page.locator(".revision-list details")).toHaveCount(2);
      await page.getByRole("button", { name: "返回书库" }).click();
      await page
        .getByRole("button")
        .filter({ has: page.getByRole("heading", { name: "纸质书测试" }) })
        .click();
      await expect(
        page.getByRole("textbox", { name: "主读后感", exact: true }),
      ).toContainText("实践是下一步。");
      const reflection = page.getByRole("textbox", {
        name: "主读后感",
        exact: true,
      });
      await reflection.fill(text + "实践是下一步。新的版本。");
      await waitSaved();
      await page.getByRole("button", { name: /版本记录/ }).click();
      await expect(page.locator(".revision-list details")).toHaveCount(3);
      const previous = page.locator(".revision-list details").nth(1);
      await previous.locator("summary").click();
      await previous.getByRole("button", { name: "恢复此版本" }).click();
      await expect(reflection).toHaveText(text + "实践是下一步。");
      assert.equal(
        (await snapshot()).summaries[0].content,
        "<p>" + text + "实践是下一步。</p>",
      );
    },
  );
  await step(
    "Journal autosave, insight promotion and practical feedback",
    async () => {
      await page.getByRole("button", { name: "写一篇日志" }).click();
      await page.getByRole("textbox", { name: "日志标题" }).fill("今天的阅读");
      await page.getByRole("textbox", { name: "日志正文" }).fill("日志第一段");
      await waitSaved();
      await page
        .locator(".modal")
        .getByRole("button", { name: "加粗" })
        .click();
      await page.getByRole("textbox", { name: "日志正文" }).press("End");
      await page.getByRole("textbox", { name: "日志正文" }).press("Enter");
      await page
        .getByRole("textbox", { name: "日志正文" })
        .pressSequentially("日志第二段");
      await waitSaved();
      await page.getByRole("button", { name: "保存", exact: true }).click();
      assert.equal((await snapshot()).journals.length, 1);
      await page.getByRole("button", { name: "提炼洞见" }).first().click();
      await page
        .getByRole("textbox", { name: "洞见标题" })
        .fill("把理解用于实践");
      await page.getByRole("button", { name: "保存", exact: true }).click();
      await page.getByRole("button", { name: "化为行动" }).click();
      await page
        .getByRole("textbox", { name: "行动描述" })
        .fill("复述一个想法");
      await page.getByRole("button", { name: "保存", exact: true }).click();
      await page
        .getByRole("combobox", { name: "行动状态" })
        .selectOption("done");
      await page.getByRole("button", { name: "记录实践反馈" }).click();
      await page
        .getByRole("textbox", { name: "实践反馈" })
        .fill("复述后更清楚");
      await page.getByRole("button", { name: "保存", exact: true }).click();
      assert.equal((await snapshot()).feedback[0].content, "复述后更清楚");
      await page.getByRole("button", { name: "返回书库" }).click();
    },
  );
  await step(
    "Native-dialog PDF and EPUB import, duplicate and malformed handling",
    async () => {
      await chooseImport(path.join(root, "fixtures/sample.pdf"));
      await chooseImport(path.join(root, "fixtures/sample.epub"));
      await chooseImport(path.join(root, "fixtures/sample.pdf"));
      await expect(
        page.getByRole("status").filter({ hasText: "该文件已在书库中" }),
      ).toBeVisible();
      await chooseImport(path.join(root, "fixtures/malformed.pdf"));
      await expect(
        page.getByRole("status").filter({ hasText: "文件损坏" }),
      ).toBeVisible();
      await chooseImport(path.join(root, "fixtures/malformed.epub"));
      await expect(
        page
          .getByRole("status")
          .filter({ hasText: "malformed.epub：文件损坏" }),
      ).toBeVisible();
      assert.equal((await snapshot()).assets.length, 2);
      await page.getByRole("button", { name: "关闭提示" }).click();
      await capture("bookshelf.png");
    },
  );
  let pdfAnchor;
  await step(
    "PDF canvas, selectable text, highlight and persisted mouse ink",
    async () => {
      await page
        .getByRole("button")
        .filter({
          has: page.getByRole("heading", { name: "The Art of Slow Reading" }),
        })
        .click();
      await page.getByRole("button", { name: /继续阅读 · PDF/ }).click();
      await selectPdf();
      await page.getByRole("button", { name: "高亮选文" }).click();
      await expect(page.locator(".annotation-layer rect")).toHaveCount(1);
      pdfAnchor = (await snapshot()).annotations[0].anchor;
      await page.getByRole("button", { name: "专注模式" }).click();
      await page.getByRole("button", { name: "手绘", exact: true }).click();
      const r = await page.locator(".annotation-layer").boundingBox();
      await page.mouse.move(r.x + 100, r.y + 170);
      await page.mouse.down();
      await page.mouse.move(r.x + 145, r.y + 180, { steps: 8 });
      await page.mouse.move(r.x + 200, r.y + 150, { steps: 8 });
      await page.mouse.up();
      await waitSaved();
      assert.equal((await snapshot()).annotations.length, 2);
      await page.getByRole("button", { name: "撤销", exact: true }).click();
      await waitSaved();
      assert.equal((await snapshot()).annotations.length, 1);
      await page.getByRole("button", { name: "重做", exact: true }).click();
      await waitSaved();
      assert.equal((await snapshot()).annotations.length, 2);
    },
  );
  await step(
    "PDF shapes, textbox, eraser and annotation comments",
    async () => {
      const r = await page.locator(".annotation-layer").boundingBox();
      for (const tool of ["直线", "圆圈"]) {
        await page.getByRole("button", { name: tool, exact: true }).click();
        await page.mouse.move(r.x + 90, r.y + 230);
        await page.mouse.down();
        await page.mouse.move(r.x + 210, r.y + 285, { steps: 5 });
        await page.mouse.up();
        await waitSaved();
      }
      await expect(page.locator(".annotation-layer ellipse")).toHaveCount(1);
      await page.getByRole("button", { name: "文本框", exact: true }).click();
      await page.mouse.click(r.x + 120, r.y + 310);
      await page
        .getByRole("textbox", { name: "文本框文字" })
        .fill("A thought to revisit");
      await page.getByRole("button", { name: "添加", exact: true }).click();
      await waitSaved();
      await expect(page.locator(".annotation-layer text")).toHaveText(
        "A thought to revisit",
      );
      await page.getByRole("button", { name: "橡皮擦", exact: true }).click();
      await page.locator(".annotation-layer text").click();
      await waitSaved();
      await expect(page.locator(".annotation-layer text")).toHaveCount(0);
      await page.getByRole("button", { name: "撤销", exact: true }).click();
      await waitSaved();
      await expect(page.locator(".annotation-layer text")).toHaveCount(1);
      await page.getByRole("button", { name: "研读模式" }).click();
      await page
        .getByRole("textbox", { name: "批注评论" })
        .first()
        .fill("值得实践");
      await page.getByRole("button", { name: "选择文字", exact: true }).click();
      await waitSaved();
      assert.equal((await snapshot()).annotations.length, 5);
      assert.ok(
        (await snapshot()).annotations.some((a) => a.comment === "值得实践"),
      );
      await page.getByRole("button", { name: "专注模式" }).click();
    },
  );
  await step(
    "PDF coordinates remain aligned after zoom and window resize",
    async () => {
      const before = await page
        .locator(".annotation-layer rect")
        .first()
        .boundingBox();
      await page
        .getByRole("combobox", { name: "PDF 缩放" })
        .selectOption("1.25");
      await expect(page.locator(".pdf-page")).toHaveCSS("width", "743.75px");
      const after = await page
        .locator(".annotation-layer rect")
        .first()
        .boundingBox();
      assert.ok(Math.abs(after.width / before.width - 1.25) < 0.01);
      await app.evaluate(({ BrowserWindow }) =>
        BrowserWindow.getAllWindows()[0].setSize(1000, 720),
      );
      await expect(page.locator(".annotation-layer rect")).toHaveCount(1);
      assert.equal(
        (await snapshot()).annotations.find((a) => a.kind === "highlight")
          .anchor,
        pdfAnchor,
      );
      await capture("pdf.png");
      await page.getByRole("spinbutton", { name: "PDF 页码" }).fill("2");
      await expect(
        page.getByRole("spinbutton", { name: "PDF 页码" }),
      ).toHaveValue("2");
      await page.getByRole("button", { name: "← 书籍主页" }).click();
      await page.getByRole("button", { name: "返回书库" }).click();
    },
  );
  let epubAnchor;
  await step(
    "EPUB selection, CFI highlight, typography/reflow restoration",
    async () => {
      await app.evaluate(({ BrowserWindow }) =>
        BrowserWindow.getAllWindows()[0].setSize(1380, 920),
      );
      await page
        .getByRole("button")
        .filter({
          has: page.getByRole("heading", {
            name: "A Small Book of Reflection",
          }),
        })
        .click();
      await page.getByRole("button", { name: /继续阅读 · EPUB/ }).click();
      await expect(page.locator("iframe")).toHaveCount(1);
      await selectEpub();
      await page.getByRole("button", { name: "高亮选文" }).click();
      await waitSaved();
      epubAnchor = (await snapshot()).annotations.find(
        (a) => a.kind === "highlight" && JSON.parse(a.anchor).cfi,
      ).anchor;
      assert.ok(
        (await snapshot()).annotations
          .find((a) => a.anchor === epubAnchor)
          .text.includes("Reading invites us to pause"),
      );
      await page.getByRole("spinbutton", { name: "EPUB 字号" }).fill("28");
      await app.evaluate(({ BrowserWindow }) =>
        BrowserWindow.getAllWindows()[0].setSize(1100, 760),
      );
      await expect(page.locator("iframe")).toHaveCount(1);
      assert.equal(
        (await snapshot()).annotations.find((a) => a.anchor === epubAnchor)
          .anchor,
        epubAnchor,
      );
      assert.equal(
        await page
          .frameLocator("iframe")
          .locator("p")
          .first()
          .evaluate(() => typeof window.readingos),
        "undefined",
      );
      await expect(page.locator(".epub-host svg rect").first()).toBeVisible();
      assert.ok(
        (await page.locator(".epub-host svg rect").count()) > 1,
        "Full excerpt spans multiple reflowed lines",
      );
      await capture("epub.png");
      await page.getByRole("button", { name: "← 书籍主页" }).click();
      await page.getByRole("button", { name: "返回书库" }).click();
    },
  );
  await step(
    "Goals and month plans persist independently of actual completion",
    async () => {
      await page.getByRole("button", { name: "阅读计划" }).click();
      const month = await page
        .getByLabel("计划月份")
        .inputValue()
        .catch(() => new Date().toLocaleDateString("sv-SE").slice(0, 7));
      await page
        .getByRole("spinbutton", { name: month.slice(0, 4) + " 目标" })
        .fill("12");
      await page.getByRole("heading", { name: "阅读计划" }).click();
      await page.locator(".plan-list input").first().click();
      await expect(page.locator(".plan-list input").first()).toBeChecked();
      await page.getByRole("button", { name: /书库/ }).first().click();
      assert.equal((await snapshot()).plans.length, 1);
    },
  );
  const before = await snapshot();
  await app.close();
  await step(
    "Application restart restores long-form notes, PDF page and annotations",
    async () => {
      await launch();
      assert.deepEqual(await snapshot(), before);
      await page
        .getByRole("button")
        .filter({
          has: page.getByRole("heading", { name: "The Art of Slow Reading" }),
        })
        .click();
      await page.getByRole("button", { name: /继续阅读 · PDF/ }).click();
      await expect(
        page.getByRole("spinbutton", { name: "PDF 页码" }),
      ).toHaveValue("2");
      await page.getByRole("spinbutton", { name: "PDF 页码" }).fill("1");
      await expect(page.locator(".annotation-layer rect")).toHaveCount(1);
      await expect(page.locator(".annotation-layer polyline")).toHaveCount(2);
      await expect(page.locator(".annotation-layer ellipse")).toHaveCount(1);
      await expect(page.locator(".annotation-layer text")).toHaveCount(1);
      await page.getByRole("button", { name: "← 书籍主页" }).click();
      await page.getByRole("button", { name: "返回书库" }).click();
    },
  );
  await step("EPUB highlights restored after application restart", async () => {
    await page
      .getByRole("button")
      .filter({
        has: page.getByRole("heading", { name: "A Small Book of Reflection" }),
      })
      .click();
    await page.getByRole("button", { name: /继续阅读 · EPUB/ }).click();
    await expect(page.locator("iframe")).toHaveCount(1);
    await expect(page.locator(".epub-host svg")).toHaveCount(1);
    assert.ok(
      (await snapshot()).annotations.some((a) => a.anchor === epubAnchor),
    );
    await page.getByRole("button", { name: "← 书籍主页" }).click();
    await page.getByRole("button", { name: "返回书库" }).click();
  });
  await step(
    "Native backup and restore preserve the full library",
    async () => {
      await page.getByRole("button", { name: "资料与设置" }).click();
      const backup = path.join(root, "full.readingos");
      await app.evaluate(({ dialog }, p) => {
        dialog.showSaveDialog = async () => ({ canceled: false, filePath: p });
        dialog.showOpenDialog = async () => ({
          canceled: false,
          filePaths: [p],
        });
        dialog.showMessageBox = async () => ({ response: 1 });
      }, backup);
      const state = await snapshot();
      await page.getByRole("button", { name: "创建完整备份" }).click();
      await expect(
        page.getByRole("status").filter({ hasText: "备份已完成" }),
      ).toBeVisible();
      assert.ok(fs.existsSync(backup));
      await page.evaluate(() =>
        window.readingos.save("books", { title: "恢复应移除" }),
      );
      await page.getByRole("button", { name: "从备份恢复" }).click();
      await expect(
        page.getByRole("status").filter({ hasText: "恢复操作已结束" }),
      ).toBeVisible();
      assert.deepEqual(await snapshot(), state);
    },
  );
  assert.deepEqual(errors, [], "No renderer errors");
  const info = await page.evaluate(() => window.readingos.info());
  fs.writeFileSync(
    path.join(root, "results.json"),
    JSON.stringify(
      { passed: results, errors, sandboxScriptBlocks: blockedScripts, info },
      null,
      2,
    ),
  );
  await app.close();
  console.log("Desktop acceptance passed: " + results.length);
})().catch(async (e) => {
  console.error(e);
  if (page) await capture("failure.png").catch(() => {});
  fs.writeFileSync(
    path.join(root, "failure.json"),
    JSON.stringify(
      { passed: results, error: e.message, rendererErrors: errors },
      null,
      2,
    ),
  );
  await app?.close().catch(() => {});
  process.exitCode = 1;
});
