# ERP 1단계 설계 (고기류 중심)

## 1. DB 스키마 초안 (1순위)

### 1.1 Item Master (`items`)

| Column | Type | Notes |
| --- | --- | --- |
| item_id | BIGINT PK | auto increment |
| item_code | VARCHAR(32) | unique, 예: `RM-MEAT-001` |
| item_name | VARCHAR(100) | |
| item_type | ENUM('RM','SF','CP','FG') | |
| unit | ENUM('g','kg','ea','pack') | 기본 재고 단위 |
| purchase_unit | ENUM('g','kg','ea','pack') | 발주 단위 |
| standard_cost | DECIMAL(12,4) | 기준 원가 |
| is_active | BOOLEAN | |
| created_at | TIMESTAMP | |

Recommended index:
- `UNIQUE (item_code)`
- `INDEX (item_type)`

### 1.2 BOM Table (`bom`)

| Column | Type | Notes |
| --- | --- | --- |
| bom_id | BIGINT PK | auto increment |
| parent_item_id | BIGINT FK -> items.item_id | FG 또는 SF |
| child_item_id | BIGINT FK -> items.item_id | RM, SF, CP 가능 |
| quantity | DECIMAL(12,4) | parent 1단위 기준 소요량 |
| loss_rate | DECIMAL(5,4) NULL | 0.0000 ~ 1.0000 |
| unit | ENUM('g','kg','ea','pack') | 소요 단위 |
| created_at | TIMESTAMP | |

Recommended constraints:
- `UNIQUE (parent_item_id, child_item_id)`
- `CHECK (parent_item_id != child_item_id)`

Multi-level BOM 지원 방식:
- `parent_item_id`가 SF인 레코드 허용
- 최종 소비는 FG 기준으로 재귀 조회

### 1.3 Inventory Table (`inventory`)

| Column | Type | Notes |
| --- | --- | --- |
| inventory_id | BIGINT PK | auto increment |
| item_id | BIGINT FK -> items.item_id | |
| current_stock | DECIMAL(12,4) | 현 재고 |
| reserved_stock | DECIMAL(12,4) | 예약 차감 |
| reorder_point | DECIMAL(12,4) | ROP |
| reorder_qty | DECIMAL(12,4) | 기본 발주 수량 |
| updated_at | TIMESTAMP | |

Recommended constraint:
- `UNIQUE (item_id)` for 1매장 기준

### 1.4 Transaction Table (`transactions`)

| Column | Type | Notes |
| --- | --- | --- |
| transaction_id | BIGINT PK | auto increment |
| transaction_type | ENUM('SALE','PURCHASE','ADJUST') | |
| item_id | BIGINT FK -> items.item_id | |
| quantity | DECIMAL(12,4) | 양수 기준, 타입으로 방향 해석 |
| reference_id | VARCHAR(64) | 주문, 발주, 조정 번호 |
| created_at | TIMESTAMP | |

Recommended index:
- `INDEX (item_id, created_at)`
- `INDEX (transaction_type, created_at)`

Optional (확장 대비) 컬럼 제안:
- `store_id` in `inventory`, `transactions` (다점포 대비)
- `uom` in `transactions` (입출고 단위 명시)

## 2. 로직 플로우 (2순위)

1. `POST /sale` 수신
2. 판매 FG 품목의 재고 차감
3. BOM 조회 (FG 기준)
4. RM/SF/CP 소요량 계산
5. 각 소요 품목 재고 차감
6. 모든 품목의 `reorder_point` 비교
7. ROP 이하 품목이면 발주 트리거 생성
8. 발주 트리거는 A형 룰로 수량 산정

## 3. ROP 계산 로직 의사코드 (2순위)

```pseudo
function calc_rop(avg_daily_usage, lead_time_days, safety_days):
    base = avg_daily_usage * lead_time_days
    safety = avg_daily_usage * safety_days
    return base + safety

function calc_reorder_qty_a_type(rop, current_stock, unit_size_kg):
    if current_stock > rop:
        return 0
    # A형: 기준 이하이면 고정 발주
    return 10.0  # kg, 정책 고정값

function round_to_unit(qty, unit_size_kg):
    return ceil(qty / unit_size_kg) * unit_size_kg

# example
avg_daily_usage = 2.5
lead_time_days = 2.0
safety_days = 0.5
rop = calc_rop(avg_daily_usage, lead_time_days, safety_days)
reorder_qty = calc_reorder_qty_a_type(rop, current_stock, 2.0)
reorder_qty = round_to_unit(reorder_qty, 2.0)
```

Notes:
- 고기류 기준: `unit_size_kg = 2.0`
- A형: `current_stock <= ROP`이면 고정 10kg 발주

## 4. API 설계 초안 (3순위)

### 4.1 `POST /sale`
Request:
- `item_code`
- `quantity`
- `reference_id`

Behavior:
- FG 차감
- BOM 기반 구성품 차감
- ROP 비교 후 발주 트리거 생성

### 4.2 `POST /purchase`
Request:
- `item_code`
- `quantity`
- `reference_id`

Behavior:
- 재고 증가
- `transactions` 기록

### 4.3 `GET /inventory`
Response:
- `item_code`
- `current_stock`
- `reserved_stock`
- `reorder_point`
- `reorder_qty`

### 4.4 `GET /reorder-alert`
Response:
- `item_code`
- `current_stock`
- `reorder_point`
- `suggested_reorder_qty`
