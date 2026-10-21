# RUNBOOK_HAIKU — 给执行模型的逐条操作规则

> 读者：通过 eda-agent MCP 操作 Altium Designer 23 的**执行模型**（Haiku 级别）。
> 你的工作只有一件事：**把 `ops.jsonl` 从上到下一行一行做完。**
> 不要设计、不要优化、不要改坐标、不要跳行。数据已经在另一台电脑上全部算好、检查过。
> 遇到本文件没写到的情况：**保存、写日志、停**。宁可停，不要猜。

---

## 1　开始之前（每次启动都做）

1. 打开工程文件夹里的 `AGENT_LOG.md`（没有就新建）。
2. 找到最后一行 `OK` 或 `SKIP` 的 op id（例如 `P8-017`）。从**下一行**开始做。没有任何记录 → 从 `P0-001` 开始。
3. 如果 AGENT_LOG 里已经有 `TOOL_MAP` 段和 `OFFSET DX=… DY=…`，直接拿来用，不要重新猜。
   - 但 P0 没做完的话，先把 P0 重做一遍。

## 2　主循环（每一行 op 都完全按这 8 步）

```
for 每一行 op in ops.jsonl（从断点开始）:
  1. 读 op 的 id / op / params / verify / on_fail
  2. 在 TOOL_MAP 里找这个 op 类型用哪个工具、参数名叫什么
  3. 换算坐标（第 3 节）
  4. 查重：同样的对象已经存在？→ 记 "SKIP 已存在"，跳到第 8 步
  5. 调用工具
  6. 按 verify 读回核对（读回的 PCB 坐标先减偏移再比较）
  7. 核对不通过 → 按 on_fail 处理（第 4 节）
  8. 在 AGENT_LOG.md 追加一行：<id> OK|SKIP|FAIL <一句话>
```

- **批量**：连续多行是同一种 op（例如 155 行 PCB_TRACK），可以一次调用发最多 **30** 个对象。发完以后仍然要**逐个**核对，日志也逐行写（可以写成 `P9-001..P9-030 OK`）。
- 每个阶段最后一行是 `SAVE_AND_LOG`：调用 `app_save_all`，日志写 `<marker>`（例如 `P8 DONE`）。
- 每次调用默认 10 秒超时；一批超时了就把批量减半重试一次，再不行按 on_fail。

## 3　坐标换算（最容易错的地方）

| 数据里的字段 | 属于 | 怎么用 |
|---|---|---|
| `x_mil` `y_mil` `x1_mil` … `y2_mil`（P0、P3、P5～P12） | **PCB** | 写入值 = 数据值 **+ DX / + DY**；读回值 **− DX / − DY** 后再和数据比 |
| `x` `y` `x1` … `y2`（P2，没有 `_mil` 后缀） | **原理图**（图纸 mil） | **不加偏移**，直接用 |
| `*_mm`（只在 json 里供参考） | — | 不要直接用；一律用 `_mil` 的值 |

**DX、DY 怎么来（op P0-004 CALIBRATE）**：读 U1 的位置（mil），
`DX = U1.x − 500.000`，`DY = U1.y − 1248.031`。写进日志：`OFFSET DX=… DY=…`。

例子：读到 U1 = (1500.000, 2248.031) → DX = 1000，DY = 1000。
op `P8-001` 过孔 `x_mil=389.764, y_mil=2188.976` → 实际写入 (1389.764, 3188.976)。

**核对**：J3 应在 (776.772, 1944.882) mil、J1 在 (116.929, 1248.031) mil（数据值，读回减偏移后比较）。误差 > 0.5 mil → 停。

**旋转**：`rotation` 是度，直接写；读回必须完全相等（0/90/180/270）。

**层名**：数据里写 `Top Layer`、`GND2`、`GND3`、`Bottom Layer`、`Mechanical 1`、`Top Overlay`。如果工具要层编号：GND2 = MidLayer1（第 1 内层），GND3 = MidLayer2（第 2 内层）。P0 盘点时把工程里的真实层名写进日志，以后照那个写。

## 4　on_fail 是什么意思

| on_fail | 你要做的 |
|---|---|
| `STOP` | 不要再试别的办法。`app_save_all` → 日志写 `FAIL` 和读回值 → 写 `AGENT_REPORT.md` → 结束。 |
| `LOG_CONTINUE` | 日志写 `FAIL` + 原因，继续下一行。 |
| `CONTINUE` | 同 LOG_CONTINUE（可选步骤）。 |
| `SKIP_PHASE` | 撤掉本阶段已加的临时东西（例如临时规则 RF_to_Via），日志写 `SKIP`，跳到下一个阶段第一行。 |
| `SEE_RUNBOOK_P5` | 看第 6.4 节。 |
| `REPORT` | 不修，把结果完整写进报告，继续做 P14。 |

