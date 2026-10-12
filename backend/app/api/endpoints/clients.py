from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_business
from app.api.serializers import client_out
from app.db.session import get_db
from app.models.models import Business, Client
from app.schemas.schemas import ClientIn, ClientOut, ClientUpdate
from app.services.event_parsing import normalize_phone

router = APIRouter()


def get_client_or_404(db: Session, business: Business, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if not client or client.business_id != business.id:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _phone(db: Session, business: Business, raw: str, exclude_id: int | None = None) -> str:
    phone = normalize_phone(raw, business.default_country_code)
    if not phone:
        raise HTTPException(
            status_code=422,
            detail="Invalid phone number. Use international format (+55 11 99999-9999) or set a default country code in Settings.",
        )
    query = db.query(Client).filter(Client.business_id == business.id, Client.phone_number == phone)
    if exclude_id is not None:
        query = query.filter(Client.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=409, detail="Another client already has this phone number")
    return phone


@router.get("/", response_model=list[ClientOut])
def list_clients(
    search: str | None = None,
    status: str | None = None,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    query = db.query(Client).options(selectinload(Client.appointments)).filter(Client.business_id == business.id)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Client.name.ilike(like), Client.email.ilike(like), Client.phone_number.ilike(like)))
    clients = [client_out(c) for c in query.order_by(Client.name).all()]
    if status:
        clients = [c for c in clients if c.status == status]
    return clients


@router.post("/", response_model=ClientOut, status_code=201)
def create_client(data: ClientIn, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    client = Client(
        business_id=business.id,
        name=data.name.strip(),
        phone_number=_phone(db, business, data.phone_number),
        email=data.email,
        notes=data.notes,
    )
    db.add(client)
    db.commit()
    return client_out(client)


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    return client_out(get_client_or_404(db, business, client_id))


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: int, data: ClientUpdate, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    client = get_client_or_404(db, business, client_id)
    changes = data.model_dump(exclude_unset=True)
    if "phone_number" in changes:
        changes["phone_number"] = _phone(db, business, changes["phone_number"], exclude_id=client.id)
    for field, value in changes.items():
        setattr(client, field, value)
    db.commit()
    return client_out(client)


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    db.delete(get_client_or_404(db, business, client_id))
    db.commit()
