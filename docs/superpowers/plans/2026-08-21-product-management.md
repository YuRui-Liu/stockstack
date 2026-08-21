# 商品管理全栈实战实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建一个 Docker Compose 一键启动的商品管理全栈 Demo，完成三类商品的 Schema 驱动发布管理，并以可重复压测验证高 QPS 商品详情读链路。

**架构：** React 管理端调用模块化 FastAPI 单体；PostgreSQL 保存权威商品、模板和图片元数据，Redis 保存公开详情快照、空值标记、重建锁与限流窗口。管理写入采用事务、乐观锁和提交后删缓存，公开读取采用 Cache-Aside、single-flight、跨实例短锁和受限数据库降级。

**技术栈：** Python 3.12、FastAPI、SQLAlchemy 2、Alembic、asyncpg、redis-py asyncio、Pydantic 2、jsonschema、uuid6（提供 Python 3.12 的 UUIDv7）、PyJWT、pwdlib、nh3、Prometheus client、pytest、React 19、TypeScript、Vite、Ant Design、TanStack Query、Vitest、Testing Library、Playwright、PostgreSQL 16、Redis 7、Docker Compose、k6。

---

## 文件结构

### 根目录与运行环境

- `compose.yaml`：编排 web、api、postgres、redis 及健康检查。
- `.env.example`：列出无敏感默认值的运行参数。
- `Makefile`：统一启动、迁移、测试和压测入口。
- `README.md`：架构、启动、演示、测试、压测和限制。
- `scripts/seed.py`：写入管理员密码哈希、三类模板和样例商品。

### 后端

- `backend/pyproject.toml`：后端依赖与 pytest/ruff 配置。
- `backend/Dockerfile`：API 容器镜像。
- `backend/alembic.ini`、`backend/alembic/env.py`：迁移运行环境。
- `backend/alembic/versions/0001_initial.py`：初始表、约束和索引。
- `backend/app/main.py`：应用工厂、中间件和路由装配。
- `backend/app/core/config.py`：类型化环境配置。
- `backend/app/core/errors.py`：统一业务异常与错误响应。
- `backend/app/core/security.py`：密码哈希和 JWT。
- `backend/app/core/metrics.py`：请求与缓存指标。
- `backend/app/db/session.py`：异步数据库引擎与会话。
- `backend/app/db/models.py`：SQLAlchemy 持久化模型。
- `backend/app/auth/router.py`、`backend/app/auth/service.py`：登录与鉴权。
- `backend/app/catalog/domain.py`：枚举、状态机和领域对象。
- `backend/app/catalog/schemas.py`：管理 API 请求响应模型。
- `backend/app/catalog/field_schema.py`：动态模板解析与 JSON Schema 校验。
- `backend/app/catalog/repository.py`：商品、模板和图片数据访问。
- `backend/app/catalog/service.py`：发布、编辑、状态转换和事务编排。
- `backend/app/catalog/router.py`：管理 API。
- `backend/app/catalog/cache.py`：Redis 键、快照、空值和锁。
- `backend/app/catalog/public_service.py`：公开详情 Cache-Aside、single-flight 与降级。
- `backend/app/catalog/public_router.py`：公开详情 API。
- `backend/app/catalog/uploads.py`：图片签名、大小、数量和安全文件名校验。
- `backend/tests/conftest.py`：测试应用、数据库、Redis、管理员和三类模板夹具。
- `backend/tests/unit/`：纯领域、模板、缓存与上传测试。
- `backend/tests/integration/`：数据库、Redis、API 和故障场景测试。

### 前端

- `frontend/package.json`、`frontend/vite.config.ts`、`frontend/tsconfig.json`：前端工具链。
- `frontend/Dockerfile`、`frontend/nginx.conf`：生产构建与反向代理。
- `frontend/src/main.tsx`、`frontend/src/app/App.tsx`：入口、路由和全局 Provider。
- `frontend/src/api/client.ts`、`frontend/src/api/types.ts`：HTTP 客户端与契约类型。
- `frontend/src/auth/`：登录页、会话存储和受保护路由。
- `frontend/src/products/ProductListPage.tsx`：筛选、分页和批量操作。
- `frontend/src/products/ProductFormPage.tsx`：发布与编辑容器。
- `frontend/src/products/DynamicFields.tsx`：Schema 驱动字段渲染。
- `frontend/src/products/ImageFields.tsx`：主图和副图上传。
- `frontend/src/products/status.ts`：前端状态转换能力映射。
- `frontend/src/test/setup.ts`、`frontend/src/test/fixtures.ts`：DOM 匹配器、API Mock 和共享商品/模板样例。
- `frontend/src/**/*.test.tsx`：Vitest 组件与页面测试。
- `frontend/e2e/product-management.spec.ts`：Playwright 业务旅程。

