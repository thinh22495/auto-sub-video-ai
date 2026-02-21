# AutoSubAI

Công cụ tạo phụ đề video hoàn toàn offline, tự host với giao diện web. Kết hợp nhận dạng giọng nói, dịch thuật AI, phân biệt người nói và xử lý video — tất cả chạy cục bộ, không phụ thuộc cloud.

## Tính năng

- **Nhận dạng giọng nói** — faster-whisper (CTranslate2) với tăng tốc GPU
- **Dịch thuật AI** — Ollama với mô hình đa ngôn ngữ (29+ ngôn ngữ qua Qwen 2.5)
- **Phân biệt người nói** — pyannote.audio nhận diện nhiều người nói
- **Định dạng phụ đề** — Xuất SRT, ASS (có style), VTT
- **Gắn phụ đề vào video** — Nhúng phụ đề trực tiếp vào video (NVENC/libx264)
- **Trình chỉnh sửa phụ đề** — Chỉnh sửa trên trình duyệt với sóng âm, timeline và xem trước video
- **Xử lý hàng loạt** — Xử lý nhiều video cùng lúc với cấu hình chung
- **Style có sẵn** — Netflix, YouTube, Blu-ray, Anime Fansub, Accessibility
- **Tự động nhận diện GPU** — Tự động sử dụng NVIDIA GPU nếu có, chuyển sang CPU nếu không

## Yêu cầu hệ thống

- Docker & Docker Compose
- (Tùy chọn) NVIDIA GPU với [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) để tăng tốc GPU
- RAM 8GB+ (khuyến nghị 16GB cho mô hình large-v3)
- Ổ cứng trống 10GB+ (mô hình sẽ được tải về khi sử dụng lần đầu)

## Bắt đầu nhanh

```bash
# Clone repository
git clone https://github.com/your-org/autosub-ai.git
cd autosub-ai

# Cài đặt một lệnh (copy .env, tạo thư mục, build, khởi chạy)
make setup

# Tải mô hình dịch thuật mặc định (tùy chọn, dùng cho tính năng dịch)
docker compose exec autosub-app bash scripts/setup_models.sh
```

Mở **http://localhost:8080** trên trình duyệt.

## Cài đặt thủ công

```bash
# 1. Sao chép file cấu hình
cp .env.example .env

# 2. Tạo thư mục dữ liệu
mkdir -p data/videos data/subtitles data/output data/models data/db data/ollama

# 3. Build và khởi chạy
docker compose build
docker compose up -d

# 4. Kiểm tra trạng thái
curl http://localhost:8080/api/health | python3 -m json.tool
```

## Chế độ chỉ CPU

Nếu bạn không có NVIDIA GPU:

```bash
make up-cpu
```

Lệnh này bỏ qua yêu cầu GPU. Whisper chạy trên CPU (chậm hơn nhưng vẫn hoạt động), FFmpeg sử dụng `libx264` thay vì NVENC.

## Hướng dẫn sử dụng

### Xử lý đơn lẻ

1. Đặt file video vào `data/videos/` (hoặc dùng trình duyệt file tích hợp)
2. Nhấn **New Job** trên dashboard
3. Chọn video, cấu hình ngôn ngữ và định dạng xuất
4. Nhấn **Start** và theo dõi tiến trình thời gian thực

### Xử lý hàng loạt

1. Nhấn **Batch** trên dashboard
2. Nhấn **New Batch** và thêm nhiều file video
3. Cấu hình chung (ngôn ngữ, mô hình, định dạng xuất)
4. Có thể ghi đè ngôn ngữ nguồn cho từng file riêng
5. Nhấn **Start Batch** để xử lý tất cả

### Chỉnh sửa phụ đề

Sau khi job hoàn thành, nhấn **Edit Subtitles** để mở trình chỉnh sửa:
- Hiển thị sóng âm với màu sắc theo người nói
- Kéo thả segment để điều chỉnh thời gian
- Tách, gộp, thêm hoặc xóa segment
- Hỗ trợ Undo/Redo (Ctrl+Z / Ctrl+Y)
- Lịch sử phiên bản với khôi phục

## Cấu hình

Tất cả cài đặt nằm trong file `.env`. Các tùy chọn chính:

