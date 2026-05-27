from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from models import DrugCheckRequest, DrugCheckResponse
from engine import load_fallback_data, check_interactions_fallback, check_allergies, check_interactions_llm
from cache import make_cache_key, get_from_cache, save_to_cache
import time
from database import engine, get_db
from db_models import Check
from sqlalchemy.orm import Session
import json
from database import Base

Base.metadata.create_all(bind=engine)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

@app.get("/health")
def home():
    return{
        "status":"ok"
    }

@app.post("/check-drugs")
def check_drugs(request: DrugCheckRequest, db: Session = Depends(get_db)):
    start_time = time.time()

    #checking cache
    cache_key = make_cache_key(request.medicines, request.patient_history.current_medications)
    cache = get_from_cache(cache_key)
    if cache:
        cache["cache_hit"] = True
        cache["processing_time_ms"] = 0
        return cache
    
    #checking llm
    try:
        source = "llm"
        llm_result = check_interactions_llm(request.medicines, request.patient_history)
        interactions = llm_result.get("interactions",[])
        requires_doctor_review = llm_result.get("requires_doctor_review", True)

    except Exception:
        #checking fallback data incase llm failed
        source = "fallback"
        fallback_data = load_fallback_data()
        interactions = check_interactions_fallback(request.medicines, fallback_data)
        requires_doctor_review = any(i.get("severity") == "high" for i in interactions)

    allergies = check_allergies(
    request.medicines,
    request.patient_history.known_allergies
    )
        

    #calculation of overall_risk_level
    all_severities = ([i["severity"] for i in interactions if "severity" in i] + [a["severity"] for a in allergies if "severity" in a])
    if "high" in all_severities:
        overall_risk_level = "high"
    elif "medium" in all_severities:
        overall_risk_level = "medium"
    else:
        overall_risk_level = "low"

    # deterministic uncertainty escalation
    requires_doctor_review = (
    overall_risk_level == "high"
    or any(i.get("source_confidence") == "low" for i in interactions)
    or len(allergies) > 0
    )

    #safe_to_prescribe calculation
    safe_to_prescribe = len(interactions) == 0 and len(allergies) == 0
    response_time = int((time.time() - start_time)*1000)   #since response time should be in ms





    response =  DrugCheckResponse(
        interactions = interactions,
        allergy_alerts = allergies,
        safe_to_prescribe = safe_to_prescribe,
        overall_risk_level = overall_risk_level,
        requires_doctor_review = requires_doctor_review,
        source = source,
        cache_hit = False,
        processing_time_ms = response_time
    )
    save_to_cache(cache_key, response.model_dump())

    #saving to database
    check_record = Check(
        doctor_id = request.doctor_id,
        medicines = json.dumps(request.medicines),
        patient_age = request.patient_history.age,
        patient_weight = request.patient_history.weight,
        patient_conditions = json.dumps(request.patient_history.conditions),
        known_allergies = json.dumps(request.patient_history.known_allergies),
        current_medications = json.dumps(request.patient_history.current_medications),
        interactions = json.dumps(interactions),
        allergy_alerts = json.dumps(allergies),
        risk_level = overall_risk_level,
        safe_to_prescribe = safe_to_prescribe,
        requires_doctor_review = requires_doctor_review,
        source = source,
        processing_time_ms = response_time
    )
    db.add(check_record)
    db.commit()

    return response

#getting history of last 20 patients
@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    checks = db.query(Check)\
        .order_by(Check.timestamp.desc())\
        .limit(20)\
        .all()
    
    result = []
    for check in checks:
        result.append({
            "id": check.id,
            "doctor_id": check.doctor_id,
            "medicines": json.loads(check.medicines),
            "risk_level": check.risk_level,
            "overall_risk_level": check.risk_level,
            "safe_to_prescribe": check.safe_to_prescribe,
            "requires_doctor_review": check.requires_doctor_review,
            "source": check.source,
            "processing_time_ms": check.processing_time_ms,
            "timestamp": check.timestamp,
            "interactions": json.loads(check.interactions) if check.interactions else [],
            "allergy_alerts": json.loads(check.allergy_alerts) if check.allergy_alerts else [],
            "cache_hit": False
        })
    
    return {"checks": result, "total": len(result)}


#making the stats dashboard information
@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Check).count()
    high_risk = db.query(Check).filter(Check.risk_level == "high").count()
    medium_risk = db.query(Check).filter(Check.risk_level == "medium").count()
    low_risk = db.query(Check).filter(Check.risk_level == "low").count()
    safe = db.query(Check).filter(Check.safe_to_prescribe == True).count()
    llm_count = db.query(Check).filter(Check.source == "llm").count()
    fallback_count = db.query(Check).filter(Check.source == "fallback").count()

    return {
        "total_checks": total,
        "risk_breakdown": {
            "high": high_risk,
            "medium": medium_risk,
            "low": low_risk
        },
        "safe_to_prescribe": safe,
        "unsafe_to_prescribe": total - safe,
        "source_breakdown": {
            "llm": llm_count,
            "fallback": fallback_count
        }
    }


# Serve React Frontend static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST_DIR = os.path.join(BASE_DIR, "..", "frontend", "dist")

if os.path.exists(FRONTEND_DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST_DIR, "assets")), name="assets")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIST_DIR, "index.html"))
else:
    print(f"Warning: Frontend distribution directory not found at {FRONTEND_DIST_DIR}. Run 'npm run build' inside frontend/ to serve the UI.")