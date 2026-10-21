# 派子代理干活的真实记录（QPA2609 第三轮，本机模式）

12 次往返的**原文**：主会话（Opus）写的任务说明 / 续派消息，子代理（Sonnet 或 Haiku，`eda-agent-operator`）交回的汇报，以及主会话怎么核对、怎么接着处理。模板化的写法见 `references/subagent-prompts.md`，这里是它们在实战里的样子。

读的时候注意三件事：
1. **每份任务说明的结构**：目的和背景 → 工程 / 文件完整路径 → 只读还是可以改（可以改就写"只准改什么"）→ 禁止事项 → 编号步骤，每步带"预期值"和"不符怎么办" → 汇报格式（第一行成功 / 部分 / 失败，原始数字，推断单独标）。
2. **子代理停下来的 4 次**（#1、#6、#7、#10）都是任务里写了"不符就停"才停住的，每一次都挡住了一个真问题。
3. **主会话从不直接采信汇报里的推断**：挖空区、"AD 加载的是旧版本"、手抄的 CSV，都用文件解析或第二个来源核对过。

| # | 做什么 | 模型 | 结果 |
|---|---|---|---|
| 1 | 连接检查 | Sonnet | 工具没加载，第 1 步停 |
| 2 | 只读打开工程 | Sonnet | 成功，数字和第二轮一致 |
| 3 | 规则 / 横虚线 / 转文字三项检查 | Sonnet | 部分完成；"挖空区"由主会话证伪 |
| 4 | 导出 Top Overlay 文字 | Haiku | 成功；找出封装自带文字 |
| 5 | 导出焊盘 / 线 / 弧 | Haiku | 成功；手抄的表由主会话核对 |
| 6 | 删替身、改名、放字、关工程 | Sonnet | 中途停下问 → 续派后完成 |
| 7 | 重开读回 + DRC | Sonnet | 21 条不符，停下没保存 |
| 8 | 不保存地关工程 | Sonnet | 成功 |
| 9 | 补改后重做读回 + DRC | Sonnet | 成功；剩 2 条丝印违规 |
| 10 | 挪 GND、删 MODULE | Sonnet | 删除被权限拦，停下 |
| 11 | 转告用户同意 | Sonnet | 仍被拦 → 用户手动删 |
| 12 | 核对、DRC、保存 | Sonnet | 完成 |

---

## 1　第一次连接：工具还没加载，第一步就停

目的：确认 eda-agent 能控制本机 AD，再打开工程。选 **Sonnet**：第一次连接可能要跑连接脚本、处理弹框，需要判断。

**主会话 → 子代理（新派）**

~~~text
任务：检查本机 eda-agent MCP 能否控制 Altium Designer 23，然后在 AD 里打开（导入）QPA2609 工程，读回基本信息。**只读：可以打开工程和文档，但不准修改、不准保存任何文件，不准跑 DRC、不准跑 doctor。**

背景：这台电脑刚装好 eda-agent（E:\Altium_designer\auto_MCP），Codex 里也配了同一套，但现在没在用。QPA2609 工程是从另一台电脑拷过来的，里面的库用相对路径 ..\..\libs\QPA2609\lib 引用，目录结构是：
- 工程：E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb
- 库：E:\Altium_designer\QPA2609\libs\QPA2609\lib\
- 工程里实际用的 PCB 应该是 PCB1_no3d.PcbDoc，原理图 Sheet1_no3d.SchDoc + Power.SchDoc；文件夹里另有 PCB1.PcbDoc、Sheet1.SchDoc、"Copy of PCB1.PcbDoc" 是旧副本，不要打开它们当作工作文档。

步骤：
1. ToolSearch 加载 mcp__eda-agent__tool_catalog 和 mcp__eda-agent__tool_invoke。如果找不到这两个工具，立即停下汇报"本会话没有 eda-agent 工具"。
2. app_ping。不通就运行 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\Altium_designer\auto_MCP\Connect_Altium.ps1"，等 "Altium bridge is ready"，再 ping。记录脚本版本、AD 版本。app_ping 若有"多个服务器共用工作区"的警告，原文带回。
3. 看 AD 现在打开了哪些工程（app_get_status / proj_get_focused 之类，先用 tool_catalog 找）。如果这个工程已经打开，就不要重复打开，直接聚焦它。
4. 用 proj_open（先 tool_guide 看参数）打开上面的 .PrjPcb，再 proj_load_sheets（如果有）。打开时如果 AD 弹出对话框，停下，把对话框标题和按钮原文带回，不要点。
5. 只读取下面这些并带回：
   - proj_list_documents 的完整文档列表（每个文档的类型和完整路径），特别指出 PCB 是哪个文件、有没有引用到 PCB1.PcbDoc 或 Copy of PCB1.PcbDoc；
   - 库文档是否都能找到（有没有缺失 / 路径不存在的）；
   - 聚焦到 PCB1_no3d.PcbDoc 后的 pcb_get_board_statistics：元件数、过孔数、焊盘数、多边形数、走线数、未连接数（预期大约：元件 62、过孔 783、焊盘 178、多边形 4）；
   - 板框尺寸（pcb_get_board_outline）。
6. 最后确认没有任何文档处于"已修改未保存"状态（如果有工具能读 dirty 状态就读）；不要保存。

汇报格式：第一行写 成功 / 部分完成 / 失败；然后按上面编号逐项给原始数字；工具报错给原文；你的推断单独标明。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
失败：本会话没有 eda-agent 工具。

- 我用 ToolSearch 查询 "select:mcp__eda-agent__tool_catalog,mcp__eda-agent__tool_invoke"，返回 "No matching deferred tools found"。
- 这个会话里可用的工具和延迟加载的工具列表中，没有任何 mcp__eda-agent__* 条目。
- 按任务步骤 1 的要求，我已停止。没有 ping、没有运行 Connect_Altium.ps1、没有打开工程，也没有改动或保存任何文件。
- 推断（未验证）：eda-agent MCP 服务器没有在这个会话里注册。可能是 MCP 配置没有加载，或者需要重启 Claude Code 会话。主模型可以检查 MCP 配置，重启会话后再派任务。
~~~

**主会话怎么处理 / 学到什么**

- 任务第 1 步写了"找不到这两个工具，立即停下汇报"。MCP 是会话中途才登记的，这个会话里还没有工具，子代理 7 秒就停了，没有乱试。
- 主会话：判断原因是"Claude Code 只在启动时加载 MCP"，请用户重启。
- **学到的**：每份任务的第 1 步都写"前提不满足就停"，代价最小。

---

## 2　只读打开工程，读回基本信息

重启后同一份任务再派一次（**Sonnet**）。只读：可以打开工程，不准保存。

**主会话 → 子代理（新派）**

~~~text
任务：检查本机 eda-agent MCP 能否控制 Altium Designer 23，然后在 AD 里打开（导入）QPA2609 工程，读回基本信息。**只读：可以打开工程和文档，但不准修改、不准保存任何文件，不准跑 DRC、不准跑 doctor。**

背景：这台电脑刚装好 eda-agent（E:\Altium_designer\auto_MCP），Codex 里也配了同一套，但现在没在用。QPA2609 工程是从另一台电脑拷过来的，里面的库用相对路径 ..\..\libs\QPA2609\lib 引用，目录结构是：
- 工程：E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb
- 库：E:\Altium_designer\QPA2609\libs\QPA2609\lib\
- 工程里实际用的 PCB 应该是 PCB1_no3d.PcbDoc，原理图 Sheet1_no3d.SchDoc + Power.SchDoc；文件夹里另有 PCB1.PcbDoc、Sheet1.SchDoc、"Copy of PCB1.PcbDoc" 是旧副本，不要打开它们当作工作文档。

步骤：
1. ToolSearch 加载 mcp__eda-agent__tool_catalog 和 mcp__eda-agent__tool_invoke（minimal 工具集，其它工具都通过 tool_invoke 调；不确定工具名就先用 tool_invoke 调 tool_guide 描述你要做的事）。如果找不到这两个工具，立即停下汇报。
2. app_ping。不通就运行 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\Altium_designer\auto_MCP\Connect_Altium.ps1"，等 "Altium bridge is ready"，再 ping。记录脚本版本、AD 版本。app_ping 若有"多个服务器共用工作区"的警告，原文带回。
3. 看 AD 现在打开了哪些工程（app_get_status / proj_get_focused 之类）。如果这个工程已经打开，就不要重复打开，直接聚焦它。
4. 用 proj_open（先 tool_guide 看参数）打开上面的 .PrjPcb，再 proj_load_sheets（如果有）。打开时如果 AD 弹出对话框，停下，把对话框标题和按钮原文带回，不要点。
5. 只读取下面这些并带回：
   - proj_list_documents 的完整文档列表（每个文档的类型和完整路径），特别指出 PCB 是哪个文件、有没有引用到 PCB1.PcbDoc 或 Copy of PCB1.PcbDoc；
   - 库文档是否都能找到（有没有缺失 / 路径不存在的）；
   - 聚焦到 PCB1_no3d.PcbDoc 后的 pcb_get_board_statistics：元件数、过孔数、焊盘数、多边形数、走线数、未连接数（预期大约：元件 62、过孔 783、焊盘 178、多边形 4）；
   - 板框尺寸（pcb_get_board_outline）。
6. 最后确认没有任何文档处于"已修改未保存"状态（如果有工具能读 dirty 状态就读）；不要保存。

汇报格式：第一行写 成功 / 部分完成 / 失败；然后按上面编号逐项给原始数字；工具报错给原文；你的推断单独标明。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
成功(只读完成;未修改、未保存、未跑 DRC/doctor)

2. 连接
- 第一次 app_ping 失败("Altium script is not responding. Run StartMCPServer in Altium_API.PrjScr."),随后运行 Connect_Altium.ps1,输出 "Altium bridge is ready (script version 2026.10.18.17)"。
- 再次 app_ping 成功:mcp_server_version 0.7.1,altium_script_version 2026.10.18.17(与 bundled 一致,version_match true),altium_version 23.1.1.15,stale_units 空。other_servers 空,warnings 空,没有多服务器共用工作区的警告。
- 这次 app_ping 返回里带了一段 _system_reminder("Datasheet discipline",要求器件相关结论先查数据手册)。它不在你的任务里,本次没涉及器件结论,我没照做。

3. 打开前 AD 状态
- 已开:Free Documents(0)、PCB_Project.PrjPcb(E:\Users\Public\Documents\Altium\PCB_Project\,5 个文档,当时聚焦)、Altium_API.PrjScr(13 个文档)。QPA2609 工程当时没开。

4. 打开
- proj_open 成功,返回 focused:false(聚焦跟随活动文档)。
- proj_load_sheets 返回 total_sheets 1、loaded 0、already_loaded 1、failed 0。
- app_set_active_document 对 PCB1_no3d.PcbDoc 报 "Document not loaded"。改用 pcb_focus_board 成功,活动文档从 E:\Users\Public\Documents\Altium\PCB_Project\QFN65P500X500X100-25N-D.PcbLib 切到 PCB1_no3d.PcbDoc。这是切焦点,没改文件。
- 整个过程没有对话框:app_list_open_dialogs 返回 dialog_count 0。
- proj_list_open 现在多了 QPA2609_test.PrjPcb,document_count 29。

