# 直接改 PcbDoc 文件（工具做不了的事）

eda-agent 转不了文字方向、碰元件位号文字有崩溃风险、改不了板区域。这些事规划端可以绕开 AD，直接改 `.PcbDoc` 文件里的固定长度字段，再让 AD 重新打开读回。QPA2609 第三轮用这个办法改了 35 条文字和板区域，DRC 全过。

脚本：`scripts/pcbdoc_io.py`（格式说明在文件开头的注释里）。第三轮的完整用法见 `examples/qpa2609/round3/apply_patch.py`。

## 什么时候用

- 文字：改旋转、改层（包括属于元件的位号和封装自带文字）、精确坐标、字高、线宽。
- 板区域（Layer Stack Region）：改板框后让它跟上。
- 只改**固定长度**的字段。要改长度的（文字内容、增删对象）不要做，交给 eda-agent（`obj_modify` 改 Text、`pcb_place_text`、`obj_delete`）或人。

## 流程（顺序不能乱）

1. **AD 里能做的先做完并保存**（删对象、改文字内容、放新字），读回确认。
2. **关闭工程**：`proj_close(save=false)`（第 1 步已保存，不会丢）。`proj_list_open` 确认它不在了。然后用写模式打开一次文件，确认没被锁：
   `python -I -c "open(r'<PcbDoc>','r+b').close()"`
3. **按内容找记录、空跑**：用"文字内容 + 所属元件 + 层 + 坐标"在 `read_texts()` 里找每一条要改的记录，核对数量（例如"10 个位号 + 12 个字 + 13 个封装文字 = 35"），有任何一条找不到或多于一个就停。**不要用上一次解析得到的偏移**：AD 每保存一次，偏移都会变。
4. **备份**：把要改的文件复制到备份文件夹（`<备份根目录>\<工程>_<时间>_<说明>\`）。
5. **改**：`patch_texts(path, [(off, {...}), ...])`、`region_move_edge(path, 'y', old, new)`。
6. **离线核对**：重新解析，逐条比对期望值；`python -I pcbdoc_io.py v7check <PcbDoc>` 必须是 0。
7. **让 AD 重新打开并读回**（派子代理）：`proj_open` → `proj_load_sheets` → `pcb_focus_board` → `obj_query` 逐条比对期望清单（CSV），再看统计数（元件、过孔、焊盘、铺铜、未连接）和板框没变。**这一步不能省**——第三轮第一次改完离线核对全对，AD 读回却有 21 条没生效（见下面"层号存两份"）。
8. DRC，保存。

## 格式要点和踩过的坑

| 要点 | 说明 |
|---|---|
| 坐标单位 | 1e-4 mil，int32，绝对坐标（和 eda-agent 读到的 X/Y 一致，差 < 0.04 mil） |
| 文字记录 | `Texts6/Data`：类型字节 5 + u32 长度 + 第一子记录（AD 23 是 252 字节）+ 第二子记录（u32 长度 + 文字） |
| **层号存了两份** | @0 旧层号（u8），@226 V7 层号（u32）。**AD 读 @226。** 只改 @0 的结果：普通文字看不出问题（层没变），属于元件的文字挪层全部无效。Top Overlay = `0x01030006`，Mechanical13 = `0x0102000D`；别的层从文件里已有记录学（`patch_texts` 会自动学，学不到就报错） |
| 所属元件 | @7 u16，是 `Components6` 里的序号；65535 = 普通文字。`component_names()` 给出序号对应的位号 |
| 特殊字符串 | 封装自带的 `.Designator` 在文件里就是 `.Designator`，eda-agent 读出来却是显示后的位号 |
| 板区域 | `BoardRegions/Data`：属性串（`OBJECTKIND=BoardRegion|...|LAYERSTACKID={...}`）之后，1 个字节，u32 顶点数，再是 (x, y) double 对 |
| Autoposition | 在 `Components6` 的属性串里（`NAMEAUTOPOSITION`）；QPA2609 里没有这个键（默认 Manual），没改 |
| 改完 AD 打开无提示 | 只改固定长度字段，AD 23 打开时没弹修复框，modified=false |

## 和执行端的配合

- 改文件前后各有一个 AD 步骤，派同一个子代理最省（它记得上下文）：先"做完 AD 那部分 → 保存 → 关工程，停下"，规划端改完再发消息"重新打开 → 读回 → DRC → 保存"。
- 给子代理一份期望清单 CSV（`Text, Owner, IsDesignator, Layer, X, Y, Rotation, Height, Width`），让它逐行报 OK / 不符；**任何一行不符就停，不保存**（第三轮靠这条规矩挡住了把半成品存进去）。
