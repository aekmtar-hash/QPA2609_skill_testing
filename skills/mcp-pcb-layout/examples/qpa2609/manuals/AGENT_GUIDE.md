# AGENT_GUIDE — QPA2609 模块：给射频板加上自带供电（eda-agent / Altium Designer 专用）

> 读者：在另一台电脑上、通过 **eda-agent MCP** 操作 Altium Designer 23 的 AI 代理。
> 任务：在**已经做到第 6 章（布线、铺铜、DRC 电气项全 0）**的 QPA2609 射频测试板工程里，加入一整套板载供电电路，做成"射频 + 供电"一个模块。
> 人类用户今晚不在场，明早看结果。**宁可停下来写清楚卡在哪，也不要猜着改。**

> **如果你是便宜/小模型（例如 Haiku 级别）**：不要自己理解全文再规划。直接打开 `RUNBOOK_HAIKU.md`，按里面的循环规则把 `ops.jsonl` **一行一行**做完。本文件只在 RUNBOOK 让你查的时候再看。

本文件夹里的数据文件是**唯一的坐标来源**。所有坐标、线宽、网络都已经用脚本按库里真实焊盘检查过（不同网络最小间距 0.20 mm、0 短路、0 漏连、0 元件重叠、阻焊桥够宽、供电元件全在切口内）。**不要自己"优化"布局，照数据放。**

---

## 0　完成的标准（Definition of Done）

1. 原理图新增一页 `Power.SchDoc`，47 个元件，网络和 `nets.csv` 完全一致；`VD`、`VG`、`GND` 与射频页的同名网络连通。
2. PCB 板子从 25.4 × 51.4 mm 变成 **25.4 × 108.5 mm**；原有射频部分（元件、线、手放的 137 个过孔、阻焊开窗）**一个都没动**。
3. 47 个新元件按 `components.csv` 摆好；45 个新过孔按 `vias.csv`；155 段新走线按 `track_segments.csv`。
4. 四层 GND 铺铜按新板框重铺；按 `stitch_vias.csv` 打了 602 个接地缝合孔。
5. 丝印：37 个小元件的位号隐藏，10 个位号移到 `silk.json` 指定位置，另加 11 个功能字（端子旁写电压和极性：+12V/GND、-5V、VD +3.5V、VG NEG、GND，以及 ADJ、QPA2609 MODULE），字高 1.0 mm、线宽 0.16 mm。
6. DRC：Clearance、Short-Circuit、Un-Routed Net、Width、Routing Via Style、Hole Size、Hole To Hole、Minimum Solder Mask Sliver 全为 0。
7. 全部保存；写出 `AGENT_REPORT.md`（见第 9 节）。

做不完也没关系：**每完成一个阶段就保存并在 `AGENT_LOG.md` 里记一笔**，第二天人从断点接着做。

---

## 1　硬性规则（违反任何一条都必须立刻停）

1. **开始前确认有备份**：工程文件夹旁边应该有 `QPA2609_test_备份_*` 的副本。没有就先把整个工程文件夹复制一份（改名 `QPA2609_test_agent备份_<日期时间>`），再开始。
2. **不准改射频部分**：不移动、不删除、不改属性以下对象：U1、J1～J8、C3、C6、C9、C12、C15、C18、所有 RFIN/RFOUT/THRU/VD/VG 原有走线、`keep_existing_vias.csv` 里的 137 个过孔、Top Solder / Bottom Solder 层上的开窗 Fill、Mechanical 层上的其他东西。
3. **不准改叠层**（Layer Stack Manager）、**不准改原点**、不准改已有规则的数值（除第 6 节 P7 明确列出的两条新增/修改）。
4. **不准删除 PCB 上任何 Remove 类 ECO**：同步原理图到 PCB 时，若变更列表里出现 Remove Component / Remove Net（VD、VG、RFIN…），**不要执行**，停。
5. **所有文字只用 ASCII**：eda-agent 会把 U+00FF 以上的字符变成 `?`（例如 `Ω`、`µ`、中文）。数据文件里的 Value 已经全部换成 ASCII（`22R 2W`、`604R`、`1R 1%`、`10uF`）。
6. **不准"顺手修"DRC**：DRC 有违规，先判断是不是新加对象引起的；只允许修改本次新加的对象；涉及射频部分的违规一律记录、不改。
7. 每个阶段结束：`app_save_all`，然后写日志。