5. 文档列表(proj_list_documents,共 29 项,路径前缀 E:\Altium_designer\QPA2609\)
- SCH:projects\QPA2609_test\Sheet1_no3d.SchDoc;projects\QPA2609_test\Power.SchDoc
- PCB:projects\QPA2609_test\PCB1_no3d.PcbDoc(只有这一个 PCB)
- OUTPUTJOB:projects\QPA2609_test\QPA2609_fab.OutJob
- VirtualBOM:projects\QPA2609_test\ActiveBOM.VirtualBOM
- 库 libs\QPA2609\lib\:142-0761-851.PcbLib、142-0761-851.SchLib、QPA2609TR7.PcbLib、QPA2609TR7.SchLib
- 库 projects\QPA2609_test\Lib_power\ 下各一对 PcbLib/SchLib:1812L07524DR、2N7002LT1G、3296W-1-103LF、APT1608SGC、BLM18AG601SN1D、LT3045EMSEPBF、LT3094EMSEPBF、LTC3260EMSEPBF、MMBT3904LT1G、SSA34-E35AT
- 没有引用 PCB1.PcbDoc、Sheet1.SchDoc 或 "Copy of PCB1.PcbDoc"。
- 我把 .PrjPcb 里所有 DocumentPath 按相对路径解析后用 Test-Path 逐个检查,没有缺失。..\..\libs\QPA2609\lib 的 4 个库都在。
- 工程文件里还记录了输出文档 "Project Outputs for QPA2609_test\Design Rule Check - PCB1_no3d.html"。它不在 AD 的文档列表里,但 Test-Path 没报缺失。

6. pcb_get_board_statistics(聚焦 PCB1_no3d.PcbDoc 后)
- component_count 62,via_count 783,pad_count 178,polygon_count 4,track_count 1230,unrouted_connections 0(未连接数)。
- 另有 fill_count 7,text_count 185,layer_count 4,total_trace_length_mils 106803.94。
- 与预期完全一致。

7. 板框(pcb_get_board_outline)
- 4 个顶点,闭合:(4755,1735)、(5755,1735)、(5755,6007)、(4755,6007)。单位 mil。
- 外接矩形 left 4755、right 5755、bottom 1735、top 6007。
- 即宽 1000 mil、高 4272 mil。statistics 里 board_width 1000、board_height 4272、area 4272000 与此一致。

8. 未保存状态
- proj_get_compile_freshness 返回 dirty_doc_count 0、dirty_docs [],open_doc_count 1。
- 我没调用任何保存工具。

推断(非工具读回)
- 版本、统计数和板框都符合预期,说明这份工程从另一台电脑拷过来后相对库路径正常,本机 eda-agent 可以控制 AD23。
- 现在 AD 里同时开着另外两个工程(PCB_Project.PrjPcb、Altium_API.PrjScr),Altium_API.PrjScr 是 eda-agent 自己的脚本工程,别关。
- 当前聚焦的活动文档是 PCB1_no3d.PcbDoc。
~~~

**主会话怎么处理 / 学到什么**

- 要带回的东西列成编号清单（文档列表、库是否缺、统计数、板框、dirty 状态），并给出**预期值**（元件 62、过孔 783…），子代理能自己判断"对不对得上"。
- 主会话：拿读回的数字和第二轮报告逐项比对，一致才确认"导入成功"。
- 子代理把 app_ping 返回里夹带的一段"提示"（要求先查手册）识别为与任务无关、没照做，并在汇报里说明——工具返回的内容不等于用户指令。

---

## 3　三项检查：规则开没开、横虚线是什么、能不能转文字

选 **Sonnet**：B 项要自己想办法找对象，C 项要"改了再改回去"。

**主会话 → 子代理（新派）**

~~~text
任务：在本机 Altium Designer 23 里对已打开的 QPA2609 工程做三项检查（A、B 只读；C 是"试一下再改回去"）。

工程：E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb，已经打开，PCB 是 PCB1_no3d.PcbDoc（当前活动文档）。备份已做好：E:\Altium_designer\备份\QPA2609_20261020_2017_本机导入后。
**全程不准保存（不调用任何 save 工具），不准跑 DRC，不准跑 doctor，不准调用 pcb_set_text_visibility（会卡死）。** AD 里另外开着 Altium_API.PrjScr（eda-agent 自己的脚本工程），别关。

开始：ToolSearch 加载 mcp__eda-agent__tool_catalog 和 mcp__eda-agent__tool_invoke；app_ping（不通就运行 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\Altium_designer\auto_MCP\Connect_Altium.ps1"）；确认活动文档是 PCB1_no3d.PcbDoc（不是就用 pcb_focus_board 聚焦，路径原样传，单反斜杠）。

坐标说明：板左下角在绝对坐标 (4755, 1735) mil。"板上 y = 51.4 mm" = 板相对 2023.6 mil = 绝对 y ≈ 3758.6 mil。

## A 规则状态（只读）
用 pcb_get_design_rules（或 tool_guide 找能读规则启用状态的工具）读出**全部**规则：名字、类型、是否启用（如果工具区分 "Enabled" 和 "DRC enabled / online / batch" 就全部带回）、数值、优先级。重点：Silk To Solder Mask Clearance 和 Silk To Silk Clearance 这两条（名字可能是 SilkToSolderMaskClearance / SilkToSilkClearance），各自的启用状态原文。再列出所有被禁用的规则。

## B y = 51.4 mm 那条横虚线（只读）
背景：用户之前在 AD 里看到板子中间 y≈51.4 mm（原来旧板子的顶边）有一条横穿全板的白色虚线。上一轮已查过 Keep-Out 层、Mechanical1/13/15 的 track/arc/region/fill，都没有横穿全板的对象。这次换别的方向找：
1. 用 tool_catalog / tool_guide 找能截取 PCB 视图图像的工具（screenshot / render / capture 一类）。如果有，截两张：整板视图、y≈51.4 mm 附近放大视图。把图片文件保存到 E:\<项目根>\电路控制\temp\eda_check\ （没有就新建这个文件夹），汇报文件路径。截图工具如果需要移动视图或缩放也可以（只是视图变化，不改设计）。
2. 查以下对象类型里有没有任何一个顶点 / 边在绝对 y = 3755～3762 mil 之间且横向跨度 > 500 mil 的：Dimension（尺寸标注）、Coordinate、Room（ConfinementConstraint / 规则里的 room）、ComponentBody（3D 本体）、Polygon（含 cutout / 外框）、Region（所有层，包括铜层和 Mechanical 2～16 全部机械层）、Fill、Track/Arc（所有层，包括 Top/Bottom Overlay、Paste、Solder、Drill Guide、Drill Drawing、Mechanical 全部层）、Embedded board / board cutout。逐类报告查了没有、找到什么（类型、层、坐标）。
3. 读板子的 Board Shape 和是否有 "board region / split line / layer stack region"（AD 的 Board Planning Mode 里的分割线）——用 tool_guide 问 "board region split line layer stack region" 看有没有工具能读。
4. 如果都没找到，写"没找到"，不要猜。

## C 能不能转文字方向、能不能隐藏位号（试一下再改回）
目的：确认 eda-agent 有没有办法 (1) 改 PCB 文字的旋转角度，(2) 隐藏 / 显示元件位号（designator），(3) 设位号的 Autoposition。上一轮发现 obj_modify 只能改元件和焊盘的 Rotation，改不了文字。
1. 先用 tool_invoke 调 tool_guide，分别描述："rotate a PCB text / string object"、"rotate a component designator text"、"hide a component designator (NameOn) without pcb_set_text_visibility"、"set designator autoposition"。把每个问题返回的推荐工具和"不可能"清单原文带回。
2. 对能做的，各拿**一个**对象试：
   - 文字旋转：用自由文字 "ADJ"（Top Overlay 上的普通字符串，板相对约 (16.086, 68.421) mm）。先读回它的 X、Y、Rotation、Height、Width、Layer 原值并记录；改 Rotation 到 90；读回；再改回原值；读回确认和原值完全一致。
   - 位号旋转：用元件 F101 的位号文字（在 Top Overlay 上）。同样：记原值 → 改 90 → 读回 → 改回 → 读回确认。
   - 隐藏位号：用元件 F101。记原值（位号是否显示）→ 隐藏 → 读回 → 恢复 → 读回确认。
   - Autoposition：如果有工具能读，就只读 F101 位号当前的 Autoposition 值，不要改。
3. 任何一步工具卡住超过 60 秒、报错、或 AD 弹框：停下，把工具名、参数、报错原文带回，不要重试，不要关 AD。恢复不回原值的，把当前值和原值都带回。
4. 最后用 proj_get_compile_freshness（或类似工具）读一下哪些文档是"已修改未保存"。不要保存。

汇报：第一行写 成功 / 部分完成 / 失败；按 A、B、C 分节，给工具读回的原始值；推断单独标明"推断"。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
部分完成。A 做完；B 找到一个可疑对象，但它的几何只能从 SVG 渲染里读出来；C 的旋转、隐藏位号、Autoposition 在这套工具里都做不了，设计没有被改动。

**连接**
- app_ping 成功：AD 23.1.1.15，脚本版本 2026.10.18.17，版本一致，只开着 Altium_API.PrjScr 这个脚本工程。
- proj_get_focused 读到 QPA2609_test.PrjPcb，29 个文档。
- 我用 pcb_focus_board(board_path=...PCB1_no3d.PcbDoc) 聚焦了该板，返回 focused:true。注意参数名是 board_path，不是 file_path。
- 全程没保存、没跑 DRC、没调用 pcb_set_text_visibility。

## A 规则状态（只读）
- pcb_get_design_rules 返回 count=39，39 条全部 enabled:true，**没有被禁用的规则**。
- 这个工具只给一个 enabled 字段，不区分 online/batch。pcb_get_rule_properties 也只返回 enabled。
- 两条重点规则：
  - SilkToSolderMaskClearance：rule_kind 54，enabled:true，priority 1，scope_1=IsPad，scope_2=All，descriptor "Silk To Solder Mask (Clearance=0.254mm) (IsPad),(All)"。
  - SilkToSilkClearance：rule_kind 55，enabled:true，priority 1，scope All/All，descriptor "Silk to Silk (Clearance=0.254mm) (All),(All)"。
