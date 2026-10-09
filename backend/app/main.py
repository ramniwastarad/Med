import os, json, hashlib, secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, DateTime, ForeignKey, Text, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medibridge.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class Record(Base):
    __tablename__ = "medical_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
    record_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(180))
    record_date: Mapped[str] = mapped_column(String(10), index=True)
    provider_name: Mapped[str] = mapped_column(String(180), default="Patient supplied")
    details: Mapped[str] = mapped_column(Text, default="{}")
    source_label: Mapped[str] = mapped_column(String(180), default="Patient entry")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ShareGrant(Base):
    __tablename__ = "share_grants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(Integer, default=1)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    record_ids: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(Integer, default=1)
    share_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    event_type: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)
app = FastAPI(title="MediBridge API", version="1.0.0", description="Synthetic-data HealthTech hackathon prototype.")
origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origin.split(",") if x.strip()], allow_credentials=False, allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"], allow_headers=["*"])

def now_utc(): return datetime.now(timezone.utc)
def as_utc(dt):
    if dt.tzinfo is None: return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
def parse_details(raw):
    try: return json.loads(raw or "{}")
    except Exception: return {}
def record_dict(r):
    return {"id":r.id,"record_type":r.record_type,"title":r.title,"record_date":r.record_date,"provider_name":r.provider_name,"details":parse_details(r.details),"source_label":r.source_label}
def audit(db, event, share_id=None, detail=""):
    db.add(AuditEvent(patient_id=1, share_id=share_id, event_type=event, detail=detail[:300]))
    db.commit()

def seed():
    with SessionLocal() as db:
        if db.scalar(select(Record.id).limit(1)) is not None: return
        data = [
          ("diagnosis","Type 2 diabetes","2025-11-12","Dr. Kavya Raman",{"status":"ongoing","notes":"Recorded diagnosis; confirm current status with clinician."},"Clinic A summary"),
          ("lab","HbA1c","2026-08-15","City Diagnostics",{"value":"7.4","unit":"%","reference":"Use lab-provided range","notes":"Synthetic demo result."},"Lab report"),
          ("medication","Metformin","2026-08-20","Dr. Kavya Raman",{"dose":"500 mg","frequency":"Twice daily","status":"recorded active","ingredient":"metformin","notes":"Verify current use with clinician."},"Prescription"),
          ("allergy","Penicillin","2026-02-03","Patient reported",{"reaction":"Rash (reported)","severity":"Not specified","status":"active","substance":"penicillin"},"Patient-reported"),
          ("lab","HbA1c","2026-02-10","City Diagnostics",{"value":"7.8","unit":"%","reference":"Use lab-provided range","notes":"Synthetic demo result."},"Lab report"),
          ("medication","Atorvastatin","2026-07-30","Dr. Arun Iyer",{"dose":"10 mg","frequency":"Once daily","status":"historical — confirm current use","ingredient":"atorvastatin"},"Prescription"),
          ("visit","Primary care visit","2026-08-20","Dr. Kavya Raman",{"notes":"Discussed routine follow-up and reviewing lab results."},"Visit summary"),
        ]
        for typ,title,date,provider,details,source in data:
            db.add(Record(patient_id=1, record_type=typ, title=title, record_date=date, provider_name=provider, details=json.dumps(details), source_label=source))
        db.commit()
seed()

class RecordIn(BaseModel):
    record_type: str = Field(pattern="^(diagnosis|lab|medication|allergy|visit|document)$")
    title: str = Field(min_length=2, max_length=180)
    record_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    provider_name: str = Field(default="Patient supplied", max_length=180)
    details: dict = Field(default_factory=dict)
    source_label: str = Field(default="Patient entry", max_length=180)

class ShareIn(BaseModel):
    record_ids: list[int] = Field(min_length=1, max_length=100)
    duration_hours: int = Field(default=2, ge=1, le=24)

@app.get("/api/health")
def health(): return {"status":"ok","service":"MediBridge API","synthetic_data":True}

@app.get("/api/demo")
def demo():
    return {"patient":{"id":1,"name":"Aarav Sharma","age":52,"conditions":["Type 2 diabetes"],"notice":"Fictional synthetic demo patient"}}

@app.get("/api/records")
def list_records(record_type: Optional[str]=None, q: Optional[str]=None):
    with SessionLocal() as db:
        rows=list(db.scalars(select(Record).where(Record.patient_id==1).order_by(Record.record_date.desc(), Record.id.desc())))
        output=[record_dict(r) for r in rows]
        if record_type and record_type != "all": output=[r for r in output if r["record_type"]==record_type]
        if q:
            needle=q.lower()
            output=[r for r in output if needle in (r["title"]+" "+r["provider_name"]+" "+json.dumps(r["details"])).lower()]
        return output

@app.post("/api/records")
def add_record(payload: RecordIn):
    with SessionLocal() as db:
        r=Record(patient_id=1, record_type=payload.record_type, title=payload.title, record_date=payload.record_date, provider_name=payload.provider_name, details=json.dumps(payload.details), source_label=payload.source_label)
        db.add(r); db.commit(); db.refresh(r)
        audit(db,"record_created",detail=f"record_id={r.id}")
        return record_dict(r)