### 压测与证据

- `loadtest/product-detail.js`：命中、穿透和热点失效场景。
- `loadtest/redis-degraded.js`：Redis 故障降级场景。
- `docs/performance/report-template.md`：环境、指标和结论模板。

## 任务 1：建立可验证的工程骨架

**文件：**
- 创建：`backend/pyproject.toml`
- 创建：`backend/app/main.py`
- 创建：`backend/app/core/config.py`
- 创建：`backend/tests/unit/test_health.py`
- 创建：`backend/tests/conftest.py`
- 创建：`frontend/package.json`
- 创建：`frontend/src/main.tsx`
- 创建：`frontend/src/app/App.tsx`
- 创建：`.env.example`

- [ ] **步骤 1：编写后端健康检查失败测试**

```python
# backend/tests/unit/test_health.py
from fastapi.testclient import TestClient
from app.main import create_app

def test_health_returns_ok() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **步骤 2：运行测试并确认因应用不存在而失败**

运行：`cd backend && python -m pytest tests/unit/test_health.py -q`

预期：FAIL，导入 `app.main` 或 `create_app` 失败。

- [ ] **步骤 3：添加最小应用、配置和项目依赖**

```python
# backend/app/main.py
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="StockStack", version="1.0.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

app = create_app()
```

`backend/pyproject.toml` 固定 Python `>=3.12,<3.13`，声明计划头部中的后端依赖，并配置 pytest 的 `pythonpath=["."]`、`asyncio_mode="auto"`。`backend/app/core/config.py` 使用 `pydantic-settings` 定义 `database_url`、`redis_url`、`jwt_secret`、`admin_username`、`admin_password_hash`、缓存 TTL、限流和回源并发上限；所有密钥仅从环境读取。`backend/tests/conftest.py` 在本任务先提供 `client`，后续任务在同一文件追加 `physical_schema`、`virtual_schema`、`creative_schema`、`db_session`、`redis_client`、`admin_headers` 和样例商品夹具，避免各测试自建不一致数据。

- [ ] **步骤 4：建立最小 React 入口并验证两端**

```tsx
// frontend/src/app/App.tsx
export function App() {
  return <main><h1>商品管理</h1></main>;
}
```

运行：`cd backend && python -m pytest tests/unit/test_health.py -q`

预期：`1 passed`。

运行：`cd frontend && npm install && npm run build`

预期：Vite 构建成功并生成 `dist/`。

- [ ] **步骤 5：提交工程骨架**

```bash
git add .env.example backend frontend
git commit -m "chore: scaffold product management application"
```

## 任务 2：用测试锁定领域规则与动态字段模板

**文件：**
- 创建：`backend/app/catalog/domain.py`
- 创建：`backend/app/catalog/field_schema.py`
- 创建：`backend/app/catalog/schemas.py`
- 创建：`backend/tests/unit/test_domain.py`
- 创建：`backend/tests/unit/test_field_schema.py`

- [ ] **步骤 1：编写状态机和三类模板的失败测试**

```python
# backend/tests/unit/test_domain.py
import pytest
from app.catalog.domain import ProductStatus, assert_transition

@pytest.mark.parametrize("source,target", [
    (ProductStatus.OFF_SHELF, ProductStatus.ON_SHELF),
    (ProductStatus.ON_SHELF, ProductStatus.OFF_SHELF),
    (ProductStatus.ON_SHELF, ProductStatus.PENALIZED),
])
def test_allowed_transitions(source, target) -> None:
    assert_transition(source, target)

def test_penalized_product_cannot_transition() -> None:
    with pytest.raises(ValueError, match="illegal product status transition"):
        assert_transition(ProductStatus.PENALIZED, ProductStatus.OFF_SHELF)
```

```python
# backend/tests/unit/test_field_schema.py
import pytest
from app.catalog.field_schema import validate_attributes

def test_physical_attributes_accept_valid_values(physical_schema) -> None:
    validate_attributes(physical_schema, {
        "weight_kg": 1.2,
        "specification": "黑色 / 30L",
        "shipping_template": "standard",
    })

def test_schema_rejects_unknown_field(physical_schema) -> None:
    with pytest.raises(ValueError, match="unexpected_field"):
        validate_attributes(physical_schema, {"unexpected_field": True})
```

- [ ] **步骤 2：运行领域测试并确认失败**

运行：`cd backend && python -m pytest tests/unit/test_domain.py tests/unit/test_field_schema.py -q`

预期：FAIL，领域枚举和校验函数尚不存在。

- [ ] **步骤 3：实现最小领域类型与校验器**

```python
# backend/app/catalog/domain.py
from enum import StrEnum