---

## 2　工程现状（第 6 章做完时的状态）

| 项目 | 值 |
|---|---|
| 工程 / PCB / 原理图 | `QPA2609_test.PrjPcb` / `PCB1.PcbDoc` / 原理图一页（文件名以工程里为准） |
| 叠层 | 4 层：**Top Layer** / RO4003C 0.203 mm / **GND2**（信号层，整片 GND 铺铜） / FR-4 0.2 / **GND3**（信号层，整片 GND 铺铜） / FR-4 1.0 / **Bottom Layer**；铜 1 oz；总厚 61.636 mil |
| 板框 | Mechanical 1 上 4 根线，(0,0)～(25.4,51.4) mm，已定义 Board Shape；**用户原点在板左下角** |
| 规则（已有，保持） | Clearance_1 0.15 mm；RF_to_Pour 1 mm（射频网络 ↔ 铺铜）；Width 0.15/0.3/1.5；RF_Width 0.2/0.417/0.417；Routing Via Style 直径 0.5～0.7、孔 0.25～0.4；Polygon Connect Direct；Via_Tent（IsVia 盖油） |
| 已有网络 | RFIN、RFOUT、THRU、VD、VG、GND |
| 射频部分关键坐标（mm） | U1 (12.70, 31.70) rot 0；J1 (2.97, 31.70) rot 90；J2 (22.43, 31.70) rot 270；J3 (19.73, 49.40)=VD 端子；J4 (19.73, 14.00)=VG 端子；J5 (5.68, 49.40)、J6 (5.68, 14.00)=GND 端子 |
| 过孔 | 共 470 个：手放 137 个（见 `keep_existing_vias.csv`）+ 自动缝合 333 个（一个 Via Stitching 组） |
| 铺铜 | 4 块 GND Polygon（Top/GND2/GND3/Bottom），Solid，Pour Over All Same Net Objects，Remove Dead Copper |

**切口**：x = 6.0 mm 和 x = 19.4 mm 两条竖线。供电元件全部在两条切口之间（拼整条链路时切下来的就是这一条）；只有 `outside_cut=True` 的 P101、TP103 在切口外（测试用）。

---

## 3　坐标、单位、层名——先校准再动手（最重要）

eda-agent 的 Altium 接口用 **mil**（1 mil = 0.0254 mm），而且返回的很可能是 Altium 的**绝对坐标**，不是用户原点。数据文件给了 mm 和 mil 两套值，都是**相对板左下角原点**的。

**校准步骤（必须做，结果写进日志）：**

1. 用 `pcb_get_components`（或 `obj_query` 查 Component）读 **U1** 的位置和角度。
2. 计算偏移：`dx = U1.x − 500.000 mil`，`dy = U1.y − 1248.031 mil`。
3. 用 **J3** 验证：期望 (776.772 + dx, 1944.882 + dy) mil，误差 < 0.5 mil；再用 J1 (116.929 + dx, 1248.031 + dy)、角度 90 验证。
4. **之后所有写入坐标 = 数据文件里的 `*_mil` + (dx, dy)**。所有读回的坐标先减 (dx, dy) 再和数据比较。
5. 若校准对不上（误差 > 0.5 mil，或 U1 角度不是 0、J1 不是 90）：**停**，把读到的原始数据写进日志。

**角度**：Altium 的 Rotation，单位度，**逆时针为正**。数据里的 `rotation_deg` 就是要填进 Rotation 的值。元件的 Location = 封装原点（下载库的封装原点都在元件中心；3296W 电位器的原点在 3 号脚；排针 HDR1X2 的原点在 1 号脚）。

