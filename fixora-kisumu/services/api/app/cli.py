import argparse
from .config import settings
from .db import Base,SessionLocal,engine
from .models import User
from .security import hash_password
def bootstrap_admin():
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password: raise SystemExit("Bootstrap admin env vars are required")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(User).filter(User.email==settings.bootstrap_admin_email.lower()).first(): raise SystemExit("Admin already exists")
        db.add(User(email=settings.bootstrap_admin_email.lower(),full_name="Fixora Admin",phone="admin",password_hash=hash_password(settings.bootstrap_admin_password),role="admin")); db.commit()
    print("Admin created")
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("command",choices=["bootstrap-admin"]); a=p.parse_args()
    if a.command=="bootstrap-admin": bootstrap_admin()
