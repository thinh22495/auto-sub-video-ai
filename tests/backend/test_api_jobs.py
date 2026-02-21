"""Tests for jobs API endpoints."""

import json
from unittest.mock import patch

import pytest


class TestJobsAPI:
    def test_create_job_file_not_found(self, client):
        resp = client.post("/api/jobs", json={
            "input_path": "/nonexistent/video.mp4",
            "output_formats": ["srt"],
            "whisper_model": "tiny",
        })
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"]

    def test_create_job_invalid_format(self, client, temp_video):
        resp = client.post("/api/jobs", json={
            "input_path": temp_video,
            "output_formats": ["invalid_format"],
            "whisper_model": "tiny",
        })
        assert resp.status_code == 400
        assert "Invalid format" in resp.json()["detail"]

    @patch("backend.api.jobs.run_pipeline")
    def test_create_job_success(self, mock_pipeline, client, temp_video):
        mock_pipeline.apply_async.return_value = None
        resp = client.post("/api/jobs", json={
            "input_path": temp_video,
            "output_formats": ["srt"],
            "whisper_model": "tiny",
        })
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "QUEUED"
        assert data["input_filename"] == "test_video.mp4"
        assert data["whisper_model"] == "tiny"

    @patch("backend.api.jobs.run_pipeline")
    def test_list_jobs(self, mock_pipeline, client, temp_video):
        mock_pipeline.apply_async.return_value = None
        # Create a job first
        client.post("/api/jobs", json={
            "input_path": temp_video,
            "output_formats": ["srt"],
            "whisper_model": "tiny",
        })

        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        jobs = resp.json()
        assert len(jobs) >= 1

    @patch("backend.api.jobs.run_pipeline")
    def test_get_job(self, mock_pipeline, client, temp_video):
        mock_pipeline.apply_async.return_value = None
        create_resp = client.post("/api/jobs", json={
            "input_path": temp_video,
            "output_formats": ["srt"],
            "whisper_model": "tiny",
        })
        job_id = create_resp.json()["id"]

        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == job_id

    def test_get_nonexistent_job(self, client):
        resp = client.get("/api/jobs/nonexistent-id")
        assert resp.status_code == 404

    @patch("backend.api.jobs.run_pipeline")
    def test_delete_job(self, mock_pipeline, client, temp_video):
        mock_pipeline.apply_async.return_value = None
        create_resp = client.post("/api/jobs", json={
            "input_path": temp_video,
            "output_formats": ["srt"],
            "whisper_model": "tiny",
        })
        job_id = create_resp.json()["id"]

        resp = client.delete(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == job_id

        # Should be gone
        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 404

    def test_get_subtitles_not_completed(self, client):
        # Try to get subtitles for non-existent job
        resp = client.get("/api/jobs/fake-id/subtitles")
        assert resp.status_code == 404


class TestSubtitleParsedEndpoint:
    def test_not_completed_job(self, client):
        resp = client.get("/api/jobs/fake-id/subtitles/parsed")
        assert resp.status_code == 404


class TestSubtitleVersions:
    def test_list_versions_no_job(self, client):
        resp = client.get("/api/jobs/fake-id/subtitles/versions")
        assert resp.status_code == 404