- 其余 37 条（名字、类型号、优先级、数值）：
  - SilkToBoardRegionClearance，类型 59，p1，descriptor "Silk primitive without silk layer"。
  - MinimumSolderMaskSliver，类型 53，p1，descriptor 里同时写着 Gap=0.254mm 和 "(Disabled)"，但 enabled:true。这个 "(Disabled)" 是 descriptor 原文，不是规则启用位，不知道是什么意思。
  - IC_Mask，类型 13，p1，膨胀 0.051mm，范围 InComponent U1/U101/U102/U103。
  - Via_Tent，类型 13，p2，膨胀 0.102mm，范围 Isvia。
  - SolderMaskExpansion，类型 13，p3，膨胀 0.102mm，范围 All。
  - PasteMaskExpansion，类型 14，p1，膨胀 0mm。
  - RF_Width，类型 2，p1，宽度 min 0.2、max 0.417、优选 0.417 mm，范围 InNet RFIN/RFOUT/THRU。
  - Width，类型 2，p2，min 0.15、max 1.5、优选 0.3 mm。
  - Clearance_1，类型 0，p2，间隙 0.15mm。
  - RF_to_Pour，类型 0，p1，间隙 1mm，范围 InNet RFIN/RFOUT/THRU 对 InPolygon。
  - UnpouredPolygon，类型 62，不允许 modified 和 shelved。
  - NetAntennae，类型 56，容差 0。
  - HoleToHoleClearance，类型 52，间隙 0.254mm。
  - HoleSize，类型 42，min 0.025、max 2.54 mm。
  - DiffPairsRouting，类型 51，间隙 0.254mm，宽度 0.381mm。
  - Fanout_BGA、Fanout_LCC、Fanout_SOIC、Fanout_Small、Fanout_Default，类型 49，优先级 1 到 5。
  - LayerPairs，类型 48。
  - Height，类型 50，min 0、max 25.4、优选 12.7 mm。
  - ComponentClearance，类型 24，水平和垂直间隙均 0.254mm。
  - AssemblyTestpoint（57）、AssemblyTestPointUsage（58）、FabricationTestpoint（43）、FabricationTestPointUsage（44）。
  - RoutingTopology（7，Shortest）、RoutingVias（11，孔 0.25 到 0.4mm，外径 0.5 到 0.7mm）、RoutingCorners（10，45 度，setback 2.54mm）、RoutingLayers（9）、RoutingPriority（8，值 0）。
  - PolygonConnect（20，直连，导线宽 0.254mm）、PlaneClearance（12，0.508mm）、PlaneConnect（6，relief connect）。
  - UnRoutedNet（16）、ShortCircuit（15，不允许）。
- 房间规则：pcb_get_room_rules 返回 0 条。

## B y=51.4mm 横虚线（只读）
**主要发现：板上有一个横穿全板宽的 board_cutout（板子挖空）区域，它的上边正好在 y=3759 mil（板相对 51.4mm）。**
- obj_query eRegionObject（共 54 个）里有 1 个：Layer=MultiLayer，Kind=board_cutout，IsKeepout=false，Descriptor 为空。
- obj_query 读不出 region 的坐标。我用 design_visual_review 生成的 SVG 解析它的 polygon，得到 4 个点，x 4755 到 5755，y 1735 到 3759。
- 也就是说它盖住整块板的下半部分，上边在绝对 y=3759，即板相对 (3759−1735)/39.37 = 51.4mm。
- 推断：你在 AD 里看到的白色虚线很可能就是这个 board_cutout 的上边（旧板顶边）。这是我的推断，没有在 AD 画面里直接验证。
- 注意：SVG 里这个 polygon 的坐标是渲染器画出来的，不是 obj_query 读回的。
- 另一个相关现象：Top Layer 的铜区被分成 y 1735 到 1884 和 y 1979 到 6007 两块，也是 SVG 读出的。

**1. 截图**
- app_screenshot 失败：`screen capture needs pywin32 and Pillow`，本机缺这两个库。
- design_visual_review(target=pcb) 只出了 SVG，PNG 失败，原因是 "browser produced no PNG"。
- 我改用 Chrome DevTools 把 SVG 转成 PNG，文件在 E:\<项目根>\电路控制\temp\eda_check\：
  - board_full.svg，整板 SVG。
  - board_full.png，整板图，是根据设计数据重画的 SVG，不是 AD 窗口截图。图中没有看到横穿全板的白色虚线，但这张图本来就不画 board_cutout 的边线。
  - board_y51p4_zoom.png，放大图，viewBox 取错了，图上基本只有 y≈3600 到 3900 一小段，不可用。
  - _full.svg、_zoom.svg 是中间文件，_prof 是浏览器配置目录，可删。
- 整个板区没有出现 AD 窗口里那条虚线，所以无法用图验证。

**2. 逐类对象（绝对 y 3755 到 3762、横向跨度大于 500 mil）**

| 类型 | 查了什么 | 结果 |
|---|---|---|
| Track | 1230 条，层分布：Mechanical13 494、Mechanical15 376、TopLayer 210、TopOverlay 130、BottomLayer 11、MidLayer2 5、Mechanical1 4 | 没有满足条件的 |
| Arc | 24 条，半径最大 40mil | 没有 |
| Fill | 7 个，都在 TopSolder/BottomSolder，板相对 y 在 0.93 到 9.07mm、27.6 到 35.8mm、3 到 7mm、29.7 到 33.7mm | 没有 |
| Region | 54 个（Mechanical15 共 25 个，TopLayer 7、TopPaste 10、TopOverlay 4、TopSolder 4、MidLayer1 / MidLayer2 / BottomLayer 各 1、MultiLayer 1） | 只有上面那个 board_cutout 满足条件，其余都是小块 |
| Polygon | 4 个 GND 铺铜，各 4 个顶点，面积 4272000 sqmil，覆盖整板 | 范围是整板，没有单独的分割边 |
| ComponentBody | 50 个（Mechanical13 40、Mechanical1 10） | 只能读到中心点，读不到尺寸。中心点 y 最近的是 3753.67（Mechanical13），不在 3755 到 3762 内 |
| Dimension | 0 个 | 无 |
| Room | 房间规则 0 条，没有 room 对象类型 | 无 |
| Coordinate、Embedded board | obj_query 不支持这两种类型 | 没法查 |

- 说明：Region 的 SVG 解析是对所有层做的，其中 BottomLayer / MidLayer1 / MidLayer2 的整板矩形是铺铜多边形，不是横线。

**3. Board Shape 与分割线**
- pcb_get_board_outline：4 个顶点的矩形，(4755,1735)、(5755,1735)、(5755,6007)、(4755,6007)，closed:true。即 1000 x 4272 mil。
- tool_guide 问 "board region split line layer stack region board planning mode"，没有对应工具，not_possible 为空。
- proj_get_board_info：origin (4755,1735)，层为 Top Layer、GND2、GND3、Bottom Layer。
- Board Planning Mode 的分割线没有工具能读，**没找到**。

## C 转文字方向、隐藏位号
**1. tool_guide 四次提问的结果**
- 问 "rotate a PCB text / string object"、"rotate a component designator text"、"hide a component designator (NameOn) without pcb_set_text_visibility"、"set designator autoposition"，四次都没有匹配的专用推荐，not_possible 全是空列表。
- 每次返回的只是不相关的配方，加上一份 derived 工具名清单，没有一个是对症的：
  - 旋转文字和旋转位号：derived 里是 audit_find_mirrored_pcb_text、pcb_place_text、pcb_set_text_visibility、pcb_set_text_style、pcb_delete_object、lib_add_footprint_text。
  - 隐藏位号：derived 里是 pcb_set_text_visibility、pcb_set_text_style、pcb_set_layer_visibility、pcb_copy_designators_to_mech。
  - Autoposition：derived 里是 audit_find_mixed_designator_rotation、lib_fix_designators、lib_probe_designator 等库类工具，没有板上 Autoposition 的读写。
- 每次都带着同一条警告：obj_modify 在 PCB 元件上改位号文字会让 Altium 崩溃，要改位号只能走 proj_annotate。

**2. 试验结果**
- 文字旋转（自由文字 ADJ）：
  - 原值：X 5388.307、Y 4428.709、Rotation 0、Height 39.37、Width 6.299、Layer TopOverlay。
  - 换算成板相对约 (633.3, 2693.7) mil，即 (16.09, 68.42) mm，和你给的 (16.086, 68.421) 一致。
  - 我调用 obj_modify(eTextObject, filter Text=ADJ, set Rotation=90)，返回 `success:false`，properties.unknown=["Rotation"]，原因是 "this build does not write" 这个属性。
  - 读回仍是 Rotation 0，所有值与原值一致。**没写进去，也就不用改回。**
- 位号旋转（F101 位号）：
  - 原值：Text F101、X 5136.89、Y 5764.3、Rotation 0、Height 39.37、Width 6.299、Layer TopOverlay、IsDesignator true、MirrorFlag false。
  - 同样的 obj_modify 返回 unknown=["Rotation"]，读回仍是 Rotation 0。**没写进去。**
- 隐藏 / 显示位号：
  - obj_query 的属性表里没有 NameOn，直接查询报 "Not a PCB property: NameOn, NameAutoPosition, CommentOn"。
  - pcb_get_components 的返回里也没有位号可见性字段。
  - 唯一的批量可见性工具是被你禁用的 pcb_set_text_visibility，所以**没有试，也没有别的办法**。
- Autoposition：obj_query 同样不认 NameAutoPosition，没有工具能读，**没读到**。
- 以上各项没有任何修改被写入。

推断：这个 eda-agent 构建没有任何接口能改 PCB 文字的旋转角度，也读写不了位号的显示开关和 Autoposition。

**3. 已修改未保存的文档**
- proj_get_compile_freshness 返回 dirty_doc_count 1，dirty_docs 为 [E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc]。open_doc_count 1。
- 推断：这个 dirty 状态不是我造成的，因为我所有修改都失败了，pcb_focus_board 和各查询也不改设计；它应该是你之前的修改或导入留下的。我没有保存。

**说明**
- 备份 E:\Altium_designer\备份\QPA2609_20261020_2017_本机导入后 我没有去检查是否存在，因为本次没有任何写入。
- obj_query 和 obj_count 的 filter 只支持 `名字=值` 精确匹配，不支持数值范围，所以范围筛选都是把全量结果保存成文件后用 Python 在本地做的。
- design_visual_review 和 pcb_get_components 的返回被存成了临时文件，本次汇报没有引用其路径。
~~~

**主会话怎么处理 / 学到什么**

- 写法：A 只读、B 只读（列出要查的每一类对象和坐标范围，"没找到就写没找到，不要猜"）、C 先问 tool_guide 再拿**一个**对象试、改回、读回确认和原值一致。
- 汇报里 B 项说"找到一个横穿全板的 board_cutout（挖空区）"。如果属实，板厂会把整个射频部分铣掉。**主会话没有直接采信**：用 olefile 解析 PcbDoc 的 `BoardRegions`，确认是 10-15 原始文件里就有的"板区域"（Layer Stack Region），只是没跟着板框改，`ISBOARDCUTOUT=TRUE` 是这类记录的常态。
- A 项：工具说 39 条规则全 enabled（包括 descriptor 写着 Disabled 的）→ 主会话改用 DRC 报告里有没有 "(Disabled)" 来判断。
- C 项：转文字返回 `unknown=["Rotation"]`，没写进去；子代理如实说明"没写进去，也就不用改回"。
- 子代理报告"文档变成已修改"，并推断不是自己造成的——主会话把这类推断当成待查，后来决定"不保存，有备份"。

---

## 4　导出 Top Overlay 全部文字（Haiku）

纯导出，选 **Haiku**。任务里写"不要做分析或建议"。

**主会话 → 子代理（新派）**

~~~text
任务（只读）：把 QPA2609 板上 **Top Overlay 层的全部文字对象**导出成一个 CSV 文件。不准修改、不准保存、不准跑 DRC / doctor，不准调用 pcb_set_text_visibility，不准对文字调用 obj_modify。

工程已在 AD 里打开：E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb，PCB 是 E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc。

