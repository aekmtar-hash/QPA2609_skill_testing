# 本机模式：派子代理的任务模板

本机模式 = 主会话（规划 + 核对）和 eda-agent 在同一台电脑上，所有 `mcp__eda-agent__*` 调用都派 `eda-agent-operator` 子代理去做（规矩见 `eda-agent` skill：只用 Sonnet / Haiku，主模型不直接调，每次派之前告诉用户用的是什么模型）。

模型怎么选：
- **Haiku**：只读、照抄数字、导出表格（ping、读规则、导出焊盘 / 文字 / 线）。
- **Sonnet**：要修改、要跑 DRC、要在不符时自己判断该不该停。

**真实例子**：`examples/qpa2609/subagent_dispatches/README.md`，12 次往返的任务原文和汇报原文，带讲解。下面的模板就是从那里提炼的。

子代理看不到主会话，所以每份说明都要写全：工程和 PCB 的完整路径、只读还是可以改（可以改就写明**只准改什么**）、备份在哪、要带回什么、什么情况停下。

同一件事分几步做（例如改文件前后各一次 AD 操作），**用 SendMessage 续派同一个子代理**，它记得前面的上下文，说明可以短很多。

---

## 模板 1：只读侦察 / 打开工程（Sonnet；第一次连时连接可能要处理）

```
任务（只读）：检查 eda-agent 能否控制 AD，打开 <工程.PrjPcb 完整路径>，读回基本信息。
不准修改、保存、跑 DRC、跑 doctor。
1. ToolSearch 加载 mcp__eda-agent__tool_catalog、mcp__eda-agent__tool_invoke；找不到就停下汇报。
2. app_ping；不通就运行 Connect_Altium.ps1，等 "bridge is ready" 再 ping。带回脚本版本、AD 版本、有无多客户端警告。
3. 看 AD 已开了哪些工程；已经开着就不重复打开。
4. proj_open → proj_load_sheets → pcb_focus_board(board_path=<PCB 完整路径>)。弹对话框就停下，带回标题和按钮原文，不要点。
5. 带回：proj_list_documents 全表（指出 PCB 是哪个文件）、库是否都在、pcb_get_board_statistics、pcb_get_board_outline、
   规则列表（名字、descriptor 原文）、dirty 状态。
汇报：第一行 成功/部分完成/失败；原始数字；报错原文；推断单独标明。
```

## 模板 2：导出数据（Haiku）

```
任务（只读）：从已打开的 <PCB> 导出 CSV。不准修改、保存、跑 DRC。
obj_query 多条件用竖线 | 连接；读不到的属性留空，不要编；坐标保持原始 mil 值。
a. ePadObject 全部 → <路径>\pads.csv：Component, Name, X, Y, TopXSize, TopYSize, TopShape, Rotation, Layer, HoleSize, Net
b. eTrackObject Layer=TopOverlay → overlay_tracks.csv：X1, Y1, X2, Y2, Width, Component
c. eTextObject Layer=TopOverlay → top_overlay_texts.csv：Text, X, Y, Rotation, Height, Width, IsDesignator, IsComment, Component
汇报：文件路径、行数（必须等于 obj_query 的 count）、读不到的属性和报错原文。不要分析。
```

注意：Haiku 可能把查询结果**手抄**进 CSV。能从 PcbDoc 直接读的（文字、线、弧、过孔），主会话用 `scripts/pcbdoc_io.py` 自己读，再和它的表比对；焊盘拿 DRC 报告里的焊盘坐标抽查。

## 模板 3：按清单修改（Sonnet）

```
任务：<一句话目的>。允许修改并保存，但只准做下面列出的操作。
工程 / PCB：<完整路径>；备份：<备份文件夹>（已存在）。
禁止：跑 doctor、pcb_set_text_visibility、改元件位号文字（IsDesignator=true）、改清单以外的任何对象、关 Altium_API.PrjScr。
每次改对象前先 pcb_focus_board（DRC 会把活动文档切走）。

第 1 步 删除 N 个对象：对每一行先 obj_query（过滤带 Layer + Text + X + Y 精确值），确认正好 1 个且 <其他特征>；
  任何一行不满足，整步停下汇报，一个都不删。都确认后再删。删后核对：<目标数量 = 0>，<必须保留的对象各还在>。
第 2 步 ...（每步：先确认对象唯一 → 改 → 读回）
最后：app_save_all（still_dirty 必须 0）。
汇报：第一行 成功/部分完成/失败；每步读回的原始值；报错原文。
```

要点：
- 过滤条件里**必须带层**：同名、同坐标的对象可能在别的层上（第三轮：替身文字和 Mechanical13 上的真位号坐标完全一样）。
- 写清"预期会看到什么"，子代理才能分辨意外。第三轮子代理发现"多出 4 个同名对象"后停下来问，避免了误删。
- 删除可能被 Claude Code 的权限系统拦下：说明里写"被拒就停下汇报，不换办法绕过"。

## 模板 4：为直接改文件做准备 —— 保存并关闭（续派同一个子代理）

```
请只做一件事：（保存后）关闭 <工程>，然后停下汇报。
proj_close(project_path=<完整路径>, save=false)；弹"是否保存"就停下汇报原文，不要点。
proj_list_open 确认工程已不在、Altium_API.PrjScr 还在。不要保存其他东西。
```

## 模板 5：重新打开 → 读回核对 → DRC → 保存（Sonnet）

```
文件已离线改好。允许的修改只有：第 4 步开关两条规则、第 6 步保存。
1. proj_open → proj_load_sheets → pcb_focus_board；弹框就停；读 modified 状态。
2. obj_query 读回 <层> 全部文字，写 CSV（行数 = count）；对照期望清单 <expected.csv> 逐行报 OK / 不符
   （Text 相同、|X|,|Y| 差 < 0.01、Rotation、Height、Width、IsDesignator 一致）。另查 <应为 0 的条件> 的数量。
   读统计数（预期 <元件/过孔/焊盘/铺铜/未连接>）和板框。
   **任何一项不符就停下汇报，不做后面的步骤，不保存。**
3. DRC（pcb_run_drc(allow_modal=true) → app_press_dialog_button "运行DRC (&R)..."），等报告文件时间更新，复制成 <A.drc>。
4. pcb_set_rules_enabled(names=[...数组...], enabled=false)，读回 descriptor 带 (Disabled)。
5. 再跑 DRC，复制成 <B.drc>。
6. app_save_all，still_dirty 0。
汇报：每步原始值；两份报告各规则违规数。
```

主会话收到后**自己读两份 .drc**（`scripts/drc_report.py`），并用 `pcbdoc_io.py` 重新解析保存后的文件，确认改动还在。

## 收到汇报以后

- 子代理"停下来问"的，先查清再答，用 SendMessage 续派；它给的推断（"可能是……"）要找证据，不能直接采信。
- 子代理说某操作被权限拒绝、让主会话代做：**不代做**，告诉用户。
- 给用户讲结果时注明"以下来自 Sonnet / Haiku 子代理"，以及哪些是主会话自己核对过的。
