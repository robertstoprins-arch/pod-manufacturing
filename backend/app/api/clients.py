"""
API: Clients — contact records for the commercial pipeline

GET    /clients              list all
POST   /clients              create (201)
GET    /clients/{id}         get
PUT    /clients/{id}         update
DELETE /clients/{id}         delete (204)
GET    /clients/{id}/quotes  quotes for this client
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client, Quote

router = APIRouter(prefix="/clients", tags=["clients"])

Db = Annotated[Session, Depends(get_db)]


# ── Schemas ───────────────────────────────────────────────────────────────────

class ClientIn(BaseModel):
    name: str
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    source: str | None = None
    client_type: str | None = None
    notes: str | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    company_name: str | None
    email: str | None
    phone: str | None
    address: str | None
    source: str | None
    client_type: str | None
    notes: str | None


class QuoteSnippet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: str
    quote_number: str | None
    total_inc_vat: float | None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ClientOut])
def list_clients(db: Db):
    return db.query(Client).order_by(Client.created_at.desc()).all()


@router.post("", response_model=ClientOut, status_code=201)
def create_client(body: ClientIn, db: Db):
    client = Client(**body.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: uuid.UUID, db: Db):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")
    return client


@router.put("/{client_id}", response_model=ClientOut)
def update_client(client_id: uuid.UUID, body: ClientIn, db: Db):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(client, k, v)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: uuid.UUID, db: Db):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")
    db.delete(client)
    db.commit()
    return Response(status_code=204)


@router.get("/{client_id}/quotes", response_model=list[QuoteSnippet])
def client_quotes(client_id: uuid.UUID, db: Db):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")
    return db.query(Quote).filter(Quote.client_id == client_id).order_by(Quote.created_at.desc()).all()