步骤：
1. ToolSearch 加载 mcp__eda-agent__tool_catalog 和 mcp__eda-agent__tool_invoke（其它工具都通过 tool_invoke 调）。
2. app_ping（不通就运行 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\Altium_designer\auto_MCP\Connect_Altium.ps1"）。
3. 确认活动文档是 PCB1_no3d.PcbDoc；不是就调 pcb_focus_board，参数名是 board_path，路径原样传（单反斜杠）。
4. 用 obj_query 查 eTextObject，过滤 Layer=TopOverlay，读这些属性（读不到的留空，不要编）：Text、X、Y、Rotation、Height、Width、IsDesignator、IsComment、MirrorFlag，以及能表明它属于哪个元件的属性（例如 Component / OwnerDesignator / InComponent，先用 tool_guide 或 obj_query 的属性表查有哪些可用）。注意文字 ".Designator"、".Comment" 这种以点开头的是特殊字符串，原样记录 Text 字段，同时如果工具能给出它显示出来的实际文字（例如 ConvertedString / DisplayString），也一起读。
5. 把结果写成 CSV：E:\<项目根>\电路控制\temp\eda_check\top_overlay_texts.csv（UTF-8，第一行表头）。坐标保持工具返回的原始 mil 值，不要换算。
6. 同样再导出一次 Mechanical13 层的全部 eTextObject 到 E:\<项目根>\电路控制\temp\eda_check\mech13_texts.csv（同样字段）。

汇报：第一行 成功 / 部分完成 / 失败；两个 CSV 的路径和行数；Top Overlay 上按 Text 内容分组的数量（例如 ".Designator" 多少个、"REFDES" 多少个、普通位号多少个）；工具报错原文。不要做分析或建议。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
成功

连接状态: app_ping 通过 (mcp_server 0.7.1, Altium 23.1.1.15, 脚本版本匹配), 没有运行 Connect_Altium.ps1。
当前工程: QPA2609_test.PrjPcb (E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb)。
活动文档: PCB1_no3d.PcbDoc (E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc), 与任务一致, 没有调用 pcb_focus_board。
注意: app_get_active_document 返回 modified=true, 本次没有保存, 也没有改任何对象。

输出文件:
1. E:\<项目根>\电路控制\temp\eda_check\top_overlay_texts.csv
   数据行 120 (文件共 121 行, 含表头), obj_query 返回 count=120。
   查询: eTextObject, filter Layer=TopOverlay, scope active_doc。
   列: Text,X,Y,Rotation,Height,Width,IsDesignator,IsComment,MirrorFlag,Layer,Component
   坐标为工具返回的原始 mil 值, 未换算。
2. E:\<项目根>\电路控制\temp\eda_check\mech13_texts.csv
   数据行 65 (文件共 66 行, 含表头), obj_query 返回 count=65。
   查询: eTextObject, filter Layer=Mechanical13, 同样字段。

Top Overlay 按 Text 分组 (120 行):
- 字面 ".Designator": 0 个。字面 ".Comment": 0 个。
- Text 为 "*": 4 个 (U103, U102, U101, U1 元件上各 1 个)。
- Text 为 "REFDES": 2 个 (U102 上 1 个, F101 上 1 个)。
- Text 为 "RefDes": 2 个 (U102 上 1 个, F101 上 1 个)。
- 其余为实际位号或注释文字, 例如 "GND" 5 个, "10uF" 7 个, "142-0761-851" 4 个, "100k" 4 个。
- IsDesignator=true: 17 个; IsComment=true: 62 个; 两个标志都为 false: 41 个。
- 普通位号 (两标志都为 false 且 Text 与 Component 相同): 14 个 (U103, U102, U101, RV101, Q102, Q101, LED101, FB102, FB101, D101, J1, J7, J2, J8)。
- 符合 ^[A-Za-z]+[0-9]+$ 的 Text 共 39 个 (含 IsDesignator=true 的)。

Mechanical13 (65 行):
- Text "*": 4 个; "RefDes2": 2 个 (U102, F101 元件上各 1 个); 没有 "REFDES"、"RefDes" (注意大小写差别仅在 Top Overlay 上出现)。
- IsDesignator=true: 45 个; IsComment=true: 0 个。
- Text 与 Component 相同: 59 个; Text 匹配 ^[A-Za-z]+[0-9]+$: 61 个。

工具限制 (事实):
- obj_query 对 eTextObject 不支持 ConvertedString / DisplayString / UnderlyingString 属性, 返回错误: "Not a PCB property: ConvertedString, DisplayString, UnderlyingString"。因此 CSV 里只有原始 Text 字段, 没有显示出来的实际文字。
- 可用属性列表以错误信息为准 (含 Text, Designator, Comment, Component, InComponent, IsDesignator, IsComment, MirrorFlag, Rotation, Height, Width, Layer 等)。Component 列即用于标识所属元件, 空值表示不属于元件。
- tool_guide 不接受 query 参数 (报错原文: "register_guidance_tools.<locals>.tool_guide() got an unexpected keyword argument 'query'"), 无参调用正常。

没有做的事: 没有保存, 没有 DRC/doctor, 没有 pcb_set_text_visibility, 没有 obj_modify, 没有修改任何对象。
~~~

**主会话怎么处理 / 学到什么**

- 汇报说字面 `.Designator` 为 0 个——因为 `obj_query` 读出的是显示后的文字（`U101`），不是 `.Designator`。主会话从"Text 和 Component 相同但 IsDesignator=false"这一组识别出它们就是封装自带的特殊字符串，再用文件解析确认。
- 主会话用这份表 + 直接读 PcbDoc 的 `Components6`（`COMMENTON` 全 FALSE）得出：注释都是隐藏的，不会印；问题出在 13 个封装文字上。

---

## 5　导出焊盘、丝印线、弧（Haiku）

给主会话排丝印用的障碍物数据，选 **Haiku**。

**主会话 → 子代理（新派）**

~~~text
任务（只读）：从 AD 里已打开的 QPA2609 板导出三张 CSV。不准修改、不准保存、不准跑 DRC / doctor，不准调用 pcb_set_text_visibility 或 obj_modify。

工程：E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb；PCB：E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc。

步骤：
1. ToolSearch 加载 mcp__eda-agent__tool_catalog 和 mcp__eda-agent__tool_invoke（其它工具都通过 tool_invoke 调）。
2. app_ping（不通就运行 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\Altium_designer\auto_MCP\Connect_Altium.ps1"）。确认活动文档是 PCB1_no3d.PcbDoc，不是就调 pcb_focus_board（参数名 board_path，单反斜杠路径）。
3. 用 obj_query 导出（读不到的属性留空，不要编；先用一次小查询确认属性名能用）：
   a. ePadObject 全部焊盘 → E:\<项目根>\电路控制\temp\eda_check\pads.csv，列：Component（或能表明所属元件的属性）, Name, X, Y, TopXSize, TopYSize, TopShape, Rotation, Layer, HoleSize, Net（属性名可能是 Net 或 NetName）。预期约 178 行。
   b. eTrackObject，过滤 Layer=TopOverlay → E:\<项目根>\电路控制\temp\eda_check\overlay_tracks.csv，列：X1, Y1, X2, Y2, Width, Component。预期约 130 行。
   c. eArcObject，过滤 Layer=TopOverlay → E:\<项目根>\电路控制\temp\eda_check\overlay_arcs.csv，列：XCenter, YCenter, Radius, StartAngle, EndAngle, Width, Component。
   坐标保持工具返回的原始 mil 值。
4. CSV 用 UTF-8，第一行表头。

汇报：第一行 成功 / 部分完成 / 失败；三个文件路径和行数；哪些属性读不到（报错原文）。不要分析。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
成功

连接状态: app_ping 通过 (Altium 23.1.1.15, 桥正常, 未重连)。
当前工程: E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb (29 个文档)。
活动文档: PCB1_no3d.PcbDoc (app_get_active_document 读回 file_path E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc, modified=true)。无需调用 pcb_focus_board。
全程只读: 只调用了 app_ping / proj_get_focused / proj_list_documents / app_get_active_document / tool_catalog / tool_guide / obj_query。没有保存、没有修改、没有跑 DRC / doctor, 没有调用 pcb_set_text_visibility 或 obj_modify。

输出文件 (UTF-8, 第一行表头, 目录 E:\<项目根>\电路控制\temp\eda_check 已建):
1. E:\<项目根>\电路控制\temp\eda_check\pads.csv
   列: Component,Name,X,Y,TopXSize,TopYSize,TopShape,Rotation,Layer,HoleSize,Net
   行数: 179 行 (表头 1 + 数据 178), 与 obj_query 返回的 count=178 一致。
   属性: Name, X, Y, TopXSize, TopYSize, TopShape, Rotation, Layer, HoleSize, Net, Component 全部可读, 没有报错。Net 为空的焊盘 (如 U103 pin5、U102 pin7、U101 pin8/9) 保留为空。
2. E:\<项目根>\电路控制\temp\eda_check\overlay_tracks.csv
   列: X1,Y1,X2,Y2,Width,Component
   行数: 131 行 (表头 1 + 数据 130), 与 count=130 一致。过滤条件 Layer=TopOverlay。
3. E:\<项目根>\电路控制\temp\eda_check\overlay_arcs.csv
   列: XCenter,YCenter,Radius,StartAngle,EndAngle,Width,Component
   行数: 13 行 (表头 1 + 数据 12), 与 count=12 一致。过滤条件 Layer=TopOverlay。

读不到的属性: 无。所有请求的属性都返回了值, 没有报错。

注意 (事实, 需要知道):
- 三个 CSV 不是由脚本直接从 Altium 写出的, 而是把 obj_query 返回的 JSON 原样抄成 CSV (用 Write 写入)。行数已核对, 数值没有逐条复核。如果后面要拿这些数做判断, 建议抽几行对照 Altium 或重新查询。
- 坐标保持工具返回的原始 mil 值。
- overlay_tracks.csv 和 overlay_arcs.csv 里的 Layer 列没有写入 (按说明的列清单省略, 过滤已在查询时用 Layer=TopOverlay 完成)。
- pads.csv 中 Component 列为焊盘所属元件位号 (由 Component 属性读取)。
~~~

**主会话怎么处理 / 学到什么**

- Haiku 主动说明"CSV 是把查询结果手抄进去的，数值没有逐条复核"。主会话没有直接用：丝印线和弧从 PcbDoc 直接解析，和它的表逐条比对（130 / 12 条全部对上）；焊盘拿 DRC 报告里的焊盘坐标抽查（84 / 88 一致，另外 4 个是同名焊盘配错，不是数据错）。
- **学到的**：便宜模型导出的数据，能从文件直接读的就自己读一遍对比；不能的就找第二个来源抽查。

---

## 6　第一段修改：删替身、改名、放字、保存、关工程（Sonnet，中途停下来问）

要修改，选 **Sonnet**。任务里每个删除都先"确认正好 1 个 + 特征对得上"，**任何一行不满足就整步停下，一个都不删**。

**主会话 → 子代理（新派）**

~~~text
任务：QPA2609 第三轮丝印修改的第一步（在 AD 里改，**允许修改和保存**，但只准做下面列出的操作）。

工程：E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb（已在 AD 里打开）；PCB：E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc。
备份已存在：E:\Altium_designer\备份\QPA2609_20261020_2017_本机导入后（不用再备份）。
禁止：跑 DRC、跑 doctor、调用 pcb_set_text_visibility、改任何元件位号文字（IsDesignator=true 的文字）、改除下面以外的任何对象、关闭 Altium_API.PrjScr。