**层名**：先列出板上的层，确认 4 层铜的名字。数据里写的是：
- `Top Layer`
- `Bottom Layer`
- `GND3 (2nd inner layer, MidLayer2)` = 从上往下第 2 个内层，用户改名为 **GND3**（Altium 内部名一般是 MidLayer2）。**只有 1 根线（第 104 号）走这层。**
- 第 1 个内层 GND2 **不放任何走线**。

### 3.1　每一层怎么处理（总表，核对用）

| 层 | 原有对象（**不准改**） | 本次操作 | 结束时应满足 |
|---|---|---|---|
| Top Layer | RFIN/RFOUT/THRU、U1、C3～C18、J1～J8 的焊盘和原有 VD/VG/GND 短线、GND 铺铜 | 放 47 个元件（全部 Top）；98 根走线 = 139 段（宽 0.3 mm 90 根 / 0.5 mm 6 根 / 0.8 mm 2 根）；P10 重铺 GND | 射频线两侧 1 mm 无铜（RF_to_Pour 自动） |
| GND2（第 1 内层，MidLayer1） | GND 铺铜 | **0 根走线**；只重铺 GND | 整层完整，除过孔外无任何开口 |
| GND3（第 2 内层，MidLayer2） | GND 铺铜 | **1 根走线**（track_no 104，VG，0.3 mm，5 段）；重铺 GND | 铺铜自动让开这根线 |
| Bottom Layer | GND 铺铜 | 6 根跳线 = 11 段（track_no 98～103，0.3 mm）；重铺 GND；不放元件 | — |
| 过孔（贯通） | 137 个手放过孔 | 删 333 个缝合孔；加 45 个新过孔（0.25/0.5）；P11 按 `stitch_vias.csv` 放 602 个缝合孔 | Via_Tent 盖油规则覆盖全部过孔 |
| Mechanical 1 | 旧板框 4 根线 | 换成 (0,0)～(25.4,108.5) mm 的 4 根线，并设 Board Shape | Gerber 输出包含此层 |
| Top Solder | 3 块射频开窗 Fill | **不加 Fill**；规则 IC_Mask（0.05 mm）、Sliver 0.08 mm | — |
| Bottom Solder | 4 块连接器开窗 Fill | 不动 | — |
| Top Overlay | 位号、连接器框 | P12：隐藏 37 个位号；10 个位号按 `silk.json` 摆；加 11 个功能字（字高 1.0 mm，线宽 0.16 mm） | 字不压焊盘/过孔（已算好）；Silk 报警不处理 |
| Top Paste | 自动 | 不动 | — |
| 叠层 / 介质 | 4 层，61.636 mil | **不改** | — |

---

## 4　数据文件

| 文件 | 内容 |
|---|---|
| `module_design.json` | 全部数据（下面几个 CSV 的合集 + 元件引脚坐标 + 期望数量） |
| `components.csv` | 47 个元件：位号、库文件、库元件名、封装名、Value（ASCII）、X/Y（mm 和 mil）、旋转、层、是否在切口外 |
| `nets.csv` | 27 个网络及其连接的脚（位号-脚号），**原理图按这个连** |
| `pad_nets.csv` | 133 个焊盘的期望网络和焊盘中心坐标（mm），摆完后用来核对 |
| `vias.csv` | 45 个新过孔：网络、X/Y、孔 0.25 mm（9.843 mil）、直径 0.5 mm（19.685 mil） |
| `track_segments.csv` | 155 段走线：所属走线号、阶段、网络、层、线宽、起终点（mm 和 mil） |
| `keep_existing_vias.csv` | 必须保留的 137 个原有手放过孔 |
| `schematic_layout.json` | 原理图**精确坐标**（图纸 mil）：47 个元件位置、129 段短导线、93 个网络标号、36 个 GND 符号、每个元件每个脚的期望端点 |
| `silk.json` | 丝印：要隐藏的 37 个位号、10 个位号的位置、11 个功能字（mm，板左下角原点） |
| `stitch_vias.csv` | 602 个接地缝合孔坐标（1.5 mm 错行网格，已避开射频线 1 mm、所有别的铜 0.2 mm、焊盘、元件外框、丝印字） |
| `ops.jsonl` / `ops.csv` | **按顺序排好的 1353 条操作**，每条带全部参数、核对方法、失败怎么办；小模型照这个逐条做 |
| `RUNBOOK_HAIKU.md` | 给小模型的执行规则：循环怎么走、每种操作用哪个工具、偏移怎么加、日志怎么写、什么时候停 |
| `libs/` | 20 个库文件（10 个 .SchLib + 10 个 .PcbLib，3D 已嵌在 PcbLib 里） |

