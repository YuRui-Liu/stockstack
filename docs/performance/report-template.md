# 商品详情性能测试报告

> 本报告中的结论只对下列环境、代码版本和数据规模有效，不应外推为生产容量承诺。

## 固定测试信息

| 日期 | Commit | 机器 CPU | 机器内存 | OS | Docker 资源限制 | 数据量 | 并发 | 时长 | 吞吐（req/s） | P50 | P95 | P99 | Error rate | Cache hit | DB fallback |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

记录原始 k6 输出、应用 metrics 快照、容器资源采样和完整运行命令。Cache hit 与 DB fallback 必须来自应用指标，不根据响应头或延迟猜测。

## 1. 缓存命中（cached）

- 运行命令：`k6 run -e SCENARIO=cached -e BASE_URL=http://localhost:8080 -e PRODUCT_ID=0198c8bc-1234-7abc-8def-0123456789ab loadtest/product-detail.js`
- 前置条件：已请求一次目标商品并确认缓存已预热。

| 并发 | 时长 | 吞吐（req/s） | P50 | P95 | P99 | Error rate | HTTP 200 | HTTP 429 | HTTP 503 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |  |  |  |  |

- 阈值结果：失败率 `< 0.001`；P95 `< 200 ms`。
- 原始证据位置：

## 2. 不存在商品（missing）

- 运行命令：`k6 run -e SCENARIO=missing -e BASE_URL=http://localhost:8080 loadtest/product-detail.js`
- 前置条件：脚本会生成合法的随机 UUIDv7；也可通过 `MISSING_ID` 覆盖，并确认覆盖值在测试数据库中不存在。

| 并发 | 时长 | 吞吐（req/s） | P50 | P95 | P99 | Error rate | HTTP 200 | HTTP 429 | HTTP 503 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |  |  |  |  |

- 结果摘要：预期 HTTP 404；404 作为业务预期响应，不计为请求失败。
- 原始证据位置：

## 3. 热点过期（hot-expiry）

- 清理命令：`docker compose exec -T redis redis-cli DEL product:v1:0198c8bc-1234-7abc-8def-0123456789ab`
- 运行命令：`k6 run -e SCENARIO=hot-expiry -e BASE_URL=http://localhost:8080 -e PRODUCT_ID=0198c8bc-1234-7abc-8def-0123456789ab loadtest/product-detail.js`
- 前置条件：紧接清理命令启动压测，不在脚本中直接操作 Redis。

| 并发 | 时长 | 吞吐（req/s） | P50 | P95 | P99 | Error rate | HTTP 200 | HTTP 429 | HTTP 503 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |  |  |  |  |

- 应用 metrics 证据（测试时间窗前后差值）：
  - 数据库回源增量：
  - 锁竞争增量：
  - 缓存结果增量：
- 判定：同一热点 ID 的数据库回源应接近 1 次；必须以上述应用 metrics 取证，不能仅凭 k6 延迟判定。

## 4. 数据库直读基线（direct-baseline）

- 运行命令：`k6 run -e SCENARIO=direct-baseline -e BASELINE_URL='http://localhost:PORT/path/{PRODUCT_ID}' -e PRODUCT_ID=0198c8bc-1234-7abc-8def-0123456789ab loadtest/product-detail.js`
- 基线端点说明：由测试环境单独提供直接读取端点；管理 API 需要鉴权，不作为公开详情的直接基线。若未提供 `BASELINE_URL`，脚本会明确失败。

| 并发 | 时长 | 吞吐（req/s） | P50 | P95 | P99 | Error rate | HTTP 200 | HTTP 429 | HTTP 503 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |  |  |  |  |

- 原始证据位置：

## 缓存与基线对比

采用相同机器、容器限制、数据量、并发和时长重复测试。

`吞吐提升倍率 = cached 吞吐（req/s） ÷ direct-baseline 吞吐（req/s）`

| 指标 | Cached | Direct baseline | 差值或倍率 |
|---|---:|---:|---:|
| 吞吐（req/s） |  |  |  |
| P50 |  |  |  |
| P95 |  |  |  |
| P99 |  |  |  |
| Error rate |  |  |  |

- 实测吞吐倍率：
- 是否达到 5 倍：是 / 否
- 若未达到 5 倍：如实保留结果，并记录 CPU 饱和、连接池、反向代理、Redis/数据库延迟、限流、网络和数据规模等排查证据；不得改写或推算测试数据。

## Redis 降级验证

- Docker Compose 暂停：`docker compose pause redis`
- 运行：`k6 run -e BASE_URL=http://localhost:8080 -e PRODUCT_ID=0198c8bc-1234-7abc-8def-0123456789ab loadtest/redis-degraded.js`
- Docker Compose 恢复（无论运行成功或失败都执行）：`docker compose unpause redis`
- 本机 Redis：使用用户自己的服务管理器停止和启动 Redis。在另一个终端用 shell `trap` 或等价的 `finally` 机制登记恢复命令后再停止服务；不要用 kill 命令。压测成功、失败或中断后都必须恢复。

| 并发 | 时长 | 吞吐（req/s） | P50 | P95 | P99 | HTTP 200 比例 | HTTP 429 比例 | HTTP 503 比例 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |  |  |  |

- `service_available` 仅输出 HTTP 200 比例，不设置虚假的最低阈值。
- `controlled_degradation` 输出 HTTP 429/503 合计比例，并同时保留两种状态的独立计数。
- `responseCallback` 将 200/429/503 标记为预期，因此 `http_req_failed` 只表示非受控状态或传输错误，不能当作服务成功率。
- 连接级错误与非预期状态：
- 原始证据位置：

## 结论与限制

- 结论：
- 未达阈值项及排障记录：
- 测试限制与偏差：
- 后续复测条件：

所有结论仅对本报告“固定测试信息”中的环境有效。任何代码、资源限制、数据量、网络拓扑或依赖版本变化都需要重新测试。