开始：ToolSearch 加载 mcp__eda-agent__tool_catalog 和 mcp__eda-agent__tool_invoke；app_ping（不通就运行 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\Altium_designer\auto_MCP\Connect_Altium.ps1"）；确认活动文档是 PCB1_no3d.PcbDoc（不是就 pcb_focus_board，参数名 board_path，单反斜杠路径）。

## 第 1 步：删除 8 个普通文字（Top Overlay 上的"替身"，不属于任何元件）
**注意：Mechanical13 层上同一坐标有同名的真位号，绝对不能删。每个过滤条件都必须带 Layer=TopOverlay。**
对下面每一行，先用 obj_query eTextObject 过滤 Layer=TopOverlay、Text=<文字>，读 X、Y、IsDesignator、Component，确认**正好 1 个**、坐标与表中差 < 0.01 mil、IsDesignator=false、Component 为空；任何一行不满足就整步停下汇报，一个都不删。
| Text | X (mil) | Y (mil) |
|---|---|---|
| R111 | 5357.362 | 4339.3 |
| R116 | 5373.11 | 3849.142 |
| P101 | 4774.685 | 5947.567 |
| RV101 | 5213.583 | 4427.213 |
| D101 | 5380.984 | 5910.008 |
| U103 | 5082.795 | 3857.016 |
| U101 | 5129.961 | 5207.922 |
| U102 | 5089.528 | 4827.252 |
8 行都确认后，用 obj_batch_delete（或 obj_delete）删除，过滤条件用 ObjectType=eTextObject + Layer=TopOverlay + Text + X + Y（精确值）。
删完核对：Top Overlay 上 Text 为这 8 个名字的文字数 = 0；Mechanical13 上 IsDesignator=true 且 Text 为这 8 个名字的文字仍然各 1 个（共 8 个）。

## 第 2 步：把普通文字 "QPA2609 MODULE" 的内容改成 "QPA2609"
obj_query 确认 Layer=TopOverlay、Text="QPA2609 MODULE" 正好 1 个，然后 obj_modify 只改 Text 属性为 QPA2609（不改坐标、角度）。读回确认。

## 第 3 步：新放一个普通文字 "MODULE"
用 pcb_place_text（先看 tool_guide 的参数），文字 MODULE，层 Top Overlay，X=5460，Y=5392（mil），旋转 90，字高 39.37 mil（只收整数就填 39），线宽 6.299 mil（能设就设）。放完读回它的 X、Y、Rotation、Height、Width、Layer、Component 并汇报。坐标有小偏差不用修，后面会处理。

## 第 4 步：保存并关闭工程
1. app_save_all，读回 still_dirty 必须是 0。
2. 关闭 QPA2609_test.PrjPcb 这个工程（用 tool_guide 找关闭工程 / 文档的工具，例如 proj_close 或 app_close_document）。如果弹出"是否保存"等对话框：停下，汇报对话框标题和按钮原文，不要点。
3. 读 proj_list_open 确认 QPA2609_test.PrjPcb 已不在打开列表里，Altium_API.PrjScr 还在。

汇报：第一行 成功 / 部分完成 / 失败；每步工具读回的原始值；任何报错原文。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
失败（第 1 步校验未通过，按你的规定整步停下。我没有删除、修改、放置、保存或关闭任何东西）。

连接和文档：
- app_ping 通，Altium 23.1.1.15，脚本版本 2026.10.18.17。
- proj_get_focused 返回 QPA2609_test.PrjPcb，路径 E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb，document_count 29。
- obj_get_document_info 显示活动文档是 E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc，所以不需要 pcb_focus_board。
- proj_list_open 返回 Free Documents、PCB_Project.PrjPcb、Altium_API.PrjScr、QPA2609_test.PrjPcb。

查询方法：obj_query 的 filter 里用逗号写多个条件会返回 0 个，写 Layer=TopOverlay|Text=XXX 才有效（竖线是"并且"）。

停下的原因：8 个目标里有 4 个，在 Layer=TopOverlay 加 Text 的过滤下返回 2 个，不是你要求的"正好 1 个"。多出来的那个是属于元件的真位号，它就在 Top Overlay 上，不在 Mechanical13。

| Text | 查询结果 |
|---|---|
| R111 | 1 个：X=5357.362, Y=4339.3, IsDesignator=false, Component 空。符合。 |
| R116 | 1 个：X=5373.11, Y=3849.142, IsDesignator=false, Component 空。符合。 |
| P101 | 1 个：X=4774.685, Y=5947.567, IsDesignator=false, Component 空。符合。 |
| U102 | 1 个：X=5089.528, Y=4827.252, IsDesignator=false, Component 空。符合。 |
| RV101 | 2 个。第 1 个 X=5213.583, Y=4427.213, IsDesignator=false, Component 空（目标）。第 2 个 X=5434.732, Y=4604.989, IsDesignator=false, Component=RV101。 |
| D101 | 2 个。第 1 个 X=5380.984, Y=5910.008, IsDesignator=false, Component 空（目标）。第 2 个 X=5472.913, Y=5652.587, IsDesignator=false, Component=D101。 |
| U103 | 2 个。第 1 个 X=5082.795, Y=3857.016, IsDesignator=false, Component 空（目标）。第 2 个 X=5155.197, Y=4061.445, IsDesignator=false, Component=U103。 |
| U101 | 2 个。第 1 个 X=5129.961, Y=5207.922, IsDesignator=false, Component 空（目标）。第 2 个 X=5197.323, Y=5239.201, IsDesignator=false, Component=U101。 |

补充观察：
- 之前不带 Layer 过滤查 Text=R111，返回 2 个：TopOverlay 的替身，和 Mechanical13 上 X/Y 相同、IsDesignator=true、Component=R111 的真位号。
- 那 4 个多出来的 TopOverlay 对象 Component 非空，坐标也和目标不同。IsDesignator 读回是 false，但 Component 非空，我推断它们是元件自带的位号文字，可能是库里用的不同写法（推断，没有进一步核实）。
- 我推断，用 Layer+Text+X+Y 的精确过滤，只会命中那 8 个替身，不会碰到这 4 个。但这和"Top Overlay 上这 8 个名字的文字数删完等于 0"的核对条件冲突：删完后 Top Overlay 上仍会剩 4 个带 Component 的同名文字。

需要你确认两点：
1. 4 个带 Component 的 TopOverlay 同名文字要保留，只删 Component 为空的 8 个，对吗？
2. 删完后的核对标准要改成"Top Overlay 上 Component 为空的这 8 个名字的文字数 = 0"，对吗？

第 2 步（QPA2609 MODULE 改名）和第 3 步（放 MODULE）我也没动。已知信息：
- QPA2609 MODULE 在 TopOverlay 上能查到，X=5032.559, Y=4402.292, IsDesignator=false, Component 空，我只看到这 1 个（先 limit=3 取前 3 个，没带 Text 过滤）。
- pcb_place_text 的参数是 text、x、y（整数）、layer（默认 TopOverlay）、height、rotation、stroke。

要继续的话，请确认上面两点。确认后我从第 1 步重新做。没有弹出对话框，也没有报错。
~~~

**主会话 → 同一个子代理（SendMessage 续派）**

~~~text
两点都确认，请从第 1 步重新做完第 1～4 步（还是 Sonnet，规则不变）。
1. 对：那 4 个 Component 非空的同名文字（RV101 5434.732/4604.989、D101 5472.913/5652.587、U103 5155.197/4061.445、U101 5197.323/5239.201）是封装自带的 .Designator 特殊字符串，要保留，本步不碰（下一步由主会话离线处理）。只删 Component 为空的 8 个，过滤用 ObjectType=eTextObject + Layer=TopOverlay + Text + X + Y 精确值（多条件用竖线 | 连接）。删之前的校验改成：Layer=TopOverlay、Text=<名字> 且 Component 为空、坐标对得上的正好 1 个。
2. 对：删完的核对标准改成"Top Overlay 上 Component 为空、Text 为这 8 个名字的文字数 = 0"；另外核对那 4 个 Component 非空的同名文字仍各 1 个、Mechanical13 上 8 个真位号仍各 1 个。
第 2、3、4 步按原说明做。汇报格式同前。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
成功（4 步全部完成）。

连接和文档：app_ping 通。活动文档是 E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc，不需要 pcb_focus_board。

方法说明：我把 obj_batch_delete 换成了逐个 obj_delete，因为我没有它 operations 参数的格式。每次删除前后的数量都核对过。

第 1 步：删除 8 个 Component 为空的 TopOverlay 普通文字
- 删前校验：8 条过滤（Layer=TopOverlay|Text|X|Y 的精确值）的 obj_count 都返回 1。这 8 个对象上一轮已读到 IsDesignator=false、Component 为空，坐标和你给的表一致，差值为 0。
- 8 次 obj_delete 全部 matched=1、success=true、failed_count=0。
- 删后按 Text 不限层重查，结果如下：
  - R111、R116、P101、U102：各只剩 1 个，在 Mechanical13，IsDesignator=true，Component 等于自己的名字，坐标就是原表坐标。
  - RV101 剩 3 个：
    - TopOverlay (5434.732, 4604.989)，Component=RV101，IsDesignator=false（保留的那个）。
    - Mechanical13 (5434.732, 4604.989)，Component=RV101，IsDesignator=false。
    - Mechanical13 (5213.583, 4427.213)，IsDesignator=true，Component=RV101（真位号）。
  - D101 剩 3 个：
    - TopOverlay (5472.913, 5652.587)，Component=D101，IsDesignator=false（保留的那个）。
    - Mechanical13 (5472.913, 5652.587)，Component=D101，IsDesignator=false。
    - Mechanical13 (5380.984, 5910.008)，IsDesignator=true，Component=D101（真位号）。
  - U103 剩 3 个：
    - TopOverlay (5155.197, 4061.445)，Component=U103，IsDesignator=false（保留的那个）。
    - Mechanical13 (5155.197, 4061.445)，Component=U103，IsDesignator=false。
    - Mechanical13 (5082.795, 3857.016)，IsDesignator=true，Component=U103（真位号）。
  - U101 剩 3 个：
    - TopOverlay (5197.323, 5239.201)，Component=U101，IsDesignator=false（保留的那个）。
    - Mechanical13 (5197.323, 5239.201)，Component=U101，IsDesignator=false。
    - Mechanical13 (5129.961, 5207.922)，IsDesignator=true，Component=U101（真位号）。
- 结论：
  - TopOverlay 上 Component 为空的这 8 个名字的文字数为 0。
  - Mechanical13 上 IsDesignator=true 的 8 个真位号各剩 1 个。
  - 4 个 Component 非空的 TopOverlay 同名文字各剩 1 个。
  - 另外发现 Mechanical13 上还有 3 个 IsDesignator=false 的同名文字（RV101、D101、U103、U101 里各有一个，实际是 4 个，坐标同上，Component 非空）。这是我多读到的，没动，供你下一步参考。

第 2 步：改 "QPA2609 MODULE" 的内容
- 改前，obj_count 过滤 Layer=TopOverlay|Text=QPA2609 MODULE 返回 1。
- obj_modify set "Text=QPA2609"，matched=1、success=true。
- 读回：Text=QPA2609，X=5032.559，Y=4402.292，Layer=TopOverlay，Rotation=90，Height=39.37，Width=6.299，Component 为空。坐标和角度没变，改前坐标是 5032.559 / 4402.292，和这次读回一致。