`no_connect`（只在 json 里）：`U101-8, U101-9, U102-7, U103-5` 这 4 个脚**不接**。

---

## 5　库

把 `libs/` 里 20 个文件复制到工程文件夹下新建的 `Lib_供电`（或 `Lib_power`，ASCII 路径更安全）文件夹，用 `proj_add_document` 加进工程。

| 库元件名（lib_ref） | 库文件 | 封装（已关联） |
|---|---|---|
| LTC3260EMSEPBF | LTC3260EMSEPBF.SchLib/.PcbLib | MSOP-16_MSE_LIT |
| LT3094EMSEPBF | LT3094EMSEPBF.* | 05-08-1666_ADI |
| LT3045EMSEPBF | LT3045EMSEPBF.* | MSOP12_MSE_ADI |
| MMBT3904LT1G / 2N7002LT1G | 同名 .* | SOT-23_3L_ONS |
| SSA34-E35AT（D101，SS34 的 SMA 封装） | SSA34-E35AT.* | CR_A34-E35AT_VIS |
| 1812L07524DR | 1812L07524DR.* | FUSE_1812L075_LTF |
| 3296W-1-103LF | 3296W-1-103LF.* | POT_3296W |
| BLM18AG601SN1D | BLM18AG601SN1D.* | FILTER_BLM18AG_MUR |
| APT1608SGC | APT1608SGC.* | LED_APT1608SGC_KNB |
| Res2 / Cap | Miscellaneous Devices.IntLib（AD 自带） | **默认是插件封装，必须换成 components.csv 里的封装**：0402、1608[0603]、6-0805_N、C1206、C1210、RESC6332，并删掉默认的 AXIAL-0.4 / RAD-0.3 |
| Header 2 / Socket | Miscellaneous Connectors.IntLib（AD 自带） | 默认 HDR1X2 / PIN1，不用改 |

注意：封装名 `1608[0603]` 带方括号，是英制 0603；**不要用名叫 `0603` 的封装**（那是英制 0201）。

**引脚号约定（布局依赖它）**：`Res2`、`Cap` 是 1、2 脚；下载的器件按 `nets.csv` 的脚号连。LT3094 的底部焊盘脚号是 `13`（接 N5V，**不是地**），LTC3260、LT3045 的底部焊盘脚号是 `EPAD`（接 GND）。D101 的 1 脚是负极，LED101 的 1 脚是负极，RV101 的 2 脚是滑动端。

---

## 6　执行阶段（每个阶段：做 → 核对 → 保存 → 写日志；逐条版见 `ops.jsonl`）

工具名以 `tool_catalog` / `tool_guide` 为准，下面写的是 eda-agent 文档里出现的名字。**第一次用某个工具前先 `tool_guide` 看参数**；有批量版本的优先用批量（每次调用默认 10 秒超时，一批不要超过 30～50 个对象）。

### 续做规则（每次开始都先做）
- 先读工程文件夹里的 `AGENT_LOG.md`，跳到第一个没有标 `DONE` 的阶段。
- 阶段内部：**创建每个对象前先查**同坐标（容差 0.01 mm）、同层、同网络、同尺寸的对象是否已经存在，存在就跳过——防止崩溃重跑时重复放出一片短路。
- 优先用 API 类工具（`obj_*`、`pcb_*`、`sch_*`、`proj_*`）；`app_click_menu` 这类模拟键鼠的工具只在没有替代时用，用之前写日志。

