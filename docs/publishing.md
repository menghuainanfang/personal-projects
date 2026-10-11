# GitHub 与朋友测试发布

当前项目仅在本机，尚未设置远程或上传任何内容。未取得公开发布授权。未读取私人凭据，未使用个人图书测试。

先在 GitHub 创建自己的空仓库 `ReadingOS`，不要勾选自动创建 README。确认所有者和地址后，在项目目录执行：

```powershell
git remote add origin https://github.com/YOUR_ACCOUNT/ReadingOS.git
git remote -v
git push -u origin main
```

`YOUR_ACCOUNT` 替换为实际所有者。Git 的登录流程由用户自行完成；不要把 token 写入项目。若远程已有工作，先查看远程历史，不强制覆盖。

朋友测试发布步骤：

1. 在本机运行 README 中的构建和测试命令，查看 `docs/testing.md`。
2. 使用 `v0.1.0` 创建 release，粘贴 `docs/release_notes_v0.1.md`。
3. 上传 `release/ReadingOS-0.1.0-win-x64-setup.exe`。不要上传 `test-results`、数据库、备份或朋友图书。
4. 朋友下载安装包，导入自己的书籍；通过 issue 模板反馈。

CI 只构建并存储 artifact，不自动公开发布。未配置签名。发布者应说明未签名状态与已知限制，不要求关闭 Windows 安全功能。