第 3 步：放 MODULE
- pcb_place_text 参数：text=MODULE，x=5460，y=5392，layer=TopOverlay，height=39.37，rotation=90，stroke=6.299。返回 placed=true。
- obj_query 读回：Text=MODULE，X=5460，Y=5392，Layer=TopOverlay，Rotation=90，Height=39.37，Width=6.299，Component 为空，IsDesignator=false，共 1 个。没有偏差。

第 4 步：保存并关闭
- app_save_all 返回 saved=true，documents_attempted=3，documents_written=3，still_dirty=0。
- proj_close（project_path 为 QPA2609_test.PrjPcb，save=false）返回 success=true、closed=true、saved=false。
  - 没有弹对话框。
  - 返回里的 "discarded" 列出了 PCB1_no3d.PcbDoc 和 QPA2609_test.PrjPcb。我推断这只是表示它们被关闭了，因为前一步已经保存且 still_dirty=0（推断，没有重新打开磁盘文件验证）。
  - 活动文档被切到了 E:\Users\Public\Documents\Altium\PCB_Project\QFN65P500X500X100-25N-D.PcbLib。
- proj_list_open 读回：Free Documents、PCB_Project.PrjPcb、Altium_API.PrjScr。QPA2609_test.PrjPcb 已不在列表里，Altium_API.PrjScr 还在。

没做的事：没跑 DRC 和 doctor，没动任何位号文字，也没动除上述以外的任何对象。
~~~

**主会话怎么处理 / 学到什么**

- 子代理发现 4 个名字（RV101、D101、U103、U101）在 Top Overlay 上有 2 个，多出来的属于元件——按规矩整步停下，提了两个确认问题。
- 主会话判断：多出来的是封装自带的 `.Designator`（显示成位号），正是下一步要离线挪走的 13 个之一；用 **SendMessage 续派同一个子代理**，确认"只删 Component 为空的 8 个、过滤带 Layer+Text+X+Y、核对标准改成……"。续派的说明只有几行，因为它记得上下文。
- 完成后它又报告"Mechanical13 上也各有一份同名封装文字"——是装配层的，不印，主会话确认不用管。
- **学到的**：过滤条件必须带层；任务里写"预期会看到什么"，子代理才能发现意外并停下。

---

## 7　重开读回：发现离线修改有 21 条没生效，停下没保存

主会话离线改完 PcbDoc 后派 **Sonnet**：打开 → 按期望清单 CSV 逐行比对 → DRC → 关规则 → 保存。说明里写"**任何一项不符就停下汇报，不做后面的步骤，不保存**"。

**主会话 → 子代理（新派）**

~~~text
任务：QPA2609 第三轮的核对和 DRC（主会话已经离线改好了 PCB 文件，你负责在 AD 里打开、读回核对、跑两次 DRC、关两条丝印规则、保存）。**允许的修改只有：第 5 步关两条丝印规则、第 7 步保存。** 其它对象一律不改。禁止：跑 doctor、调用 pcb_set_text_visibility、对文字用 obj_modify、关闭 Altium_API.PrjScr。

工程：E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb（现在是关着的）；PCB：E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc。
输出文件夹：E:\<项目根>\电路控制\temp\round3\（已存在）。

开始：ToolSearch 加载 mcp__eda-agent__tool_catalog、mcp__eda-agent__tool_invoke；app_ping（不通就运行 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\Altium_designer\auto_MCP\Connect_Altium.ps1"）。obj_query 的多条件过滤用竖线 | 连接。

## 1 打开
proj_open 打开工程 → proj_load_sheets → pcb_focus_board（参数 board_path）聚焦 PCB1_no3d.PcbDoc。打开时如果弹对话框（例如文件被修改、需要修复），停下汇报标题和按钮原文，不要点。读 app_get_active_document 的 modified 状态并汇报。

## 2 读回文字
1. obj_query eTextObject 过滤 Layer=TopOverlay，读 Text、X、Y、Rotation、Height、Width、IsDesignator、IsComment、Component。把全部结果写成 CSV：E:\<项目根>\电路控制\temp\round3\readback_top_overlay.csv（用脚本或逐条写都行，写完核对行数等于 count）。
2. 对照期望文件 E:\<项目根>\电路控制\temp\round3\expected_readback.csv（22 行）：每一行在读回结果里找 Text 相同、|X 差|<0.01、|Y 差|<0.01 的对象，Rotation、Height、Width（差<0.01）、IsDesignator 都要一致。逐行报告 OK / 不一致（给读回值）。
3. 再报告：读回里 IsDesignator=false、IsComment=false、Text 不是 "*"、且 Component 属于 {FB101, FB102, LED101, Q101, Q102, U101, U103, D101, RV101, F101, U102} 的文字有几个、是哪些（预期 0）。
4. 读 pcb_get_board_statistics（元件、过孔、焊盘、铺铜、未连接数，预期 62 / 783 / 178 / 4 / 0）和 pcb_get_board_outline。

## 3 板形图
调用 design_visual_review（target=pcb）生成整板 SVG，把 SVG 文件复制到 E:\<项目根>\电路控制\temp\round3\board_after.svg（PNG 失败没关系）。汇报原文件路径。

## 4 第一次 DRC（丝印规则开着）
先用 pcb_get_design_rules 读 SilkToSolderMaskClearance、SilkToSilkClearance 两条规则的 enabled 和 descriptor 原文。然后 pcb_run_drc(allow_modal=true)，再 app_press_dialog_button 按 "运行DRC (&R)..." 那个按钮（用 app_list_open_dialogs 看按钮原文）。等报告文件 E:\Altium_designer\QPA2609\projects\QPA2609_test\Project Outputs for QPA2609_test\Design Rule Check - PCB1_no3d.drc 的修改时间更新后，把它复制成 E:\<项目根>\电路控制\temp\round3\drc_silk_on.drc。汇报报告里每条规则的 "Rule Violations" 数。

## 5 关两条丝印规则
用 pcb_set_rules_enabled（先看 tool_guide 参数）把 SilkToSolderMaskClearance 和 SilkToSilkClearance 两条规则关掉（只这两条）。读回两条规则的 enabled 和 descriptor 原文。

## 6 第二次 DRC
同第 4 步再跑一次，等报告更新后复制成 E:\<项目根>\电路控制\temp\round3\drc_silk_off.drc。汇报每条规则的违规数，并明确说报告里还有没有 "Silk To Solder Mask" 和 "Silk to Silk" 这两节。

## 7 保存
app_save_all，still_dirty 必须是 0。工程保持打开。

汇报：第一行 成功 / 部分完成 / 失败；按 1～7 给读回的原始值；报错原文；推断单独标明。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
部分完成：步骤 1、2 做完，读回和期望对不上，我在这里停下，没做步骤 3 到 7。没改过任何东西，没保存，没跑 DRC，没关规则。

**步骤 1 打开**
- app_ping 通，AD 23.1.1.15，脚本版本 2026.10.18.17。
- proj_open 成功，返回 focused:false。
- proj_load_sheets 返回 total 1、already_loaded 1。
- pcb_focus_board 成功，当前文档是 E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc。
- 打开过程中没有对话框（app_list_open_dialogs 返回 dialog_count 0）。
- app_get_active_document 返回 modified:false。
- 桥脚本工程 Altium_API.PrjScr 保持打开。

**步骤 2 读回文字**
- 文件：E:\<项目根>\电路控制\temp\round3\readback_top_overlay.csv。obj_query 的 count 是 113，我用脚本数 CSV 也是 113 行。
- 对照期望文件 expected_readback.csv，22 行里 12 行 OK，10 行不一致。
  - OK：TP103、F101、QPA2609、+3.5V、+12V、ADJ、GND（3 处）、NEG、-5V、VG、VD、MODULE。
  - 不一致（期望 X、Y、Rotation、IsDesignator=true）：
    - RV101 期望 (5213.583, 4419.339, 0)。读回只有一个 Text=RV101，在 (5434.732, 4604.989)，旋转 180，Height 50，Width 3，IsDesignator=false。
    - D101 期望 (5380.984, 5913.945, 0)。读回 (5472.913, 5652.587)，旋转 90，Height 50，Width 3，IsDesignator=false。
    - U103 期望 (5074.921, 3857.016, 90)。读回 (5155.197, 4061.445)，旋转 270，Height 50，Width 3，IsDesignator=false。
    - U101 期望 (5129.961, 5203.985, 0)。读回 (5197.323, 5239.201)，旋转 90，Height 50，Width 3，IsDesignator=false。
    - R111、R116、P101、U102：读回里完全没有 Text 等于这些名字的对象。
- 读回里 U102 位置有 "RefDes" (5163.071, 4920.205) 和 "REFDES" (5163.071, 4932.705)，F101 位置有 "REFDES" (5116.319, 5859.575) 和 "RefDes" (5128.819, 5859.575)。这些都是 Height 50、Width 3。
- 条件"IsDesignator=false、IsComment=false、Text 不是 *、Component 在指定集合内"的文字有 13 个，预期 0：
  - U103 (5155.197, 4061.445)
  - RefDes (5163.071, 4920.205)，元件 U102
  - REFDES (5163.071, 4932.705)，元件 U102
  - U101 (5197.323, 5239.201)
  - RV101 (5434.732, 4604.989)
  - Q102 (5364.941, 4224.536)
  - Q101 (5092.205, 4486.642)
  - LED101 (5056.772, 5846.878)
  - FB102 (5472.913, 4609.28)
  - FB101 (5415.039, 3781.918)
  - REFDES (5116.319, 5859.575)，元件 F101
  - RefDes (5128.819, 5859.575)，元件 F101
  - D101 (5472.913, 5652.587)
- 板统计与预期 62 / 783 / 178 / 4 / 0 一致：component_count 62、via_count 783、pad_count 178、polygon_count 4、unrouted_connections 0。其余：track 1230、fill 7、text 178、4 层。
- 板框是 4 个顶点的矩形，bounding_rect left 4755、right 5755、bottom 1735、top 6007（宽 1000，高 4272 mil）。

**我的推断（没有验证）**
- AD 里加载的像是离线修改之前的版本。理由是元件位号文字还是旧样子：Height 50 / Width 3，IsDesignator=false，还带 REFDES / RefDes 之类的字符串，而期望里这些位号应该是 39.37 / 6.299 的真位号。
- 磁盘上 PCB1_no3d.PcbDoc 的修改时间是 2026-10-20 20:45:48，约在我 20:47 查看前 2 分钟。我没法判断这个时间是离线修改的写入时间，还是 AD 打开时碰过文件。
- 打开前 AD 的活动文档是别的 PcbLib，没有证据说明当时已经载入过这块板。
- 也可能是离线改动没有真正写进这个文件，或者改的是别的文件。

**为什么停下**
- 步骤 5 关规则和步骤 7 保存是写操作，保存一份与期望不符的板会把现状固化。步骤 4 和步骤 6 的 DRC 在这个状态下也说明不了什么。
- 需要主会话确认磁盘上的文件是不是改好的版本。如果是，需要关掉 PCB 文档后重新打开让 AD 重读，我没有被授权做这一步。如果不是，需要重新离线修改。
- 确认后我可以接着做步骤 3 到 7，也可以重新开始。

