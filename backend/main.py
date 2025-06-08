from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import jwt
from datetime import datetime, timedelta
import uvicorn
import os

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="TailingsIQ API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class Facility(BaseModel):
    id: Optional[int] = None
    name: str
    location: str
    type: str
    owner: str
    status: str

class RiskAssessment(BaseModel):
    facility_id: int
    risk_score: float
    risk_level: str
    recommendations: List[str]
    timestamp: datetime

# In-memory storage (replace with database in production)
facilities_db = []
risk_assessments_db = []
facility_counter = 1

# Authentication functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Routes
@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Simple demo authentication
    if form_data.username == "demo" and form_data.password == "demo":
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/facilities", response_model=List[Facility])
async def get_facilities(current_user: str = Depends(verify_token)):
    return facilities_db

@app.post("/facilities", response_model=Facility)
async def create_facility(facility: Facility, current_user: str = Depends(verify_token)):
    global facility_counter
    facility.id = facility_counter
    facility_counter += 1
    facilities_db.append(facility)
    return facility

@app.get("/facilities/{facility_id}", response_model=Facility)
async def get_facility(facility_id: int, current_user: str = Depends(verify_token)):
    facility = next((f for f in facilities_db if f.id == facility_id), None)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility

@app.post("/facilities/{facility_id}/risk-assessment", response_model=RiskAssessment)
async def perform_risk_assessment(facility_id: int, current_user: str = Depends(verify_token)):
    facility = next((f for f in facilities_db if f.id == facility_id), None)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    
    # Mock risk assessment
    import random
    risk_score = round(random.uniform(0.1, 0.9), 2)
    
    if risk_score < 0.3:
        risk_level = "Low"
        recommendations = [
            "Continue regular monitoring",
            "Maintain current safety protocols"
        ]
    elif risk_score < 0.7:
        risk_level = "Medium"
        recommendations = [
            "Increase monitoring frequency",
            "Review safety procedures",
            "Consider additional safety measures"
        ]
    else:
        risk_level = "High"
        recommendations = [
            "Immediate safety review required",
            "Increase monitoring to daily",
            "Consider emergency response planning",
            "Consult with safety experts"
        ]
    
    assessment = RiskAssessment(
        facility_id=facility_id,
        risk_score=risk_score,
        risk_level=risk_level,
        recommendations=recommendations,
        timestamp=datetime.utcnow()
    )
    
    risk_assessments_db.append(assessment)
    return assessment

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

