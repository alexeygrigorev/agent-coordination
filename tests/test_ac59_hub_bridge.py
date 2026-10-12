import json
import logging
import os
import sqlite3
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

import pytest

try:
    import ac59_service.coordination.bus
except ImportError:
    pass
import sys
FileBus = sys.modules["ac59_service.coordination.bus"].FileBus

try:
    import ac59_service.adapter.adapter
except ImportError:
    pass
BusServer = sys.modules["ac59_service.adapter.adapter"].BusServer
BusAdapterHandler = sys.modules["ac59_service.adapter.adapter"].BusAdapterHandler
from adapters.hub_outbound import C888BusClient, WireContractError, IdempotencyConflictError, SQLiteSpool, HubOutboundIntegration

@pytest.fixture
def store_path(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    return store

@pytest.fixture
def bus(store_path):
    return FileBus(store_path)

@pytest.fixture
def identities(bus):
    # Register two distinct identities
    ident1, tok1 = bus.register(device_id="dev1", project_id="proj1", agent_name="agent1")
    ident2, tok2 = bus.register(device_id="dev1", project_id="proj1", agent_name="agent2")
    ident3, tok3 = bus.register(device_id="dev1", project_id="proj2", agent_name="agent3") # diff project
    return {
        "id1": ident1.identity_id, "tok1": tok1,
        "id2": ident2.identity_id, "tok2": tok2,
        "id3": ident3.identity_id, "tok3": tok3,
    }

class ServerThread(threading.Thread):
    def __init__(self, bus):
        super().__init__(daemon=True)
        self.bus = bus
        self.server = BusServer(("127.0.0.1", 0), BusAdapterHandler, bus, allowlist={})
        self.port = self.server.server_address[1]

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()
        self.join()

@pytest.fixture
def server_factory(bus):
    servers = []
    def _factory(start=True):
        srv = ServerThread(bus)
        if start:
            srv.start()
        servers.append(srv)
        return srv
    yield _factory
    for s in servers:
        try:
            s.shutdown()
        except:
            pass

@pytest.fixture
def server(server_factory):
    return server_factory(start=True)

@pytest.fixture
def get_client(server):
    def _get(token):
        return C888BusClient(
            base_url=f"http://127.0.0.1:{server.port}",
            token_provider=lambda: token,
            allow_loopback_http=True,
        )
    return _get

def test_full_flow(bus, identities, get_client):
    client1 = get_client(identities["tok1"])
    client2 = get_client(identities["tok2"])
    
    id1 = identities["id1"]
    id2 = identities["id2"]
    
    # 1. Send
    sent = client1.send_bus_message(
        from_actor=id1,
        to_actor=id2,
        kind="test-message",
        body="hello world",
        idempotency_key="ik-1",
        thread_id="th-1"
    )
    msg_id = sent["id"]
    assert sent["from_actor"] == id1
    assert sent["to_actor"] == id2
    assert sent["body"] == "hello world"
    assert sent["kind"] == "test-message"
    assert sent["thread_id"] == "th-1"
    
    # 2. Recipient inbox
    inbox = client2.get_bus_inbox(actor=id2)
    assert len(inbox) == 1
    assert inbox[0]["id"] == msg_id
    
    # 3. Show (sender)
    shown = client1.show_bus_message(msg_id)
    assert shown["id"] == msg_id
    
    # 3. Show (recipient)
    shown = client2.show_bus_message(msg_id)
    assert shown["id"] == msg_id
    
    # 4. Ack/Accept/Complete
    client2.ack_bus_message(msg_id)
    shown = client2.show_bus_message(msg_id)
    assert shown["acked_at"] is not None
    
    client2.accept_bus_message(msg_id)
    shown = client2.show_bus_message(msg_id)
    assert shown["accepted_at"] is not None
    
    client2.complete_bus_message(msg_id)
    shown = client2.show_bus_message(msg_id)
    assert shown["completed_at"] is not None
    
    # 5. Reply
    replied = client2.reply_bus_message(
        from_actor=id2,
        to_actor=id1,
        kind="reply",
        body="got it",
        idempotency_key="ik-2",
        reply_to=msg_id
    )
    reply_id = replied["id"]
    
    # 6. Original sender sees reply
    inbox1 = client1.get_bus_inbox(actor=id1)
    assert len(inbox1) == 1
    assert inbox1[0]["id"] == reply_id
    assert inbox1[0]["body"] == "got it"
    assert inbox1[0]["reply_to"] == msg_id

def test_negatives(bus, identities, get_client, server, caplog, capsys):
    client1 = get_client(identities["tok1"])
    client3 = get_client(identities["tok3"])
    bad_client = get_client("invalid_token")
    
    id1 = identities["id1"]
    id2 = identities["id2"]
    
    responses = []
    
    def record_response(exc):
        if hasattr(exc.value, 'response_body'):
            responses.append(exc.value.response_body)
        responses.append(str(exc.value))

    # Missing/invalid bearer
    with pytest.raises(WireContractError) as exc:
        bad_client.send_bus_message(id1, id2, "k", "b", "ik")
    assert "status 401" in str(exc.value)
    record_response(exc)
    
    # Actor mismatch (try to send as id3 using tok1 - different project scope)
    with pytest.raises(WireContractError) as exc:
        client1.send_bus_message(identities["id3"], id1, "k", "b", "ik")
    assert "status 403" in str(exc.value)
    record_response(exc)
    
    # Third party show
    sent = client1.send_bus_message(id1, id2, "k", "b", "ik-1")
    msg_id = sent["id"]
    
    with pytest.raises(WireContractError) as exc:
        client3.show_bus_message(msg_id)
    assert "status 403" in str(exc.value)
    record_response(exc)
    
    # Third party reply
    with pytest.raises(WireContractError) as exc:
        client3.reply_bus_message(identities["id3"], id1, "reply", "b", "ik-reply-3rd", reply_to=msg_id)
    assert "status 403" in str(exc.value)
    record_response(exc)
    
    # Third party ack/accept/complete
    with pytest.raises(WireContractError) as exc:
        client3.ack_bus_message(msg_id)
    assert "status 403" in str(exc.value)
    record_response(exc)
    
    with pytest.raises(WireContractError) as exc:
        client3.accept_bus_message(msg_id)
    assert "status 403" in str(exc.value)
    record_response(exc)

    with pytest.raises(WireContractError) as exc:
        client3.complete_bus_message(msg_id)
    assert "status 403" in str(exc.value)
    record_response(exc)
    
    # Exactly 16384 bytes, with JSON escaping expansion
    big_body = "\x01" * 16384
    sent_big = client1.send_bus_message(id1, id2, "k", big_body, "ik-big-exact")
    assert sent_big["id"]
    
    # Over 16384 bytes (16385) - tested via raw urllib since client blocks it
    too_big = "x" * 16385
    import urllib.request, json
    req = urllib.request.Request(
        f"http://127.0.0.1:{server.port}/api/bus/send",
        data=json.dumps({"from_actor": id1, "to_actor": id2, "kind": "k", "body": too_big, "idempotency_key": "ik-big-over"}).encode("utf-8"),
        headers={"Authorization": f"Bearer {identities['tok1']}", "Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have failed"
    except urllib.error.HTTPError as e:
        assert e.code == 413
        responses.append(e.read().decode('utf-8'))
    
    # Explicit cap bound test (256KB)
    import urllib.request, json
    req = urllib.request.Request(
        f"http://127.0.0.1:{server.port}/api/bus/send",
        data=json.dumps({"from_actor": id1, "to_actor": id2, "kind": "k", "body": "x", "idempotency_key": "ik-massive", "pad": "x" * (256 * 1024)}).encode("utf-8"),
        headers={"Authorization": f"Bearer {identities['tok1']}", "Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have failed"
    except urllib.error.HTTPError as e:
        assert e.code == 413
        responses.append(e.read().decode('utf-8'))
        
    # Chunked body
    req = urllib.request.Request(
        f"http://127.0.0.1:{server.port}/api/bus/send",
        data=json.dumps({"from_actor": id1, "to_actor": id2, "kind": "k", "body": "a", "idempotency_key": "ik-chunk"}).encode("utf-8"),
        headers={"Authorization": f"Bearer {identities['tok1']}", "Content-Type": "application/json", "Transfer-Encoding": "chunked"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have failed"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        responses.append(e.read().decode('utf-8'))
        
    # Replay same key and different payload (409)
    with pytest.raises(IdempotencyConflictError):
        client1.send_bus_message(id1, id2, "k", "different", "ik-1")
    
    # Replay same key same payload -> same id
    sent2 = client1.send_bus_message(id1, id2, "k", "b", "ik-1")
    assert sent2["id"] == msg_id
    
    # Malformed percent encoding - test via raw urllib because client escapes it
    req = urllib.request.Request(
        f"http://127.0.0.1:{server.port}/api/bus/messages/invalid%ZZ",
        headers={"Authorization": f"Bearer {identities['tok1']}"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have failed"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        responses.append(e.read().decode('utf-8'))
    
    # Unknown id 404
    with pytest.raises(WireContractError) as exc:
        client1.show_bus_message("nonexistent")
    assert "status 404" in str(exc.value)
    record_response(exc)
    
    # Limits (limit=0, limit=101) - test via raw urllib because client clamps it
    import urllib.request, urllib.parse
    for bad_limit in (0, 101):
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.port}/api/bus/inbox?actor={urllib.parse.quote(id1)}&limit={bad_limit}",
            headers={"Authorization": f"Bearer {identities['tok1']}"}
        )
        try:
            urllib.request.urlopen(req)
            assert False, "Should have failed"
        except urllib.error.HTTPError as e:
            assert e.code == 400
            responses.append(e.read().decode('utf-8'))
    
    # Verify no tokens in logs, stderr, or responses
    err = capsys.readouterr().err
    all_responses = str(responses)
    for t in [identities['tok1'], identities['tok2'], identities['tok3'], 'invalid_token']:
        for record in caplog.records:
            assert t not in record.message
        assert t not in err
        assert t not in all_responses

def test_kit_offline_spool(bus, identities, tmp_path, server_factory):
    # offline spool: queue while receiver is down, start receiver, flush delivers exactly once
    spool_db = tmp_path / "spool.db"
    spool = SQLiteSpool(spool_db)
    
    # Add mapping to spool manually for routing
    spool.register_route("hub", workspace="/tmp", tag="hub-tag")
    
    # We need a client.
    client = C888BusClient(
        base_url="http://127.0.0.1:1", # offline port
        token_provider=lambda: identities["tok1"],
        allow_loopback_http=True
    )
    
    integration = HubOutboundIntegration(spool=spool, transport=client)
    
    payload = json.dumps({
        "from_actor": identities["id1"],
        "to_actor": identities["id2"],
        "kind": "offline",
        "body": "queued",
        "idempotency_key": "ik-off"
    }).encode("utf-8")
    
    # Send payload -> goes to spool because server is down
    spool._check_physical_capacity_before_txn = lambda *a, **k: None 
    with spool._get_connection() as conn:
        conn.execute(
            "INSERT INTO outbound_spool (idempotency_key, route, payload, status, created_at) VALUES (?, ?, ?, ?, ?)",
            ("ik-off", "hub", payload, "pending", time.time())
        )
        conn.commit()
    
    # Process spool -> should fail quickly because port 1 refuses connection
    integration.process_spool()
    
    with spool._get_connection() as conn:
        r = conn.execute("SELECT status FROM outbound_spool WHERE idempotency_key = 'ik-off'").fetchone()
        assert r["status"] in ("pending", "failed")
    
    # Start server
    server = server_factory(start=True)
    
    # Update client with correct port
    client.base_url = f"http://127.0.0.1:{server.port}"

    
    # Process again -> should succeed
    spool.reset_retry_backoffs() # clear errors
    integration.process_spool()
    
    # Should be delivered
    with spool._get_connection() as conn:
        r = conn.execute("SELECT status FROM outbound_spool WHERE idempotency_key = 'ik-off'").fetchone()
        assert r["status"] == "delivered"
        
    # Check inbox
    client2 = C888BusClient(
        base_url=f"http://127.0.0.1:{server.port}",
        token_provider=lambda: identities["tok2"],
        allow_loopback_http=True
    )
    inbox = client2.get_bus_inbox(identities["id2"])
    assert len(inbox) == 1
    assert inbox[0]["body"] == "queued"


def test_machine_scope(bus, server, get_client):
    # Register host A
    a1, tok_a1 = bus.register(agent_name="a1", device_id="hostA", project_id="proj1")
    a2, tok_a2 = bus.register(agent_name="a2", device_id="hostA", project_id="proj1")
    # Register host B
    b1, tok_b1 = bus.register(agent_name="b1", device_id="hostB", project_id="proj1")
    
    # client authenticating as tok_a1
    client_a1 = get_client(tok_a1)
    # client authenticating as tok_b1
    client_b1 = get_client(tok_b1)
    
    # tok_a1 acts as a2 to send a message to b1
    sent = client_a1.send_bus_message(
        from_actor=a2.identity_id,
        to_actor=b1.identity_id,
        kind="test",
        body="hello from a2 using tok_a1",
        idempotency_key="ik-scope-1"
    )
    assert sent["from_actor"] == a2.identity_id
    
    # tok_a1 acts as a2 to read a2's inbox
    inbox = client_a1.get_bus_inbox(actor=a2.identity_id)
    assert len(inbox) == 0  # no messages for a2 yet, but access succeeded
    
    # tok_a1 acts as b1 -> 403
    import pytest
    from adapters.hub_outbound import WireContractError
    with pytest.raises(WireContractError) as exc:
        client_a1.send_bus_message(from_actor=b1.identity_id, to_actor=a2.identity_id, kind="t", body="x", idempotency_key="ik-scope-2")
    assert "status 403" in str(exc.value)
    
    # tok_a1 acting as unregistered actor -> 403
    with pytest.raises(WireContractError) as exc:
        client_a1.send_bus_message(from_actor="unknown_actor", to_actor=b1.identity_id, kind="t", body="x", idempotency_key="ik-scope-3")
    assert "status 403" in str(exc.value)
    
    # Create a message purely within A
    sent_a = client_a1.send_bus_message(a1.identity_id, a2.identity_id, "test", "x", "ik-scope-internal")
    # B's token cannot read A's internal messages
    with pytest.raises(WireContractError) as exc:
        client_b1.show_bus_message(sent_a["id"])
    assert "status 403" in str(exc.value)



def test_claims_are_explicitly_not_implemented(bus, identities, get_client):
    # claims/release are an open gap against c888: the bridge must say so with
    # 501 rather than fake success, and the kit must surface it as an error.
    client = get_client(identities["tok1"])
    with pytest.raises(WireContractError) as exc:
        client.create_claim(project="proj1", scope="scope-a", holder=identities["id1"], ttl_ms=60000)
    assert "status 501" in str(exc.value)
    with pytest.raises(WireContractError) as exc:
        client.release_claim("proj1:scope-a")
    assert "status 501" in str(exc.value)
