# 用户系统 Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. 用户已于本轮确认执行；在当前已准备的工作目录扩展，保留未提交内容，不自动提交或推送。

**Goal:** 完成微信强制登录、用户档案、MySQL 持久化、历史回看和三栏 TabBar。
**Architecture:** 保留现有出题与确定性报告服务。FastAPI lifespan 管理 aiomysql；用户服务和仓储封装身份、事务、历史；前端保留六状态视觉并接入登录态。
**Tech Stack:** Taro 4.2.1 / React 18 / TypeScript / FastAPI / Pydantic 2 / aiomysql / PyJWT / MySQL 8。
**Spec:** docs/用户系统方案设计文档-最终版.md

## Global Constraints

- 强制微信登录，H5 仅预览；不添加游客、续答、错题本、上传、额外奖励。
- 四表沿用 sql/001_user_system.sql；每题答对 20 XP，整轮一次结算。
- 保留现有接口请求和报告响应结构，服务端以数据库快照判题。
- SQL 参数化，凭证只在本地后端环境文件；测试使用独立库 yu_ai_learn_test。
- 前端与后端工作目录独立，接口约定下述一致；审核后再完整联调。

## Task 1: 身份与连接池

Files: backend/app/config.py, core/db.py, core/auth.py, schemas/user.py, services/user_service.py, repositories/user_repository.py, api/v1/routes/user.py, main.py; tests/test_user_system.py, tests/conftest.py。

- [x] 使用工作区 .venv-user（保留原 .venv），核对现有业务库四表并准备独立测试库。
- [x] 写接口失败测试：login 404 -> 200；同 openid 相同 id；无/伪造/过期 Token -> 401；资料不能跨用户修改。
- [x] 实现 lifespan pool、JWT HS256 固定算法/exp/user_id 校验、微信 GET code2Session 和脱敏错误。
- [x] 运行真实 MySQL 测试，核对连接退出后关闭。

## Task 2: 结算与历史

Files: backend/app/repositories/quiz_repository.py, services/history_service.py, main.py; tests/test_settlement.py。

- [x] 写失败测试：生成题库落库；伪造客户端答案无效；缺题/重复/空答案/非法选项 -> 422；越权 -> 404。
- [x] 实现保存题库和结算：锁 quiz_sessions 行，先查询已结算报告，再校验并使用数据库快照生成报告；同事务保存两表和 XP。
- [x] 写并通过并发结算、不同轮次累计 XP、失败回滚、仅完成历史、分页/加权正确率/详情隔离测试。
- [x] 保持报告响应原字段；详情返回 {quiz_id,title,summary,questions,answer_records,report}，answer_records 含服务端 is_correct 和 duration_ms；前端从详情读取确定性 XP。
- [x] 旧 API 测试增加真实认证/题库前置条件，保留全部原出题校验断言。

## Task 3: 前端用户扩展

Files: frontend/src/services/auth.ts, domain/user.ts, api.ts, app.ts, app.config.ts, custom-tab-bar/*, pages/{index,quiz,report,history,profile}/*, tests/user.test.cjs。

- [x] 先写并运行请求层/登录状态测试：共享登录请求，Bearer，401 清理身份，同账号保留完整待提交记录，换账号清缓存，H5 禁止正式答题。
- [x] 新增 get/put 并保留 post；微信登录和 profile 校验；页面进入守卫。
- [x] 新增历史、档案、昵称编辑、首页真实昵称/XP/最近历史、报告历史回看。
- [x] 原六状态与 CSS 保持，三栏 custom TabBar、一级页 usingComponents、switchTab、路由选中状态、安全区。
- [x] 运行 node --test tests/*.test.cjs、tsc --noEmit、weapp 和 H5 构建。

## Task 4: 审核与联调

- [x] 审核上述接口约定、强制鉴权与数据库原子性、前端账号切换及导航。
- [x] 全量后端和前端测试；检查构建产物不含服务端凭证。
- [x] 启动真实后端检查健康/登录错误/数据库；取得真实微信 code 并验证实际登录。
- [x] UI 以正常手机比例检查原型、新页面、TabBar；在交付记录中分清模拟验证与微信真机验证。

## Execution evidence

- 基线：后端 17 passed，前端 4 passed，TypeScript passed。
- 官方依据：本对话已实际读取 Taro 4.x custom-tabbar、微信 login/code2Session、FastAPI lifespan、aiomysql pool/transactions、PyJWT claim 验证。
- 运行环境：原 .venv 缺少 encodings，系统 Python 3.14 可运行现有后端测试；创建新项目环境不删除原环境。
