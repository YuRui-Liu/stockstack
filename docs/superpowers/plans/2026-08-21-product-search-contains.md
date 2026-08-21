# 商品关键词包含搜索实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 商品列表关键词可按商品标题或商品 UUID 的任意连续片段搜索。

**架构：** 保持现有 API 和前端不变，只替换仓储层的关键词过滤条件。使用 SQLAlchemy 生成两个自动转义的包含条件，以 OR 组合标题和转换为文本的 UUID，再与类型、状态过滤条件按 AND 组合。

**技术栈：** Python 3.12、SQLAlchemy 2、asyncpg、PostgreSQL 16、pytest

---

### 任务 1：锁定包含搜索行为

**文件：**
- 修改：`backend/tests/integration/test_repository.py`
- 修改：`backend/app/catalog/repository.py`

- [ ] **步骤 1：编写失败的测试**

在仓储集成测试中创建标题为 `红色保暖外套` 和 `夏季短袖` 的两件商品。断言 `repository.list(query="保暖")` 只返回前者；再取前者 UUID 的中间片段，断言该片段也只返回前者。

```python
@pytest.mark.asyncio
async def test_product_list_searches_title_and_id_by_contained_fragment(db_session):
    repository = ProductRepository(db_session)
    first = await repository.create_with_images(
        product_values("红色保暖外套"), image_values()
    )
    await repository.create_with_images(product_values("夏季短袖"), image_values())
    await db_session.commit()

    title_items, title_total = await repository.list(query="保暖")
    id_items, id_total = await repository.list(query=str(first.id)[9:17])

    assert title_total == 1
    assert [item.id for item in title_items] == [first.id]
    assert id_total == 1
    assert [item.id for item in id_items] == [first.id]
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```bash
cd backend && TEST_DATABASE_URL='postgresql+asyncpg://liuyuxiang05@127.0.0.1:5432/stockstack_repository_test' uv run --frozen pytest tests/integration/test_repository.py::test_product_list_searches_title_and_id_by_contained_fragment -q
```

预期：FAIL；当前 `simple` 全文搜索不能匹配中文标题片段，UUID 逻辑只接受完整 UUID。

- [ ] **步骤 3：实现最小查询修改**

在 `ProductRepository.list` 中删除 UUID 解析和全文搜索分支，使用自动转义包含条件：

```python
filters.append(
    or_(
        ProductModel.title.icontains(normalized_query, autoescape=True),
        cast(ProductModel.id, String).icontains(normalized_query, autoescape=True),
    )
)
```

同时从 SQLAlchemy 导入 `String`、`cast` 和 `or_`，移除不再需要的 `UUID` 导入（若文件其他逻辑仍使用 UUID，则保留）。

- [ ] **步骤 4：运行测试验证通过**

重新运行步骤 2 的单项测试，预期：`1 passed`。

- [ ] **步骤 5：运行后端回归验证**

运行：

```bash
cd backend && TEST_DATABASE_URL='postgresql+asyncpg://liuyuxiang05@127.0.0.1:5432/stockstack_repository_test' uv run --frozen pytest -q
cd backend && uv run --frozen ruff check .
git diff --check
```

预期：测试全部通过或仅有已有的环境性 skip；Ruff 和 diff 检查退出码为 0。

- [ ] **步骤 6：提交实现**

```bash
git add backend/tests/integration/test_repository.py backend/app/catalog/repository.py docs/superpowers/plans/2026-08-21-product-search-contains.md
git commit -m "feat: support partial product search"
```
