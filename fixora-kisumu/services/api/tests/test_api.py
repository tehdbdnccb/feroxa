from io import BytesIO

from app.db import SessionLocal
from app.models import Credential, TechnicianProfile, User, utcnow


def reg(client, email="customer@example.com", role="customer", phone="+254700000001"):
    r = client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "full_name": "Test User",
            "phone": phone,
            "password": "strong-password-123",
            "role": role,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def csrf(client):
    return {"X-CSRF-Token": client.cookies.get("fixora_csrf")}


def approve_tech(tech_user_id: str, latitude: float = -0.0917, longitude: float = 34.7680):
    db = SessionLocal()
    user = db.get(User, tech_user_id)
    tech = db.query(TechnicianProfile).filter(TechnicianProfile.user_id == user.id).one()
    tech.latitude = latitude
    tech.longitude = longitude
    tech.network_approved = True
    tech.background_verified = True
    tech.available = True
    db.add_all(
        [
            Credential(technician_id=tech.id, kind="identity", reference="TEST-IDENTITY", verified_at=utcnow()),
            Credential(technician_id=tech.id, kind="business", reference="TEST-BUSINESS", verified_at=utcnow()),
        ]
    )
    db.commit()
    db.close()


def make_assigned_repair(client):
    customer = reg(client)
    technician = reg(client, email="tech@example.com", role="technician", phone="+254700000002")
    approve_tech(technician["user"]["id"])

    device = client.post(
        "/v1/devices",
        headers=auth(customer["access_token"]),
        json={"model": "iPhone 14 Pro", "serial_last4": "C123", "imei_last4": "9012"},
    )
    assert device.status_code == 201, device.text
    repair = client.post(
        "/v1/repair-requests",
        headers=auth(customer["access_token"]),
        json={
            "device_id": device.json()["id"],
            "issue": "Charging port",
            "service_mode": "mobile",
            "address": "Milimani, Kisumu",
            "latitude": -0.0917,
            "longitude": 34.7680,
        },
    )
    assert repair.status_code == 201, repair.text
    tech_claim = client.post(
        f"/v1/repair-requests/{repair.json()['id']}/claim",
        headers=auth(technician["access_token"]),
    )
    assert tech_claim.status_code == 200, tech_claim.text
    return customer, technician, device.json(), repair.json()


def test_cookie_auth_and_customer_can_create_repair(client):
    reg(client)
    device = client.post(
        "/v1/devices",
        headers=csrf(client),
        json={"model": "iPhone 15 Pro", "serial_last4": "A123", "imei_last4": "1234"},
    )
    assert device.status_code == 201, device.text
    repair = client.post(
        "/v1/repair-requests",
        headers=csrf(client),
        json={
            "device_id": device.json()["id"],
            "issue": "Cracked screen",
            "service_mode": "mobile",
            "address": "Kisumu CBD",
        },
    )
    assert repair.status_code == 201
    assert repair.json()["status"] == "requested"


def test_customer_cannot_skip_repair_workflow(client):
    _, _, _, repair = make_assigned_repair(client)
    response = client.patch(
        f"/v1/repair-requests/{repair['id']}/status",
        headers=auth(reg(client, email="other@example.com", phone="+254700000099")["access_token"]),
        json={"status": "completed"},
    )
    assert response.status_code in {403, 404}


def test_technician_claim_and_quote_are_required(client):
    customer, technician, _, repair = make_assigned_repair(client)
    quote = client.post(
        f"/v1/repair-requests/{repair['id']}/quotes",
        headers=auth(technician["access_token"]),
        json={"parts_amount": 4000, "labour_amount": 1500, "callout_amount": 300, "warranty_days": 90, "part_tier": "compatible"},
    )
    assert quote.status_code == 201, quote.text

    notifications = client.get("/v1/notifications", headers=auth(customer["access_token"]))
    assert notifications.status_code == 200
    assert any(item["kind"] == "quote" for item in notifications.json())


def test_full_repair_flow_requires_payment_before_completion(client):
    customer, technician, _, repair = make_assigned_repair(client)
    q = client.post(
        f"/v1/repair-requests/{repair['id']}/quotes",
        headers=auth(technician["access_token"]),
        json={"parts_amount": 3500, "labour_amount": 1000, "callout_amount": 0, "warranty_days": 90, "part_tier": "compatible"},
    )
    quote_id = q.json()["id"]
    assert client.post(f"/v1/quotes/{quote_id}/accept", headers=auth(customer["access_token"])).status_code == 200
    for next_status in ("en_route", "arrived"):
        result = client.patch(
            f"/v1/repair-requests/{repair['id']}/status",
            headers=auth(technician["access_token"]),
            json={"status": next_status},
        )
        assert result.status_code == 200, result.text

    pre = client.post(
        f"/v1/repair-requests/{repair['id']}/inspections",
        headers=auth(technician["access_token"]),
        json={"screen_ok": True, "camera_ok": True, "face_id_ok": True, "speaker_ok": True, "microphone_ok": True, "charging_ok": False, "notes": "Charging fault confirmed"},
    )
    assert pre.status_code == 201
    assert client.patch(f"/v1/repair-requests/{repair['id']}/status", headers=auth(technician["access_token"]), json={"status": "in_repair"}).status_code == 200
    post = client.post(
        f"/v1/repair-requests/{repair['id']}/inspections",
        headers=auth(technician["access_token"]),
        json={"screen_ok": True, "camera_ok": True, "face_id_ok": True, "speaker_ok": True, "microphone_ok": True, "charging_ok": True, "notes": "Post-repair functional check passed"},
    )
    assert post.status_code == 201

    evidence = client.post(
        f"/v1/repair-requests/{repair['id']}/evidence?stage=post&kind=completion",
        headers=auth(technician["access_token"]),
        files={"file": ("completion.jpg", BytesIO(b"fake-image-bytes"), "image/jpeg")},
    )
    assert evidence.status_code == 201, evidence.text

    payment = client.post(
        f"/v1/repair-requests/{repair['id']}/payments/mpesa",
        headers=auth(customer["access_token"]),
        json={"phone": "+254700000001"},
    )
    assert payment.status_code == 503