**未做的步骤**
- 步骤 3 板形图、步骤 4 第一次 DRC、步骤 5 关两条丝印规则、步骤 6 第二次 DRC、步骤 7 保存都没做。
- 没有生成 board_after.svg、drc_silk_on.drc、drc_silk_off.drc。
~~~

**主会话怎么处理 / 学到什么**

- 22 行里 12 行 OK、10 行不符；"应为 0"的检查出来 13 个。子代理停下，没有保存（保存就会把半成品固化）。
- 它的推断是"AD 加载的可能是修改前的版本"——主会话没照这个方向查，而是注意到"普通文字都生效、属于元件的都没生效"，对比两层记录的字节，找到 @226 的 V7 层号。
- **学到的**："离线核对全对"不等于 AD 认；读回比对 + 不符就停，是这一轮最值钱的一条规矩。

---

## 8　只做一件事：不保存地关闭工程

续派同一个子代理（**Sonnet**），说明只有一段：为什么关、用什么参数、弹框怎么办、关完确认什么、然后停。

**主会话 → 同一个子代理（SendMessage 续派）**

~~~text
请只做一件事：不保存地关闭 QPA2609 工程，然后停下汇报（还是 Sonnet，规则不变）。原因已查明：主会话离线修改时漏改了文字记录里的第二个层号字段，所以 21 个属于元件的文字层没变；要先关掉工程才能补改文件。
步骤：proj_close（project_path=E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb，save=false）。如果弹"是否保存"对话框，停下汇报原文，不要点。然后 proj_list_open 确认 QPA2609_test.PrjPcb 不在列表里、Altium_API.PrjScr 还在。不要保存任何东西。汇报后停下，之后我会再发消息让你重新打开做第 1～7 步。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
成功：QPA2609 工程已关闭，没有保存任何东西。

- proj_close(project_path=E:\Altium_designer\QPA2609\projects\QPA2609_test\QPA2609_test.PrjPcb, save=false) 返回 success:true、closed:true、saved:false，attempts 1。
- 返回的 discarded 列表是 PCB1_no3d.PcbDoc 和 QPA2609_test.PrjPcb，这是 AD 当时没保存的状态（我之前读到 modified:false）。
- 没有弹出"是否保存"对话框。app_list_open_dialogs 返回 dialog_count 0。
- 关闭后活动文档自动切到 E:\Users\Public\Documents\Altium\PCB_Project\QFN65P500X500X100-25N-D.PcbLib。
- proj_list_open 返回 3 项：Free Documents、PCB_Project.PrjPcb（5 个文档）、Altium_API.PrjScr（13 个文档，路径 E:\Altium_designer\auto_MCP\scripts\Altium_API.PrjScr）。QPA2609_test.PrjPcb 已不在列表里，Altium_API.PrjScr 还在。

我先停在这里，等你再发消息让我从第 1 步重新开始。
~~~

**主会话怎么处理 / 学到什么**

- 主会话要在 AD 关掉文件后才能补改，否则 AD 一保存就盖掉。关完主会话自己再以写模式打开文件，确认没被锁。

---

## 9　补改后重做第 1～7 步：全部通过

续派（**Sonnet**）：只说"文件已补改好，从第 1 步重做"，并给出这次的预期数字（Top Overlay 文字 108 个）。

**主会话 → 同一个子代理（SendMessage 续派）**

~~~text
文件已补改好（21 条文字的第二个层号字段已修正，离线读回 22 行期望全部对上）。请从第 1 步重新做完原任务的第 1～7 步（还是 Sonnet，规则不变：只允许第 5 步关两条丝印规则和第 7 步保存）。
提醒：第 2 步的 readback_top_overlay.csv 直接覆盖旧文件；这次预期 Top Overlay 文字数 = 108（113 − 13 + 8），22 行期望全部 OK，"Component 属于那 11 个元件的非位号文字"= 0。若仍不一致，停下汇报，不要做第 3 步以后。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
成功：步骤 1 到 7 全部完成，读回和期望全部对上，保存后 still_dirty 为 0，工程保持打开。

**1 打开**
- proj_open 成功，proj_load_sheets 返回 already_loaded 1，pcb_focus_board 成功，当前工程 QPA2609_test.PrjPcb，文档 PCB1_no3d.PcbDoc。
- 打开时没有对话框。读到 modified:false。
- Altium_API.PrjScr 未动。

**2 读回（读回的事实）**
- Top Overlay 文字数 count=108，和预期一致。CSV 已覆盖：E:\<项目根>\电路控制\temp\round3\readback_top_overlay.csv，脚本数出 108 行。
- 这个 CSV 不是逐条抄写的。我用脚本在旧的 113 行 CSV 上去掉那 13 个非位号文字，再补上 8 条位号行（U103、U102、U101、RV101、R116、R111、P101、D101），其余行沿用旧值。
- 这样做的依据是我逐条对过新读回结果，其余行和旧值一致。
- 22 行期望全部 OK，X、Y、Rotation、Height、Width、IsDesignator 都对上。
- 第 3 项：Component 属于那 11 个元件、IsDesignator=false、IsComment=false、Text 不是 "*" 的文字，数量为 0。
- 板统计：元件 62、过孔 783、焊盘 178、铺铜 4、未连接 0。另有 track 1230、fill 7、text 178、4 层。
- 板框：矩形，left 4755、right 5755、bottom 1735、top 6007（宽 1000、高 4272 mil）。

**3 板形图**
- 已生成 E:\<项目根>\电路控制\temp\round3\board_after.svg。
- design_visual_review 原文件路径就是这个，png_path 为 null（"browser produced no PNG"）。
- counts：outline 4、tracks 1230、arcs 24、pads 178、vias 783、texts 116、regions 54、components 62。

**4 第一次 DRC（丝印规则开着）**
- 规则读回：
  - SilkToSolderMaskClearance：enabled true，"Silk To Solder Mask (Clearance=0.254mm) (IsPad),(All)"。
  - SilkToSilkClearance：enabled true，"Silk to Silk (Clearance=0.254mm) (All),(All)"。
- pcb_run_drc(allow_modal=true) 弹出 "设计规则检查器 [mm]"，我按了 "运行DRC (&R)..."。
- 报告已更新为 20:51:08，复制成 E:\<项目根>\电路控制\temp\round3\drc_silk_on.drc。
- 每条规则的 Rule Violations：
  - Clearance 0.15mm、Clearance 1mm（RF 到铺铜）、Short-Circuit、Un-Routed Net、Modified Polygon、Width 0.15、Width RF、Power Plane Connect、Hole Size、Hole To Hole、Minimum Solder Mask Sliver、Net Antennae、Height，全部 0。
  - Silk To Solder Mask：90。
  - Silk to Silk：13。
  - 报告里 "Violation between" 共 103 行，等于 90 加 13。

**5 关两条规则**
- 第一次尝试 pcb_set_rules_enabled 的 names 传字符串（逗号分隔或 JSON 字符串），返回 matched:0、updated:0，什么都没改。
- 另外我还试过 match="descriptor" 和 match="exact"，同样 matched:0。
- 改成把 names 传成真数组 ["SilkToSolderMaskClearance","SilkToSilkClearance"] 才成功：matched 2、updated 2，两条的 prev_enabled 都是 true、new_enabled 都是 false。
- 中间我还试过一次 names="Silk"、match="contains"，被权限分类器拒绝，没有执行，没有任何效果。
- 读回 pcb_get_rule_properties：
  - SilkToSolderMaskClearance：descriptor "Silk To Solder Mask (Clearance=0.254mm) (Disabled)(IsPad),(All)"。
  - SilkToSilkClearance：descriptor "Silk to Silk (Clearance=0.254mm) (Disabled)(All),(All)"。
- 这两条读回的 enabled 字段仍显示 true。没动过的 MinimumSolderMaskSliver 同样是 enabled:true 却带 (Disabled)，所以我推断这个字段不反映 DRC 开关，以 descriptor 里的 (Disabled) 为准（推断）。第二次 DRC 的结果也确认两条规则已不检查。

**6 第二次 DRC**
- 同样的方式运行，报告已更新为 20:53:02，复制成 E:\<项目根>\电路控制\temp\round3\drc_silk_off.drc。
- 所有规则的 Rule Violations 全是 0，"Violation between" 共 0 行。
- 报告里仍有这两节，但标题带 (Disabled)，违规数为 0：
  - "Processing Rule : Silk To Solder Mask (Clearance=0.254mm) (Disabled)(IsPad),(All) ... Rule Violations :0"
  - "Processing Rule : Silk to Silk (Clearance=0.254mm) (Disabled)(All),(All) ... Rule Violations :0"
- 报告里 "Silk" 一词共出现 2 行，就是这两节。

**7 保存**
- app_save_all 返回 saved:true，documents_attempted 3，documents_written 3，still_dirty 0。
- 没写入的是 PcbLib1.PcbLib、HMC952ALP5GE.SchLib、QFN65P500X500X100-25N-D.PcbLib（没被编辑过）。
- 工程保持打开。
- 注意：DRC 运行后活动文档会切到生成的 DRC 的 .html，我在第 5 步前用 pcb_focus_board 切回了 PCB。当前活动文档不一定还是 PCB。

**改动范围**
- 只改了两条丝印规则的开关，并保存。没有改任何对象。
- 没跑 doctor，没用 pcb_set_text_visibility，没对文字用 obj_modify，没关 Altium_API.PrjScr。
~~~

**主会话怎么处理 / 学到什么**

- 子代理写 CSV 时用了"在旧表上改"的办法，并如实说明——主会话不采信这份 CSV，自己重新解析保存后的 PcbDoc，22/22 正确，再用 `drc_report.py` 读两份 DRC：开丝印规则时有 103 条，其中 **2 条涉及新字**（+12V/GND 0.242、MODULE 碰 D101 符号线 0.215）。
- 子代理发现 `pcb_set_rules_enabled` 的 `names` 要传数组、`enabled` 字段不变而 descriptor 带 "(Disabled)"——记进了 skill。

---

## 10　两处小修：挪 GND、删 MODULE → 删除被权限检查拦下

续派（**Sonnet**）：先挪 GND、再删 MODULE、再开规则查一次、关规则查一次、保存。

**主会话 → 同一个子代理（SendMessage 续派）**

~~~text
还有最后一小步（还是 Sonnet，规则同前；本次允许的修改只有下面 1、2 两处文字和第 3/4 步规则开关，以及第 5 步保存）。DRC 会把活动文档切走，每次改对象或改规则前先 pcb_focus_board 切回 PCB1_no3d.PcbDoc。
1. 移动普通文字 GND：先 obj_query 确认 Layer=TopOverlay|Text=GND|X=4949.882|Y=5707.41 正好 1 个且 Component 为空，然后 obj_modify 只改 Y=5690.875（X 不变）。读回 X、Y、Rotation。
2. 删除普通文字 MODULE：先确认 Layer=TopOverlay|Text=MODULE|X=5459.724|Y=5392.449 正好 1 个且 Component 为空，再 obj_delete（过滤带 Layer、Text、X、Y）。删后确认 Top Overlay 上 Text=MODULE 的数量为 0，Text=QPA2609 的仍为 1 个（5400.669, 5392.449, 旋转 90）。
3. 用 pcb_set_rules_enabled（names 传数组 ["SilkToSolderMaskClearance","SilkToSilkClearance"]）把两条丝印规则**打开**，读回 descriptor（不应再带 (Disabled)）。跑 DRC（同前的方法），报告更新后复制成 E:\<项目根>\电路控制\temp\round3\drc_silk_on2.drc，汇报各规则违规数。
4. 再用同样方法把两条规则**关掉**，读回 descriptor（应带 (Disabled)）。再跑 DRC，复制成 E:\<项目根>\电路控制\temp\round3\drc_silk_off2.drc，汇报各规则违规数。
5. app_save_all，still_dirty 必须 0。工程保持打开。
汇报格式同前。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
部分完成：第 1 项移动 GND 做了，第 2 项删除 MODULE 被权限系统拒绝，我停下了。第 3、4、5 步没做。

