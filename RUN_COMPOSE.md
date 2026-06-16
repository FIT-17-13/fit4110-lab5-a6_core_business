# RUN_COMPOSE.md – Hướng dẫn chạy Lab 05 (Core Business Service)

Tài liệu này hướng dẫn người khác clone repo sạch và chạy lại stack Compose của Lab 05 cho **Core Business Policy Engine**.

---

## 1. Clone repo

```bash
git clone <repo-url>
cd fit4110-lab5-a6_core_business
```

---

## 2. Cài dependencies cho Newman/Prism/Spectral (tuỳ chọn)

```bash
npm install
```

---

## 3. Build & chạy stack Docker Compose

```bash
# Copy .env.example sang .env (không commit file .env thật)
cp .env.example .env

# Build images và khởi động tất cả container trong nền
docker compose up -d --build
```

Stack sẽ tạo 3 container theo thứ tự:

| Container | Image | Port | Vai trò |
|---|---|---|---|
| `fit4110-db-lab05` | postgres:15-alpine | 5432 (internal) | Cơ sở dữ liệu PostgreSQL |
| `fit4110-ai-lab05` | python:3.11-slim | 9000 | AI Vision Mock |
| `fit4110-core-lab05` | (build local) | 8000 | Core Business Policy Engine |

Theo dõi log:

```bash
docker compose logs -f
```

---

## 4. Kiểm tra readiness

Sau khi stack khởi động, kiểm tra health của từng service:

```bash
# Core Business API
curl http://localhost:8000/health

# AI Vision Mock
curl http://localhost:9000/health

# PostgreSQL
docker exec -it fit4110-db-lab05 pg_isready -U lab05
```

Kết quả mong đợi từ API:
```json
{"status": "ok", "service": "core-business", "version": "0.5.0"}
```

---

## 5. Thử nghiệm các endpoint

### Gửi sự kiện nhiệt độ cao (sẽ tạo alert)
```bash
curl -X POST http://localhost:8000/events/iot \
  -H "Authorization: Bearer local-dev-token" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32-LAB-A01","metric":"temperature","value":38.5,"unit":"celsius","timestamp":"2026-05-13T08:30:00+07:00"}'
```

### Gửi sự kiện quẹt thẻ ngoài giờ
```bash
curl -X POST http://localhost:8000/events/access \
  -H "Authorization: Bearer local-dev-token" \
  -H "Content-Type: application/json" \
  -d '{"card_id":"RFID-0042","gate_id":"GATE-A1","direction":"IN","timestamp":"2026-05-13T23:15:00+07:00"}'
```

### Gửi kết quả AI Vision rủi ro cao
```bash
curl -X POST http://localhost:8000/events/vision \
  -H "Authorization: Bearer local-dev-token" \
  -H "Content-Type: application/json" \
  -d '{"camera_id":"CAM-01","objects":["person"],"confidence":[0.95],"risk_level":"high","timestamp":"2026-05-13T08:30:00+07:00"}'
```

### Xem danh sách cảnh báo
```bash
curl http://localhost:8000/alerts \
  -H "Authorization: Bearer local-dev-token"
```

### Xem danh sách quy tắc
```bash
curl http://localhost:8000/rules \
  -H "Authorization: Bearer local-dev-token"
```

---

## 6. Chạy Newman test trên stack Compose (tuỳ chọn)

```bash
npm run test:compose
```

Report sinh tại:

```text
reports/newman-lab05-compose.xml
reports/newman-lab05-compose.html
```

---

## 7. Dừng stack

```bash
docker compose down

# Xoá cả volume dữ liệu DB
docker compose down -v
```

---

## 8. Lệnh nhanh (Makefile)

```bash
make compose-up    # build & chạy stack
make compose-down  # dừng stack
make logs          # theo dõi log
make build         # build image riêng (không compose)
make lint          # lint OpenAPI contract
```

---

## 9. Mẹo gỡ lỗi

- `docker compose ps` → xem trạng thái tất cả container.
- Nếu `class-net` không tồn tại, tạo trước: `docker network create class-net`.
- Nếu port 8000/9000 bị chiếm, sửa `APP_PORT`/`AI_PORT` trong `.env`.
- AI Vision Mock dùng Python stdlib → không cần cài thêm gói, khởi động gần như tức thì.