class ProductType(StrEnum):
    PHYSICAL = "physical"
    VIRTUAL = "virtual"
    CREATIVE = "creative"

class ProductStatus(StrEnum):
    ON_SHELF = "on_shelf"
    OFF_SHELF = "off_shelf"
    PENALIZED = "penalized"

_ALLOWED = {
    (ProductStatus.OFF_SHELF, ProductStatus.ON_SHELF),
    (ProductStatus.ON_SHELF, ProductStatus.OFF_SHELF),
    (ProductStatus.OFF_SHELF, ProductStatus.PENALIZED),
    (ProductStatus.ON_SHELF, ProductStatus.PENALIZED),
}

def assert_transition(source: ProductStatus, target: ProductStatus) -> None:
    if (source, target) not in _ALLOWED:
        raise ValueError("illegal product status transition")
```

```python
# backend/app/catalog/field_schema.py
from jsonschema import Draft202012Validator

def validate_attributes(schema: dict, attributes: dict) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(attributes), key=lambda e: list(e.path))
    if errors:
        paths = [".".join(map(str, error.path)) or error.validator for error in errors]
        raise ValueError(", ".join(paths))
```

在 `schemas.py` 定义发布、编辑、状态更新、批量状态和统一分页响应模型；金额用 `Decimal`，库存限制 `ge=0`，标题和短标题使用规格中的长度边界，`attributes` 为 `dict[str, object]`，编辑请求必须包含 `version`。

- [ ] **步骤 4：补足三类成功与失败样例并运行测试**

运行：`cd backend && python -m pytest tests/unit/test_domain.py tests/unit/test_field_schema.py -q`

预期：所有领域与模板测试 PASS。

- [ ] **步骤 5：提交领域规则**

```bash
git add backend/app/catalog backend/tests/unit
git commit -m "feat: define product domain and extensible schemas"
```

## 任务 3：建立 PostgreSQL 模型、迁移和仓储

**文件：**
- 创建：`backend/app/db/session.py`
- 创建：`backend/app/db/models.py`
- 创建：`backend/alembic.ini`
- 创建：`backend/alembic/env.py`
- 创建：`backend/alembic/versions/0001_initial.py`
- 创建：`backend/app/catalog/repository.py`
- 创建：`backend/tests/integration/test_repository.py`

- [ ] **步骤 1：编写事务、不可变模板和乐观锁失败测试**

```python
# backend/tests/integration/test_repository.py
import pytest
from app.catalog.repository import ProductRepository, VersionConflict

@pytest.mark.asyncio
async def test_update_rejects_stale_version(db_session, stored_product) -> None:
    repo = ProductRepository(db_session)
    await repo.update(stored_product.id, expected_version=1, title="第一次更新")
    with pytest.raises(VersionConflict):
        await repo.update(stored_product.id, expected_version=1, title="过期更新")
```

另加测试：同类型同版本模板不能重复；同类型只能一个活动模板；商品和图片写入异常时整笔事务回滚；每个商品最多五张副图且恰好一张主图。

- [ ] **步骤 2：运行集成测试并确认失败**

运行：`cd backend && python -m pytest tests/integration/test_repository.py -q`

预期：FAIL，模型、迁移和仓储尚不存在。

- [ ] **步骤 3：实现模型和初始迁移**

`models.py` 创建 `ProductModel`、`ProductFieldSchemaModel` 和 `ProductImageModel`。`ProductModel.id` 使用 PostgreSQL UUID，`attributes` 使用 JSONB，`price_amount` 使用 `NUMERIC(18, 2)`，`version` 默认 1。迁移创建规格中的组合索引和标题 `to_tsvector('simple', title)` GIN 索引，并以部分唯一索引保证每类只有一个活动模板。

仓储更新必须使用以下条件更新形态：

```python
statement = (
    update(ProductModel)
    .where(ProductModel.id == product_id, ProductModel.version == expected_version)
    .values(**changes, version=ProductModel.version + 1)
    .returning(ProductModel)
)
```

返回空结果时抛出 `VersionConflict`。批量状态更新在一个事务内先锁定目标行、验证全部转换，再一次性更新；不允许部分成功。

- [ ] **步骤 4：迁移测试数据库并运行集成测试**

运行：`cd backend && alembic upgrade head && python -m pytest tests/integration/test_repository.py -q`

预期：迁移成功，仓储测试全部 PASS。

- [ ] **步骤 5：提交持久化层**

```bash
git add backend/alembic.ini backend/alembic backend/app/db backend/app/catalog/repository.py backend/tests/integration
git commit -m "feat: persist products and versioned field schemas"
```

## 任务 4：实现统一错误、管理员登录和 JWT 保护

**文件：**
- 创建：`backend/app/core/errors.py`
- 创建：`backend/app/core/security.py`
- 创建：`backend/app/auth/service.py`
- 创建：`backend/app/auth/router.py`
- 创建：`backend/tests/unit/test_security.py`
- 创建：`backend/tests/integration/test_auth_api.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：编写登录和受保护路由失败测试**

