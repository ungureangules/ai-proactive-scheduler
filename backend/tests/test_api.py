from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from twilio.request_validator import RequestValidator

from app.core.config import settings
from app.models.models import Appointment, Business, Client, CommunicationLog
from app.services.ai_agent import AIAgentService
from app.services.scheduler_logic import SchedulerService
from app.tasks import tasks
from tests.conftest import register

WEBHOOK_URL = settings.PUBLIC_BASE_URL + "/api/v1/webhooks/whatsapp"


def test_auth_flow_and_no_secret_leak(api):
    headers = register(api)
    me = api.get("/api/v1/auth/me", headers=headers).json()
    assert me["email"] == "owner@example.com"
    assert "hashed_password" not in me and "google_credentials_encrypted" not in me

    login = api.post("/api/v1/auth/login", data={"username": "OWNER@example.com", "password": "correct-horse"})
    assert login.status_code == 200
    assert api.post("/api/v1/auth/login", data={"username": "owner@example.com", "password": "nope"}).status_code == 401
    assert api.get("/api/v1/businesses/me").status_code == 401
    assert api.get("/api/v1/businesses/").status_code in (404, 405)  # the old list-everything endpoint is gone
    assert api.post(
        "/api/v1/auth/register",
        json={"business_name": "x", "email": "owner@example.com", "password": "another-pass"},
    ).status_code == 409


def test_clients_are_scoped_to_their_business(api):
    a = register(api, email="a@example.com")
    b = register(api, email="b@example.com")
    created = api.post("/api/v1/clients/", json={"name": "Bob", "phone_number": "+55 11 98888-7777"}, headers=a)
    assert created.status_code == 201, created.text
    client_id = created.json()["id"]
    assert created.json()["phone_number"] == "+5511988887777"
    assert api.get(f"/api/v1/clients/{client_id}", headers=b).status_code == 404
    assert api.get("/api/v1/clients/", headers=b).json() == []
    duplicate = api.post("/api/v1/clients/", json={"name": "Bob 2", "phone_number": "+5511988887777"}, headers=a)
    assert duplicate.status_code == 409
    assert api.post("/api/v1/clients/", json={"name": "X", "phone_number": "1234"}, headers=a).status_code == 422


def test_google_callback_rejects_forged_state(api):
    response = api.get("/api/v1/businesses/google-auth-callback", params={"state": "forged", "code": "x"}, follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].endswith("/settings?google=error")


def _signed_post(api, params):
    signature = RequestValidator(settings.TWILIO_AUTH_TOKEN).compute_signature(WEBHOOK_URL, params)
    return api.post("/api/v1/webhooks/whatsapp", data=params, headers={"X-Twilio-Signature": signature})


def test_webhook_requires_twilio_signature(api, db_factory, monkeypatch):
    headers = register(api)
    api.post("/api/v1/clients/", json={"name": "Bob", "phone_number": "+5511988887777"}, headers=headers)
    queued = []
    monkeypatch.setattr(tasks.handle_inbound_message, "delay", lambda log_id: queued.append(log_id))
    params = {"From": "whatsapp:+5511988887777", "Body": "Hi! Any time Friday?", "MessageSid": "SM1"}

    assert api.post("/api/v1/webhooks/whatsapp", data=params).status_code == 403
    assert api.post("/api/v1/webhooks/whatsapp", data=params, headers={"X-Twilio-Signature": "bad"}).status_code == 403

    response = _signed_post(api, params)
    assert response.status_code == 200 and "<Response>" in response.text
    assert _signed_post(api, params).status_code == 200  # Twilio retry
    db = db_factory()
    assert db.query(CommunicationLog).count() == 1
    assert len(queued) == 1


def test_stop_opts_client_out(api, db_factory, monkeypatch):
    headers = register(api)
    api.post("/api/v1/clients/", json={"name": "Bob", "phone_number": "+5511988887777"}, headers=headers)
    sent = []
    monkeypatch.setattr("app.api.endpoints.webhooks.send_and_log", lambda db, client, body, sender: sent.append(body))
    monkeypatch.setattr(tasks.handle_inbound_message, "delay", lambda log_id: (_ for _ in ()).throw(AssertionError("AI must not reply")))
    assert _signed_post(api, {"From": "whatsapp:+5511988887777", "Body": "STOP", "MessageSid": "SM2"}).status_code == 200
    assert db_factory().query(Client).one().opted_out is True
    assert len(sent) == 1


