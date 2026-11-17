import json
import logging
import threading
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import settings
from database import Base, engine, get_db
import models
import schemas
from scanner import run_scan
from url_guard import UnsafeURLError, normalize_url, resolve_public_ip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("a11y-auditor")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auditeur d'accessibilité web (RGAA)", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Les routes synchrones tournent dans un pool de threads : ce sémaphore borne le nombre
# de navigateurs ouverts en même temps, pour qu'une rafale de requêtes ne sature pas la machine.
_scan_slots = threading.BoundedSemaphore(settings.MAX_CONCURRENT_SCANS)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/scans", response_model=schemas.ScanDetailOut, status_code=201)
def create_scan(payload: schemas.ScanRequest, db: Session = Depends(get_db)):
    try:
        url = normalize_url(payload.url)
        pinned_ip = resolve_public_ip(url)
    except UnsafeURLError as e:
        raise HTTPException(400, str(e))

    if not _scan_slots.acquire(blocking=False):
        raise HTTPException(503, "Trop de scans en cours. Réessaie dans quelques secondes.")
    try:
        result = run_scan(url, pinned_ip)
    except UnsafeURLError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        scan = models.Scan(
            url=url, score=0, critical_count=0, serious_count=0, moderate_count=0,
            minor_count=0, passes_count=0, violations_json="[]", error=str(e),
        )
        db.add(scan)
        db.commit()
        raise HTTPException(502, str(e))
    finally:
        _scan_slots.release()

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
def list_scans(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Scan)
        .order_by(models.Scan.created_at.desc(), models.Scan.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def _get_scan_or_404(db: Session, scan_id: int) -> models.Scan:
    scan = db.get(models.Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan introuvable")
    return scan


@app.get("/api/scans/{scan_id}", response_model=schemas.ScanDetailOut)
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    return _to_detail(_get_scan_or_404(db, scan_id))


@app.delete("/api/scans/{scan_id}", status_code=204)
def delete_scan(scan_id: int, db: Session = Depends(get_db)):
    db.delete(_get_scan_or_404(db, scan_id))
    db.commit()
    return None
