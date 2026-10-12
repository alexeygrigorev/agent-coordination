import hmac
import json
import logging
import re
import urllib.parse
import os
import time
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple

try:
    from ac59_service.coordination.bus import BusMessage, FileBus
    from ac59_service.coordination.errors import IdempotencyConflict, CoordinationError
except ImportError:
    # Dummy for tests without proper PYTHONPATH
    BusMessage = Any
    FileBus = Any
    class IdempotencyConflict(Exception): pass
    class CoordinationError(Exception): pass

logger = logging.getLogger(__name__)

# Pattern for valid ULIDs/IDs to decode
MESSAGE_ID_PATTERN = re.compile(r"^/api/bus/messages/([^/]+)(?:/(ack|accept|complete))?$")
CLAIM_ID_PATTERN = re.compile(r"^/api/bus/claims/([^/]+)/release$")

def datetime_to_epoch_ms(dt_str: Optional[str]) -> Optional[int]:
    if not dt_str:
        return None
    try:
        from datetime import datetime, timezone
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(dt_str)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None

def convert_message_to_hub(msg: BusMessage) -> Dict[str, Any]:
    created_ms = datetime_to_epoch_ms(msg.created_at) or int(time.time() * 1000)
    
    # Extract thread_id from data if available
    thread_id = None
    if isinstance(msg.data, dict):
        thread_id = msg.data.get("thread_id")
    
    return {
        "id": msg.message_id,
        "from_actor": msg.sender_id,
        "to_actor": msg.recipient_id,
        "kind": msg.kind,
        "thread_id": thread_id,
        "reply_to": msg.reply_to,
        "body": msg.body,
        "created_at": created_ms,
        "expires_at": created_ms + 7 * 86400 * 1000, # 7 days expiry
        "delivered_at": datetime_to_epoch_ms(msg.delivered_at),
        "read_at": datetime_to_epoch_ms(msg.acked_at),
        "acked_at": datetime_to_epoch_ms(msg.acked_at),
        "accepted_at": datetime_to_epoch_ms(msg.accepted_at),
        "completed_at": datetime_to_epoch_ms(msg.outcome_at) if getattr(msg, "outcome", None) else None,
    }

def get_bearer_token(handler) -> Optional[str]:
    auth_header = handler.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header[7:]

