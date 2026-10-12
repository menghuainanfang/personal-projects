# GitHub 与朋友测试发布

源码仓库：[menghuainanfang/personal-projects](https://github.com/menghuainanfang/personal-projects)。ReadingOS 独立位于 `leisure/readingos/`，桌面工作副本位于 `D:\桌面\ReadingOS`。在此仓库根目录使用 Git，同一仓库的其他项目保持各自目录。

## 维护和同步

在修改前执行 `git pull --ff-only`，在 `leisure/readingos/` 编辑应用、运行相关测试并构建。随后在仓库根目录执行：

```powershell
 git add leisure/readingos .github/workflows/readingos-windows.yml
 git diff --cached --stat
 git commit -m "Update ReadingOS"
 git push origin main
```

`node_modules`、`dist`、`release`、`research` 和 `test-results` 均被忽略。个人图书、数据库、日志备份不进入仓库。

## 版本发布

首版标签为 `readingos-v0.1.0`，安装包位于 [GitHub Releases](https://github.com/menghuainanfang/personal-projects/releases/tag/readingos-v0.1.0)。多个项目共用仓库，因此 ReadingOS 的发布标签以 `readingos-` 开头。

后续朋友测试发布步骤：

1. 更新版本号与 CHANGELOG，在应用目录执行相关测试及 `npm run package`。
2. 按 `docs/testing.md` 验收安装版，在仓库根目录提交并上传源码。
3. 创建新的 `readingos-v版本号` 标签，推送标签，在 GitHub 创建对应 Release，使用 `docs/release_notes_v0.1.md` 的结构撰写说明。
4. 上传应用目录 `release/` 下的新安装包；只分发原创或获许可的示例。
5. 朋友下载安装、导入自己的书籍，通过 GitHub Issues 反馈。

仓库根目录的 Windows 工作流构建 ReadingOS，保留 artifact，不自动创建公开 Release。安装包未签名；发布说明应注明 SmartScreen 可能提示和已知限制。
