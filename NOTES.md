# BLA 单次实测说明

## REA 审批：仅对本次进程的一个 MCP 服务生效

`run_once.py` 给 `codex exec` 传入 `-c 'mcp_servers.rea.default_tools_approval_mode="approve"'`，保留 `-s workspace-write`，不改全局配置，不提权，也不调整其他 MCP 服务。这里批准的是 REA 工具调用，不是对 Windows 沙箱限制或组织策略的豁免。按工具配置 `mcp_servers.<id>.tools.<tool>.approval_mode` 会优先于服务默认值；本次使用服务级规则，允许模型自行选择 REA 的分析工具，不预设工具顺序。

- 本机 `codex-cli 0.171.0` 的 `codex exec --help`：`-c, --config <key=value>` 可单次覆盖 `~/.codex/config.toml` 的配置，并接受点分隔路径和 TOML 值。
- [OpenAI Codex 配置参考](https://developers.openai.com/codex/config-reference) 列出上述服务器级和工具级键，其值为 `auto | prompt | writes | approve`。
- [0.171.0 配置定义](https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/config/src/mcp_types.rs) 定义了这些键；[同版本审批实现](https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/core/src/mcp_tool_call.rs) 的 `requires_mcp_tool_approval_for_mode` 对 `Approve` 返回 `false`。
- 只读验证：带 `-c` 的 `codex mcp get rea` 显示 `default_tools_approval_mode: approve`；不带覆盖则没有这项。未运行 `run_once.py` 或实时 REA 调用；此前 Shell/Node REPL 的 Windows provisioning 故障是另一问题，此覆盖不能修复它。

## 有效性与空载基线参考

`valid` 只描述运行条件：超时、非零退出码（或未能启动），或 MCP 失败文本显示审批/权限/环境故障，均使运行无效。MCP 事件按调用 ID 去重；`mcp_failed` 也计入不会使运行无效的普通工具错误。`answer_exists` 表示本次生成或更新了两份非空答案；有效运行仍需对照原件验证结果，文件存在不代表等价。

2026-11-25 14:09:41 JST 的 `dx-ball` 首测（181,696 input tokens）是**空载基线参考**：此次 agent 未完成任何分析，token 推测主要是固定开销（系统提示、工具目录），并非已分解的实测；后续计算倍数时需单独测量并扣除同配置的基线。原始 JSONL 保留，CSV 原记录只补充判定字段，不重复计数。