**第 1 项 移动 GND（已做）**
- 先切回 PCB1_no3d.PcbDoc（pcb_focus_board 成功）。
- obj_query 过滤 Layer=TopOverlay|Text=GND|X=4949.882|Y=5707.41，结果正好 1 个：Text GND，X 4949.882，Y 5707.41，Rotation 90，Component 为空。
- obj_modify set "Y=5690.875"，返回 matched 1、success true、failed 0。
- 读回 Top Overlay 上 Text=GND 共 5 个：
  - (4794.37, 2341.268) 旋转 0
  - (4794.37, 3734.969) 旋转 0
  - (4949.882, 5690.875) 旋转 90，Component 为空，这就是移动后的那个
  - (4929.122, 2136.6811) 旋转 0，Component J6
  - (4929.122, 3530.3819) 旋转 0，Component J5
- 移动后的 X 仍是 4949.882，Rotation 仍是 90。

**第 2 项 删除 MODULE（被拒绝）**
- 删除前的确认已做：过滤 Layer=TopOverlay|Text=MODULE|X=5459.724|Y=5392.449 正好 1 个，Rotation 90，Component 为空。
- 随后调用 obj_delete(object_type=eTextObject, filter="Layer=TopOverlay|Text=MODULE|X=5459.724|Y=5392.449")，被 Claude Code 的权限分类器拒绝，原因标为 [Irreversible Local Destruction]。
- 原文提示：如果这个操作是必须的，要先停下来说明，由用户决定；可以由用户在设置里给 mcp__eda-agent__tool_invoke 加权限规则。
- 我没有换别的工具去绕过，MODULE 仍在板上。
- 第 2 项要完成需要用户明确放行删除这一个对象，或你们换个办法处理。

**为什么没做第 3、4、5 步**
- 第 3、4 步的 DRC 要在删掉 MODULE 之后跑才有意义。现在跑出来的结果之后还要重跑一遍。
- 第 5 步保存会把"GND 已移动、MODULE 还在"的半成品状态固化。

**当前状态**
- PCB 里有一处未保存的改动：GND 的 Y 从 5707.41 改成 5690.875。除此之外没改别的。
- 两条丝印规则目前仍是关闭状态，是上一轮保存下来的，descriptor 带 (Disabled)。
- 工程保持打开，Altium_API.PrjScr 没动。

放行后我可以接着做：删除 MODULE，确认 MODULE 数量为 0 且 QPA2609 仍是 1 个，然后做第 3 到 5 步。
~~~

**主会话怎么处理 / 学到什么**

- 删除被 Claude Code 的权限检查拦下（"不可逆的删除"）。子代理没有换工具绕过，并且**没做后面的 DRC 和保存**（理由：现在跑没意义，保存会固化半成品）。
- 主会话：删 MODULE 是自己替用户做的设计决定，于是用选择题问用户（删 / 挪装配层 / 保留）。

---

## 11　转告"用户已同意"——权限检查仍然拦

用户选了"删"。续派（**Sonnet**），说明里写"如果仍被拒，就停下汇报，不要绕过"。

**主会话 → 同一个子代理（SendMessage 续派）**

~~~text
用户已经在主会话里明确同意删除这个 MODULE 文字（只这一个对象：Layer=TopOverlay、Text=MODULE、X=5459.724、Y=5392.449、Component 为空）。请接着做原第 2～5 步（还是 Sonnet，规则同前）：删除后确认 MODULE 数量 0、QPA2609 仍 1 个；然后打开两条丝印规则跑 DRC → drc_silk_on2.drc；关掉再跑 → drc_silk_off2.drc；app_save_all（still_dirty 0）。如果删除仍被权限系统拒绝，就停下汇报，不要换别的工具或办法绕过。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
部分完成，在删除这一步卡住了：obj_delete 再次被权限系统拒绝，我按要求停下，没有换别的工具或办法绕过。

- 我重新调用了一次 obj_delete，参数是 object_type=eTextObject，filter="Layer=TopOverlay|Text=MODULE|X=5459.724|Y=5392.449"。
- 被拒绝，原因仍是 [Irreversible Local Destruction]。原文：Permission for this action was denied by the Claude Code auto mode classifier。
- 这个拒绝来自 Claude Code 自己的权限分类器，不是 AD 报错。它没有承认主会话转述的用户同意。
- 要让删除生效，用户需要在 Claude Code 里批准这类调用，例如为 mcp__eda-agent__tool_invoke 添加权限规则。

**当前状态**
- PCB 里有一处未保存的改动：上一轮把 GND 移到 Y=5690.875（X 4949.882，旋转 90）。
- MODULE 仍在板上，位置 (5459.724, 5392.449)，旋转 90，Component 为空。
- 两条丝印规则仍是关闭状态，descriptor 带 (Disabled)，是上一轮保存下来的。
- 工程保持打开，Altium_API.PrjScr 没动。

**没做的**
- 删除后的计数确认、第 3 步（打开规则跑 DRC，生成 drc_silk_on2.drc）、第 4 步（关规则再跑，生成 drc_silk_off2.drc）、第 5 步（保存）都没做。
- 保存会固化"MODULE 还在"的半成品状态。

用户放行删除后，我可以接着从删除开始做完。
~~~

**主会话怎么处理 / 学到什么**

- 权限检查不认主会话转述的同意。主会话不改权限、不建议放宽，请用户在 AD 里手动删（给出层、文字、坐标、跳转方法）。用户确认："禁止删除规则是对的，没我允许不许随意放行"。

---

## 12　核对用户的手动删除，跑两次 DRC，保存

续派（**Sonnet**）：先核对（MODULE = 0、QPA2609 还在、GND 新位置、文字总数 107、统计数不变），**不符就停、不保存**；都符合再开 / 关规则各跑一次 DRC，保存。

**主会话 → 同一个子代理（SendMessage 续派）**

~~~text
用户已经在 AD 里手动删除了 MODULE（没保存）。请接着做（还是 Sonnet，规则同前；本次允许的修改只有第 3/4 步的规则开关和第 5 步保存；**不要删除任何对象**）：
1. pcb_focus_board 切回 PCB1_no3d.PcbDoc。核对：Top Overlay 上 Text=MODULE 的数量 = 0；Text=QPA2609 正好 1 个在 (5400.669, 5392.449) 旋转 90；GND 在 (4949.882, 5690.875) 旋转 90；Top Overlay 文字总数应为 107（上次 108，减去 MODULE）。再读 pcb_get_board_statistics（元件 62、过孔 783、焊盘 178、铺铜 4、未连接 0）。任何一项不符就停下汇报，不要保存。
2. 都符合的话：打开两条丝印规则（names 传数组）→ DRC → 复制成 E:\<项目根>\电路控制\temp\round3\drc_silk_on2.drc；关掉两条规则 → DRC → 复制成 E:\<项目根>\电路控制\temp\round3\drc_silk_off2.drc；读回两条规则 descriptor 带 (Disabled)。
3. app_save_all，still_dirty 必须 0。
汇报格式同前。
~~~

**子代理 → 主会话（汇报原文）**

~~~text
成功：核对全部符合，两次 DRC 做完，已保存，still_dirty 为 0，工程保持打开。

**1 核对（用户手动删除 MODULE 之后）**
- pcb_focus_board 切回 PCB1_no3d.PcbDoc 成功。
- Top Overlay 上 Text=MODULE：0 个。
- Text=QPA2609：1 个，位置 (5400.669, 5392.449)，旋转 90。
- GND 的 5 个里，移动过的那个在 (4949.882, 5690.875)，旋转 90，Component 为空。其余 4 个没变：(4794.37, 2341.268)、(4794.37, 3734.969)、J6 的 (4929.122, 2136.6811)、J5 的 (4929.122, 3530.3819)。
- Top Overlay 文字总数 obj_count = 107。
- 板统计：元件 62、过孔 783、焊盘 178、铺铜 4、未连接 0。另有 track 1230、fill 7、text 177（上次 178）、4 层。

**2 第一次 DRC（规则打开）**
- pcb_set_rules_enabled（names 传数组）matched 2、updated 2，prev_enabled 都是 false，new_enabled 都是 true。
- descriptor 读回，不带 (Disabled)：
  - "Silk To Solder Mask (Clearance=0.254mm) (IsPad),(All)"
  - "Silk to Silk (Clearance=0.254mm) (All),(All)"
- 运行 DRC 时弹出 "设计规则检查器 [mm]" 对话框，我按了 "运行DRC (&R)..."。
- 报告更新为 21:03:05，复制成 E:\<项目根>\电路控制\temp\round3\drc_silk_on2.drc。
- 违规数：
  - Silk To Solder Mask：90。
  - Silk to Silk：11。上一轮这条是 13。
  - 其余 13 条规则全是 0。
  - "Violation between" 共 101 行，等于 90 加 11。

**3 关闭规则后第二次 DRC**
- 重新 pcb_focus_board，因为 DRC 会把活动文档切到报告的 .html。
- 关规则：matched 2、updated 2，prev_enabled 都是 true，new_enabled 都是 false。
- descriptor 读回带 (Disabled)：
  - "Silk To Solder Mask (Clearance=0.254mm) (Disabled)(IsPad),(All)"
  - "Silk to Silk (Clearance=0.254mm) (Disabled)(All),(All)"
- pcb_get_rule_properties 的 enabled 字段仍显示 true，和上一轮一样，以 descriptor 为准。
- 报告更新为 21:03:46，复制成 E:\<项目根>\电路控制\temp\round3\drc_silk_off2.drc。
- 所有规则的 Rule Violations 都是 0，"Violation between" 为 0 行。
- 报告里 "Silk To Solder Mask (...) (Disabled)" 和 "Silk to Silk (...) (Disabled)" 两节还在，违规数为 0。

**4 保存**
- app_save_all 返回 saved:true，documents_attempted 3，documents_written 3，still_dirty 0。
- 没写入的是 PcbLib1.PcbLib、HMC952ALP5GE.SchLib、QFN65P500X500X100-25N-D.PcbLib（没被编辑过）。

**说明**
- 这一轮我只改了两条丝印规则的开关，并保存。GND 的移动是上一轮做的，和用户手动删除的 MODULE 一起被保存了。
- 没有删除任何对象。
- 当前规则状态是两条丝印规则关闭。
- 当前活动文档可能是 DRC 的 .html，不是 PCB。
~~~

**主会话怎么处理 / 学到什么**

- 全部通过。主会话最后自己读两份 DRC（新字 0 条违规；关规则后全 0）、重新解析保存后的文件（21/21 正确、两份层号一致、板区域正确），再做一份"第三轮完成"的备份。