| Cài đặt | Mặc định | Mô tả |
|---------|---------|-------|
| `AUTOSUB_PORT` | 8080 | Cổng giao diện web |
| `AUTOSUB_DEFAULT_WHISPER_MODEL` | large-v3-turbo | Mô hình STT (tiny/base/small/medium/large-v3/large-v3-turbo) |
| `AUTOSUB_DEFAULT_OLLAMA_MODEL` | qwen2.5:7b | Mô hình dịch thuật |
| `AUTOSUB_WHISPER_DEVICE` | auto | Chọn cuda/cpu (auto tự nhận diện GPU) |
| `AUTOSUB_MAX_CONCURRENT_JOBS` | 2 | Số job chạy song song tối đa |
| `AUTOSUB_GPU_WORKER_CONCURRENCY` | 1 | Số tác vụ GPU đồng thời (giữ 1 để tránh tràn VRAM) |

Xem [.env.example](.env.example) để biết tất cả tùy chọn.

## Kiến trúc

```
Docker Compose Stack
├── autosub-app          (FastAPI + Celery + Next.js SPA)
│   ├── FastAPI          (REST API + WebSocket)
│   ├── Celery Worker    (Xử lý tác vụ GPU/CPU)
│   └── Celery Beat      (Dọn dẹp định kỳ & kiểm tra sức khỏe)
├── autosub-redis        (Hàng đợi tác vụ + pub/sub)
└── autosub-ollama       (LLM cục bộ cho dịch thuật)
```

### Quy trình xử lý

```
Video → Trích xuất âm thanh (FFmpeg)
      → Nhận dạng giọng nói (faster-whisper)
      → Phân biệt người nói (pyannote, tùy chọn)
      → Dịch thuật (Ollama, tùy chọn)
      → Tạo phụ đề (pysubs2)
      → Gắn phụ đề vào video (FFmpeg, tùy chọn)
```

## API

URL gốc: `http://localhost:8080/api`

| Phương thức | Endpoint | Mô tả |
|-------------|----------|-------|
| POST | `/jobs` | Tạo job phụ đề |
| GET | `/jobs` | Danh sách job |
| GET | `/jobs/{id}` | Chi tiết job |
| DELETE | `/jobs/{id}` | Hủy/xóa job |
| POST | `/batch` | Tạo batch |
| GET | `/batch/{id}` | Trạng thái batch |
| GET | `/health` | Kiểm tra sức khỏe hệ thống |
| GET | `/system/info` | Thông tin hệ thống |
| GET | `/files/browse` | Duyệt file trên server |
| GET | `/models/whisper` | Danh sách mô hình Whisper |
| GET | `/models/ollama` | Danh sách mô hình Ollama |

Tài liệu API đầy đủ: `http://localhost:8080/docs` (Swagger UI)

## Phát triển

```bash
# Backend (yêu cầu Python 3.12, Redis đang chạy)
make dev-backend

# Frontend (yêu cầu Node.js 22)
make dev-frontend

# Chạy tests
cd backend && python -m pytest ../tests/ -v
```

## Lệnh Makefile

| Lệnh | Mô tả |
|-------|-------|
| `make setup` | Cài đặt lần đầu (build + khởi chạy) |
| `make build` | Build Docker images |
| `make up` | Khởi chạy dịch vụ (GPU) |
| `make up-cpu` | Khởi chạy dịch vụ (chỉ CPU) |
| `make down` | Dừng dịch vụ |
| `make logs` | Theo dõi log |
| `make restart` | Khởi động lại dịch vụ |
| `make clean` | Xóa containers, volumes, images |
| `make health` | Kiểm tra sức khỏe API |

## Xử lý sự cố

**Không nhận diện được GPU**: Đảm bảo NVIDIA Container Toolkit đã cài đặt và `nvidia-smi` hoạt động trong Docker:
```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

**Tải mô hình Ollama thất bại**: Pull thủ công:
```bash
docker compose exec autosub-ollama ollama pull qwen2.5:7b
```

**Tràn VRAM**: Sử dụng mô hình Whisper nhỏ hơn (`small` hoặc `base`) hoặc đặt `AUTOSUB_GPU_WORKER_CONCURRENCY=1`.

**Nhận dạng chậm trên CPU**: Sử dụng mô hình `tiny` hoặc `base` để xử lý nhanh hơn (độ chính xác thấp hơn).

## Giấy phép

MIT
