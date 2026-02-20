from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.db.models import AppSetting, Job


def get_job(db: Session, job_id: str) -> Job | None:
    return db.query(Job).filter(Job.id == job_id).first()


def get_jobs(
    db: Session, skip: int = 0, limit: int = 50, status: str | None = None
) -> list[Job]:
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    return query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()


def create_job(db: Session, **kwargs) -> Job:
    job = Job(**kwargs)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job(db: Session, job_id: str, **kwargs) -> Job | None:
    job = get_job(db, job_id)
    if not job:
        return None
    for key, value in kwargs.items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return job


def delete_job(db: Session, job_id: str) -> bool:
    job = get_job(db, job_id)
    if not job:
        return False
    db.delete(job)
    db.commit()
    return True


def get_setting(db: Session, key: str) -> str | None:
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    return setting.value if setting else None


def set_setting(db: Session, key: str, value: str) -> AppSetting:
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if setting:
        setting.value = value
        setting.updated_at = datetime.now(timezone.utc)
    else:
        setting = AppSetting(key=key, value=value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