### P0　连接与盘点
- `app_attach` → `app_ping`。确认打开的是 `QPA2609_test.PrjPcb`。
- 盘点并写入日志：元件数、过孔数（应为 470）、多边形数（应为 4）、规则列表、层列表。数量不对就停。
- 完成第 3 节校准。
- **试操作**：在板外空地（例如 x = −200 mil + 偏移，y = 0 + 偏移）放 1 个 GND 过孔（0.25/0.5）和 1 段 0.3 mm、Top Layer 的线，读回坐标、尺寸、层名，和写入值比较（减偏移后误差 < 0.1 mil）；**然后删掉这两个对象**，确认过孔数回到 470。单位、偏移、层名任何一项不对就停。

### P1　加库
- 复制 20 个库文件，`proj_add_document` 加入工程。核对：工程里多 20 个库文档。

### P2　原理图
1. 新建原理图文档 `Power.SchDoc` 加入工程（找创建文档的工具；没有就 `app_click_menu` / `app_run_ui_command` 走 File→New→Schematic 再保存）。
2. **网络作用域**：用 `proj_get_options` 读层次模式。目标是 **Global**（或 Automatic 且工程里没有端口/图纸入口——此时 Altium 按 Global 处理）。最终以第 5 步的连通性核对为准。
3. 用 `sch_place_components` 放 47 个元件（位号、Value、Comment=Value，全 ASCII），**位置按 `schematic_layout.json`**（图纸 mil，不加 PCB 偏移，旋转全 0）。图纸设成 A1。放完第一个元件就读回它的脚端坐标，和 `expect_pin_ends` 比：一致才继续。
4. 给 Res2 / Cap 换封装（`lib_link_footprint` / `sch_set_components_parameters` / `obj_modify`，看哪个能改已放置元件的 Footprint 模型），删掉默认插件封装。
5. 连线：坐标全部在 `schematic_layout.json` 里——129 段 200 mil 短导线（`sch_place_wires`），导线外端放 93 个网络标号（`sch_place_net_label`，方向 0）或 36 个 GND 符号（`sch_place_power_port`，Power Ground 样式，方向 270）。`no_connect` 的 4 个脚不接。
6. `proj_compile` / `proj_force_recompile`，然后 `proj_get_connectivity_many` 或 `obj_crossref_net` 核对：**每个网络的脚集合与 nets.csv 完全一致**；并且 `VD` 网络里同时有 `J3-1` 和 `FB101-2`、`VG` 里同时有 `J4-1` 和 `FB102-2`（证明跨页连通）。不一致就修原理图，直到一致；修不好就停。
7. `run_erc` / `design_validate`：不应有 Error。可以忽略：上述 4 个空脚未连接、"no driving source"、off-grid。
8. **原理图门槛**：第 6、7 步必须 100% 通过才能进 P3；只要有一个网络对不上、修了两轮还不对，就保存、写报告、**停**（PCB 部分留给人第二天确认原理图后再跑）。
   - 如果用户在启动时说了"原理图做完就停"，那么无论核对结果如何，P2 结束后都停下等人确认。

### P3　PCB 清场（在 ECO 之前）
1. **删自动缝合孔**：列出所有过孔；与 `keep_existing_vias.csv`（137 个，坐标容差 0.02 mm，注意加偏移）比对；**不在保留表里的 GND 过孔应该正好 333 个**。数量正好是 333 才删；不是 333 就停并把差异写进日志。
2. **删 4 块铺铜**：多边形应正好 4 块（Top/GND2/GND3/Bottom，网络 GND），删除。
3. **新板框**：
   - `pcb_set_board_shape` 设成矩形 (0,0)～(25.4,108.5) mm = (0,0)～(1000.000, 4271.654) mil（加偏移）。
   - Mechanical 1 上原来 4 根板框线删掉，按新矩形画 4 根新线（线宽保持原来的值）。Gerber 输出用的是 Mechanical 1。
4. 保存、写日志。

