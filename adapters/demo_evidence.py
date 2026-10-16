import json
import sys
import hashlib
import re
from typing import Dict, Any, List, Tuple, Optional

SCHEMA_VERSION = "2.0"
SHA256_REGEX = re.compile(r"^[a-fA-F0-9]{64}$")

def is_true_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)

def is_nonempty_string(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())

def compute_sha256_and_size(content: str) -> Tuple[str, int]:
    # Deterministic UTF-8 encoding
    try:
        encoded = content.encode("utf-8")
    except UnicodeEncodeError as e:
        raise ValueError(f"Content encoding error: {e}")
    digest = hashlib.sha256(encoded).hexdigest()
    return digest, len(encoded)

def validate_manifest(manifest: Any) -> Tuple[str, List[str]]:
    base_flags = ["PHYSICAL_EVIDENCE_MISSING (supplied-but-unverified evidence from JSON manifest)"]
    
    if not isinstance(manifest, dict):
        return "INVALID", ["Manifest must be a dictionary"] + base_flags
        
    if manifest.get("version") not in ["1.0", "2.0"]:
        return "INVALID", ["Unsupported schema version"] + base_flags
        
    errors = []
    
    # Validate project/task/correlation
    for field in ["project", "task", "correlation_id"]:
        val = manifest.get(field)
        if not is_nonempty_string(val):
            errors.append(f"Missing or invalid string field: {field}")
            
    manifest_project = manifest.get("project")
    manifest_task = manifest.get("task")
    manifest_correlation = manifest.get("correlation_id")

    raw_actors = manifest.get("actors", {})
    if not isinstance(raw_actors, dict):
        errors.append("actors must be a dictionary")
        raw_actors = {}
    elif not raw_actors:
        errors.append("No actors defined")
        
    actors = {}
    for actor_id, actor_info in raw_actors.items():
        if not is_nonempty_string(actor_id):
            errors.append(f"Invalid actor ID format: {actor_id}")
            continue
        if not isinstance(actor_info, dict):
            errors.append(f"Actor {actor_id} is not a dictionary")
            continue
            
        dev_id = actor_info.get("device_id")
        if not is_nonempty_string(dev_id):
            errors.append(f"Actor {actor_id} missing or invalid device_id")
            
        role_epoch = actor_info.get("role_epoch")
        if not is_true_int(role_epoch) or role_epoch <= 0:
            errors.append(f"Actor {actor_id} missing or invalid role_epoch")
            
        generation = actor_info.get("generation")
        if not is_nonempty_string(generation):
            errors.append(f"Actor {actor_id} missing or invalid generation")
            
        actors[actor_id] = actor_info
            
    messages = manifest.get("messages", [])
    if not isinstance(messages, list):
        errors.append("messages must be a list")
        messages = []
    elif not messages:
        errors.append("No messages defined")
        
    messages_by_id = {}
    idempotency_map = {}
    sender_idem_map = {}
    
    source_messages = set()
    transport_receipts = set()
    handled_acks = set()
    ownership_agreements = set()
    completed_artifacts = set()
    
    for msg in messages:
        if not isinstance(msg, dict):
            errors.append("Message item is not a dictionary")
            continue
            
        msg_id = msg.get("id")
        if not is_nonempty_string(msg_id):
            errors.append("Message missing or invalid id")
            continue
            
        if msg_id in messages_by_id:
            if messages_by_id[msg_id] != msg:
                errors.append(f"Duplicate message ID with conflicting content: {msg_id}")
            continue
            
        messages_by_id[msg_id] = msg
            
        mtype = msg.get("type")
        valid_types = ["source", "transport_receipt", "handled_ack", "ownership_agreement", "completed_artifact"]
        if not is_nonempty_string(mtype) or mtype not in valid_types:
            errors.append(f"Message {msg_id} has unknown or invalid type: {mtype}")
            continue
            
        for field, expected in [("project", manifest_project), ("task", manifest_task), ("correlation_id", manifest_correlation)]:
            if field not in msg:
                errors.append(f"Message {msg_id} missing {field}")
            elif msg.get(field) != expected:
                errors.append(f"Message {msg_id} {field} '{msg.get(field)}' mismatches manifest '{expected}'")
        
        sender = msg.get("sender")
        if not is_nonempty_string(sender) or sender not in actors:
            errors.append(f"Message {msg_id} has unknown or invalid sender: {sender}")
            continue
            
        epoch = msg.get("epoch")
        if not is_true_int(epoch) or epoch <= 0:
            errors.append(f"Message {msg_id} missing or invalid epoch")
        else:
            actor_epoch = actors[sender].get("role_epoch")
            if is_true_int(actor_epoch) and epoch != actor_epoch:
                errors.append(f"Sender epoch mismatch in message {msg_id} (expected {actor_epoch}, got {epoch})")
                
        generation = msg.get("generation")
        if not is_nonempty_string(generation):
            errors.append(f"Message {msg_id} missing or invalid generation")
        else:
            actor_generation = actors[sender].get("generation")
            if is_nonempty_string(actor_generation) and generation != actor_generation:
                errors.append(f"Sender generation mismatch in message {msg_id} (expected {actor_generation}, got {generation})")
                
        if mtype == "source":
            source_messages.add(msg_id)
            
            recipient = msg.get("recipient")
            if not is_nonempty_string(recipient):
                errors.append(f"Message {msg_id} missing or invalid recipient")
            elif recipient not in actors:
                errors.append(f"Message {msg_id} has unknown recipient: {recipient}")
            elif sender == recipient:
                errors.append(f"Source message {msg_id} has sender == recipient (self-send forbidden)")
                
            recipient_epoch = msg.get("recipient_epoch")
            if not is_true_int(recipient_epoch) or recipient_epoch <= 0:
                errors.append(f"Message {msg_id} missing or invalid recipient_epoch")
            elif is_nonempty_string(recipient) and recipient in actors:
                expected_rep_epoch = actors[recipient].get("role_epoch")
                if is_true_int(expected_rep_epoch) and recipient_epoch != expected_rep_epoch:
                    errors.append(f"Recipient epoch mismatch in message {msg_id}")
                    
            recipient_generation = msg.get("recipient_generation")
            if not is_nonempty_string(recipient_generation):
                errors.append(f"Message {msg_id} missing or invalid recipient_generation")
            elif is_nonempty_string(recipient) and recipient in actors:
                expected_rep_gen = actors[recipient].get("generation")
                if is_nonempty_string(expected_rep_gen) and recipient_generation != expected_rep_gen:
                    errors.append(f"Recipient generation mismatch in message {msg_id}")
                    
            idem_key = msg.get("idempotency_key")
            if not is_nonempty_string(idem_key):
                errors.append(f"Message {msg_id} missing or invalid idempotency_key")
                
            payload_sha256 = msg.get("payload_sha256")
            if not is_nonempty_string(payload_sha256) or not SHA256_REGEX.match(str(payload_sha256)):
                errors.append(f"Missing or bogus payload_sha256 in source message {msg_id}")
                
            payload_byte_size = msg.get("payload_byte_size")
            if not is_true_int(payload_byte_size) or payload_byte_size < 0:
                errors.append(f"Invalid payload_byte_size in source message {msg_id}")
                
            payload_content = msg.get("payload")
            if payload_content is None:
                payload_content = msg.get("body")
            if payload_content is None:
                errors.append(f"Missing payload/body content in source message {msg_id}")
            elif not isinstance(payload_content, str):
                errors.append(f"Payload/body must be a string in message {msg_id}")
            else:
                try:
                    computed_hash, computed_size = compute_sha256_and_size(payload_content)
                    if computed_hash != payload_sha256:
                        errors.append(f"Supplied payload content hash mismatch in message {msg_id}")
                    if computed_size != payload_byte_size:
                        errors.append(f"Supplied payload content size mismatch in message {msg_id}")
                except ValueError as e:
                    errors.append(f"Payload encoding error in message {msg_id}: {e}")
                    
            if is_nonempty_string(idem_key) and is_nonempty_string(recipient) and is_nonempty_string(sender):
                scoped_key = (sender, recipient, idem_key)
                sender_key = (sender, idem_key)
                
                if sender_key in sender_idem_map and sender_idem_map[sender_key] != recipient:
                    errors.append(f"Idempotency key {idem_key} reused with different recipient {recipient} (expected {sender_idem_map[sender_key]})")
                    
                if scoped_key in idempotency_map:
                    prev_msg = idempotency_map[scoped_key]
                    if prev_msg["payload_sha256"] != payload_sha256:
                        errors.append(f"Changed payload for same idempotency key in message {msg_id}")
                    if prev_msg["id"] != msg_id:
                        errors.append(f"Idempotency key reused with different message ID {msg_id} (expected {prev_msg['id']})")
                else:
                    idempotency_map[scoped_key] = {"payload_sha256": payload_sha256, "id": msg_id}
                    sender_idem_map[sender_key] = recipient
                    
        else:
            reply_to = msg.get("reply_to")
            if not is_nonempty_string(reply_to) or reply_to not in messages_by_id:
                errors.append(f"{mtype} {msg_id} missing or invalid reply_to")
                continue
                
            orig_msg = messages_by_id[reply_to]
            if orig_msg.get("type") != "source":
                errors.append(f"{mtype} {msg_id} reply_to does not point to a source message")
                continue
                
            intended_recipient = orig_msg.get("recipient")
            if is_nonempty_string(intended_recipient):
                orig_sender = orig_msg.get("sender")
                if sender == orig_sender:
                    errors.append(f"Self-ACK forbidden: reply {msg_id} sender {sender} is the original sender")
                elif sender != intended_recipient:
                    errors.append(f"Wrong recipient reply: sender {sender} is not intended recipient {intended_recipient}")
                    
                expected_device = actors.get(intended_recipient, {}).get("device_id")
                if mtype in ["transport_receipt", "handled_ack"]:
                    device_ack = msg.get("device_ack")
                    if device_ack != expected_device:
                        errors.append(f"Wrong device ACK: device {device_ack} is not enrolled device {expected_device}")
                        
            if mtype == "transport_receipt":
                transport_receipts.add(reply_to)
            elif mtype == "handled_ack":
                handled_acks.add(reply_to)
            elif mtype == "ownership_agreement":
                ownership_agreements.add(reply_to)
            elif mtype == "completed_artifact":
                completed_artifacts.add(reply_to)
                
                artifact_sha256 = msg.get("artifact_sha256")
                if not is_nonempty_string(artifact_sha256) or not SHA256_REGEX.match(str(artifact_sha256)):
                    errors.append(f"Missing or bogus artifact_sha256 in {mtype} {msg_id}")
                    
                artifact_byte_size = msg.get("artifact_byte_size")
                if not is_true_int(artifact_byte_size) or artifact_byte_size < 0:
                    errors.append(f"Invalid artifact_byte_size in {mtype} {msg_id}")
                    
                artifact_content = msg.get("artifact")
                if artifact_content is not None:
                    if not isinstance(artifact_content, str):
                        errors.append(f"Artifact content must be a string in message {msg_id}")
                    else:
                        try:
                            computed_hash, computed_size = compute_sha256_and_size(artifact_content)
                            if computed_hash != artifact_sha256:
                                errors.append(f"Supplied artifact content hash mismatch in message {msg_id}")
                            if computed_size != artifact_byte_size:
                                errors.append(f"Supplied artifact content size mismatch in message {msg_id}")
                        except ValueError as e:
                            errors.append(f"Artifact encoding error in message {msg_id}: {e}")

    presentation_claim = manifest.get("presentation_claim") if isinstance(manifest, dict) else None
    if not is_nonempty_string(presentation_claim) or presentation_claim not in ["physical_proof", "scripted_fixture"]:
        errors.append(f"Invalid or missing presentation_claim: {presentation_claim}")
        
    if presentation_claim == "physical_proof":
        is_scripted = any(a.get("is_scripted", False) for a in actors.values() if isinstance(a, dict))
        device_ids = set(a.get("device_id") for a in actors.values() if isinstance(a, dict) and is_nonempty_string(a.get("device_id")))
        if is_scripted or len(device_ids) <= 1:
            errors.append("Scripted/single-host fixtures presented as physical proof")
            
    base_flags = ["PHYSICAL_EVIDENCE_MISSING (supplied-but-unverified evidence from JSON manifest)"]
            
    if errors:
        return "INVALID", errors + base_flags
        
    missing_stages = []
    for src_id in source_messages:
        if src_id not in transport_receipts:
            missing_stages.append(f"Message {src_id} missing transport_receipt")
        if src_id not in handled_acks:
            missing_stages.append(f"Message {src_id} missing handled_ack")
        if src_id not in ownership_agreements:
            missing_stages.append(f"Message {src_id} missing ownership_agreement")
        if src_id not in completed_artifacts:
            missing_stages.append(f"Message {src_id} missing completed_artifact")
            
    if missing_stages:
        return "INCOMPLETE", missing_stages + base_flags
        
    return "CONSISTENT", base_flags

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m adapters.demo_evidence <manifest.json>")
        sys.exit(1)
        
    manifest_path = sys.argv[1]
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        status, details = validate_manifest(manifest)
    except Exception as e:
        status = "INVALID"
        details = [f"Failed to read manifest: {e}", "PHYSICAL_EVIDENCE_MISSING (supplied-but-unverified evidence from JSON manifest)"]
        
    output = {"status": status, "details": details}
    if len(sys.argv) == 3 and sys.argv[2] == "--json":
        print(json.dumps(output, indent=2))
    else:
        print(status)
        for detail in details:
            print(f"- {detail}")
        
    if status == "INVALID":
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
