# QPA2609 AI 画板 skill（Claude Code）

用 Claude Code + eda-agent MCP 在 Altium Designer 23 里按坐标改射频链路板的一套 skill，经过 QPA2609 测试板三轮实跑（两轮远程数据包 + 一轮本机子代理）整理而成。

**核心做法**：主会话（规划端）把设计一次想清楚、算出每个坐标并自检；执行端（Sonnet / Haiku 子代理，或另一台电脑上的代理）只照清单施工、逐项读回、不符就停；工具做不了的由主会话直接改 PcbDoc 文件；DRC 报告文件是最后的裁判。

## 目录

```
skills/
  mcp-pcb-layout/          主 skill（只在明确要求时加载）
    SKILL.md               入口：两种工作方式、工作循环、17 条经验、硬规矩、文件地图
    references/            射频板计算方法、规划流程、清单、子代理任务模板、执行端规则、
                           eda-agent 的坑、PcbDoc 二进制格式、数据包格式、经验完整版
    scripts/               pcbdoc_io / pcblib_inventory / drc_report / silk_geom
    examples/qpa2609/      完整实例（从 README.md 开始读）
      design_basis/        设计依据原文：统一设计标准、阻抗线宽、板厚、偏置供电
      data/                交给执行端的全部数据表 + 逐表说明
      manuals/             四份说明书原文 + 每一节为什么要有
      subagent_dispatches/ 12 次派子代理的真实往返（任务原文、汇报原文、讲解）
      round3/              第三轮（丝印修复）用的脚本和数据原样
  eda-agent/SKILL.md       调用 eda-agent 的规矩：只派 Sonnet/Haiku 子代理、只读默认、一次一个客户端
agents/
  eda-agent-operator.md    执行子代理的定义（model: sonnet）
```

推荐阅读顺序：`skills/mcp-pcb-layout/SKILL.md` → `references/rf-board-calcs.md` → `examples/qpa2609/README.md`。

## 安装

1. 把 `skills/` 和 `agents/` 下的内容复制到 `~/.claude/skills/`、`~/.claude/agents/`（Windows：`C:\Users\<用户名>\.claude\`）。
2. 安装 eda-agent 0.7.1，在 Claude Code 里加成用户级 MCP，服务名必须叫 `eda-agent`。下面路径按自己电脑改：

   ```
   claude mcp add-json --scope user eda-agent '{
     "type": "stdio",
     "command": "E:\\Altium_designer\\auto_MCP\\.venv\\Scripts\\python.exe",
     "args": ["-m", "eda_agent", "serve", "--headless"],
     "env": {
       "EDA_AGENT_BACKEND": "altium",
       "EDA_AGENT_HEADLESS": "1",
       "EDA_AGENT_POINTER_FILE": "E:\\Altium_designer\\auto_MCP\\workspace-path.txt",
       "EDA_AGENT_SCRIPTS_DIR": "E:\\Altium_designer\\auto_MCP\\scripts",
       "EDA_AGENT_TOOLSET": "minimal",
       "EDA_AGENT_WORKSPACE": "E:\\Altium_designer\\auto_MCP\\workspace",
       "PYTHONUTF8": "1"
     }
   }'
   ```
   加完重启 Claude Code，子代理才看得到这个 MCP。
3. 脚本需要 Python 3 和 `olefile`、`shapely`、`matplotlib`：`pip install olefile shapely matplotlib`。脚本用 `python -I` 跑，路径作参数。
4. 用的时候在 Claude Code 里输入 `/mcp-pcb-layout`（这个 skill 设了 `disable-model-invocation: true`，不会自己加载）。

## 注意

- 文件里的路径（`E:\Altium_designer\...`、`C:\Users\<用户名>\...`、`E:\<项目根>\...`）是原作者电脑上的，换电脑要改：主要在 `skills/eda-agent/SKILL.md` 和 `agents/eda-agent-operator.md`。
- 调用 eda-agent 一律派子代理（Sonnet 改板子 / 跑 DRC，Haiku 只读导出），主模型不直接调用；每次派之前告诉用户用的是哪个模型。
- 删除这类不可逆操作由用户决定；被权限检查拦下时不改权限、不绕过，请用户在 AD 里手动删。
- 不要跑 `eda_agent doctor`（会把所有文档都保存）；AD 里的脚本桥一次只服务一个客户端（Codex 和 Claude 不能同时连）。
- 实例里的数据表、说明书是原样复制的，坐标针对 QPA2609 测试板（RO4003C 0.203 mm，板 25.4 × 108.5 mm），别的板子要按 `rf-board-calcs.md` 重新算。