```python
# backend/tests/integration/test_auth_api.py
def test_login_returns_bearer_token(client, admin_credentials) -> None:
    response = client.post("/api/v1/auth/login", json=admin_credentials)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"

def test_management_api_rejects_missing_token(client) -> None:
    response = client.get("/api/v1/products")
    assert response.status_code == 401
    assert set(response.json()) == {"code", "message", "field_errors", "request_id"}
```

- [ ] **步骤 2：运行认证测试并确认失败**

运行：`cd backend && python -m pytest tests/unit/test_security.py tests/integration/test_auth_api.py -q`

预期：FAIL，认证路由和统一错误尚不存在。

- [ ] **步骤 3：实现密码、JWT、依赖注入和错误处理器**

`security.py` 使用 `pwdlib.PasswordHash.recommended()` 验证环境中的管理员密码哈希，使用 HS256 JWT 写入 `sub`、`iat`、`exp`。`errors.py` 定义 `AppError(code, message, status_code, field_errors)` 并注册 FastAPI 处理器；中间件为每个响应写入 `X-Request-ID`。

```python
async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    payload = decode_token(credentials.credentials)
    if payload.get("sub") != settings.admin_username:
        raise AppError("UNAUTHORIZED", "登录已失效", 401)
    return payload["sub"]
```

- [ ] **步骤 4：运行测试并验证敏感信息不进入日志**

运行：`cd backend && python -m pytest tests/unit/test_security.py tests/integration/test_auth_api.py -q`

预期：认证成功/失败、过期 token、错误结构和日志脱敏测试全部 PASS。

- [ ] **步骤 5：提交认证与错误基线**

```bash
git add backend/app/core backend/app/auth backend/app/main.py backend/tests
git commit -m "feat: add admin authentication and error contract"
```

## 任务 5：实现发布、管理、编辑和状态 API

