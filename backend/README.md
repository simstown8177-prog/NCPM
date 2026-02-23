# ERP Phase 1 API (FastAPI)

## Run (Local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

## Seed (example)

```bash
curl -X POST http://localhost:8000/admin/seed
```

## Endpoints

- `POST /purchase`
- `POST /sale`
- `GET /inventory`
- `GET /reorder-alerts`
- `GET /items`
- `POST /items`
- `PATCH /items/{item_code}`
- `GET /bom/{parent_code}`
- `POST /bom`
- `DELETE /bom?parent_code=...&child_code=...`
- `GET /transactions`
- `POST /rop/recalculate`
- `POST /admin/seed`

Example:

```bash
curl -X POST http://localhost:8000/purchase \
  -H 'Content-Type: application/json' \
  -d '{"item_code":"RM-MEAT-001","quantity":20,"unit":"kg"}'
```

## Deploy (Render)

1. Render에서 New Web Service → GitHub 레포 연결
2. 자동으로 `render.yaml` 인식됨
3. 배포 후 `POST /admin/seed` 실행

Note: Render 디스크(`/var/data`)에 SQLite 파일을 저장합니다. 데이터 지속됩니다.
