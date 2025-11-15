import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from bson.objectid import ObjectId

from database import db, create_document, get_documents
from schemas import Organizer, Event, Participant, Registration, Job

app = FastAPI(title="Competitions Service API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities

def to_str_id(doc):
    if not doc:
        return doc
    doc = dict(doc)
    _id = doc.get("_id")
    if _id:
        doc["id"] = str(_id)
        del doc["_id"]
    return doc

# Request models for endpoints
class CreateOrganizer(BaseModel):
    name: str
    email: EmailStr
    organization: Optional[str] = None

class CreateEvent(BaseModel):
    organizer_id: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    capacity: Optional[int] = None
    is_published: bool = False

class RegisterRequest(BaseModel):
    participant_name: str
    participant_email: EmailStr

@app.get("/")
def root():
    return {"service": "competitions", "status": "ok"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            response["collections"] = db.list_collection_names()
    except Exception as e:
        response["database"] = f"❌ Error: {e}"  
    return response

# Organizers
@app.post("/organizers")
def create_organizer(body: CreateOrganizer):
    organizer = Organizer(**body.model_dump())
    oid = create_document("organizer", organizer)
    doc = db["organizer"].find_one({"_id": ObjectId(oid)})
    return to_str_id(doc)

@app.get("/organizers")
def list_organizers() -> List[dict]:
    docs = get_documents("organizer")
    return [to_str_id(d) for d in docs]

# Events
@app.post("/events")
def create_event(body: CreateEvent):
    # verify organizer exists
    if not ObjectId.is_valid(body.organizer_id):
        raise HTTPException(status_code=400, detail="Invalid organizer_id")
    org = db["organizer"].find_one({"_id": ObjectId(body.organizer_id)})
    if not org:
        raise HTTPException(status_code=404, detail="Organizer not found")

    event = Event(**body.model_dump())
    oid = create_document("event", event)
    doc = db["event"].find_one({"_id": ObjectId(oid)})
    return to_str_id(doc)

@app.get("/events")
def list_events(organizer_id: Optional[str] = None, published: Optional[bool] = None):
    filt = {}
    if organizer_id and ObjectId.is_valid(organizer_id):
        filt["organizer_id"] = organizer_id
    if published is not None:
        filt["is_published"] = published
    docs = get_documents("event", filt)
    return [to_str_id(d) for d in docs]

@app.get("/events/{event_id}")
def get_event(event_id: str):
    if not ObjectId.is_valid(event_id):
        raise HTTPException(status_code=400, detail="Invalid event_id")
    doc = db["event"].find_one({"_id": ObjectId(event_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    # include registration count
    reg_count = db["registration"].count_documents({"event_id": event_id, "status": {"$ne": "cancelled"}})
    out = to_str_id(doc)
    out["registrations"] = reg_count
    return out

# Registrations
@app.post("/events/{event_id}/register")
def register(event_id: str, body: RegisterRequest):
    if not ObjectId.is_valid(event_id):
        raise HTTPException(status_code=400, detail="Invalid event_id")
    ev = db["event"].find_one({"_id": ObjectId(event_id)})
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    # Optional capacity check
    capacity = ev.get("capacity")
    if capacity:
        current = db["registration"].count_documents({"event_id": event_id, "status": {"$ne": "cancelled"}})
        if current >= capacity:
            raise HTTPException(status_code=409, detail="Event at capacity")

    reg = Registration(event_id=event_id,
                       participant_name=body.participant_name,
                       participant_email=body.participant_email)
    reg_id = create_document("registration", reg)

    # Enqueue post-registration job
    job = Job(type="post_registration", payload={"registration_id": reg_id, "event_id": event_id})
    create_document("job", job)

    doc = db["registration"].find_one({"_id": ObjectId(reg_id)})
    return to_str_id(doc)

@app.get("/events/{event_id}/registrations")
def list_registrations(event_id: str):
    if not ObjectId.is_valid(event_id):
        raise HTTPException(status_code=400, detail="Invalid event_id")
    docs = get_documents("registration", {"event_id": event_id})
    return [to_str_id(d) for d in docs]

# Simple health endpoint for worker/cron to call
@app.get("/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
