import json
import logging
from typing import List
from urllib.parse import urlparse

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import settings
from database import Base, engine, get_db
import models
import schemas
from scanner import run_scan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("a11y-auditor")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auditeur d'accessibilité web (RGAA)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "healthy"}


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not urlparse(url).scheme:
        url = f"https://{url}"
    parsed = urlparse(url)
    if not parsed.netloc:
        raise HTTPException(400, "URL invalide")
    return url


@app.post("/api/scans", response_model=schemas.ScanDetailOut, status_code=201)
def create_scan(payload: schemas.ScanRequest, db: Session = Depends(get_db)):
    url = _normalize_url(payload.url)

    try:
        result = run_scan(url)
    except RuntimeError as e:
        scan = models.Scan(
            url=url, score=0, critical_count=0, serious_count=0, moderate_count=0,
            minor_count=0, passes_count=0, violations_json="[]", error=str(e),
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        raise HTTPException(502, str(e))

    counts = result["counts"]
    scan = models.Scan(
        url=url,
        score=result["score"],
        critical_count=counts["critical"],
        serious_count=counts["serious"],
        moderate_count=counts["moderate"],
        minor_count=counts["minor"],
        passes_count=result["passes_count"],
        violations_json=json.dumps(result["violations"], ensure_ascii=False),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    return _to_detail(scan)


def _to_detail(scan: models.Scan) -> schemas.ScanDetailOut:
    violations = json.loads(scan.violations_json)
    return schemas.ScanDetailOut(
        id=scan.id, url=scan.url, score=scan.score,
        critical_count=scan.critical_count, serious_count=scan.serious_count,
        moderate_count=scan.moderate_count, minor_count=scan.minor_count,
        passes_count=scan.passes_count, error=scan.error, created_at=scan.created_at,
        violations=violations,
    )


@app.get("/api/scans", response_model=List[schemas.ScanOut])
def list_scans(db: Session = Depends(get_db)):
    return db.query(models.Scan).order_by(models.Scan.created_at.desc()).all()


@app.get("/api/scans/{scan_id}", response_model=schemas.ScanDetailOut)
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(models.Scan).get(scan_id)
    if not scan:
        raise HTTPException(404, "Scan introuvable")
    return _to_detail(scan)


@app.delete("/api/scans/{scan_id}", status_code=204)
def delete_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(models.Scan).get(scan_id)
    if not scan:
        raise HTTPException(404, "Scan introuvable")
    db.delete(scan)
    db.commit()
    return None