**同一行最多重试 1 次**（而且只能是：重新换算坐标、减小批量、关掉弹窗）。第 2 次还不对就按 on_fail 走。

## 5　TOOL_MAP：每种 op 用哪个工具（P0-002 时核对并写进日志）

> 下表的工具名来自 eda-agent 的文档，**没有在真机上逐个试过**。P0-002 时用 `tool_catalog` 列出全部工具，对每一行用 `tool_guide <工具名>` 看真实参数名，把「op 类型 → 工具名 → 参数名」写进 AGENT_LOG 的 `TOOL_MAP` 段。表里第一个不存在就用第二个。全都不存在：on_fail 是 STOP 的类型 → 现在就停；其他类型 → 记下来，到时 SKIP。

| op 类型 | 首选工具 | 备选 | 核对用的读取工具 |
|---|---|---|---|
| CONNECT | `app_attach`、`app_ping` | — | — |
| INVENTORY / CALIBRATE | `pcb_get_components`、`obj_query` | `pcb_get_vias`、`pcb_get_polygons` 之类 | 同左 |
| SMOKE_TEST | `pcb_place_vias`、`pcb_place_tracks` | — | `obj_query`；删除用 `obj_delete` 之类 |
| COPY_FILES | 文件复制（shell / 文件工具） | — | 列目录 |
| ADD_DOCUMENT | `proj_add_document` | — | `proj_get_documents` 之类 |
| NEW_SCHDOC | 创建文档的 `proj_*` 工具 | `app_run_ui_command` / `app_click_menu`（File→New→Schematic，再另存为 Power.SchDoc） | 工程文档列表 |
| SET_SHEET_SIZE / SET_NET_SCOPE | `sch_set_document_options` / `proj_set_options` 之类 | 跳过 | `proj_get_options` |
| SCH_PLACE | `sch_place_components` | — | `get_sch_doc_pins`（脚端坐标） |
| SCH_SET_FOOTPRINT | `lib_link_footprint` | `sch_set_components_parameters`、`obj_modify` | 读元件的模型列表 |
| SCH_WIRE | `sch_place_wires` | — | 读导线 |
| SCH_NETLABEL | `sch_place_net_label` | — | 读网络标号 |
| SCH_POWERPORT | `sch_place_power_port` | — | 读电源符号 |
| SCH_COMPILE | `proj_compile` | `proj_force_recompile` | — |
| SCH_VERIFY_NET | `proj_get_connectivity_many` | `obj_crossref_net` | 同左 |
| SCH_ERC | `run_erc` | `design_validate` | 消息列表 |
| SET_ACTIVE_DOC | 打开/激活文档的工具 | — | — |
| PCB_DELETE_STITCH_VIAS | 读全部过孔 + 删除对象的工具 | — | 过孔计数 |
| PCB_DELETE_POLYGONS | 读多边形 + 删除 | — | 多边形计数 |
| PCB_DELETE_LINE / PCB_LINE | 读/删/放 Track（Mechanical 1 层） | — | 读回 |
| PCB_SET_BOARD_SHAPE | `pcb_set_board_shape` | — | 读板框 |
| ECO_SYNC | `pcb_place_components`（synced 模式，带 UniqueId 和焊盘网络；第一次实跑用的就是它） | `proj_sync_pcb`（会弹模态框，用 `app_list_open_dialogs`、`app_drive_dialogs`） | 读元件、读焊盘网络 |
| PCB_LIB_KEEPOUT_TO_MECH15 | `obj_batch_modify`（Region 的 Layer 改 Mechanical15） | — | 读 Region |
| DRC_PRUNE_NEW_VIAS | DRC（同 DRC 行）+ `obj_batch_delete` | — | 违规列表、过孔计数 |
| PAD_CONTAIN_CHECK | `obj_query` 读焊盘 | REPORT | — |
| PCB_DELETE_ROOMS_NEW | 读 Room + 删除 | — | — |
| PCB_MOVE | `pcb_move_components` | `obj_modify` | 读元件 + 读焊盘（位置、网络） |
| PCB_SET_PAD_HOLE | `obj_modify`（Pad 的 HoleSize） | 跳过 | 读焊盘 |
| PCB_RULE / PCB_RULE_SET / PCB_RULE_DELETE | `pcb_create_design_rule`、`pcb_set_rule_properties`、`pcb_delete_design_rule` | — | 读规则（Minimum Solder Mask Sliver 改不了，属正常，LOG_CONTINUE） |
| PCB_VIA | `pcb_place_vias` | — | 读过孔 |
| PCB_TRACK | `pcb_place_tracks` | — | 读线段 |
| PCB_VERIFY_UNROUTED | `pcb_get_unrouted_nets` | DRC 的 Un-Routed Net 项 | — |
| PCB_POLYGON_RECT | `pcb_place_polygon_rect` + `pcb_modify_polygon` | — | 读多边形属性 |
| PCB_REPOUR_ALL | `pcb_repour_polygons` | — | — |
| SILK_HIDE_DESIGNATOR / SILK_SET_DESIGNATOR | `obj_modify` / `pcb_set_component_properties` 之类（改位号文字的 Hide、位置、角度、字高、线宽、Autoposition=Manual） | 跳过 | 读文字 |
| SILK_STRING | 放 PCB 文字（String）的工具 | 跳过 | 读文字 |
| DRC | `pcb_run_drc`（模态）| `run_drc` + `pcb_get_clearance_violations` | 违规列表 |
| SAVE_AND_LOG / SAVE_ALL | `app_save_all` | — | — |

