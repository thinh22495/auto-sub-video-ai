"""Tests for batch API endpoints."""

from unittest.mock import patch

import pytest


class TestBatchAPI:
    def test_list_batches_empty(self, client):
        resp = client.get("/api/batch")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_batch_no_files(self, client):
        resp = client.post("/api/batch", json={
            "files": [],
            "output_formats": ["srt"],
        })
        # Pydantic validation should catch min_length=1
        assert resp.status_code == 422

    def test_create_batch_file_not_found(self, client):
        resp = client.post("/api/batch", json={
            "files": [{"input_path": "/nonexistent/video.mp4"}],
            "output_formats": ["srt"],
        })
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"]

    @patch("backend.api.batch.run_pipeline")
    def test_create_batch_success(self, mock_pipeline, client, temp_video):
        mock_pipeline.apply_async.return_value = None
        resp = client.post("/api/batch", json={
            "name": "Test Batch",
            "files": [{"input_path": temp_video}],
            "output_formats": ["srt"],
            "whisper_model": "tiny",
        })
        assert resp.status_code == 202
        data = resp.json()
        assert data["name"] == "Test Batch"
        assert data["total_jobs"] == 1
        assert data["status"] == "QUEUED"
        assert len(data["jobs"]) == 1

    @patch("backend.api.batch.run_pipeline")
    def test_get_batch(self, mock_pipeline, client, temp_video):
        mock_pipeline.apply_async.return_value = None
        create_resp = client.post("/api/batch", json={
            "files": [{"input_path": temp_video}],
            "output_formats": ["srt"],
        })
        batch_id = create_resp.json()["id"]

        resp = client.get(f"/api/batch/{batch_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == batch_id

    def test_get_nonexistent_batch(self, client):
        resp = client.get("/api/batch/nonexistent")
        assert resp.status_code == 404

    @patch("backend.api.batch.run_pipeline")
    def test_cancel_batch(self, mock_pipeline, client, temp_video):
        mock_pipeline.apply_async.return_value = None
        create_resp = client.post("/api/batch", json={
            "files": [{"input_path": temp_video}],
            "output_formats": ["srt"],
        })
        batch_id = create_resp.json()["id"]

        resp = client.post(f"/api/batch/{batch_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["cancelled"] >= 0

    @patch("backend.api.batch.run_pipeline")
    def test_delete_batch(self, mock_pipeline, client, temp_video):
        mock_pipeline.apply_async.return_value = None
        create_resp = client.post("/api/batch", json={
            "files": [{"input_path": temp_video}],
            "output_formats": ["srt"],
        })
        batch_id = create_resp.json()["id"]

        resp = client.delete(f"/api/batch/{batch_id}")
        assert resp.status_code == 200

        resp = client.get(f"/api/batch/{batch_id}")
        assert resp.status_code == 404

    @patch("backend.api.batch.run_pipeline")
    def test_batch_progress(self, mock_pipeline, client, temp_video):
        mock_pipeline.apply_async.return_value = None
        create_resp = client.post("/api/batch", json={
            "files": [{"input_path": temp_video}],
            "output_formats": ["srt"],
        })
        batch_id = create_resp.json()["id"]

        resp = client.get(f"/api/batch/{batch_id}/progress")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_percent" in data
        assert "total" in data
