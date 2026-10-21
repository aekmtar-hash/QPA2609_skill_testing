# eda-agent 实测的坑（eda-agent 0.7.1 + Altium Designer 23.1.1，2026-10）

来源：三轮 QPA2609 实跑（另一台电脑两轮 + 本机一轮），外加 eda-agent 源码。按主题排，每条写"现象 → 怎么办"。
标【未核实】的是执行端的说法，没找到读回数据支撑。版本变了要重新验证。

## 1　连接、环境、工具入口

- **minimal 工具集**只暴露 `tool_catalog` 和 `tool_invoke`；其他约 450 个工具都通过 `tool_invoke` 调。不确定用哪个工具，就用 `tool_invoke` 调 `tool_guide`（不带 `query` 参数，带了会报 unexpected keyword）。
- MCP 服务启动不会去碰 AD；AD 里的脚本桥要单独挂。本机用 `E:\Altium_designer\auto_MCP\Connect_Altium.ps1`：AD 没开就启动并运行 StartMCPServer，开着就 relaunch，然后等 ping 通。
- **同一时间只能有一个客户端连桥**（Codex、Claude、两个子代理都算）。
- 轮询循环 10 分钟没请求会自动退出 → 再用前先 `app_ping`，不通就重跑连接脚本。
- `eda_agent doctor` 会让 AD 执行一次"全部保存"（canary），有工程开着时别跑。
- `app_screenshot` 需要 pywin32 + Pillow，本机 venv 里没有；`design_visual_review` 只能出 SVG（PNG 那步失败）。要看画面就用 SVG，或者让人截图。
- 只用 ASCII：U+00FF 以上字符会变成 `?`。

## 2　坐标、单位、精度

- 坐标单位 mil，绝对坐标；原点约定 README 没写 → **开工先校准**：读 2～3 个位置已知的元件，算偏移，互相验证（QPA2609：DX 4755.000、DY 1734.969 mil）。
- 只收整数 mil 的：`pcb_place_components`、`pcb_set_board_shape`、`pcb_place_text`、规则数值（`pcb_create_design_rule`：1 mm → 39 mil = 0.991 mm；0.05 mm → 2 mil = 0.051 mm）。先放，再用 `obj_modify` / `obj_batch_modify` 改成精确的小数坐标；规则差一点可以接受，记日志。
- `pcb_place_vias` **保留小数**，每批 30 个很稳定。
- 读出来的坐标可能是取整的，板上存的是小数 → 按读到的值做精确过滤会匹配不上。删除 / 修改时用精确值（从 `obj_query` 原样拿），或按对象 ID。

## 3　查询和过滤语法

- `obj_query` / `obj_count` / `obj_delete` / `obj_modify` 的 filter：**多个条件用竖线 `|` 连接**（`Layer=TopOverlay|Text=GND|X=4949.882|Y=5707.41`）；用逗号会返回 0 个。只支持"名字=值"精确匹配，不支持范围 → 范围筛选要把全量结果存成文件再用脚本筛。
- 读不到的属性：文字的 ConvertedString / DisplayString（特殊字符串 `.Designator` 读出来就是显示后的文字，例如 `U101`，不是 `.Designator`）、NameOn / NameAutoPosition / CommentOn（位号显示开关和 Autoposition）、Region 的顶点。Region 顶点用 `design_visual_review` 的 SVG 推，或者直接读 PcbDoc（`scripts/pcbdoc_io.py`）。
- `obj_query` 把"板区域"（Layer Stack Region）报成 `Kind=board_cutout`，**不是挖空区**（原始板上就有，props 里 `ISBOARDCUTOUT=TRUE` 是这类记录的常态）。用 PcbDoc 里 `BoardRegions` 的 `OBJECTKIND=BoardRegion` 确认。
- `pcb_focus_board` 的参数名是 `board_path`；路径照 `proj_list_documents` 返回的原样传（单反斜杠）。传了双反斜杠会多建一个重复 PCB 文档、还会多开一个 AD。
- 工程里实际引用的可能是副本（QPA2609 是 `PCB1_no3d.PcbDoc`），**以 `proj_list_documents` 为准**。

## 4　放置和修改

- **不要用 `pcb_place_stitching_vias`**：它的 clearance 参数对所有对象生效（填 1 mm = 离每个焊盘、每根线都 1 mm），孔又稀又不错行，还会打进焊盘、离原有过孔太近。规划端算好坐标，用 `pcb_place_vias` 照表放。
- `proj_sync_pcb`（ECO）是模态对话框，不能无人值守。替代：`pcb_place_components` 的 synced 模式（带原理图 UniqueId + 编译网表里的焊盘网络），先放 1 个试，再批量。
- `pcb_modify_polygon` 的 index 顺序和 `pcb_get_polygons` 对不上 → 用 `obj_modify` 按 Layer 过滤，一层改一次。
- 删掉重放原理图元件后，网表里还留着旧元件（95 个而不是 62 个）→ 保存 → 关闭重开工程 → `proj_load_sheets` → 重新编译。
- 自带 IntLib 要当库路径用：复制出来用 `lib_extract_intlib` 解包（弹框选 Extract）；注意当前聚焦的工程，别把新文档建进 LibPkg。
- 只做查询或失败的修改，文档也会被标成"已修改"（dirty）→ 事先备份；不打算保存就 `proj_close(save=false)`。
- 关闭工程：`proj_close(project_path=..., save=false)` 不弹框；关完 `proj_list_open` 确认，别关 `Altium_API.PrjScr`（那是桥本身）。

