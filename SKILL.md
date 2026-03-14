---
name: crm-coach
description: 用于在数据库新建、更新、查询客户信息时候调用。
---

# Skill V2

## 1) 定位

- 用于在数据库新建、更新、查询客户信息时候调用。
- 技能调用 V2 API，只传结构化参数，不生成 SQL。

## 2) 固定安全约束

- 固定 API：`POST https://veon-api-vercel.vercel.app/api`
- 固定 `table_key`：`customer_profiles`
- `table_key` 由脚本内常量写死，用户自然语言不可覆盖。
- 必须带 `access_code`，由 API + RLS 完成多租户隔离。

## 3) customer_code 统一规则（由 API 自动生成）

格式：`YYYYMMDDHHmm-XX`

示例：`202603082130-7F`

要求：

- `create_one` 无需提供 `payload.customer_code`，由 API 自动生成。
- `upsert_one` 若命中更新，沿用原 code；若走插入分支且未给 filter.code，由 API 自动生成。
- 查询或更新时，继续使用 API 返回的 `customer_code`。

## 4) 更新策略（按最新规则）

- 大多数字段采用局部更新（patch）。
- `project` 为单个项目名字符串字段；可在 `create_one/update_one/upsert_one` 中按普通业务字段传入。
- `summary` 每次更新必须传完整文本，并覆盖旧值。
- 即：`update_one/upsert_one` 时 `payload.summary` 必填。

## 5) 推荐动作映射

- 查单客：`get_one`（filter 用 `customer_code`）
- 新增：`create_one`
- 局部更新：`update_one`（但 `summary` 必传且全量覆盖）
- 不确定存在性时：`upsert_one`（同样 `summary` 必传）
- 分页列表：`list`


## 6) 执行规则（非常重要）

- 仅能执行 skill 自带脚本；skill 内资源路径一律相对于当前 `SKILL.md` 所在目录解析。
- 查询所有客户时，直接使用 `action=list`；默认可不传 `filter` / `payload`。

## 7) 本地调用脚本

脚本路径：`scripts/call_v2_api.py`

### 7.1 查询所有客户

```bash
python scripts/call_v2_api.py \
  --action list \
  --access-code 888
```

### 7.2 按 code 查询

```bash
python scripts/call_v2_api.py \
  --action get_one \
  --filter-json "{\"customer_code\":\"202603082130-7F\"}" \
  --access-code 888
```

### 7.3 局部更新（summary 必传）

```bash
python scripts/call_v2_api.py \
  --action update_one \
  --filter-json "{\"customer_code\":\"202603082130-7F\"}" \
  --payload-json "{\"living_area\":\"浦东\",\"project\":\"滨江壹号\",\"summary\":\"2026-03-08: 二访后关注学区与预算，计划周三复看\"}" \
  --access-code 888
```

### 7.4 upsert（summary 必传）

```bash
python scripts/call_v2_api.py \
  --action upsert_one \
  --payload-file examples/customer_full_payload.json \
  --filter-json "{\"customer_code\":\"202603082130-7F\"}" \
  --access-code 888
```


## 8) 质量要求

- 信息不足先追问，信息充分再落库。
- `customer_code` 在单任务内保持一致。
- `project` 仅保存单个项目名，按字符串处理。
- 每次更新必须携带完整 `summary` 文本覆盖旧值。

## 9) 代码位置

- Skill 调用脚本：`scripts/call_v2_api.py`
- 示例 payload：`examples/customer_full_payload.json`
- 仓库内 API 规格文档：`api/API_V2_SPEC.md`