## 6　几种复杂 op 的固定做法

### 6.1　SCH_PLACE（原理图放元件）
1. 放元件：库文件 `library`、库元件名 `lib_ref`、位置 (`x`,`y`)、旋转 0、位号 `designator`、参数 Value 和 Comment。
2. 读这个元件每个脚的端点坐标，和 `expect_pin_ends` 比（±1 mil）。
3. 全部脚都差同一个 (dx,dy) → 把元件挪 (−dx,−dy)，再比一次。还不对 → STOP。
4. **第一个元件 P2-004（P101）必须做完第 2 步再放后面的。** 后面的元件也逐个核对。

### 6.2　SCH_VERIFY_NET
读这个网络连着哪些脚。要求：`pins` 里每个脚都在；`must_also_contain` 里的脚也在（这是射频页的脚，证明两页连上了）；而且 `pins` 里没有任何一个脚出现在别的网络里。
不通过 → 先回头核对这个网络相关的 SCH_WIRE / SCH_NETLABEL 坐标有没有放错，**只改放错的那一个**，重新 SCH_COMPILE 再核对。还不对 → STOP（P2 的门槛：原理图不对，后面全部白做）。

### 6.3　PCB_DELETE_STITCH_VIAS（删 333 个缝合孔）
1. 读出全部过孔（应 470 个），每个减偏移。
2. 和 `keep_existing_vias.csv` 的 137 个比：坐标差都 < 0.02 mm（0.787 mil）算同一个。
3. 不在保留表里的 = 要删的。**正好 333 个**才删；不是 333 → STOP，把多出来/少了的坐标写进日志。
4. 删完再数：剩 137 个。

### 6.4　SEE_RUNBOOK_P5（摆放后焊盘核对不过）
- 位置对、但两个焊盘的网络正好对调，而且元件是 R*、C*、FB*、F101 → 把 rotation 加 180（超过 360 减 360）再核对一次。日志写清楚。
- 是 D101、LED101、U101～U103、Q101、Q102、RV101、P101 → **不要转**，STOP（原理图连错了，要人看）。
- 位置差一个固定量 → 偏移没加对，回第 3 节重新校准，STOP 前先确认。

### 6.5　ECO_SYNC（原理图同步到 PCB）
1. 先 SET_ACTIVE_DOC 让 PCB 成为活动文档。
2. 调 `proj_sync_pcb`，弹出 Engineering Change Order 对话框后用 `app_list_open_dialogs` 读变更列表。
3. 数 Add Component：必须 47。**出现任何 Remove Component / Remove Net → 点 Cancel，STOP。**
4. 只有 Add / Change 类 → Execute Changes → Close。
5. 只删本次新出现的 Room（名字一般是 `Power`），别的对象不碰。

