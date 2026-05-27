#creation of checks table

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.sql import func
from database import Base

class Check(Base):
    __tablename__ = "checks"
    id = Column(Integer, primary_key = True, index = True)
    doctor_id = Column(String, nullable = False)
    medicines = Column(String, nullable=False)
    patient_age = Column(String, nullable=True)
    patient_weight = Column(String, nullable=True)
    patient_conditions = Column(String, nullable=True)
    known_allergies = Column(String, nullable=True)
    current_medications = Column(String, nullable=True)
    interactions = Column(String, nullable=True)
    allergy_alerts = Column(String, nullable=True)
    risk_level = Column(String, nullable = False)
    safe_to_prescribe = Column(Boolean, nullable=False)
    requires_doctor_review = Column(Boolean, nullable=False)
    source = Column(String, nullable=False)
    processing_time_ms = Column(Integer, nullable=False)
    timestamp = Column(DateTime, server_default=func.now()) #automatically set timestamp when a record is created