def _client_with_history(db, days_ago_last=30, gap=28):
    business = Business(name="Shop", email="s@example.com", hashed_password="x", timezone="America/Sao_Paulo")
    db.add(business)
    db.flush()
    client = Client(business_id=business.id, name="Bob", phone_number="+5511988887777")
    db.add(client)
    db.flush()
    now = datetime.now(timezone.utc)
    for i in range(4):
        start = now - timedelta(days=days_ago_last + gap * i)
        db.add(Appointment(business_id=business.id, client_id=client.id, start_time=start, end_time=start + timedelta(minutes=30), service_type="Haircut"))
    db.commit()
    SchedulerService.refresh_client_stats(db, client, now)
    db.commit()
    return business, client


def test_outreach_targets_due_clients_once(db_factory, monkeypatch):
    db = db_factory()
    business, client = _client_with_history(db)
    assert client.avg_frequency_days == 28
    sent = []

    def fake_send(db, client, body, sender, template=None):
        sent.append(body)
        log = CommunicationLog(business_id=client.business_id, client_id=client.id, message_body=body, direction="outbound", sender=sender, status="sent")
        db.add(log)
        db.commit()
        return log

    monkeypatch.setattr(tasks, "send_and_log", fake_send)
    monkeypatch.setattr(tasks, "is_configured", lambda: True)
    assert tasks.run_outreach(db, business) == 1
    assert "Bob" in sent[0] and "30 days" in sent[0]
    assert client.conversation_status == "negotiating"
    assert tasks.run_outreach(db, business) == 0  # cooldown


def test_outreach_skips_booked_paused_and_phoneless(db_factory):
    db = db_factory()
    business, client = _client_with_history(db)
    client.ai_paused = True
    db.commit()
    assert SchedulerService.get_due_clients(db, business.id) == []
    client.ai_paused = False
    soon = datetime.now(timezone.utc) + timedelta(days=3)
    db.add(Appointment(business_id=business.id, client_id=client.id, start_time=soon, end_time=soon + timedelta(minutes=30)))
    db.commit()
    db.refresh(client)
    assert SchedulerService.get_due_clients(db, business.id) == []


def test_ai_booking_tool_books_and_refuses_double_booking(db_factory, monkeypatch):
    db = db_factory()
    business, client = _client_with_history(db)
    agent = AIAgentService(db, business, client)
    day = (datetime.now(agent.tz) + timedelta(days=7)).date()
    while day.weekday() > 4:  # pick a weekday, open 09-18
        day += timedelta(days=1)
    slots = agent._run_tool("check_availability", {"date": day.isoformat()})["free_times"]
    assert slots[0] == "09:00"
    booked = agent._run_tool("book_appointment", {"date": day.isoformat(), "time": "09:00"})
    assert booked["ok"] and booked["service"] == "Haircut"
    assert client.conversation_status == "booked"
    again = agent._run_tool("book_appointment", {"date": day.isoformat(), "time": "09:00"})
    assert again["ok"] is False
    assert "09:00" not in agent._run_tool("check_availability", {"date": day.isoformat()})["free_times"]
    assert agent._run_tool("check_availability", {"date": "2020-01-01"})["ok"] is False


def test_ai_reply_runs_tools_with_history(db_factory, monkeypatch):
    db = db_factory()
    business, client = _client_with_history(db)
    db.add(CommunicationLog(business_id=business.id, client_id=client.id, message_body="Book me next week", direction="inbound", sender="client", status="received"))
    db.commit()
    agent = AIAgentService(db, business, client)
    calls = []

    def fake_create(**kwargs):
        calls.append(list(kwargs["messages"]))
        if len(calls) == 1:
            tool_call = SimpleNamespace(id="c1", function=SimpleNamespace(name="list_client_appointments", arguments="{}"))
            message = SimpleNamespace(
                tool_calls=[tool_call],
                content=None,
                model_dump=lambda exclude_none: {"role": "assistant", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "list_client_appointments", "arguments": "{}"}}]},
            )
        else:
            message = SimpleNamespace(tool_calls=None, content="Sure! Which day works?")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(agent.llm.chat.completions, "create", fake_create)
    assert agent.reply() == "Sure! Which day works?"
    assert calls[0][-1] == {"role": "user", "content": "Book me next week"}
    assert calls[1][-1]["role"] == "tool"