@app.get("/api/summary")
def summary():
    with SessionLocal() as db:
        rows=list(db.scalars(select(Record).where(Record.patient_id==1)))
        recs=[record_dict(r) for r in rows]
        allergies=[r for r in recs if r["record_type"]=="allergy"]
        meds=[r for r in recs if r["record_type"]=="medication" and "historical" not in str(r["details"].get("status","")).lower()]
        labs=[r for r in recs if r["record_type"]=="lab"]
        return {"patient":{"id":1,"name":"Aarav Sharma","age":52,"conditions":["Type 2 diabetes"]},"allergies":allergies,"medications":meds,"recent_labs":sorted(labs,key=lambda x:x["record_date"],reverse=True)[:4],"record_count":len(recs)}

@app.get("/api/continuity")
def continuity():
    records=list_records()
    alerts=[]
    labs={}
    for r in records:
        if r["record_type"]=="lab":
            key=r["title"].strip().lower()
            labs.setdefault(key,[]).append(r)
    for test, items in labs.items():
        if len(items)>1:
            items=sorted(items,key=lambda x:x["record_date"],reverse=True)
            days=(datetime.strptime(items[0]["record_date"],"%Y-%m-%d")-datetime.strptime(items[1]["record_date"],"%Y-%m-%d")).days
            if days <= 180:
                alerts.append({"kind":"duplicate_test_candidate","severity":"review","title":f"Recent {items[0]['title']} result exists","message":f"Similar test records are {days} days apart. Review the prior result before considering repeat testing.","record_ids":[items[0]["id"],items[1]["id"]]})
    for r in records:
        if r["record_type"]=="medication" and "historical" in str(r["details"].get("status","")).lower():
            alerts.append({"kind":"stale_medication","severity":"review","title":f"Confirm {r['title']} status","message":"This record is marked historical. Confirm current use with the patient.","record_ids":[r["id"]]})
    for r in records:
        if r["record_type"]=="allergy":
            alerts.append({"kind":"recorded_allergy","severity":"notice","title":f"Recorded allergy: {r['title']}","message":"Review the reported allergy and reaction during clinical assessment.","record_ids":[r["id"]]})
    return {"alerts":alerts,"disclaimer":"Review prompts only. Not a diagnosis, prescription, or clinical decision."}

@app.post("/api/shares")
def create_share(payload: ShareIn):
    with SessionLocal() as db:
        valid=set(db.scalars(select(Record.id).where(Record.patient_id==1,Record.id.in_(payload.record_ids))))
        ids=sorted(valid)
        if not ids: raise HTTPException(400,"No valid patient records selected.")
        raw=secrets.token_urlsafe(32)
        digest=hashlib.sha256(raw.encode()).hexdigest()
        grant=ShareGrant(patient_id=1,token_hash=digest,record_ids=json.dumps(ids),expires_at=now_utc()+timedelta(hours=payload.duration_hours))
        db.add(grant); db.commit(); db.refresh(grant)
        audit(db,"share_created",grant.id,f"records={len(ids)}; expires={grant.expires_at.isoformat()}")
        # Raw token is returned only once to the owner for link generation.
        return {"share_id":grant.id,"token":raw,"expires_at":grant.expires_at.isoformat(),"record_count":len(ids)}

def get_valid_grant(db, token):
    digest=hashlib.sha256(token.encode()).hexdigest()
    grant=db.scalar(select(ShareGrant).where(ShareGrant.token_hash==digest))
    if not grant: raise HTTPException(404,"This share link is invalid or unavailable.")
    if grant.revoked_at is not None: raise HTTPException(410,"This share has been revoked by the patient.")
    if as_utc(grant.expires_at) <= now_utc(): raise HTTPException(410,"This share link has expired.")
    return grant

@app.get("/api/shared/{token}")
def shared_view(token: str):
    with SessionLocal() as db:
        grant=get_valid_grant(db,token)
        ids=json.loads(grant.record_ids)
        rows=list(db.scalars(select(Record).where(Record.patient_id==grant.patient_id,Record.id.in_(ids)).order_by(Record.record_date.desc())))
        audit(db,"share_viewed",grant.id,"Clinician view accessed")
        return {"patient":{"name":"Aarav Sharma","age":52},"records":[record_dict(r) for r in rows],"expires_at":as_utc(grant.expires_at).isoformat(),"notice":"Synthetic demo data. Verify all information with the patient.","read_only":True}

@app.post("/api/shares/{share_id}/revoke")
def revoke_share(share_id: int):
    with SessionLocal() as db:
        grant=db.get(ShareGrant,share_id)
        if not grant or grant.patient_id != 1: raise HTTPException(404,"Share grant not found.")
        if grant.revoked_at is None:
            grant.revoked_at=now_utc(); db.commit()
            audit(db,"share_revoked",grant.id,"Patient revoked access")
        return {"revoked":True,"share_id":share_id}

@app.get("/api/audit")
def audit_log():
    with SessionLocal() as db:
        rows=list(db.scalars(select(AuditEvent).where(AuditEvent.patient_id==1).order_by(AuditEvent.created_at.desc()).limit(50)))
        return [{"id":r.id,"share_id":r.share_id,"event_type":r.event_type,"detail":r.detail,"created_at":as_utc(r.created_at).isoformat()} for r in rows]
