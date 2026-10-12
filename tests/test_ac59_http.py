
import json
import logging
import pathlib
import threading
import time
import unittest
from http.client import HTTPConnection
import urllib.request
import urllib.error
import socket
from typing import Any

from ac59_service.adapter.adapter import BusServer, BusAdapterHandler, main
try:
    import ac59_service.coordination.bus
except ImportError:
    pass
import sys
FileBus = sys.modules["ac59_service.coordination.bus"].FileBus

class TestAdapterHandler(BusAdapterHandler):
    def _get_cert_fingerprint(self):
        cert_der = getattr(self.server, "test_cert_der", None)
        if not cert_der:
            return None
        import hashlib
        return hashlib.sha256(cert_der).hexdigest()

class TestBusServer(BusServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_cert_der = None

def get_free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

class TestAC59HTTP(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = pathlib.Path(self.temp_dir.name) / "store"
        self.store.mkdir()
        self.bus = FileBus(self.store)
        
        # Setup allowlist
        import hashlib
        self.cert1 = b"cert1"
        self.cert2 = b"cert2"
        self.cert1_fp = hashlib.sha256(self.cert1).hexdigest()
        self.cert2_fp = hashlib.sha256(self.cert2).hexdigest()
        
        self.allowlist = {
            self.cert1_fp: {
                "devices": ["dev1"],
                "projects": ["proj1", "proj2"]
            },
            self.cert2_fp: {
                "devices": ["dev2"],
                "projects": ["proj2"]
            }
        }
        
        self.port = get_free_port()
        self.server = TestBusServer(('127.0.0.1', self.port), TestAdapterHandler, self.bus, self.allowlist)
        self.server.test_cert_der = self.cert1
        
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        time.sleep(0.1) # Wait for server to start

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()
        self.temp_dir.cleanup()

    def request(self, method, path, payload=None, headers=None, cert_der=None):
        if cert_der is not None:
            self.server.test_cert_der = cert_der
        else:
            self.server.test_cert_der = self.cert1
            
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        if payload is not None:
            data = json.dumps(payload).encode('utf-8')
            req.add_header('Content-Type', 'application/json')
            req.add_header('Content-Length', str(len(data)))
            req.data = data
            
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode('utf-8'))

    def test_registration_scope_spoof(self):
        # dev1 proj1 is allowed for cert1
        status, body = self.request('POST', '/v1/register', {
            "device_id": "dev1", "agent_name": "agent1", "project_id": "proj1"
        })
        self.assertEqual(status, 201)
        
        # dev2 proj1 is not allowed for cert1
        status, body = self.request('POST', '/v1/register', {
            "device_id": "dev2", "agent_name": "agent1", "project_id": "proj1"
        })
        self.assertEqual(status, 403)
        self.assertIn("Device scope", body["detail"])

    def test_crossproject_device_token_substitution(self):
        # Register on cert1
        status, b1 = self.request('POST', '/v1/register', {
            "device_id": "dev1", "agent_name": "a1", "project_id": "proj2"
        })
        self.assertEqual(status, 201)
        ident1 = b1["identity"]["identity_id"]
        tok1 = b1["token"]
        
        # Switch cert to cert2 (allowed for dev2 proj2)
        # Attempt to use ident1/tok1 via cert2 should FAIL
        # because cert2 does not allow dev1
        status, body = self.request('POST', '/v1/send', {
            "sender_id": ident1, "token": tok1, "recipient_id": ident1,
            "body": "hello"
        }, cert_der=self.cert2)
        self.assertEqual(status, 403)
        self.assertIn("Identity device scope", body["detail"])

    def test_send_and_inbox_headers(self):
        status, b1 = self.request('POST', '/v1/register', {
            "device_id": "dev1", "agent_name": "a1", "project_id": "proj1"
        })
        ident1, tok1 = b1["identity"]["identity_id"], b1["token"]
        
        # Test malformed
        status, body = self.request('POST', '/v1/send', None, headers={"Content-Length": "-1"})
        self.assertEqual(status, 400)
        self.assertEqual(body["detail"], "Negative Content-Length")
        
        # Test large payload
        status, body = self.request('POST', '/v1/send', None, headers={"Content-Length": str(11*1024*1024)})
        self.assertEqual(status, 413) # REQUEST_ENTITY_TOO_LARGE
        
        # Successful send
        status, s1 = self.request('POST', '/v1/send', {
            "sender_id": ident1, "token": tok1, "recipient_id": ident1,
            "body": "hello structured", "data": {"key": "val"}, "kind": "command"
        })
        self.assertEqual(status, 200)
        msg_id = s1["message"]["id"]
        
        # Inbox via POST avoiding URLs
        status, i1 = self.request('POST', '/v1/inbox', {}, headers={
            "X-Bus-Identity": ident1,
            "X-Bus-Token": tok1
        })
        self.assertEqual(status, 200)
        msgs = i1["messages"]
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["id"], msg_id)
        self.assertEqual(msgs[0]["kind"], "command")
        self.assertEqual(msgs[0]["data"], {"key": "val"})

    def test_structured_reply_linkage_and_foreign_ack(self):
        status, b1 = self.request('POST', '/v1/register', {
            "device_id": "dev1", "agent_name": "a1", "project_id": "proj1"
        })
        id1, t1 = b1["identity"]["identity_id"], b1["token"]
        
        status, b2 = self.request('POST', '/v1/register', {
            "device_id": "dev1", "agent_name": "a2", "project_id": "proj1"
        })
        id2, t2 = b2["identity"]["identity_id"], b2["token"]
        
        # id1 sends to id2
        status, s1 = self.request('POST', '/v1/send', {
            "sender_id": id1, "token": t1, "recipient_id": id2,
            "body": "hi", "data": {"x": 1}
        })
        msg_id = s1["message"]["id"]
        
        # Foreign ACK: id1 tries to ack a message sent to id2
        status, ack_err = self.request('POST', '/v1/ack', {
            "identity_id": id1, "token": t1, "message_id": msg_id
        })
        self.assertEqual(status, 400)
        self.assertIn("not_recipient", ack_err["detail"])
        
        # id2 replies to id1
        status, r1 = self.request('POST', '/v1/send', {
            "sender_id": id2, "token": t2, "recipient_id": id1,
            "body": "reply", "reply_to": msg_id, "kind": "reply"
        })
        self.assertEqual(status, 200)
        reply_id = r1["message"]["id"]
        
        status, i1 = self.request('GET', f'/v1/inbox?identity_id={id1}&token={t1}')
        self.assertEqual(len(i1["messages"]), 1)
        self.assertEqual(i1["messages"][0]["id"], reply_id)
        self.assertEqual(i1["messages"][0]["reply_to"], msg_id)
        self.assertEqual(i1["messages"][0]["kind"], "reply")

    def test_failed_retry_then_success(self):
        status, b1 = self.request('POST', '/v1/register', {
            "device_id": "dev1", "agent_name": "a1", "project_id": "proj1"
        })
        id1, t1 = b1["identity"]["identity_id"], b1["token"]
        
        idem_key = "idem123"
        
        # Failed retry (wrong body -> conflict)
        status, s1 = self.request('POST', '/v1/send', {
            "sender_id": id1, "token": t1, "recipient_id": id1,
            "body": "hello", "idempotency_key": idem_key
        })
        self.assertEqual(status, 200)
        
        # Malformed request should NOT poison the retry
        # Let's do a request with bad token
        status, s2 = self.request('POST', '/v1/send', {
            "sender_id": id1, "token": "bad_token", "recipient_id": id1,
            "body": "hello", "idempotency_key": idem_key
        })
        self.assertEqual(status, 400)
        self.assertIn("auth_failed", s2["detail"])
        
        # Conflicting content rejects
        status, s3 = self.request('POST', '/v1/send', {
            "sender_id": id1, "token": t1, "recipient_id": id1,
            "body": "hello different", "idempotency_key": idem_key
        })
        self.assertEqual(status, 409)
        self.assertIn("Replay detected", s3["detail"])
        
        # Success retry returning SAME message
        status, s4 = self.request('POST', '/v1/send', {
            "sender_id": id1, "token": t1, "recipient_id": id1,
            "body": "hello", "idempotency_key": idem_key
        })
        self.assertEqual(status, 200)
        self.assertEqual(s1["message"]["id"], s4["message"]["id"])
        
    def test_process_restart_replay_durability(self):
        status, b1 = self.request('POST', '/v1/register', {
            "device_id": "dev1", "agent_name": "a1", "project_id": "proj1"
        })
        id1, t1 = b1["identity"]["identity_id"], b1["token"]
        
        idem_key = "idem_dur"
        status, s1 = self.request('POST', '/v1/send', {
            "sender_id": id1, "token": t1, "recipient_id": id1,
            "body": "durability", "idempotency_key": idem_key
        })
        self.assertEqual(status, 200)
        msg_id = s1["message"]["id"]
        
        # Simulate restart by instantiating new BusServer
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()
        
        # Instantiate fresh bus instance and server
        self.bus = FileBus(self.store)
        self.port = get_free_port()
        self.server = TestBusServer(('127.0.0.1', self.port), TestAdapterHandler, self.bus, self.allowlist)
        self.server.test_cert_der = self.cert1
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(0.1)
        
        # Exact same retry should succeed and return same message
        status, s2 = self.request('POST', '/v1/send', {
            "sender_id": id1, "token": t1, "recipient_id": id1,
            "body": "durability", "idempotency_key": idem_key
        })
        self.assertEqual(status, 200)
        self.assertEqual(s2["message"]["id"], msg_id)
        
    def test_structured_completion(self):
        status, b1 = self.request('POST', '/v1/register', {
            "device_id": "dev1", "agent_name": "a1", "project_id": "proj1"
        })
        id1, t1 = b1["identity"]["identity_id"], b1["token"]
        
        status, s1 = self.request('POST', '/v1/send', {
            "sender_id": id1, "token": t1, "recipient_id": id1,
            "body": "task"
        })
        msg_id = s1["message"]["id"]
        
        status, c1 = self.request('POST', '/v1/complete', {
            "identity_id": id1, "token": t1, "message_id": msg_id,
            "status": "success", "artifact": "out.txt", "digest": "hex123", "extra": {"stats": 1}
        })
        self.assertEqual(status, 200)
        outcome = c1["message"]["outcome"]
        self.assertEqual(outcome["status"], "success")
        self.assertEqual(outcome["artifact"], "out.txt")
        self.assertEqual(outcome["digest"], "hex123")
        self.assertEqual(outcome["stats"], 1)

    def test_canonical_import_namespace(self):
        import sys
        import pathlib
        import ac59_service.adapter.adapter
        adapter_parent = str(pathlib.Path(ac59_service.adapter.adapter.__file__).resolve().parent.parent)
        # Ensure the adapter didn't poison sys.path
        if sys.path:
            self.assertNotEqual(sys.path[0], adapter_parent)
            
    def test_chunked_rejection(self):
        status, body = self.request('POST', '/v1/register', headers={"Transfer-Encoding": "chunked"})
        self.assertEqual(status, 400)
        self.assertIn("chunked not supported", body.get("detail", ""))

    def test_timeout_set(self):
        self.assertEqual(BusAdapterHandler.timeout, 30.0)

if __name__ == '__main__':
    unittest.main()