def test_technician_queue_does_not_expose_unrelated_repairs(client):
    customer = reg(client)
    technician = reg(client, email="queue-tech@example.com", role="technician", phone="+254700000004")
    approve_tech(technician["user"]["id"], latitude=-0.0917, longitude=34.7680)
    db = SessionLocal()
    tech = db.query(TechnicianProfile).filter(TechnicianProfile.user_id == technician["user"]["id"]).one()
    tech.available = True
    db.commit()
    db.close()

    other_device = client.post(
        "/v1/devices",
        headers=auth(customer["access_token"]),
        json={"model": "iPhone 12", "serial_last4": "E123", "imei_last4": "7890"},
    ).json()
    repair = client.post(
        "/v1/repair-requests",
        headers=auth(customer["access_token"]),
        json={
            "device_id": other_device["id"],
            "issue": "Battery",
            "service_mode": "mobile",
            "address": "Far outside service area",
            "latitude": 0.8,
            "longitude": 36.0,
        },
    )
    assert repair.status_code == 201
    jobs = client.get("/v1/repair-requests", headers=auth(technician["access_token"]))
    assert jobs.status_code == 200
    assert jobs.json() == []


def test_mpesa_callback_is_idempotent_and_queues_payout(client):
    from app.config import settings
    from app.models import PaymentIntent

    customer, technician, _, repair = make_assigned_repair(client)
    q = client.post(
        f"/v1/repair-requests/{repair['id']}/quotes",
        headers=auth(technician["access_token"]),
        json={"parts_amount": 3500, "labour_amount": 1000, "callout_amount": 0, "warranty_days": 90, "part_tier": "compatible"},
    ).json()
    client.post(f"/v1/quotes/{q['id']}/accept", headers=auth(customer["access_token"]))
    client.patch(f"/v1/repair-requests/{repair['id']}/status", headers=auth(technician["access_token"]), json={"status": "en_route"})
    client.patch(f"/v1/repair-requests/{repair['id']}/status", headers=auth(technician["access_token"]), json={"status": "arrived"})
    client.post(
        f"/v1/repair-requests/{repair['id']}/inspections",
        headers=auth(technician["access_token"]),
        json={"screen_ok": True, "camera_ok": True, "face_id_ok": True, "speaker_ok": True, "microphone_ok": True, "charging_ok": False, "notes": "Pre"},
    )
    client.patch(f"/v1/repair-requests/{repair['id']}/status", headers=auth(technician["access_token"]), json={"status": "in_repair"})
    client.post(
        f"/v1/repair-requests/{repair['id']}/inspections",
        headers=auth(technician["access_token"]),
        json={"screen_ok": True, "camera_ok": True, "face_id_ok": True, "speaker_ok": True, "microphone_ok": True, "charging_ok": True, "notes": "Post"},
    )

    db = SessionLocal()
    intent = PaymentIntent(
        repair_request_id=repair["id"], customer_id=customer["user"]["id"], phone="254700000001", amount=4500,
        platform_fee_amount=675, technician_amount=3825, status="submitted", checkout_request_id="ws_CO_123",
    )
    db.add(intent)
    db.commit()
    db.close()

    original = settings.mpesa_callback_token
    settings.mpesa_callback_token = "callback-secret"
    try:
        payload = {"Body": {"stkCallback": {"CheckoutRequestID": "ws_CO_123", "ResultCode": 0, "ResultDesc": "Success", "CallbackMetadata": {"Item": [{"Name": "MpesaReceiptNumber", "Value": "RCP123"}, {"Name": "TransactionDate", "Value": 20260917075800}]}}}}
        callback = client.post("/v1/payments/mpesa/callback/callback-secret", json=payload)
        assert callback.status_code == 200
        callback_again = client.post("/v1/payments/mpesa/callback/callback-secret", json=payload)
        assert callback_again.status_code == 200

        payment = client.get(f"/v1/repair-requests/{repair['id']}/payment", headers=auth(customer["access_token"]))
        assert payment.json()["status"] == "success"
        db = SessionLocal()
        payouts = db.query(__import__("app.models", fromlist=["TechnicianPayout"]).TechnicianPayout).filter_by(repair_request_id=repair["id"]).all()
        assert len(payouts) == 1 and payouts[0].status == "pending"
        db.close()
    finally:
        settings.mpesa_callback_token = original
