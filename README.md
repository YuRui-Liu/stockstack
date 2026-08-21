# StockStack 商品管理演示

StockStack 是一个本机优先的商品发布、管理与公开详情演示：React 管理端通过 FastAPI API 管理 PostgreSQL 数据，Redis 保护公开读路径。Docker Compose 是可选启动方式，不是本机开发的前提。

## 架构与目录

```text
浏览器 :8080 ── Vite/nginx ── FastAPI :8000 ── PostgreSQL
                                  └──── Redis（缓存、锁、限流）
backend/      API、领域逻辑、迁移与测试
frontend/     React 管理端与 Playwright
scripts/      固定演示数据 seed
loadtest/     k6 场景
docs/         UI 说明、设计、计划与性能证据模板
```

## 本机启动（推荐）

前置条件：Python 3.12、[uv](https://docs.astral.sh/uv/)、Node.js 与 npm、PostgreSQL、Redis。PostgreSQL 和 Redis 请用操作系统或用户自己的服务管理器启动；项目不会替你安装、停止或重启它们。

```bash
cp .env.example .env
cd backend && uv sync --frozen && cd ..
cd frontend && npm ci && cd ..
```

编辑 `.env`，替换所有 `CHANGE_ME`。以下命令只输出待复制的秘密，不把真实值写进仓库；管理员密码通过隐藏输入读取，避免出现在 shell 历史中：

```bash
openssl rand -hex 32
cd backend && uv run --frozen python -c 'import getpass; from pwdlib import PasswordHash; print(PasswordHash.recommended().hash(getpass.getpass("Admin password: ")))'
```

把第一条输出填入 `JWT_SECRET`，第二条输出填入 `ADMIN_PASSWORD_HASH`。`ADMIN_USERNAME` 是登录用户名；登录密码是生成该 Argon2 hash 时输入的原始密码，hash 本身不是密码。

确认 `.env` 的 `DATABASE_URL` 与本机 PostgreSQL 用户、密码和数据库一致，然后执行：

```bash
make migrate-local
make seed-local
```

分别打开两个终端：

```bash
make dev-api
make dev-web
```

访问：

- 管理端登录：<http://127.0.0.1:8080/login>
- API 文档：<http://127.0.0.1:8000/docs>
- Prometheus 指标：<http://127.0.0.1:8000/metrics>
- 健康检查：<http://127.0.0.1:8000/health>

### 可选：Docker Compose

安装 Docker 后，同样先准备安全的 `.env`，再运行：

```bash
make up
```

Compose 会等待依赖、迁移和 seed 完成，对外入口仍是 <http://127.0.0.1:8080/login>。查看日志用 `make logs`，停止用 `make down`（不会删除数据卷）。

## 演示路径

1. 用 `.env` 中的管理员用户名及生成 hash 时输入的密码登录。
2. 点击“发布商品”，分别创建实物、虚拟、创意三类商品；动态字段来自各类型当前启用的字段模板。
3. 在商品管理页按关键词、类型、状态筛选，进入详情或编辑；可执行单条上架、下架、处罚，以及批量上架或下架。
4. seed 的三类演示商品初始为“已下架”。先把固定实物商品 `0198c8bc-1234-7abc-8def-0123456789ab` 上架，再请求：

   ```bash
   curl http://127.0.0.1:8080/api/v1/public/products/0198c8bc-1234-7abc-8def-0123456789ab
   ```

字段模板按商品类型和版本保存；商品记录绑定创建或更新时使用的版本，历史版本可以读取，不会因启用新模板而被悄悄重解释。

状态只允许 `已上架 ↔ 已下架`，两者都可转为`处罚中`；处罚是终态。公开 GET 只返回已上架商品，其他状态统一表现为不存在。写操作使用记录版本做并发冲突保护，成功后使详情缓存失效；没有消息队列，因此多进程或多实例之间可能在 TTL 窗口内短暂陈旧。

## 测试与验证

```bash
# 不配置 PostgreSQL 时，依赖真实数据库的用例会 skip
cd backend && uv run --frozen pytest -q
cd backend && uv run --frozen ruff check .

# 完整 PostgreSQL 集成测试需指向专用、可清理的测试库
cd backend && TEST_DATABASE_URL='postgresql+asyncpg://USER:PASSWORD@127.0.0.1:5432/stockstack_test' uv run --frozen pytest -q

cd frontend && npm test
cd frontend && npm run build
cd frontend && npx playwright test --list

# E2E 需要已启动且已迁移、seed 的完整服务
make e2e

# 可选 Compose 配置检查
docker compose config
```

本次交付的逐条命令、日期、commit 和环境限制见 [验证状态](docs/performance/verification-status.md)。主 README 不固化容易过时的通过数。当前历史证据包括：后端纯/模拟测试曾为 137 passed、16 skipped；前端测试曾为 33 passed 且 build 成功；PostgreSQL 商品集成曾分组得到 5/10 passed，但最终全套 PostgreSQL 集成测试未重跑。Docker 完整启动、浏览器 E2E 和 k6 完整压测也没有被当作已验证结果。

## 公开读保护与压测

公开商品详情采用 cache-aside：正常商品缓存、短 TTL negative cache 与 TTL jitter 降低穿透和集中失效；进程内 singleflight 加 Redis 分布式锁抑制热点回源；按客户端 IP 限流；Redis 异常时 fail-open 到受信号量、等待时间和查询超时约束的 PostgreSQL fallback；缓存、锁竞争、回源、依赖错误、限流和延迟均暴露为 metrics。

安装 k6 后可使用：

```bash
make load-cached
make load-missing
make load-hot
make load-degraded

# 可覆盖入口和固定 seed 商品
make load-cached BASE_URL=http://127.0.0.1:8080 PRODUCT_ID=0198c8bc-1234-7abc-8def-0123456789ab
```

`load-hot` 只提醒操作者先清理指定缓存 key；`load-degraded` 只提醒操作者停止/暂停 Redis 并保证恢复，Makefile 不会自动改变 Redis 状态。运行前置条件、故障恢复步骤、指标取证和空白结果表见 [性能报告模板](docs/performance/report-template.md)。“缓存吞吐达到数据库直读的 5 倍”是待验证目标，不是当前实测结论；任何结果都必须绑定机器、资源限制、数据规模、代码版本与完整命令。

容量演进方向包括 Redis Cluster、PostgreSQL 只读副本、数据分片、CDN 和 CDC 驱动失效；这些能力当前均未实现，不能据此推断生产容量或一致性保证。

## 安全边界与已知限制

- 认证固定为单一管理员，没有用户管理或 RBAC；JWT 使用 HS256，生产部署需独立密钥管理与轮换。
- 图片上传的本地 magic 检查只验证签名和基本边界，不是完整图片解码、重编码或恶意内容扫描。
- 商品富文本在服务端清理；不要把它当作任意 HTML 托管能力。
- 公开接口只可见 `on_shelf` 商品；管理接口必须携带管理员令牌。
- 本地文件保存是同步 I/O，但已通过 threadpool 从异步事件循环卸载；本地磁盘仍不是多实例共享存储。
- 缓存失效没有消息队列广播，多实例下允许短暂陈旧；性能测试结果仅对记录的环境有效。