### P4　同步到 PCB（ECO）
- **首选（第一次实跑验证过）**：`pcb_place_components` 的 synced 模式——每个元件带上原理图的 UniqueId（`obj_query` 查 eSchComponent 的 Designator.Text、UniqueId）和编译后网表里的焊盘网络。eda-agent 文档自己说 `proj_sync_pcb` 是模态框、不要无人值守用。这个工具只收整数 mil，放完再用 `obj_batch_modify` 把 47 个元件坐标改成带小数的精确值。
- 备选：`proj_sync_pcb`（模态对话框；先让 PCB 文档成为活动文档；用 `app_list_open_dialogs` / `app_drive_dialogs` 处理）。
- **执行前检查变更列表**：只能有 Add Component（47 个）、Add Net、Add Pin、Add/Change Room 一类；**出现任何 Remove Component / Remove Net 就取消并停**。
- 执行后删除新生成的 Room（如果有）。核对 PCB 上新增 47 个元件。

### P5　摆放
- `pcb_move_components` 批量：位置 = `x_mil, y_mil` + 偏移，旋转 = `rotation_deg`，层 Top。
- **核对**：对 `pad_nets.csv` 每一行，读回焊盘中心和网络（减偏移后比较），位置误差 < 0.01 mm，网络一致。
  - 两脚**无极性**元件（R*、C*、FB*、F101）位置对但两个焊盘网络对调：把 Rotation 加 180 再核对（原理图 1、2 脚接反了，焊盘对称所以转 180 等效）。记日志。
  - D101、LED101、U101～U103、Q101、Q102、RV101、P101 网络不对：**不要转**，是原理图连错了，回 P2 改，再同步。
- **库里自带的禁布区（第一次实跑发现）**：D101（3 块）、FB101、FB102、LED101（各 Top Layer 1 块 + Keep-Out Layer 1 块）封装里有 **Region 禁布区**，离自己的焊盘只有 0.05 mm，DRC 会报约 26 条 Clearance，还会挡住 Top 层铺铜。摆完后把这 9 块 Region 的层改成 **Mechanical 15**（只改这 9 块，别的不动）。

### P6　孔径（可选）
- 自带库排针/单针孔 0.9 mm，P101 要插 2.54 排针：只把 **P101、TP103** 的焊盘孔径改 1.0 mm。J3～J6 属于射频部分（第 1 节第 2 条），**不改**，留给人。做不到就跳过并记日志。

### P7　规则（只加/改这两条）
1. 新建 Solder Mask Expansion 规则 **IC_Mask**：查询 `InComponent('U1') Or InComponent('U101') Or InComponent('U102') Or InComponent('U103')`，外扩 0.05 mm（1.969 mil），不盖油，优先级高于默认 SolderMaskExpansion。
2. Minimum Solder Mask Sliver 规则数值改成 0.08 mm（3.150 mil）。eda-agent 0.7.1 的 `pcb_set_rule_properties` **改不了这类规则**（第一次实跑确认）→ 记日志、跳过，留给人手动改。

### P8　过孔
- `pcb_place_vias`：45 个，按 `vias.csv`（网络、坐标 + 偏移、孔 9.843 mil、直径 19.685 mil）。
- 核对数量和网络。

### P9　走线
- `pcb_place_tracks`：155 段，按 `track_segments.csv`（网络、层、宽度、起终点 + 偏移）。
- 层：`Top Layer` 139 段；`Bottom Layer` 11 段（6 根跳线，track_no 98～103，step S6）；**GND3 只有 1 根**（track_no 104，5 段，网络 VG）。track_no 与人类版指南的走线序号一致。
- 线段端点在焊盘中心、过孔中心或其他线段上，已经算好，**不要改道**。
- 核对：`pcb_get_unrouted_nets` → 除 GND 以外**没有**未连网络（GND 要等铺铜）。有别的网络未连 → 对照 pad_nets.csv 找原因，修不好就停。