def send_json(handler, status: HTTPStatus, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def send_error(handler, code: int, message: str) -> None:
    handler.log_error("code %d: %s", code, message)
    try:
        phrase = HTTPStatus(code).phrase
    except ValueError:
        phrase = "Error"
    body = json.dumps({"status": "error", "detail": phrase}).encode("utf-8")
    handler.send_response(code, phrase)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Connection", "close")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    if getattr(handler, "command", None) != "HEAD" and code >= 200 and code not in (204, 304):
        handler.wfile.write(body)
    handler.close_connection = True

def get_machine_actors(bus, token: str) -> dict:
    from ac59_service.coordination.bus import FileLock
    import hmac
    with FileLock(bus._lock):
        tokens = bus._read(bus._tokens, {})
        auth_id = None
        for k, v in tokens.items():
            if hmac.compare_digest(v, token):
                auth_id = k
                break
        if not auth_id:
            return {}
        
        identities = bus._read(bus._identities, {})
        auth_ident = identities.get(auth_id)
        if not auth_ident:
            return {}
            
        machine_actors = {}
        for k, ident in identities.items():
            if ident.get("device_id") == auth_ident.get("device_id") and ident.get("project_id") == auth_ident.get("project_id"):
                machine_actors[k] = tokens.get(k)
        return machine_actors

def peek_message(bus, msg_id: str) -> dict:
    from ac59_service.coordination.bus import FileLock
    with FileLock(bus._lock):
        messages = bus._read(bus._messages, {})
        return messages.get(msg_id)

def handle_hub_bridge_request(handler, bus, method: str, path: str, payload: dict = None, query: dict = None) -> bool:
    if not path.startswith("/api/bus/"):
        return False
        
    token = get_bearer_token(handler)
    if not token:
        send_error(handler, HTTPStatus.UNAUTHORIZED, "Missing Bearer token")
        return True
        
    machine_actors = get_machine_actors(bus, token)
    if not machine_actors:
        send_error(handler, HTTPStatus.UNAUTHORIZED, "Invalid Bearer token")
        return True

    try:
        if method == "POST" and path in ("/api/bus/send", "/api/bus/reply"):
            return _handle_send(handler, bus, payload, machine_actors, is_reply=(path=="/api/bus/reply"))
            
        elif method == "GET" and path.startswith("/api/bus/inbox"):
            actor = query.get("actor", [""])[0]
            if not actor:
                send_error(handler, HTTPStatus.BAD_REQUEST, "Missing actor parameter")
                return True
            if actor not in machine_actors:
                send_error(handler, HTTPStatus.FORBIDDEN, "actor mismatch")
                return True
                
            limit = 50
            if "limit" in query:
                try:
                    limit = int(query["limit"][0])
                except ValueError:
                    send_error(handler, HTTPStatus.BAD_REQUEST, "Invalid limit parameter")
                    return True
                if not (1 <= limit <= 100):
                    send_error(handler, HTTPStatus.BAD_REQUEST, "limit must be between 1 and 100")
                    return True
            
            try:
                messages = bus.inbox(identity_id=actor, token=machine_actors[actor], unread_only=False)
                out = [convert_message_to_hub(m) for m in messages[-limit:]]
                send_json(handler, HTTPStatus.OK, out)
            except Exception as err:
                code = getattr(err, "code", "")
                send_error(handler, HTTPStatus.BAD_REQUEST, str(err))
            return True
            
        elif method in ("GET", "POST") and path.startswith("/api/bus/messages/"):
            m = MESSAGE_ID_PATTERN.match(path)
            if not m:
                send_error(handler, HTTPStatus.BAD_REQUEST, "Invalid message path")
                return True
                
            encoded_id = m.group(1)
            import re
            if "%" in encoded_id and not re.match(r'^(?:[^%]|%[0-9a-fA-F]{2})*$', encoded_id):
                send_error(handler, HTTPStatus.BAD_REQUEST, "Malformed percent-encoding")
                return True
            msg_id = urllib.parse.unquote(encoded_id)
            action = m.group(2)
            
            msg_raw = peek_message(bus, msg_id)
            if not msg_raw:
                send_error(handler, HTTPStatus.NOT_FOUND, "unknown_message")
                return True
                
            if action is None and method == "GET":
                if msg_raw["sender_id"] in machine_actors:
                    actor = msg_raw["sender_id"]
                elif msg_raw["recipient_id"] in machine_actors:
                    actor = msg_raw["recipient_id"]
                else:
                    send_error(handler, HTTPStatus.FORBIDDEN, "not_participant")
                    return True
                    
                try:
                    msg = bus.get(identity_id=actor, token=machine_actors[actor], message_id=msg_id)
                    send_json(handler, HTTPStatus.OK, convert_message_to_hub(msg))
                except Exception as err:
                    code = getattr(err, "code", "")
                    if code == "unknown_message":
                        send_error(handler, HTTPStatus.NOT_FOUND, str(err))
                    elif code in ("not_participant", "not_recipient"):
                        send_error(handler, HTTPStatus.FORBIDDEN, str(err))
                    else:
                        send_error(handler, HTTPStatus.BAD_REQUEST, str(err))
                return True
                
            elif action in ("ack", "accept", "complete") and method == "POST":
                if msg_raw["recipient_id"] in machine_actors:
                    actor = msg_raw["recipient_id"]
                else:
                    send_error(handler, HTTPStatus.FORBIDDEN, "not_recipient")
                    return True
                    
                try:
                    if action == "ack":
                        msg = bus.ack(identity_id=actor, token=machine_actors[actor], message_id=msg_id)
                    elif action == "accept":
                        msg = bus.accept(identity_id=actor, token=machine_actors[actor], message_id=msg_id)
                    elif action == "complete":
                        msg = bus.complete(identity_id=actor, token=machine_actors[actor], message_id=msg_id, status="completed")
                    
                    send_json(handler, HTTPStatus.OK, convert_message_to_hub(msg))
                except Exception as err:
                    code = getattr(err, "code", "")
                    if code == "unknown_message":
                        send_error(handler, HTTPStatus.NOT_FOUND, str(err))
                    elif code in ("not_participant", "not_recipient"):
                        send_error(handler, HTTPStatus.FORBIDDEN, str(err))
                    else:
                        send_error(handler, HTTPStatus.BAD_REQUEST, str(err))
                return True
                
        elif method == "POST" and path.startswith("/api/bus/claims"):
            send_error(handler, HTTPStatus.NOT_IMPLEMENTED, "Claims not supported")
            return True

    except Exception as exc:
        logger.exception("Bridge error")
        send_error(handler, HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        return True
        
    return False

def _handle_send(handler, bus, payload, machine_actors, is_reply):
    if not payload:
        send_error(handler, HTTPStatus.BAD_REQUEST, "Missing JSON payload")
        return True
        
    from_actor = payload.get("from_actor")
    to_actor = payload.get("to_actor")
    kind = payload.get("kind")
    body = payload.get("body")
    idempotency_key = payload.get("idempotency_key")
    reply_to = payload.get("reply_to")
    thread_id = payload.get("thread_id")
    
    if not all([from_actor, to_actor, kind, body is not None, idempotency_key]):
        send_error(handler, HTTPStatus.BAD_REQUEST, "Missing required fields")
        return True
        
    if is_reply and not reply_to:
        send_error(handler, HTTPStatus.BAD_REQUEST, "reply_to required")
        return True
        
    if from_actor not in machine_actors:
        send_error(handler, HTTPStatus.FORBIDDEN, "from_actor mismatch")
        return True
        
    actor_token = machine_actors[from_actor]
        
    body_str = str(body)
    if len(body_str.encode("utf-8")) > 16384:
        send_error(handler, HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body exceeds 16384 bytes")
        return True
        
    data = {}
    if thread_id:
        data["thread_id"] = thread_id
        
    try:
        if is_reply:
            msg = bus.reply(
                sender_id=from_actor,
                token=actor_token,
                message_id=reply_to,
                body=body_str,
                data=data,
                idempotency_key=idempotency_key,
            )
        else:
            msg = bus.send(
                sender_id=from_actor,
                token=actor_token,
                recipient_id=to_actor,
                body=body_str,
                data=data,
                idempotency_key=idempotency_key,
                kind=kind,
                reply_to=reply_to,
            )
        send_json(handler, HTTPStatus.OK, convert_message_to_hub(msg))
    except Exception as err:
        if type(err).__name__ == "IdempotencyConflict":
            send_error(handler, HTTPStatus.CONFLICT, "Idempotency conflict")
            return True
            
        code = getattr(err, "code", "")
        if code == "unknown_message":
            send_error(handler, HTTPStatus.NOT_FOUND, str(err))
        elif code in ("not_participant", "not_recipient"):
            send_error(handler, HTTPStatus.FORBIDDEN, str(err))
        else:
            send_error(handler, HTTPStatus.BAD_REQUEST, str(err))
            
    return True
