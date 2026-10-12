import argparse
import hashlib
import json
import logging
import pathlib
import ssl
import sys
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

try:
    try:
        import ac59_service.coordination.bus
    except ImportError:
        pass
    import sys
    FileBus = sys.modules["ac59_service.coordination.bus"].FileBus
    BusError = sys.modules["ac59_service.coordination.bus"].BusError
    CoordinationError = sys.modules["ac59_service.coordination.errors"].CoordinationError
    IdempotencyConflict = sys.modules["ac59_service.coordination.errors"].IdempotencyConflict
except (KeyError, AttributeError, ImportError):
    # Fallback to standard generic classes if bus_core doesn't exist in the same way
    class BusError(Exception): pass
    class CoordinationError(Exception): pass
    class IdempotencyConflict(Exception): pass

logger = logging.getLogger(__name__)

class BusAdapterHandler(BaseHTTPRequestHandler):
    timeout = 30.0

    # Rejected bodies up to this size are read and discarded before replying,
    # so a client still uploading sees the 413 instead of a reset connection.
    DRAIN_LIMIT = 1024 * 1024

    def _drain_chunked(self) -> None:
        # Read (and discard) a chunked body up to its terminating zero-size
        # chunk, bounded by DRAIN_LIMIT, so the client sees our error reply.
        try:
            self.connection.settimeout(2.0)
            consumed = 0
            while consumed <= self.DRAIN_LIMIT:
                size_line = self.rfile.readline(1024)
                if not size_line:
                    return
                consumed += len(size_line)
                size = int(size_line.split(b";", 1)[0].strip() or b"0", 16)
                if size == 0:
                    self.rfile.readline(1024)
                    return
                consumed += size + 2
                self.rfile.read(size + 2)
        except (OSError, ValueError):
            pass

    def _reject_oversized(self, content_length: int) -> None:
        if content_length <= self.DRAIN_LIMIT:
            try:
                self.connection.settimeout(2.0)
                remaining = content_length
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
            except OSError:
                pass
        self.close_connection = True
        self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"status": "error", "detail": "Payload too large"})

    def _log_target(self):
        # command/path are unset when the request line itself fails to parse.
        path = getattr(self, "path", None)
        return (getattr(self, "command", None) or "-",
                urlparse(path).path if path else "-")

    def log_message(self, format, *args):
        # The default handler logs the raw request line, query string included;
        # identity tokens must never reach the journal, so log the path only.
        logger.info("%s %s %s", self.client_address[0], *self._log_target())

    def log_request(self, code="-", size="-"):
        logger.info("%s %s %s %s", self.client_address[0], *self._log_target(),
                    getattr(code, "value", code))

    def log_error(self, format, *args):
        # args can carry the raw request line; keep only numeric status codes.
        codes = [a for a in args if isinstance(a, int)]
        logger.warning("%s %s %s error %s", self.client_address[0],
                       *self._log_target(), codes[0] if codes else "-")

    def send_error(self, code, message=None, explain=None):
        # The default echoes the raw request line (query tokens included) in
        # the status line and HTML body; reply with a fixed JSON error instead.
        self.log_error("code %d", code)
        try:
            phrase = HTTPStatus(code).phrase
        except ValueError:
            phrase = "Error"
        body = json.dumps({"status": "error", "detail": phrase}).encode("utf-8")
        self.send_response(code, phrase)
        self.send_header("Content-Type", "application/json")
        self.send_header("Connection", "close")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if getattr(self, "command", None) != "HEAD" and code >= 200 and code not in (204, 304):
            self.wfile.write(body)
        self.close_connection = True

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_cert_fingerprint(self):
        if not hasattr(self.server, "ssl_context") or self.server.ssl_context is None:
            return "insecure_mode"
        cert_der = self.connection.getpeercert(binary_form=True)
        if not cert_der:
            return None
        return hashlib.sha256(cert_der).hexdigest()

    def _verify_registration_scopes(self, device_id: str, project_id: str) -> bool:
        fingerprint = self._get_cert_fingerprint()
        if fingerprint == "insecure_mode":
            return True
        if not fingerprint:
            self._send_json(HTTPStatus.FORBIDDEN, {"status": "error", "detail": "Client cert required"})
            return False
        
        allowlist = self.server.allowlist
        if fingerprint not in allowlist:
            self._send_json(HTTPStatus.FORBIDDEN, {"status": "error", "detail": "Cert fingerprint not allowed"})
            return False
            
        allowed = allowlist[fingerprint]
        if device_id not in allowed.get("devices", []):
            self._send_json(HTTPStatus.FORBIDDEN, {"status": "error", "detail": f"Device scope {device_id} not allowed"})
            return False
        if project_id not in allowed.get("projects", []):
            self._send_json(HTTPStatus.FORBIDDEN, {"status": "error", "detail": f"Project scope {project_id} not allowed"})
            return False
        return True

    def _verify_identity_scopes(self, identity_id: str) -> bool:
        fingerprint = self._get_cert_fingerprint()
        if fingerprint == "insecure_mode":
            return True
        if not fingerprint:
            self._send_json(HTTPStatus.FORBIDDEN, {"status": "error", "detail": "Client cert required"})
            return False
            
        allowlist = self.server.allowlist
        if fingerprint not in allowlist:
            self._send_json(HTTPStatus.FORBIDDEN, {"status": "error", "detail": "Cert fingerprint not allowed"})
            return False
            
        identities = self.server.bus._read(self.server.bus._identities, {})
        identity = identities.get(identity_id)
        if not identity:
            # If identity not found, let the bus handle it normally
            return True
            
        allowed = allowlist[fingerprint]
        device_id = identity.get("device_id")
        project_id = identity.get("project_id")
        
        if not device_id or device_id not in allowed.get("devices", []):
            self._send_json(HTTPStatus.FORBIDDEN, {"status": "error", "detail": f"Identity device scope {device_id} not allowed by certificate"})
            return False
        if not project_id or project_id not in allowed.get("projects", []):
            self._send_json(HTTPStatus.FORBIDDEN, {"status": "error", "detail": f"Identity project scope {project_id} not allowed by certificate"})
            return False
        return True

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path

            if path.startswith("/api/bus/"):
                import ac59_service.adapter.hub_bridge as hb
                query = parse_qs(parsed.query)
                if hb.handle_hub_bridge_request(self, self.server.bus, "GET", path, query=query):
                    return

            if path == "/v1/inbox":
                query = parse_qs(parsed.query)
                identity_id = query.get("identity_id", [None])[0] or self.headers.get("X-Bus-Identity")
                token = query.get("token", [None])[0] or self.headers.get("X-Bus-Token")
                
                # Check for Authorization Bearer header as a secure alternative
                auth_header = self.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = token or auth_header[7:]

                unread_only = query.get("unread_only", ["false"])[0].lower() == "true"
                cursor = query.get("cursor", [None])[0]
                
                if not identity_id or not token:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "identity_id and token required"})
                    return
                    
                if not self._verify_identity_scopes(identity_id):
                    return

                messages = self.server.bus.inbox(identity_id=identity_id,
                    token=token,  unread_only=unread_only)
                out_msgs = []
                for m in messages:
                    pub = m.to_public()
                    pub["id"] = m.message_id
                    out_msgs.append(pub)
                self._send_json(HTTPStatus.OK, {
                    "status": "ok",
                    "messages": out_msgs,
                })
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"status": "error", "detail": "Path not found"})
        except IdempotencyConflict as err:
            self._send_json(HTTPStatus.CONFLICT, {"status": "error", "detail": "Replay detected with conflicting payload"})
        except BusError as err:
            self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": str(err)})
        except Exception as exc:
            logger.exception("Internal error")
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "error", "detail": str(exc)})

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path

            if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
                self._drain_chunked()
                self.close_connection = True
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "Transfer-Encoding: chunked not supported"})
                return

            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "Invalid Content-Length"})
                return

            if content_length < 0:
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "Negative Content-Length"})
                return
            
            # Bound request bodies: 10MB limit generally, 256KB for hub bridge
            limit = 256 * 1024 if path.startswith("/api/bus/") else 10 * 1024 * 1024
            if content_length > limit:
                self._reject_oversized(content_length)
                return

            if content_length == 0:
                payload = {}
            else:
                body = self.rfile.read(content_length)
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "Malformed JSON"})
                    return
                
            if not isinstance(payload, dict):
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "Payload must be a JSON object"})
                return

            if path.startswith("/api/bus/"):
                import ac59_service.adapter.hub_bridge as hb
                if hb.handle_hub_bridge_request(self, self.server.bus, "POST", path, payload=payload):
                    return

            if path == "/v1/register":
                device_id = payload.get("device_id")
                agent_name = payload.get("agent_name")
                project_id = payload.get("project_id")

                if not device_id or not agent_name or not project_id:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "Missing fields"})
                    return
                
                if not self._verify_registration_scopes(device_id, project_id):
                    return

                ident_obj, token = self.server.bus.register(
                    device_id=device_id,
                    agent_name=agent_name,
                    project_id=project_id
                )
                ident_data = getattr(ident_obj, '__dict__', ident_obj)
                self._send_json(HTTPStatus.CREATED, {
                    "status": "ok",
                    "identity": ident_data,
                    "token": token,
                })
                return

            if path == "/v1/send":
                sender_id = payload.get("sender_id")
                token = payload.get("token")
                recipient_id = payload.get("recipient_id")
                body = payload.get("body")
                idempotency_key = payload.get("idempotency_key")
                data = payload.get("data")
                kind = payload.get("kind", "note")
                reply_to = payload.get("reply_to")
                
                if not sender_id or not token or not recipient_id or body is None:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "Missing fields"})
                    return
                    
                if not self._verify_identity_scopes(sender_id):
                    return

                msg = self.server.bus.send(
                    sender_id=sender_id,
                    token=token,
                    recipient_id=recipient_id,
                    body=body,
                    data=data,
                    idempotency_key=idempotency_key,
                    kind=kind,
                    reply_to=reply_to,
                )
                msg_data = msg.to_public()
                msg_data["id"] = msg.message_id
                self._send_json(HTTPStatus.OK, {"status": "ok", "message": msg_data})
                return

            for action in ["ack", "accept"]:
                if path == f"/v1/{action}":
                    identity_id = payload.get("identity_id")
                    token = payload.get("token")
                    message_id = payload.get("message_id")
                    if not identity_id or not token or not message_id:
                        self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "Missing fields"})
                        return
                        
                    if not self._verify_identity_scopes(identity_id):
                        return
                        
                    fn = getattr(self.server.bus, action)
                    msg = fn(identity_id=identity_id, token=token, message_id=message_id)
                    self._send_json(HTTPStatus.OK, {"status": "ok", "message": msg.to_public()})
                    return

            if path == "/v1/complete":
                identity_id = payload.get("identity_id")
                token = payload.get("token")
                message_id = payload.get("message_id")
                status = payload.get("status", "completed")
                artifact = payload.get("artifact")
                digest = payload.get("digest")
                extra = payload.get("extra")
                
                if not identity_id or not token or not message_id:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "Missing fields"})
                    return
                    
                if not self._verify_identity_scopes(identity_id):
                    return
                    
                msg = self.server.bus.complete(
                    identity_id=identity_id,
                    token=token,
                    message_id=message_id,
                    status=status,
                    artifact=artifact,
                    digest=digest,
                    extra=extra,
                )
                self._send_json(HTTPStatus.OK, {"status": "ok", "message": msg.to_public()})
                return

            if path == "/v1/inbox":
                identity_id = payload.get("identity_id") or self.headers.get("X-Bus-Identity")
                token = payload.get("token") or self.headers.get("X-Bus-Token")
                
                auth_header = self.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = token or auth_header[7:]

                unread_only = str(payload.get("unread_only", "false")).lower() == "true"
                cursor = payload.get("cursor")
                
                if not identity_id or not token:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": "identity_id and token required"})
                    return
                    
                if not self._verify_identity_scopes(identity_id):
                    return

                messages = self.server.bus.inbox(identity_id=identity_id, token=token, unread_only=unread_only)
                out_msgs = []
                for m in messages:
                    pub = m.to_public()
                    pub["id"] = m.message_id
                    out_msgs.append(pub)
                self._send_json(HTTPStatus.OK, {
                    "status": "ok",
                    "messages": out_msgs,
                })
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"status": "error", "detail": "Path not found"})
        except IdempotencyConflict as err:
            self._send_json(HTTPStatus.CONFLICT, {"status": "error", "detail": "Replay detected with conflicting payload"})
        except BusError as err:
            self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "detail": str(err)})
        except Exception as exc:
            logger.exception("Internal error")
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "error", "detail": str(exc)})

