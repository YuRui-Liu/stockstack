# 验证状态

本页记录 2026-08-21 最终收口的可复现验证。功能与测试发现修复基线 commit 为 `0eb786d`；其后变更仅涉及 Makefile 命令安全与验证文档。

## 本次新鲜验证

| 命令 | 结果 |
|---|---|
| `env UV_CACHE_DIR=/private/tmp/stockstack-uv-cache uv run --frozen pytest -q`（`backend/`） | 通过：137 passed、16 skipped、1 个依赖弃用 warning；未设置 `TEST_DATABASE_URL`，真实 PostgreSQL 集成用例被跳过。 |
| `env UV_CACHE_DIR=/private/tmp/stockstack-uv-cache uv run --frozen ruff check .`（`backend/`） | 通过：`All checks passed!`。 |
| `npm ci`（`frontend/`） | 通过：按 lockfile 安装 285 packages。 |
| `npm test -- --run`（`frontend/`） | 通过：Vitest 仅发现 8 个 unit test files，33 passed、0 failed suite。仍有既有的 jsdom `getComputedStyle` 和 MSW 未匹配请求 stderr；不影响退出码。此前 Vitest 误收集 Playwright E2E 文件的失败已通过独立 discovery 配置修复。 |
| `npm run build`（`frontend/`） | 修复后重跑通过：TypeScript 与 Vite production build 完成；有 bundle 大于 500 kB 的提示。 |
| `npx playwright test --list`（`frontend/`） | 修复后重跑通过：Playwright 独立发现 1 test in 1 file；仅列出，未执行浏览器 E2E。 |
| `docker compose --env-file .env.example config --quiet` | 通过配置解析；使用的是包含 `CHANGE_ME` 的示例值，仅验证语法和插值，不代表容器已构建或启动。直接运行 `docker compose config --quiet` 因缺少 `.env` 的必填秘密而按设计失败。非 quiet 输出未写入 CI 日志。 |
| `node --check loadtest/product-detail.js` 与 `node --check loadtest/redis-degraded.js` | 通过 JavaScript 语法检查；没有运行 k6。 |
| `make validate-load-env`（默认值与 IPv6 URL） | 通过；默认 seed UUID、默认 URL 和 `https://[::1]:8080/path?a=1&b=two` 均被接受。 |
| `make validate-load-env` / `make load-cached`（含反引号或 GNU make `$(shell …)` 与 `touch` 文本的恶意 `BASE_URL`，以及非法 `PRODUCT_ID`） | 均在调用 k6 前以 exit 2 被拒绝；断言两个 `/private/tmp/stockstack-*-INJECTED` marker 均不存在，未产生命令注入副作用。 |
| `git diff --check` | 编辑后检查通过。 |

## 历史证据（不等同于本次重跑）

- 后端纯单元/模拟环境：曾报告 137 passed、16 skipped。
- 前端：曾报告 33 passed，且 production build 成功。
- PostgreSQL 商品集成：曾分组报告 5/10 passed；最终全套 PostgreSQL 集成测试未重跑。

## 当前环境限制与未验证项

- `pg_isready -h 127.0.0.1 -p 5432` 返回 `no response`；本机没有 `redis-cli`；未安装或未发现 `k6`。
- Docker CLI 存在，但当前沙箱无权连接 OrbStack Docker socket，因此没有构建或启动 Compose 服务。
- 尝试在 `127.0.0.1:18000` 启动无需依赖连接的 API health smoke；应用 startup 完成，但沙箱禁止绑定端口（`operation not permitted`），所以没有 curl health 结果。未继续尝试 Vite 绑定。
- 未执行最终全套 PostgreSQL 集成、完整 Docker Compose 启动、浏览器 E2E 或任何 k6 场景。
- 没有填写吞吐、延迟、错误率、缓存命中或数据库回源数字；5 倍吞吐仅是目标。
