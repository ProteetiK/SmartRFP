from typing import Optional
from sqlalchemy.orm import Session
from backend.models import ResourceRate


class PricingService:
    def __init__(self, db: Session):
        self.db = db

    def get_rate(self, role: str, experience_level: str = "Mid",
                 location: str = "India") -> Optional[ResourceRate]:
        return (self.db.query(ResourceRate)
                .filter(ResourceRate.role == role,
                        ResourceRate.experience_level == experience_level,
                        ResourceRate.location == location,
                        ResourceRate.active.is_(True))
                .first())

    def get_all_rates(self):
        return self.db.query(ResourceRate).filter(ResourceRate.active.is_(True)).all()

    def get_roles(self):
        rows = self.db.query(ResourceRate.role).distinct().all()
        return [r[0] for r in rows]