class BusServer(HTTPServer):
    def __init__(self, server_address, handler_class, bus, allowlist, ssl_context=None):
        super().__init__(server_address, handler_class)
        self.bus = bus
        self.allowlist = allowlist
        self.ssl_context = ssl_context

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--store", type=pathlib.Path, required=True)
    parser.add_argument("--allowlist", type=pathlib.Path)
    parser.add_argument("--ca-cert", type=pathlib.Path)
    parser.add_argument("--server-cert", type=pathlib.Path)
    parser.add_argument("--server-key", type=pathlib.Path)
    parser.add_argument("--insecure-loopback", action="store_true")
    args = parser.parse_args()

    if args.insecure_loopback and args.host not in ("127.0.0.1", "::1", "localhost"):
        parser.error("--insecure-loopback requires loopback host (e.g. 127.0.0.1)")

    try:
        import ac59_service.coordination.bus
    except ImportError:
        pass
    import sys
    FileBus = sys.modules["ac59_service.coordination.bus"].FileBus
    bus = FileBus(args.store)
    
    allowlist = {}
    if args.allowlist and args.allowlist.exists():
        with open(args.allowlist) as f:
            allowlist = json.load(f)

    ctx = None
    if not args.insecure_loopback:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=args.server_cert, keyfile=args.server_key)
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_verify_locations(cafile=args.ca_cert)
        
    server = BusServer((args.host, args.port), BusAdapterHandler, bus, allowlist, ctx)
    if ctx:
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        
    logger.info("Starting adapter...")
    server.serve_forever()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