### P10　四层铺铜
- `pcb_place_polygon_rect` ×4：网络 GND，层 Top Layer / GND2 / GND3 / Bottom Layer，矩形 (0,0)～(25.4,108.5) mm（+偏移）。
- `pcb_modify_polygon` 设：Solid、**Pour Over All Same Net Objects**、**Remove Dead Copper**（与原来一致）。
- `pcb_repour_polygons`。核对：`pcb_get_unrouted_nets` 为空；RFIN/RFOUT/THRU 两侧地铜离线 1 mm（RF_to_Pour 规则还在，会自动做到）。

### P11　重新打缝合孔
1. 新建临时规则 **RF_to_Via**：Clearance，第一对象 `InNet('RFIN') Or InNet('RFOUT') Or InNet('THRU')`，第二对象 `IsVia`，1 mm，优先级最高。
2. **用 `pcb_place_vias` 按 `stitch_vias.csv` 放 602 个孔**（网络 GND，0.25/0.5，坐标 + 偏移）。**不要用 `pcb_place_stitching_vias`**：第一次实跑用它，它的间距参数对所有对象生效（填 1 mm 就离每个焊盘、每根线都 1 mm），孔打得很稀、也没错行；还有 8 个打进了焊盘、6 个离原有屏蔽孔太近。坐标表已经按"只对射频线 1 mm、别的 0.2 mm"算好。
3. 重铺，跑 DRC（RF_to_Via 开着）：违规里只要有 `stitch_vias.csv` 里的孔（1 mil 内），就删**那个孔**；别的对象一律不删。预计 0 个，超过 20 个就停（说明模型和板子对不上）。再查一遍孔心是否落在任何焊盘（外扩 0.25 mm）里，落在里面的删掉（预计 0）。
   - **只准删 `stitch_vias.csv` 里的孔。** 第一次实跑修孔距时误删了 14 个原有屏蔽孔（又按原坐标补回来了）。删完数一遍：`keep_existing_vias.csv` 137 个 + `vias.csv` 45 个必须全在。
4. 把 RF_to_Via **删除**（不要只禁用：第一次实跑发现禁用后 DRC 仍然按它报了 84 条）。别删成 RF_to_Pour。
5. 放不了：跳过本阶段并记日志（不影响电路，只影响接地效果）。

### P12　丝印（让板子上的字好看、好认）
- 数据：`silk.json`。坐标是 mm（板左下角原点），转 mil 后**加偏移**；层 Top Overlay；字体 Stroke；不镜像；字高 1.0 mm（39.370 mil），线宽 0.16 mm（6.299 mil）。尺寸和布局要求见 `7_完成指南` 的 C1 节。
1. 隐藏 37 个位号（R、C、FB，以及放不下的 LED101、Q101、Q102；列表在 `hide_designators`）：把位号文字的 Hide 设为 true（`obj_modify` / `pcb_set_component_properties` 之类，按 `tool_guide` 找）。
2. 10 个位号（U102、U101、U103、D101、F101、RV101、P101、TP103、R116、R111）：位号文字改成手动位置（Autoposition = Manual），位置/角度/字高/线宽按 `labels` 里 `kind=designator` 的行。
3. 11 个功能字（`kind=string`）：放 String 文字，文字内容、位置、角度照抄。
4. 坐标含义：`x,y` = 文字框**左下角**（rot 0）；rot 90 时文字从下往上读，`x,y` 仍是 Altium 报告的文字位置点。读回后和写入值比（误差 < 1 mil）。
5. 这些位置已经用库里的真实焊盘、过孔、元件外框检查过：不压焊盘、不压过孔、互相不重叠。**不要自己挪**。找不到能改位号文字的工具 → 跳过本阶段并写日志（不影响电路）。

### P13　DRC
- `pcb_run_drc`（模态）或 `run_drc` + `pcb_get_clearance_violations`。确认 Routing Via Style 也参与检查。
- 期望：第 0 节第 6 条全部为 0。Silk To Solder Mask / Silk to Silk 可以有，不处理。
- 有违规：逐条判断。只修本次新加的对象；如果是坐标偏移、层名、宽度传错导致的，回到对应阶段修正。涉及射频部分 → 只记录。

