# Readiness Checklist – Lab 05 (Core Business Service)

Danh sách kiểm tra để đảm bảo stack Docker Compose của **Core Business Policy Engine** sẵn sàng trước khi nộp bài.

- [x] **Database ready:** container `fit4110-db-lab05` (PostgreSQL) đã chạy và phản hồi `pg_isready`.
  ```bash
  docker exec -it fit4110-db-lab05 pg_isready -U lab05
  # Expected: /var/run/postgresql:5432 - accepting connections
  ```

- [x] **AI service ready:** container `fit4110-ai-lab05` (AI Vision Mock) trả về `200` cho `/health` và `/predict`.
  ```bash
  curl http://localhost:9000/health
  # Expected: {"status":"ok","service":"ai-vision-mock","version":"0.5.0"}
  curl -X POST http://localhost:9000/predict
  # Expected: {"objects":["person"],"confidence":[0.95],"risk_level":"low"}
  ```

- [x] **API ready:** container `fit4110-core-lab05` (Core Business) trả `200` cho `/health` và các endpoint `/events/*`, `/alerts`, `/rules` hoạt động với token hợp lệ.
  ```bash
  curl http://localhost:8000/health
  # Expected: {"status":"ok","service":"core-business","version":"0.5.0"}
  ```

- [x] **Environment variables:** `.env` đã được thiết lập đúng (`APP_PORT`, `POSTGRES_USER`, `AUTH_TOKEN`, `AI_SERVICE_URL`). Không sử dụng secret thật; commit `.env.example`, giữ `.env` cục bộ.

- [x] **Network & Ports:** mạng `team-internal` hoạt động; Core Business API có thể gọi AI service qua hostname `ai-service:9000`; ports được map: 8000 (API), 9000 (AI), 5432 (DB, internal only).

- [x] **Image tags:** build image với tag `v0.1.0-team-core` và push lên registry (ghcr.io hoặc Docker Hub).
  ```bash
  docker build -t fit4110/core-business:v0.1.0-team-core .
  docker push fit4110/core-business:v0.1.0-team-core
  ```

---

## Ghi chú

- Service `team-core` không dùng AI trực tiếp trong business logic, nhưng container `ai-service` (AI Vision Mock) vẫn có mặt trong Compose stack để đáp ứng yêu cầu 3 container.
- Dữ liệu alerts và rules được lưu in-memory (Lab 05). PostgreSQL sẵn sàng cho persistence trong các Lab sau.
- `class-net` external network cần tạo trước nếu chưa có: `docker network create class-net`.
