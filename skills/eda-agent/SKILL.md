---
name: eda-agent
description: 用本机的 eda-agent MCP 操作 Altium Designer 23（"使用 eda-agent"、"使用eda-agentMCP"、"连接 Altium"、去 AD 里查板子 / 规则 / DRC、按清单改 PCB 或原理图）时先读。规定只能派 Sonnet / Haiku 子代理调用，主模型（Opus）不准直接调用；还有连接方法、只读默认、和 Codex 不能同时连。
---

# 使用 eda-agent（本机 Altium）

本机装好的东西：
- AD23：`E:\Program Files\Altium\AD23\X2.EXE`
- eda-agent 0.7.1：`E:\Altium_designer\auto_MCP`（独立 .venv、改过路径的源码 `eda-agent-main`、AD 脚本 `scripts`、工作区 `workspace`）
- 连接脚本：`E:\Altium_designer\auto_MCP\Connect_Altium.ps1`（AD 没开就启动并挂脚本，开着就重挂，等 ping 通）
- Claude Code 里的 MCP 服务名 `eda-agent`（用户级，minimal 工具集：只有 `tool_catalog`、`tool_invoke` 两个入口）；Codex 里叫 `eda-agentMCP`，同一套环境
- QPA2609 工程副本：`E:\Altium_designer\QPA2609\projects\QPA2609_test`（第三轮修好的版本，和另一台电脑那份已分叉）
- 备份：`E:\Altium_designer\备份\<工程>_<时间>_<说明>\`，一次一个文件夹，保持原目录结构

## 规则 1：主模型不准直接调用，必须派 Sonnet 或 Haiku 子代理

**任何 `mcp__eda-agent__*` 调用都用 Agent 工具派子代理做。** 用户原话："调用这个MCP务必用sonnet或者haiku子代理去调用不准用opus,我的额度不够"。

- 用 `subagent_type: "eda-agent-operator"`（定义里固定 `model: sonnet`）。
- 简单的只读查询（ping、读几个数、看规则开没开）传 `model: "haiku"`；改板子、跑 DRC、要判断的用默认的 sonnet。
- **不准**用 `subagent_type: "fork"`（fork 一定继承主模型），也不准不传 model 去用通用代理。
- 主模型自己连一次 `app_ping` 也不行。主模型只负责：写任务说明、核对子代理带回的数字、给用户讲结论。
- **每次派子代理都要告诉用户用的是哪个子代理、什么模型**：派之前在回复里写一句，例如"派 eda-agent-operator 子代理（Sonnet）去……"；汇报结果时再注明"以下结果来自 Sonnet / Haiku 子代理"。用户要求知道每次花的是哪个模型的额度。

## 规则 2：任务说明要写全

子代理看不到主会话。说明里写：
1. 目标、背景、要操作的工程 / 文档名（写完整路径）。
2. **只读还是可以改。** 不写就是只读。可以改时写明备份位置、允许改哪些对象、不准动哪些。
3. 要带回的数字和格式（例如"每条规则的名字、Enabled、数值"，"DRC 报告文件路径和每类违规数"）。
4. 做到哪一步算完、出什么情况要停。

现成的模板：`C:\Users\<用户名>\.claude\skills\mcp-pcb-layout\references\subagent-prompts.md`（只读侦察、导出、按清单修改、关工程、重开读回 + DRC）。改板子这类大任务按 `mcp-pcb-layout` skill 的流程做（用户要求时加载）。

几条实测下来最容易错的（详见 `mcp-pcb-layout\references\eda-agent-pitfalls.md`）：
- `obj_query` / `obj_delete` / `obj_modify` 的多条件过滤用竖线 `|` 连接；过滤里**必须带层**（同名同坐标的对象可能在别的层）。
- `pcb_set_rules_enabled` 的 `names` 传数组；规则开没开看 descriptor 里有没有 "(Disabled)"，`enabled` 字段不可信。
- DRC 要按对话框按钮，结果以 `.drc` 报告文件为准；DRC 后活动文档会切走，改东西前先 `pcb_focus_board`。
- 关工程用 `proj_close(save=false)`；别关 `Altium_API.PrjScr`。
- 不能用：`pcb_set_text_visibility`（卡死）、`pcb_place_stitching_vias`（孔稀）、`eda_agent doctor`（会全部保存）；改不了：文字旋转、位号显示开关、板区域 → 主会话直接改 PcbDoc（`pcbdoc-direct-edit.md`）。

## 规则 5：删除和权限

子代理的删除可能被 Claude Code 的权限检查拦下。**不改权限设置、不建议放宽、不换工具绕过**：把对象的层、文字、坐标和操作步骤告诉用户，请他在 AD 里手动删，删完再派子代理核对。用户原话："确实你的禁止删除规则是对的没我允许不许随意放行这个"。

## 规则 3：一次只让一个客户端连

AD 里的脚本桥同一时间只服务一个连接。派子代理前问清用户 Codex 有没有在用 eda-agent；两个子代理也不要同时操作 AD。

## 规则 4：核对

子代理带回的是待核对材料。关键数字要找原始依据（DRC 报告文件、读回值）；子代理给的"原因""解释"没有读回数据支撑的，告诉用户时标明是推测。
