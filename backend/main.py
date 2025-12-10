from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv

from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from . import models
from .utils import safe_generate


# INIT
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# create tables if not exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# DB DEP 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ROUTES 
@app.get("/health")
def check():
    return {"status": "ok"}


@app.post("/generate")
def generate(data: dict, db: Session = Depends(get_db)):
    """
    Generate PRD, Landing Page, FAQ, and Video Script
    for a given brief and save them in the database.
    """
    product_brief = data["brief"]
    depth = data["depth"]

    prompts = {
        "PRD": "Write a full Product Requirements Document (PRD) for this product: " + product_brief,
        "Landing Page": "Write a detailed landing page text for this product: " + product_brief,
        "FAQ": "Write 10 FAQs (questions + answers) for this product: " + product_brief,
        "Video Script": (
            "You are a professional video script writer. "
            "Write a 60–90 second promotional video script for this product. "
            "Use this structure:\n"
            "1. Hook (attention grabbing)\n"
            "2. Problem (relatable pain point)\n"
            "3. Solution (introduce the product)\n"
            "4. Key features/benefits\n"
            "5. Social proof or example\n"
            "6. Strong call to action.\n\n"
            "Write it in simple English, with speaker lines and scene suggestions.\n\n"
            "Product: " + product_brief
        ),
    }

    output = {}

    # helper function for calling OpenAI
    def call_openai(prompt: str) -> str:
        return client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}]
        ).choices[0].message.content

    for key, prompt in prompts.items():
        # SAFE: if OpenAI fails (no credit / bad key), we still return a mock response
        output[key] = safe_generate(call_openai, prompt)


    # Save product
    product = models.Product(
        brief=product_brief,
        depth=depth,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # Save docs
    for doc_type, content in output.items():
        doc = models.Document(
            product_id=product.id,
            doc_type=doc_type,
            content=content,
        )
        db.add(doc)

    db.commit()

    return output


@app.get("/history")
def history(db: Session = Depends(get_db)):
    """
    Return last 10 generations (without calling OpenAI).
    """
    products = (
        db.query(models.Product)
        .order_by(models.Product.created_at.desc())
        .limit(10)
        .all()
    )

    result = []
    for p in products:
        item = {
            "id": p.id,
            "brief": p.brief,
            "depth": p.depth,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "documents": {d.doc_type: d.content for d in p.documents},
        }
        result.append(item)

    return result
