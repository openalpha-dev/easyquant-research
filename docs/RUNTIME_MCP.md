# 运行时 MCP 接口

托管研究引擎本身就是一个 MCP 服务器。本包的 `client.py` 与 `easyquant-research-mcp` 桥接到它。

## 端点与传输

- 端点：`POST {base}/api/agent/v1/mcp`，默认 `base = https://trade.goeasyquant.com`。
- 传输：Streamable HTTP 的**无状态请求-响应子集**——每个工具一次 POST 出结果，不开 SSE 流、不发会话 ID。算得慢的返回 `job_id`，由 `get_job` 轮询。
- 协议：JSON-RPC 2.0。支持的 `protocolVersion`：`2025-06-18`、`2025-03-26`、`2024-11-05`（`initialize` 时协商；不要发送服务端不支持的 `MCP-Protocol-Version` 头）。
- 平台子路径（按宿主区分，可选）：`/mcp/chatgpt`（港美股、强制 OAuth）、`/mcp/workbuddy`、`/mcp/qoder`。通用端点 `/mcp` 允许未登录体验。

## 鉴权

- API Key：`Authorization: Bearer eqk_...`（用户在运行时个人中心生成）。只在 `/api/agent/v1/**` 生效。
- 或标准 MCP OAuth 2.1：未登录调用受限工具时返回 `401 + WWW-Authenticate: Bearer resource_metadata="..."`，客户端据此发现授权服务器、走 OAuth（DCR + PKCE）。
- 未登录体验：按 IP 开放 `catalog`、`screen`、`backtest_timing`、`backtest_portfolio`、`factor_report`、`get_job`，计次工具合计每天有限次数；用完或调其它工具要求登录。

## 配置

```bash
export EASYQUANT_BASE_URL="https://trade.goeasyquant.com"   # 可省略，默认即此
export EASYQUANT_API_KEY="eqk_..."                          # 可省略：省略则走匿名体验
export EASYQUANT_LANG="zh"                                  # 运行时消息语言 zh|en
```

## 工具

完整契约（名称、描述、输入 schema、是否需登录）见本包 `catalog/tools.json`，离线用 `list_research_tools` 查询，实时用 `easyquant-research tools --live`。

| 工具 | 用途 | 体验可用 |
| --- | --- | --- |
| `catalog` | 字段、函数、指标、市场规则、数据日期、额度、已解锁全局因子 | ✓ |
| `screen` | 某一天条件选股完整名单 | ✓ |
| `backtest_portfolio` | 组合回测（可能返回 job_id） | ✓ |
| `backtest_timing` | 单标的择时回测 | ✓ |
| `factor_report` | 因子体检（可能返回 job_id） | ✓ |
| `robustness` | 稳健性检验（按开关开放） | 需登录 |
| `get_job` | 轮询异步任务 | ✓ |
| `research_capabilities` | AlphaSpec 能力与额度 | 需登录 |
| `submit_artifact` | 提交 AlphaSpec 研究草稿 | 需登录 |
| `evaluate_artifact` | 入队评估 | 需登录 |
| `get_evaluation` | 评估状态/结果 | 需登录 |
| `get_research_evidence` | 冻结回测证据 | 需登录 |

## 结果与错误

`tools/call` 返回 `{content:[{type:"text",text:...}], structuredContent:{...}, isError:bool}`。本包优先取 `structuredContent`。工具层错误放在结果里（`isError=true`），`client.py` 转成 `ResearchError`；HTTP 401 转成 `LoginRequired`（附带登录提示）。

## 在 MCP 客户端里使用

stdio（本包，适合只支持 stdio 的客户端，如 Claude Desktop / Cursor 本地）：

```json
{
  "mcpServers": {
    "easyquant-research": {
      "command": "easyquant-research-mcp",
      "env": { "EASYQUANT_API_KEY": "eqk_..." }
    }
  }
}
```

远程直连（支持 streamable-http + OAuth 的客户端，如豆包工作 / Qoder 插件）：

```json
{
  "mcpServers": {
    "easyquant-research": {
      "type": "streamable-http",
      "url": "https://trade.goeasyquant.com/api/agent/v1/mcp"
    }
  }
}
```