## 5　文字和丝印

- **转不了文字方向**：`obj_modify` 改 eTextObject 的 Rotation 返回 `unknown=["Rotation"]`（"this build does not write"），普通文字和位号都一样。
- **隐藏位号的 `pcb_set_text_visibility` 会卡 120 秒并把桥弄死**（AD 重启了两次）→ 不用。隐藏位号的办法：把文字挪到 Mechanical13（`obj_batch_modify` 改 Layer；板厂丝印上看不到）。
- `tool_guide` 警告：用 `obj_modify` 改**元件上的位号文字**可能让 AD 崩溃，改位号要走 `proj_annotate`。第二轮挪层没出事，但有风险：挪前先保存。
- 位号 Autoposition 读写不了。
- 普通文字（不属于元件）的 X / Y / Text 内容可以用 `obj_modify` 改；`pcb_place_text` 放新字（参数 text、x、y 整数、layer、height、rotation、stroke）。
- **封装库自带的 Top Overlay 文字**会印到板上：`.Designator`（特殊字符串，显示成位号——藏了位号它照样印）、`REFDES` / `RefDes` / `DES`（原样印出字母）、`*`（1 脚标记，该留）。藏位号时这些也要挪走。规划前用 `scripts/pcblib_inventory.py --texts` 查每个封装。
- 转方向、挪属于元件的文字、改板区域这类工具做不了或有风险的，可以由规划端直接改 PcbDoc 文件，见 `pcbdoc-direct-edit.md`。

## 6　规则

- **规则的 `enabled` 字段不可信**：39 条全报 true，连 descriptor 里写着 "(Disabled)" 的也是。规则开没开，看 descriptor 有没有 "(Disabled)"，或看 DRC 报告里这一节的标题。
- 开关已有规则用 `pcb_set_rules_enabled`，**`names` 要传数组**（`["SilkToSolderMaskClearance","SilkToSilkClearance"]`）；传逗号分隔的字符串会 matched 0。`pcb_set_rule_properties` 改 enabled 不影响 DRC。
- 临时规则用完要**删除**（`pcb_delete_design_rule`），只禁用的话 DRC 照样按它报（第一轮报了 84 条）。
- 临时规则会命中原有对象：RF_to_Via（第二项 IsVia）命中了原有屏蔽孔，报 84 条。说明书要预告这类"噪声"有多少条，执行端只处理新对象。
- `pcb_set_rule_properties` 不肯改 Minimum Solder Mask Sliver（rule kind 53），`pcb_create_design_rule` 也没有这一类 → 留给人在 AD 里改。

## 7　DRC

- `pcb_run_drc(allow_modal=true)` 弹出"设计规则检查器"后 3 秒就返回，框还开着 → `app_list_open_dialogs` 看按钮原文，`app_press_dialog_button` 按"运行DRC (&R)..."。
- **以报告文件为准**：`<工程>\Project Outputs for <工程名>\Design Rule Check - <PCB名>.drc`（工具自己的 `drc_confirmed` 一直是 false）。等文件修改时间更新后再读；要保留就立刻复制一份，下一次 DRC 会覆盖。`scripts/drc_report.py` 汇总。
- 跑完 DRC，活动文档会切到报告的 .html → 再改对象或规则前先 `pcb_focus_board` 切回 PCB。
- 报告里没有 Routing Via Style 这一项 → 读出全部过孔自己核对尺寸范围。
- `pcb_get_unrouted_nets` 不可信（地铜删了它也报 0）→ 以 DRC 的 Un-Routed Net 为准。
- 【未核实】执行端曾说"丝印规则检查过一次后，报告会一直列着这两节"。第三轮实测：规则真关掉后，报告里这两节仍在但标题带 "(Disabled)"、违规 0。当时报告还有 240 条，是规则根本没关上。

## 8　板形

- `pcb_set_board_shape` 只改板框（BoardOutline），**不改板区域**（Layer Stack Region）。板区域还是旧尺寸，AD 在旧板边位置画一条白色虚线。eda-agent 没有改板区域的工具 → 让人在 AD 里重新定义板形，或者直接改 PcbDoc（`pcbdoc_io.region_move_edge`）。

## 9　崩溃和恢复

- `lib_get_pad_geometry` 报错弹框后桥卡死；`pcb_set_text_visibility` 卡死。恢复：关掉 AD → 重开 → 跑连接脚本（或 `eda_agent relaunch`）→ `proj_open` + `proj_load_sheets` → 重新核对已保存的状态。事先保存过就不丢数据。
- 没实测过的修改类工具：先保存，再拿一个对象试。

## 10　Claude Code 这边的权限

- 子代理调用 `obj_delete` 可能被 Claude Code 的权限检查拦下（"Irreversible Local Destruction"），主会话转告"用户已同意"也没用。**不要改权限设置、不要换工具绕过。** 由用户在 AD 里手动删（给出对象的层、文字、坐标和步骤），或者等用户自己决定放不放行。用户原话："确实你的禁止删除规则是对的没我允许不许随意放行这个"。
