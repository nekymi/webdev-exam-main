from app import db
from app.models import CorporateRequest


def create_corporate_request(name, phone=None, email=None, message=None):
    req = CorporateRequest(
        name=name.strip(),
        phone=(phone or "").strip() or None,
        email=(email or "").strip() or None,
        message=(message or "").strip() or None,
        status="NEW",
    )
    db.session.add(req)
    db.session.commit()
    return req
