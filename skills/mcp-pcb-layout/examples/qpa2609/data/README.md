# QPA2609 数据表：每张表是什么、怎么算出来的、执行端怎么用

这些是第一、二轮交给执行端的**真实数据**（`8_AI代理包\`、`9_第二次修改\`），格式说明在 `references/data-package.md`，计算方法在 `references/rf-board-calcs.md`。这里逐表讲：每一列的意思、数字从哪来、执行端拿它做什么、读回时按什么标准核对。

## 共同约定（所有表都一样）

- **坐标原点**：板左下角（用户原点）。`*_mm` 是设计用的值，`*_mil = mm / 0.0254`，保留 3 位小数。
- eda-agent 用 **mil、绝对坐标**。写入时 `绝对 = *_mil + (DX, DY)`，读回时先减 (DX, DY) 再比。偏移由执行端开工时用 U1 / J1 / J3 校准得到（QPA2609：DX = 4755.000，DY = 1734.969 mil）。原理图坐标（图纸 mil）**不加**偏移。
- 所有文字 ASCII（`10uF`、`22R 2W`、`604R`），eda-agent 会把 U+00FF 以上的字符变成 `?`。
- CSV 用 UTF-8 带 BOM（Excel 直接打开不乱码）；JSON 是全集，CSV 是按类拆开的。
- 所有表都由**同一个坐标源**（`pmod.py`）用脚本生成（`export_agent.py`），不手抄；生成前自检必须 0 错误（`prender.py check()`：不同网络间距 ≥ 0.20 mm、0 短路、0 漏连、外框不重叠、在切口内、离板边 ≥ 0.4 mm、孔距 ≥ 0.25 mm、阻焊桥 ≥ 0.08 mm）。

---

## `module_design.json`（全集）

`meta`、`components`、`nets`、`no_connect`、`vias`、`track_segments`、`keep_vias`。`meta` 里是执行端开工前必须知道的东西：

| 字段 | 值 | 用途 |
|---|---|---|
| `units_note` | 原点、mm/mil 换算、要先校准 | 防止执行端直接把 mm 当 mil、或忘了加偏移 |
| `board_mm` | [0, 0, 25.4, 108.5] | 新板框 |
| `cut_lines_x_mm` | [6.0, 19.4] | 模块切口：供电元件必须全在中间（拼整板时整条切下来） |
| `calibration_refs` | U1 (12.70, 31.70) 0°、J3 (19.73, 49.40)、J1 (2.97, 31.70) 90°、J2 (22.43, 31.70) 270° | 算偏移 + 验证角度方向。挑**射频部分里位置最确定的元件**，不共线，带不同角度 |
| `expected_counts` | 新元件 47、新过孔 45、新线段 155、保留过孔 137、要删的缝合孔 333、要删的铺铜 4、网络 27 | 每个阶段的核对门槛："正好等于"才继续 |

## `components.csv`（47 行）

`designator, lib_file, lib_ref, footprint, value, x_mm, y_mm, x_mil, y_mil, rotation_deg, layer, outside_cut`

- **x/y = 封装原点**，不一定是元件中心：下载库的原点一般在中心，但 3296W 电位器原点在 3 脚、排针 HDR1X2 在 1 脚。坐标是"让焊盘落在规划位置"反推出来的。
- `rotation_deg`：AD 的 Rotation，逆时针为正。
- `footprint` 必须是库里的真名：AD23 自带库英制 0603 叫 `1608[0603]`（名叫 `0603` 的是英制 0201）、0805 叫 `6-0805_N`。自带 Res2 / Cap 的默认插件封装必须换掉。
- `outside_cut=True`：测试用、拼整板时切掉的（P101 电源插针、TP103 测试点）。
- 执行端用法：放置后用 `obj_batch_modify` 把整数 mil 改成精确值（`pcb_place_components` 只收整数）。核对：位置误差 0、角度一致。

## `nets.csv`（27 行）+ `no_connect`

`net, pins`（`位号-脚号` 空格分隔）。

- 原理图按这张表连；脚号以库里焊盘的 Designator 为准（逐个读库确认：LT3094 底部焊盘叫 `13` 且接 N5V **不是地**；LTC3260 / LT3045 底部焊盘叫 `EPAD` 接 GND）。
- **跨页 / 跨原有设计的网络**要能核对：编译后 `VD` 必须同时含 `J3-1`（原射频页）和 `FB101-2`（新供电页），`VG` 同时含 `J4-1` 和 `FB102-2`。这是"供电真的接到射频芯片上了"的证据。
- `no_connect`：U101-8、U101-9、U102-7、U103-5 不接（编译后会各自成单脚网络，属于正常）。
- 核对：编译后 27 个网络逐个"脚集合完全相等"。

## `pad_nets.csv`（133 行）

`designator, pin, net, x_mm, y_mm` —— 每个焊盘**期望的中心坐标和网络**。

- 怎么算：元件放置坐标 + 旋转 + 库里读出的焊盘相对坐标（olefile 读 PcbLib：焊盘偏移、尺寸、形状、旋转；旋转 90/270 时 X/Y 尺寸要交换）。
- 为什么最重要：**一张表同时验证原理图连接、封装选对没有、坐标、旋转**。摆完后执行端逐个读回焊盘中心和网络，误差 < 0.01 mm。
- 不一致时的处理写死在说明书里：两脚无极性元件网络对调 → 转 180°；有极性 / 多脚的 → 原理图连错了，回去改，不准转。

## `vias.csv`（45 行）

`no, net, x_mm, y_mm, x_mil, y_mil, hole_mm, diameter_mm, hole_mil, diameter_mil`

- 0.25 / 0.5 mm（9.843 / 19.685 mil），在 Routing Via Style 范围内（孔 0.25～0.4、直径 0.5～0.7）。
- 网络必须填：没网络的过孔会被间距规则挡住，或者和铺铜"短路"。
- 用途：芯片底部焊盘散热孔、去耦电容接地孔、跳线换层孔（Bottom、GND3）。

## `track_segments.csv`（155 段 = 105 根线）

`track_no, step, step_name, net, layer, width_mm, width_mil, x1_mm, y1_mm, x2_mm, y2_mm, x1_mil, y1_mil, x2_mil, y2_mil`

- 一根线拆成多段，同一 `track_no`；`step` S1～S7 和人类版指南的分段一致（输入、LTC3260、LT3094、门卫、LT3045、底层跳线、GND3）。
- **顺序已排好**：每段的起点必须是已存在的焊盘中心、过孔中心或之前画好的线（生成表格时检查过），执行端照顺序画就不会出现悬空线。
- 线宽只有 0.3 / 0.5 / 0.8 mm 三种（直流线；电流大的 12 V 主线 0.8）。射频线不在这张表里，射频部分一根都不动。
- 层：Top 139 段、Bottom 11 段（6 根跳线）、**GND3 5 段**（VG 从射频线下面穿过去，GND2 整层保持完整，因为它是射频线的参考地）。
- 核对：不分方向逐段几何匹配（起终点、宽度、网络、层）。

## `keep_existing_vias.csv`（137 行）

`kind, x_mm, y_mm, x_mil, y_mil` —— **原有设计里必须保留的手放过孔**，删除操作的白名单。

| kind | 个数 | 是什么 |
|---|---|---|
| `U1 centre pad` | 25 | 芯片底部焊盘 5 × 5 散热 / 接地孔，间距 0.55 |
| `fence RFIN` / `fence RFOUT` / `fence THRU` | 14 / 14 / 46 | 射频线两侧屏蔽孔，离线中心 1.61 mm、间距 ≤ 0.6 mm |
| `connector J1/J2/J7/J8 (0.4/0.7)` | 各 8 | SMA 接地孔 |
| `cap C3…C18` | 各 1 | 去耦电容接地孔 |

- 怎么用：删旧缝合孔时 = 全部过孔 − 白名单（容差 0.02 mm），**剩下的必须正好 333 个**才删。
- 第一轮教训：这张表按记录建模，两个过孔差了 0.13 mm（执行端用 6 mil 容差才对上）；以后尽量从真实板子读。

## `required_vias_asbuilt.csv`（182 行，第二轮）

格式同上，= 137 原有 + 45 第一轮新放（**按实际做成的坐标**，含执行端挪过 0.03 mm 的那个）。第二轮所有删除都先排除它，删完数一遍，182 个必须都在。

## `stitch_vias.csv`（602 行）

格式同 `vias.csv`，网络 GND。算法见 `references/rf-board-calcs.md` 第 5 节：1.5 mm 网格、隔行错开 0.75 mm；离射频线铜边 ≥ 1 mm、离别的网络的铜 ≥ 0.2 mm、离已有过孔中心 ≥ 0.75 mm；不压焊盘、元件外框、丝印字；离板边 ≥ 0.75 mm。

- 和原设计比密度：原 51.4 mm 那块范围内原来 333 个，新表 316 个，同一水平。
- 这张表**同时是"允许删除清单"**：DRC 筛孔时只能删表里的孔（超过 20 个就停）。
- 第二轮实际被 DRC 筛掉 1 个（#182 离原板 VG 线 0.025 mm）：原板的非射频走线没进模型。

## `silk.json`

```
text_height_mm 1.0, stroke_mm 0.16, layer Top Overlay, font Default (stroke)
labels: [{kind: designator|string, ref, text, x, y, rot}, ...]   21 条（10 位号 + 11 功能字）
hide_designators: [...]                                           37 个
```
- `x, y` = 文字框左下角（rot 0）；rot 90 从下往上读，x,y 仍是 AD 报告的文字位置点。
- 第二轮的 silk.json 有两处不足（第三轮修掉）：没避开封装自带的 Top Overlay 线和文字，字宽靠估；没写"转不了方向 / 藏不了位号时怎么办"。第三轮的最终位置见 `../round3/placement.json`。

## `schematic_layout.json`

原理图的**精确坐标**（图纸 mil，不加 PCB 偏移）：`components`（47，位置 + 旋转）、`wires`（129 段 200 mil 短线，从脚端向外拉）、`net_labels`（93，线外端）、`power_ports`（36，GND 符号，方向 270）、`no_connect_pins`（4）、`extent`（图纸范围）。

- 怎么算：从 SchLib 读每个符号的脚端点和方向，按功能分组排网格，每个脚向外拉一段短线，线端放网络标号；自查"不同网络的端点不重合、单元格不重叠"。
- 执行端放完第一个元件就读回它的脚端坐标，和期望比——符号原点和想的不一样时，所有脚会差同一个偏移，第一个元件就能发现。

## `ops_samples.jsonl`（每种操作一条，共 46 种；完整版 1353 条）

一行一个操作：`{"id", "phase", "op", "params", "verify", "on_fail"}`。

- `params` 里带 `_mil` 后缀的是 PCB 坐标（写入时加偏移），不带后缀的是原理图坐标。
- `verify` 是能量化判断的一句话（"读回 182 个必须全在"），`on_fail` 只有 STOP / LOG_CONTINUE / SKIP_PHASE / REPORT 几种，在 RUNBOOK 里逐个解释。
- 每阶段最后一条 `SAVE_AND_LOG`（带 marker，续做时找断点）。
- 复杂流程（删缝合孔、DRC 筛孔、焊盘核对）写成**一个** op，步骤写在 RUNBOOK 里。
- 第 0 阶段的 `TOOL_MAP`：先把每种 op 对应的真实工具名和参数名查出来写进日志，缺了当场停。

`ops_round2_head.jsonl` 是第二轮差量包的开头几行 + 丝印几行。