### P14　保存和输出
- `app_save_all`。若工程里已有 OutJob，可用 `proj_generate_fab_package` 出 Gerber；没有就**跳过**（人来出）。

---

## 7　为什么这样设计（别"改进"它）

- **供电元件全部在 x = 6.0～19.4 之间**：拼整条链路时，从两条切口切下的就是"QPA2609 + 自己的供电"这个模块。
- **VG 走 GND3**：VG 要从射频线上方到下方；它在芯片右侧和 RFOUT 第一个屏蔽孔（15.80, 30.09/33.31）之间的缝里穿过，离两边孔各 0.20 mm，**不需要拆屏蔽孔**，GND2 保持完整。在 y = 36.6～39.6 绕到 x = 14.6 是为了避开 C12 的接地孔 (15.55, 37.91)。
- **新 VD 线接在原有 VD 线 (17.4, 46.88) 上，新 VG 通过 (15.2, 28.4) 过孔和一小段顶层线接在原有 VG 竖线 (13.70, 28.4) 上。** 原有的 J3、J4 保留当测量点（在切口外）。
- **LTC3260 的 EN−（13 脚）接 +5 V（12 脚）**，不是 12 V——这是有意的（12 V 走不过去，效果一样）。
- 6 根底层跳线、5 段 GND3 走线都是为了避开顶层交叉，坐标已经过检查。

---

## 8　出问题怎么办

| 现象 | 处理 |
|---|---|
| 某次调用超时 / DelphiScript 崩了 | 等几秒 `app_ping`；不行就记录，人工重启 StartMCPServer 才能继续——此时**停在当前阶段**并保存已完成部分 |
| 模态对话框卡住 | `app_list_open_dialogs` 看是什么；只按 OK/Cancel，不确定就 Cancel 并停 |
| 文字变成 `?` | 有非 ASCII 字符，改成 ASCII |
| 读回坐标和数据差一个固定量 | 偏移没加对，回第 3 节 |
| 读回坐标差 0.0x mm 级别 | Altium 网格吸附；用属性直接写坐标，不要用拖动 |
| 层名找不到 GND3 | 列出层；用"第 2 个内层"（MidLayer2）；还不确定就停 |
| 工具只收整数 mil（`pcb_set_board_shape`、`pcb_place_components`、规则数值） | 先放，再用 `obj_batch_modify` 改成精确值；板形 1 mil 误差可以接受，记日志 |
| `pcb_get_unrouted_nets` 说 0 | **不可信**（第一次实跑铺铜删掉时它也报 0），以 DRC 的 Un-Routed Net 为准 |
| DRC 报告里没有 Routing Via Style 这一项 | 读出全部过孔，逐个对 0.5～0.7 / 0.25～0.4 mm 检查，写进报告 |
| 读到的坐标是整数 mil，删除对象按坐标匹配不上 | 板上存的是小数 mil；用 `obj_batch_delete` 带精确 X/Y/Net 过滤，或按对象 ID 删 |
| ECO 里有 Remove | 取消，停 |

**停止的时候**：保存（不要保存到一半的批量操作也可以，Altium 有撤销），写日志和报告。

---

## 9　日志和报告

- `AGENT_LOG.md`（工程文件夹里）：每个阶段一段，写做了什么、调用了哪些工具、核对数字（例如"删除缝合孔 333 个"、"pcb_get_unrouted_nets: 仅 GND"）。
- `AGENT_REPORT.md`（结束时）：
  1. 完成到哪个阶段；
  2. 校准得到的偏移 (dx, dy)；
  3. 各阶段核对结果（数量对不对）；
  4. DRC 汇总表（每条规则的违规数）；
  5. 没做完 / 跳过的步骤和原因；
  6. 需要人第二天确认的事（截图位置、怀疑的地方）。

人类用户第二天会对照 `7_完成指南\完成步骤总指南.html`（人类版，同一套坐标）检查结果。
