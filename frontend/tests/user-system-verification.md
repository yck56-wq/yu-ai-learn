# 用户系统前端验证记录

## 0. 基线

- 命令：`node --test tests/*.test.cjs`
- 结果：现有 4 个测试通过，0 失败。
- 范围：仅现有答题领域函数；尚未包含登录、鉴权请求、账号切换与缓存策略。

## 1. RED：用户系统行为测试

- 新增覆盖：Bearer 请求、GET/POST/PUT、401 身份清理、并发共享登录、同账号保留待提交记录、换账号清缓存、应用重启不恢复中途答题、H5 禁止正式答题、昵称校验。
- 命令：`node --test tests/user.test.cjs`
- 结果：6 个测试均按预期失败；断言分别指出缺少 `createApiClient`、`createAuthController`、`discardInterruptedQuiz`、`canStartOfficialQuiz` 等待实现行为。
- 运行环境修正：Node 不能直接加载 Taro runtime，测试仅替换该外部运行时并注入请求函数，生产逻辑仍由真实模块执行。

## 2. GREEN 与回归

- `node --test tests/*.test.cjs`：10 个测试通过，覆盖原有 4 项答题行为及用户系统 6 项行为。
- 追加回归：旧请求迟到 401 不清理新 Token；题库缓存 owner 必须匹配当前用户；完整待提交复盘按账号和题数恢复；资料编辑用户 ID 门禁。
- `node node_modules/typescript/bin/tsc --noEmit`：通过。

## 3. 构建与 UI 验收

- `npm run build:weapp`：Taro 4.2.1 编译成功，custom Tabbar 产物和 5 个页面配置已生成。
- custom Tabbar 样式隔离修复：`index.config.ts` 设置 `styleIsolation: 'shared'`，全局 `app.scss` 引入同一份 Tabbar Sass；构建产物 `dist/custom-tab-bar/index.json` 与 `dist/common.wxss` 均已核对。
- `npm run build:h5`：编译成功；仅有 Webpack 入口体积提示。
- 375px H5 截图：`.playwright-cli/page-2026-09-07T13-08-45-152Z.png`（首页）、`.playwright-cli/page-2026-09-07T13-10-36-206Z.png`（学习记录）、`.playwright-cli/page-2026-09-07T13-21-29-204Z.png`（我的）。三页均显示三栏 custom Tabbar；我的页面验证了昵称编辑与保存态。
- H5 预览不调用微信登录和正式答题；微信小程序正式答题仍由服务端 Bearer 鉴权控制。

## 4. 安全检查

- `frontend/.env` 已移除；`.env.example` 仅保留公开 API 地址示例。
- `src`、`dist`、`dist-h5` 未发现模型配置名称或服务端模型凭证内容。
