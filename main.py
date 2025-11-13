import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime

from database import create_document, get_documents
from schemas import Message, Gig

app = FastAPI(title="MAFFA API", description="Backend for DJ/Producer MAFFA website")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "MAFFA Backend Running"}

# Public endpoints
@app.get("/api/gigs", response_model=List[Gig])
def list_gigs(limit: int = 20):
    try:
        docs = get_documents("gig", {}, limit)
        # Convert Mongo documents to Pydantic-compatible
        gigs: List[Gig] = []
        for d in docs:
            # Support both string/iso and datetime
            date_val = d.get("date")
            if isinstance(date_val, str):
                try:
                    date_val = datetime.fromisoformat(date_val)
                except Exception:
                    date_val = datetime.utcnow()
            gigs.append(Gig(
                title=d.get("title", ""),
                venue=d.get("venue", ""),
                city=d.get("city", ""),
                date=date_val,
                ticket_url=d.get("ticket_url"),
                is_confirmed=bool(d.get("is_confirmed", True))
            ))
        return gigs
    except Exception as e:
        # If DB not available, return an empty list for now
        return []

@app.post("/api/contact")
def submit_contact(message: Message):
    try:
        doc_id = create_document("message", message)
        return {"status": "ok", "id": doc_id}
    except Exception as e:
        # Gracefully degrade if DB not configured
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