**文件：**
- 创建：`backend/app/catalog/service.py`
- 创建：`backend/app/catalog/router.py`
- 创建：`backend/tests/integration/test_product_api.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：编写完整管理 API 的失败测试**

```python
# backend/tests/integration/test_product_api.py
def test_publish_physical_product(client, admin_headers, physical_payload) -> None:
    response = client.post("/api/v1/products", json=physical_payload, headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["product_type"] == "physical"
    assert response.json()["schema_version"] == 1

def test_edit_rejects_stale_version(client, admin_headers, stored_product) -> None:
    payload = {"version": 0, "title": "过期编辑"}
    response = client.put(f"/api/v1/products/{stored_product.id}", json=payload, headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["code"] == "PRODUCT_VERSION_CONFLICT"
```

补充测试覆盖三类发布、活动模板过期、编辑时切换类型、组合筛选、详情、单个上下架、设为处罚、处罚后恢复失败，以及批量全有或全无。

- [ ] **步骤 2：运行 API 测试并确认失败**

运行：`cd backend && python -m pytest tests/integration/test_product_api.py -q`

预期：FAIL，商品服务和路由尚不存在。

- [ ] **步骤 3：实现服务事务和路由**

发布服务必须按顺序：读取活动模板、比较请求版本、清理富文本、校验动态属性、写入商品和图片元数据、提交事务。编辑服务读取商品绑定模板而非活动模板，拒绝修改 `product_type`。路由使用规格第 7 节的路径，并为管理路由统一依赖 `require_admin`。

```python
async def publish(self, command: ProductCreate) -> ProductView:
    schema = await self.repo.get_active_schema(command.product_type)
    if schema.version != command.schema_version:
        raise SchemaVersionConflict()
    validate_attributes(schema.schema, command.attributes)
    command.description_html = nh3.clean(command.description_html)
    return await self.repo.create_with_images(command)
```

- [ ] **步骤 4：运行管理 API 集成测试**

运行：`cd backend && python -m pytest tests/integration/test_product_api.py -q`

预期：所有发布、编辑、筛选和状态测试 PASS。

- [ ] **步骤 5：提交管理 API**

```bash
git add backend/app/catalog backend/app/main.py backend/tests/integration/test_product_api.py
git commit -m "feat: implement product publishing and management APIs"
```

## 任务 6：实现安全图片上传

**文件：**
- 创建：`backend/app/catalog/uploads.py`
- 创建：`backend/tests/unit/test_uploads.py`
- 修改：`backend/app/catalog/router.py`
- 修改：`backend/app/catalog/service.py`

- [ ] **步骤 1：编写签名、大小、数量和文件名失败测试**

```python
# backend/tests/unit/test_uploads.py
import pytest
from app.catalog.uploads import validate_image

def test_rejects_executable_disguised_as_png() -> None:
    with pytest.raises(ValueError, match="unsupported image signature"):
        validate_image(b"#!/bin/sh\necho bad", "image/png", "cover.png")

def test_rejects_image_over_two_megabytes(valid_png) -> None:
    with pytest.raises(ValueError, match="image exceeds 2 MB"):
        validate_image(valid_png + b"0" * (2 * 1024 * 1024), "image/png", "cover.png")
```

- [ ] **步骤 2：运行上传测试并确认失败**

运行：`cd backend && python -m pytest tests/unit/test_uploads.py -q`

预期：FAIL，上传校验器尚不存在。

- [ ] **步骤 3：实现上传校验与存储适配器**

允许 JPEG、PNG 和 WebP；读取实际文件签名并与声明 MIME 对照；单文件最大 `2 * 1024 * 1024` 字节；服务层强制一张主图和最多五张副图。文件名使用 `uuid7 + 受控扩展名`，存储根目录来自配置，解析后的目标路径必须仍位于该根目录下。

- [ ] **步骤 4：运行上传及商品事务测试**

运行：`cd backend && python -m pytest tests/unit/test_uploads.py tests/integration/test_product_api.py -q`

预期：文件签名、大小、数量和事务清理测试全部 PASS。

- [ ] **步骤 5：提交上传能力**

```bash
git add backend/app/catalog backend/tests
git commit -m "feat: validate and store product images safely"
```

## 任务 7：实现高 QPS 公开详情读链路

**文件：**
- 创建：`backend/app/catalog/cache.py`
- 创建：`backend/app/catalog/public_service.py`
- 创建：`backend/app/catalog/public_router.py`
- 创建：`backend/app/core/metrics.py`
- 创建：`backend/tests/unit/test_cache.py`
- 创建：`backend/tests/integration/test_public_product_api.py`
- 修改：`backend/app/catalog/service.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：编写命中、穿透和热点重建失败测试**

```python
# backend/tests/integration/test_public_product_api.py
async def test_cache_hit_does_not_query_database(public_service, cache, repo, product_snapshot) -> None:
    await cache.set_snapshot(product_snapshot)
    result = await public_service.get(product_snapshot.id)
    assert result == product_snapshot
    repo.get_public.assert_not_awaited()

async def test_concurrent_misses_query_database_once(public_service, repo, product_id) -> None:
    await asyncio.gather(*(public_service.get(product_id) for _ in range(30)))
    assert repo.get_public.await_count == 1
```

补充测试：空值短 TTL、随机 TTL 范围、非上架返回 404、随机令牌 Lua 解锁、锁等待预算、Redis 故障受信号量限制回源、数据库故障 503、更新提交后删缓存。

- [ ] **步骤 2：运行公开读取测试并确认失败**

运行：`cd backend && python -m pytest tests/unit/test_cache.py tests/integration/test_public_product_api.py -q`

预期：FAIL，缓存和公开读取服务尚不存在。

- [ ] **步骤 3：实现缓存协议与 single-flight**

缓存键固定为 `product:v1:{id}`、空值内容固定为 `{"kind":"missing"}`、锁键为 `product-lock:v1:{id}`。正常 TTL 使用 `base_ttl + secrets.randbelow(jitter + 1)`；空值 TTL 独立配置。锁值使用随机令牌，释放脚本如下：

```lua
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
```

`PublicProductService` 维护 `dict[UUID, asyncio.Task]`，在 `asyncio.Lock` 保护下复用同 ID 的未完成任务，并在任务结束后清理字典。跨实例未取得 Redis 锁的请求按固定短间隔重读缓存，达到预算后进入受信号量限制的回源路径。

- [ ] **步骤 4：实现限流、指标、降级和公开路由**

Redis 滑动窗口 Lua 脚本使用时间戳有序集合原子执行删除旧成员、计数、添加当前请求和设置过期。公开路由只接受有效 UUIDv7 格式；命中非上架或空值均映射为同一 `404`。指标至少暴露请求总数、延迟直方图、缓存结果、数据库回源、锁竞争、429 和依赖错误。

- [ ] **步骤 5：运行并发与故障测试**

运行：`cd backend && python -m pytest tests/unit/test_cache.py tests/integration/test_public_product_api.py -q`

预期：缓存命中不查库；30 个同实例并发未命中只查库一次；跨实例锁、空值、限流和降级测试全部 PASS。

- [ ] **步骤 6：提交公开读取链路**

```bash
git add backend/app/catalog backend/app/core backend/app/main.py backend/tests
git commit -m "feat: protect high qps product detail reads"
```

## 任务 8：由 UI Designer 审核视觉方案并建立前端基础

**文件：**
- 创建：`frontend/src/api/types.ts`
- 创建：`frontend/src/api/client.ts`
- 创建：`frontend/src/app/App.tsx`
- 创建：`frontend/src/app/theme.ts`
- 创建：`frontend/src/auth/LoginPage.tsx`
- 创建：`frontend/src/auth/RequireAuth.tsx`
- 创建：`frontend/src/auth/LoginPage.test.tsx`
- 创建：`frontend/src/test/setup.ts`
- 创建：`frontend/src/test/fixtures.ts`

- [ ] **步骤 1：委派 UI Designer 做有边界的设计审查**

给 UI Designer 的输入必须包含已批准规格第 4、5、10、14 节，并要求只输出登录、管理列表、发布/编辑页的布局、Ant Design 组件映射、状态色、焦点顺序和窄屏策略；不得改变字段、状态机或功能范围。将结论记录到 `docs/ui/product-admin-ui.md`。

- [ ] **步骤 2：编写登录与受保护路由失败测试**

```tsx
// frontend/src/auth/LoginPage.test.tsx
it("submits credentials and enters the protected application", async () => {
  render(<LoginPage />);
  await userEvent.type(screen.getByLabelText("管理员账号"), "admin");
  await userEvent.type(screen.getByLabelText("密码"), "secret");
  await userEvent.click(screen.getByRole("button", { name: "登录" }));
  expect(await screen.findByText("商品管理")).toBeInTheDocument();
});
```

- [ ] **步骤 3：运行前端测试并确认失败**

运行：`cd frontend && npm test -- --run src/auth/LoginPage.test.tsx`

预期：FAIL，登录页面和 API 客户端尚不存在。

- [ ] **步骤 4：实现 API 客户端、主题和登录流程**

`client.ts` 统一附加 Bearer token、解析统一错误结构，并在 `401` 时清除会话回到登录页。token 仅保存在 `sessionStorage`。`theme.ts` 落实 UI Designer 已审核的颜色、圆角、间距和状态标签；所有表单控件具备可关联标签和键盘焦点。`src/test/setup.ts` 注册 `@testing-library/jest-dom` 与 MSW 生命周期，`src/test/fixtures.ts` 导出后续测试引用的 `physicalSchema`、`virtualSchema`、`creativeSchema`、`penalizedProduct` 和 API handler。

- [ ] **步骤 5：运行测试和构建**

运行：`cd frontend && npm test -- --run && npm run build`

预期：登录测试 PASS，TypeScript 和 Vite 构建无错误。

- [ ] **步骤 6：提交前端基础**

```bash
git add docs/ui frontend
git commit -m "feat: add accessible admin login shell"
```

## 任务 9：实现 Schema 驱动发布与编辑页面

**文件：**
- 创建：`frontend/src/products/DynamicFields.tsx`
- 创建：`frontend/src/products/ImageFields.tsx`
- 创建：`frontend/src/products/ProductFormPage.tsx`
- 创建：`frontend/src/products/DynamicFields.test.tsx`
- 创建：`frontend/src/products/ProductFormPage.test.tsx`
- 修改：`frontend/src/app/App.tsx`

- [ ] **步骤 1：编写动态字段和图片边界失败测试**

```tsx
// frontend/src/products/DynamicFields.test.tsx
it("renders physical fields from the server schema", () => {
  render(<DynamicFields schema={physicalSchema} />);
  expect(screen.getByLabelText("重量（kg）")).toBeRequired();
  expect(screen.getByLabelText("物流模板")).toHaveRole("combobox");
});

it("does not render fields absent from the selected schema", () => {
  render(<DynamicFields schema={virtualSchema} />);
  expect(screen.queryByLabelText("重量（kg）")).not.toBeInTheDocument();
  expect(screen.getByLabelText("核销方式")).toBeInTheDocument();
});
```

另加测试覆盖广告素材、模板版本随请求提交、主图必填、副图最多五张、单图 2 MB、服务端字段错误定位、编辑时类型不可切换且使用绑定版本。

- [ ] **步骤 2：运行页面测试并确认失败**

运行：`cd frontend && npm test -- --run src/products/DynamicFields.test.tsx src/products/ProductFormPage.test.tsx`

预期：FAIL，商品表单组件尚不存在。

- [ ] **步骤 3：实现受控动态组件映射**

只允许模板控件类型 `text`、`number`、`select`、`textarea`、`date`。未知控件类型显示阻断性错误而不是执行任意组件。`ProductFormPage` 在创建时读取活动模板，在编辑时读取商品详情中的绑定模板；提交值包含 `product_type`、`schema_version` 和 `attributes`。

- [ ] **步骤 4：实现图片和统一错误回填**

`ImageFields` 在客户端预检 MIME、2 MB 上限、单主图和五副图；服务端 `field_errors` 按字段路径写入 Ant Design Form。`409` 模板冲突提示重新载入模板，商品版本冲突提示刷新详情后重试。

- [ ] **步骤 5：运行表单测试和构建**

运行：`cd frontend && npm test -- --run src/products && npm run build`

预期：三类动态表单、上传边界、冲突提示和生产构建全部 PASS。

- [ ] **步骤 6：提交商品表单**

```bash
git add frontend/src/products frontend/src/app
git commit -m "feat: build schema driven product form"
```

## 任务 10：实现管理列表和状态操作

**文件：**
- 创建：`frontend/src/products/ProductListPage.tsx`
- 创建：`frontend/src/products/status.ts`
- 创建：`frontend/src/products/ProductListPage.test.tsx`
- 修改：`frontend/src/app/App.tsx`

- [ ] **步骤 1：编写筛选、分页和状态能力失败测试**

```tsx
// frontend/src/products/ProductListPage.test.tsx
it("sends combined filters and stable page parameters", async () => {
  render(<ProductListPage />);
  await userEvent.type(screen.getByLabelText("商品 ID 或标题"), "背包");
  await userEvent.selectOptions(screen.getByLabelText("商品类型"), "physical");
  await userEvent.click(screen.getByRole("button", { name: "查询" }));
  expect(api.listProducts).toHaveBeenCalledWith(expect.objectContaining({
    query: "背包", product_type: "physical", page: 1,
  }));
});

it("does not offer recovery actions for penalized products", () => {
  render(<ProductRow product={penalizedProduct} />);
  expect(screen.queryByRole("button", { name: "上架" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "下架" })).not.toBeInTheDocument();
});
```

- [ ] **步骤 2：运行列表测试并确认失败**

运行：`cd frontend && npm test -- --run src/products/ProductListPage.test.tsx`

预期：FAIL，列表和状态映射尚不存在。

- [ ] **步骤 3：实现列表、详情入口和状态映射**

使用 URL 查询参数保存筛选和页码；列固定为规格字段；批量操作仅允许上架或下架，并在提交前用 `status.ts` 检查所有选中项。处罚只作为单商品二次确认操作；处罚商品不展示恢复按钮。

- [ ] **步骤 4：验证全有或全无错误展示**

当批量 API 返回 `409` 时，在对话框列出失败商品 ID 和原因，保留选择状态，不将部分行乐观更新为成功。

- [ ] **步骤 5：运行前端全量测试和构建**

运行：`cd frontend && npm test -- --run && npm run build`

预期：所有前端测试 PASS，构建成功。

- [ ] **步骤 6：提交管理列表**

```bash
git add frontend/src/products frontend/src/app
git commit -m "feat: add product management list and status actions"
```

## 任务 11：容器化、初始化和端到端验收

**文件：**
- 创建：`backend/Dockerfile`
- 创建：`frontend/Dockerfile`
- 创建：`frontend/nginx.conf`
- 创建：`compose.yaml`
- 创建：`scripts/seed.py`
- 创建：`Makefile`
- 创建：`frontend/e2e/product-management.spec.ts`
- 修改：`.env.example`

- [ ] **步骤 1：编写端到端业务旅程**

```ts
// frontend/e2e/product-management.spec.ts
test("admin publishes and manages all product types", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("管理员账号").fill("admin");
  await page.getByLabel("密码").fill("demo-password");
  await page.getByRole("button", { name: "登录" }).click();
  for (const type of ["实物商品", "虚拟商品", "广告素材"]) {
    await page.getByRole("button", { name: "发布商品" }).click();
    await page.getByLabel("商品类型").selectOption({ label: type });
    await fillValidProduct(page, type);
    await page.getByRole("button", { name: "提交商品" }).click();
    await expect(page.getByText("发布成功")).toBeVisible();
  }
});
```

同文件继续覆盖组合筛选、编辑、单个和批量上下架、设为处罚及处罚后无恢复操作。

- [ ] **步骤 2：创建容器与健康检查**

`compose.yaml` 为 PostgreSQL 使用 `pg_isready`，Redis 使用 `redis-cli ping`，API 使用 `/health`，Web 使用 Nginx `/healthz`；API 仅在数据库和 Redis 健康后启动，Web 仅在 API 健康后启动。迁移和种子通过独立一次性服务执行，重复运行必须幂等。

- [ ] **步骤 3：运行一键启动并确认服务健康**

运行：`docker compose up --build -d`

预期：`docker compose ps` 中 postgres、redis、api、web 均为 healthy，迁移和 seed 服务成功退出。

- [ ] **步骤 4：运行 Playwright 验收**

运行：`cd frontend && npm run test:e2e`

预期：登录、三类发布、筛选编辑、状态操作全部 PASS。

- [ ] **步骤 5：提交可运行环境**

```bash
git add .env.example Makefile compose.yaml backend/Dockerfile frontend/Dockerfile frontend/nginx.conf scripts frontend/e2e
git commit -m "feat: deliver one command product management demo"
```

## 任务 12：压测、文档和最终证据

**文件：**
- 创建：`loadtest/product-detail.js`
- 创建：`loadtest/redis-degraded.js`
- 创建：`docs/performance/report-template.md`
- 创建：`README.md`
- 修改：`Makefile`

- [ ] **步骤 1：编写 k6 场景与阈值**

```javascript
// loadtest/product-detail.js
import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    cached: { executor: "constant-vus", vus: 50, duration: "30s" },
  },
  thresholds: {
    http_req_failed: ["rate<0.001"],
    http_req_duration: ["p(95)<200"],
  },
};

export default function () {
  const response = http.get(`${__ENV.BASE_URL}/api/v1/public/products/${__ENV.PRODUCT_ID}`);
  check(response, { "status is 200": (r) => r.status === 200 });
}
```

扩展同一脚本支持数据库直读基线、随机有效 UUIDv7 不存在 ID 和显式清理热点缓存后的并发重建。`redis-degraded.js` 在运维步骤暂停 Redis 后只验证受限降级，不自动执行破坏性容器命令。

- [ ] **步骤 2：创建报告模板与 README**

报告表格固定包含机器配置、容器限制、数据量、并发、时长、吞吐、P50/P95/P99、错误率、命中率和数据库回源。README 给出一条启动命令、演示账号生成方式、三类发布路径、测试命令、四种压测步骤、安全说明、容量演进和非生产限制。

- [ ] **步骤 3：运行完整验证**

运行：`cd backend && python -m pytest -q`

预期：后端单元与集成测试全部 PASS。

运行：`cd frontend && npm test -- --run && npm run build && npm run test:e2e`

预期：组件测试、生产构建和端到端测试全部 PASS。

运行：`docker compose config && docker compose ps`

预期：Compose 配置有效，四个长驻服务均为 healthy。

- [ ] **步骤 4：运行压测并填写真实结果**

运行：`k6 run -e BASE_URL=http://localhost -e PRODUCT_ID=0198c8bc-1234-7abc-8def-0123456789ab loadtest/product-detail.js`

预期：`scripts/seed.py` 已为压测商品固定使用 UUIDv7 `0198c8bc-1234-7abc-8def-0123456789ab`；脚本完成并输出吞吐、P95/P99 和错误率。分别记录数据库直读与缓存命中结果，确认缓存吞吐提升至少 5 倍；若未达到，不修改验收口径，保留结果并定位瓶颈后修复。

运行 Redis 故障场景前先执行：`docker compose pause redis`；完成后立即执行：`docker compose unpause redis`。

- [ ] **步骤 5：执行最终静态检查并提交交付材料**

运行：`git diff --check && cd backend && python -m ruff check .`

预期：无空白错误和 Ruff 错误。

```bash
git add README.md Makefile loadtest docs/performance
git commit -m "docs: add reproducible verification and performance evidence"
```

## 最终规格覆盖检查

- 商品发布、管理、编辑、筛选和状态机：任务 2、3、5、9、10。
- 三类商品和不可变版本化模板：任务 2、3、5、9。
- 图片边界与安全：任务 6、9。
- 登录、JWT、统一错误与安全基线：任务 4、5、8。
- 事务、乐观锁和提交后删缓存：任务 3、5、7。
- Cache-Aside、空值缓存、随机 TTL、single-flight、短锁、限流和降级：任务 7。
- Docker Compose、种子数据和独立验收：任务 11。
- 单元、集成、组件、端到端和四类压测证据：任务 1 至 12，集中收口于任务 12。
- UI Designer 的参与边界：任务 8。