### 6.6　缝合孔：DRC_PRUNE_NEW_VIAS 和 PAD_CONTAIN_CHECK
缝合孔按 `stitch_vias.csv` 逐个用 PCB_VIA 放（**不用** `pcb_place_stitching_vias`）。放完：
1. DRC_PRUNE_NEW_VIAS：RF_to_Via 规则开着、重铺后跑 DRC。每条违规看两个对象：其中一个是 `stitch_vias.csv` 里的孔（加偏移后 1 mil 内）→ 删掉**这个孔**。其他违规只记录。删了超过 20 个 → STOP。
2. PAD_CONTAIN_CHECK：读全部焊盘（X、Y、XSize、YSize、Rotation）。旋转 0/180 用 XSize×YSize 的矩形，90/270 交换，其他角度按半径 max(XSize,YSize)/2 的圆；各向外扩 0.25 mm。`stitch_vias.csv` 里的孔心落在里面 → 删掉。
3. 两步都**只删 `stitch_vias.csv` 里的孔**。删完检查：`keep_existing_vias.csv` 137 个 + `vias.csv` 45 个必须全在，少一个都 STOP。

### 6.7　DRC
- 要求这些项为 0：Clearance、Short-Circuit、Un-Routed Net、Width、Routing Via Style、Hole Size、Hole To Hole、Minimum Solder Mask Sliver。
- Silk To Solder Mask、Silk to Silk 不为 0 也没关系，不处理。
- 不为 0：**不要自己修**。把每条违规（规则名、两个对象、坐标减偏移后的值）写进报告，交给人。

## 7　绝对不能做的事

1. 不移动、不删除、不修改射频部分：U1、J1～J8、C3/C6/C9/C12/C15/C18、原有 RFIN/RFOUT/THRU/VD/VG 走线、`keep_existing_vias.csv` 的 137 个过孔、阻焊开窗 Fill。（P6 只改 P101、TP103，J3～J6 不碰。P5 只把 D101、FB101、FB102、LED101 自带的 9 块禁布区移到 Mechanical 15。）
2. 不改叠层、不改原点、不改已有规则的数值（P7、P11 列出的除外）。
3. 不执行任何 Remove 类 ECO。
4. 文字只用 ASCII（`Ω` `µ` 中文会变成 `?`）。数据里的 Value 已经是 ASCII，照抄。
5. 不改任何坐标、线宽、层、网络；不加数据里没有的对象；DRC 报错不自己改线。
6. 不跳行。上一行没有 OK / SKIP，就不做下一行。

## 8　日志格式（AGENT_LOG.md）

```
# AGENT_LOG
TOOL_MAP
  PCB_VIA -> pcb_place_vias(net, x, y, hole_size, size)
  ...
OFFSET DX=1000.000 DY=1000.000
LAYERS Top Layer | MidLayer1=GND2 | MidLayer2=GND3 | Bottom Layer

P0-001 OK app_ping ok, project QPA2609_test.PrjPcb
P0-003 OK vias=470 polygons=4 components=...
...
P3-002 OK deleted 333 stitching vias, remaining 137
P5-0xx FAIL Cxxx pad 1/2 nets swapped -> rotation+180 -> OK
P0 DONE / P1 DONE / ...
```

停下时还要写 `AGENT_REPORT.md`：做到哪一行、偏移、每阶段核对数字、DRC 汇总、跳过了什么、需要人第二天看什么。

## 9　顺序一览（为什么是这个顺序）

| 阶段 | 做什么 | 为什么排在这里 |
|---|---|---|
| P0 | 连接、对工具、盘点、校准偏移、试放一个过孔一根线再删掉 | 单位、偏移、层名错了，后面全错；越早发现越好 |
| P1 | 加 20 个库 | 原理图要用 |
| P2 | 原理图（47 元件、129 导线、93 标号、36 地符号）→ 编译 → 核对 27 个网络 | **门槛**：网络不对，PCB 全部白做 |
| P3 | 删缝合孔、删 4 块铺铜、换板框 | 必须在 ECO 之前：旧铺铜会挡住新元件；板框不扩大元件放不进去 |
| P4 | 同步到 PCB | 新元件出现在 PCB 上 |
| P5 | 摆 47 个元件，逐个核对焊盘网络 | 走线端点都依赖焊盘位置 |
| P6 | 改孔径（可选） | 不影响后面 |
| P7 | 两条阻焊规则 | 在放线之前定好，DRC 才对 |
| P8 | 45 个过孔 | 走线要接到过孔上 |
| P9 | 155 段走线 → 核对只剩 GND 没连 | GND 靠铺铜连，所以铺铜要在走线之后 |
| P10 | 4 层铺铜 → 重铺 → 核对全部连通 | 铺铜会自动让开走线和过孔 |
| P11 | 按坐标表放缝合孔 → DRC 筛 → 删临时规则 | 要在铺铜之后；DRC 只能删表里的新孔 |
| P12 | 丝印 | 不影响电路，放在最后；失败可以跳过 |
| P13 | DRC | 最终检查 |
| P14 | 保存、写报告 | — |
