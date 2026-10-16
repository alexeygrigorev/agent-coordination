import unittest
import copy
from adapters.demo_evidence import validate_manifest, compute_sha256_and_size

class TestDemoEvidenceValidator(unittest.TestCase):
    def setUp(self):
        payload_content = "test_payload"
        payload_hash, payload_size = compute_sha256_and_size(payload_content)
        
        artifact_content = "test_artifact"
        artifact_hash, artifact_size = compute_sha256_and_size(artifact_content)
        
        self.base_manifest = {
            "version": "2.0",
            "project": "proj_1",
            "task": "task_1",
            "correlation_id": "corr_1",
            "actors": {
                "actor_A": {"device_id": "dev_1", "role_epoch": 1, "generation": "gen_A", "is_scripted": False},
                "actor_B": {"device_id": "dev_2", "role_epoch": 1, "generation": "gen_B", "is_scripted": False}
            },
            "presentation_claim": "physical_proof",
            "messages": [
                {
                    "id": "msg_1",
                    "type": "source",
                    "sender": "actor_A",
                    "recipient": "actor_B",
                    "idempotency_key": "idem_1",
                    "payload": payload_content,
                    "payload_sha256": payload_hash,
                    "payload_byte_size": payload_size,
                    "epoch": 1,
                    "generation": "gen_A",
                    "recipient_epoch": 1,
                    "recipient_generation": "gen_B",
                    "project": "proj_1",
                    "task": "task_1",
                    "correlation_id": "corr_1"
                },
                {
                    "id": "ack_1",
                    "type": "transport_receipt",
                    "sender": "actor_B",
                    "device_ack": "dev_2",
                    "reply_to": "msg_1",
                    "epoch": 1,
                    "generation": "gen_B",
                    "project": "proj_1",
                    "task": "task_1",
                    "correlation_id": "corr_1"
                },
                {
                    "id": "ack_2",
                    "type": "handled_ack",
                    "sender": "actor_B",
                    "device_ack": "dev_2",
                    "reply_to": "msg_1",
                    "epoch": 1,
                    "generation": "gen_B",
                    "project": "proj_1",
                    "task": "task_1",
                    "correlation_id": "corr_1"
                },
                {
                    "id": "reply_1",
                    "type": "ownership_agreement",
                    "sender": "actor_B",
                    "reply_to": "msg_1",
                    "epoch": 1,
                    "generation": "gen_B",
                    "project": "proj_1",
                    "task": "task_1",
                    "correlation_id": "corr_1"
                },
                {
                    "id": "reply_2",
                    "type": "completed_artifact",
                    "sender": "actor_B",
                    "reply_to": "msg_1",
                    "artifact": artifact_content,
                    "artifact_sha256": artifact_hash,
                    "artifact_byte_size": artifact_size,
                    "epoch": 1,
                    "generation": "gen_B",
                    "project": "proj_1",
                    "task": "task_1",
                    "correlation_id": "corr_1"
                }
            ]
        }

    def test_valid_manifest(self):
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "CONSISTENT", f"Expected CONSISTENT, got {status} with {details}")
        self.assertTrue(any("PHYSICAL_EVIDENCE_MISSING" in d for d in details))

    # FINDING-R2-1
    def test_finding_r2_1_unknown_recipient_crash(self):
        self.base_manifest["messages"][0]["recipient"] = "actor_C"
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("unknown recipient" in d for d in details))
        
    # FINDING-R2-2
    def test_finding_r2_2_non_integer_role_epoch(self):
        self.base_manifest["actors"]["actor_A"]["role_epoch"] = "1"
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("missing or invalid role_epoch" in d for d in details))
        
    # FINDING-R2-3
    def test_finding_r2_3_inconsistent_hash_size(self):
        self.base_manifest["messages"][0]["payload_sha256"] = "a" * 64
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Supplied payload content hash mismatch" in d for d in details))
        
        self.base_manifest["messages"][0]["payload_sha256"] = compute_sha256_and_size(self.base_manifest["messages"][0]["payload"])[0]
        self.base_manifest["messages"][0]["payload_byte_size"] = 999
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Supplied payload content size mismatch" in d for d in details))

    def test_finding_r2_3_artifact_inconsistent_hash_size(self):
        self.base_manifest["messages"][4]["artifact_sha256"] = "a" * 64
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Supplied artifact content hash mismatch" in d for d in details))

    # FINDING-R2-4
    def test_finding_r2_4_four_distinct_stages(self):
        # Remove one stage to test incomplete
        self.base_manifest["messages"].pop(2) # remove handled_ack
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INCOMPLETE")
        self.assertTrue(any("missing handled_ack" in d for d in details))
        
    # FINDING-R2-5
    def test_finding_r2_5_missing_recipient(self):
        del self.base_manifest["messages"][0]["recipient"]
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("missing or invalid recipient" in d for d in details))
        
    # FINDING-R2-6
    def test_finding_r2_6_missing_recipient_epoch(self):
        del self.base_manifest["messages"][0]["recipient_epoch"]
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("missing or invalid recipient_epoch" in d for d in details))

    # Earlier Negative Categories
    def test_changed_payload_same_idempotency_key(self):
        new_payload = "changed"
        new_hash, new_size = compute_sha256_and_size(new_payload)
        new_msg = copy.deepcopy(self.base_manifest["messages"][0])
        new_msg["id"] = "msg_2"
        new_msg["payload"] = new_payload
        new_msg["payload_sha256"] = new_hash
        new_msg["payload_byte_size"] = new_size
        self.base_manifest["messages"].append(new_msg)
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Changed payload" in d for d in details))
        
    def test_wrong_device_ack(self):
        self.base_manifest["messages"][1]["device_ack"] = "dev_1" # Should be dev_2
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Wrong device ACK" in d for d in details))

    def test_wrong_recipient_reply(self):
        self.base_manifest["actors"]["actor_C"] = {"device_id": "dev_3", "role_epoch": 1, "generation": "gen_C", "is_scripted": False}
        self.base_manifest["messages"][3]["sender"] = "actor_C" # actor_B should reply
        self.base_manifest["messages"][3]["generation"] = "gen_C"
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Wrong recipient reply" in d for d in details))

    def test_missing_hashes(self):
        del self.base_manifest["messages"][0]["payload_sha256"]
        del self.base_manifest["messages"][4]["artifact_sha256"]
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Missing or bogus payload_sha256" in d for d in details))
        self.assertTrue(any("Missing or bogus artifact_sha256" in d for d in details))

    def test_stale_role_epoch(self):
        self.base_manifest["messages"][0]["epoch"] = 2 # Actor has epoch 1
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Sender epoch mismatch" in d for d in details))

    def test_scripted_single_host_presented_as_physical(self):
        self.base_manifest["actors"]["actor_B"]["is_scripted"] = True
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Scripted/single-host" in d for d in details))

    def test_missing_byte_size(self):
        del self.base_manifest["messages"][0]["payload_byte_size"]
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Invalid payload_byte_size" in d for d in details))

    # --- R3 FINDINGS TESTS ---
    def test_r3_list_recipient_crash(self):
        self.base_manifest["messages"][0]["recipient"] = ["actor_B"]
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")

    def test_r3_dict_recipient_crash(self):
        self.base_manifest["messages"][0]["recipient"] = {"name": "actor_B"}
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")

    def test_r3_list_idempotency_key_crash(self):
        self.base_manifest["messages"][0]["idempotency_key"] = ["idem_1"]
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")

    def test_r3_dict_idempotency_key_crash(self):
        self.base_manifest["messages"][0]["idempotency_key"] = {"k": "idem_1"}
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")

    def test_r3_conflicting_idempotency_changed_recipient(self):
        self.base_manifest["actors"]["actor_C"] = {"device_id": "dev_3", "role_epoch": 1, "is_scripted": False}
        new_msg = copy.deepcopy(self.base_manifest["messages"][0])
        new_msg["id"] = "msg_2"
        new_msg["recipient"] = "actor_C"
        self.base_manifest["messages"].append(new_msg)
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("reused with different recipient" in d for d in details))

    # --- R4 FINDINGS TESTS ---
    def test_r4_missing_actor_generation(self):
        del self.base_manifest["actors"]["actor_A"]["generation"]
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("missing or invalid generation" in d for d in details))

    def test_r4_missing_sender_generation(self):
        del self.base_manifest["messages"][0]["generation"]
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("missing or invalid generation" in d for d in details))

    def test_r4_missing_recipient_generation(self):
        del self.base_manifest["messages"][0]["recipient_generation"]
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("missing or invalid recipient_generation" in d for d in details))

    def test_r4_stale_sender_generation(self):
        self.base_manifest["messages"][0]["generation"] = "stale_gen"
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Sender generation mismatch" in d for d in details))

    def test_r4_stale_recipient_generation(self):
        self.base_manifest["messages"][0]["recipient_generation"] = "stale_gen"
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Recipient generation mismatch" in d for d in details))
        
    def test_r4_list_generation_crash(self):
        self.base_manifest["messages"][0]["generation"] = ["gen_A"]
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")

    def test_r4_dict_generation_crash(self):
        self.base_manifest["messages"][0]["generation"] = {"gen": "gen_A"}
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")

    def test_r4_zero_role_epoch(self):
        self.base_manifest["actors"]["actor_A"]["role_epoch"] = 0
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        
    def test_r4_negative_role_epoch(self):
        self.base_manifest["actors"]["actor_A"]["role_epoch"] = -1
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")
        
    def test_r4_zero_event_epoch(self):
        self.base_manifest["messages"][0]["epoch"] = 0
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")

    def test_r4_zero_recipient_epoch(self):
        self.base_manifest["messages"][0]["recipient_epoch"] = 0
        status, details = validate_manifest(self.base_manifest)
        self.assertEqual(status, "INVALID")

    # --- R5/R6 FINDINGS TESTS ---
    def test_r6_empty_string_payload(self):
        new_manifest = copy.deepcopy(self.base_manifest)
        new_manifest["messages"][0]["payload"] = ""
        # The correct SHA256 of empty string is e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        new_manifest["messages"][0]["payload_sha256"] = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        new_manifest["messages"][0]["payload_byte_size"] = 0
        status, details = validate_manifest(new_manifest)
        self.assertEqual(status, "CONSISTENT", f"Expected CONSISTENT, got {status} with {details}")

    def test_r6_lone_surrogate(self):
        new_manifest = copy.deepcopy(self.base_manifest)
        new_manifest["messages"][0]["payload"] = "\ud800"
        # Before fix, this would crash. Now it should fail validation.
        status, details = validate_manifest(new_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Payload encoding error" in d for d in details))
        
    def test_r6_self_ack_source(self):
        new_manifest = copy.deepcopy(self.base_manifest)
        new_manifest["messages"][0]["recipient"] = "actor_A"
        status, details = validate_manifest(new_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("self-send forbidden" in d for d in details))

    def test_r6_self_ack_reply(self):
        new_manifest = copy.deepcopy(self.base_manifest)
        new_manifest["messages"][1]["sender"] = "actor_A"
        status, details = validate_manifest(new_manifest)
        self.assertEqual(status, "INVALID")
        self.assertTrue(any("Self-ACK forbidden" in d for d in details))


    def test_r6_doc_json_smoke(self):
        import re
        import json
        import os
        doc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_docs", "demo-evidence.md")
        with open(doc_path, "r") as f:
            content = f.read()
        match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        self.assertIsNotNone(match, "Could not find JSON example in docs")
        json_content = match.group(1)
        manifest = json.loads(json_content)
        status, details = validate_manifest(manifest)
        self.assertEqual(status, "CONSISTENT", f"Doc JSON example is not CONSISTENT: {details}")


if __name__ == '__main__':
    unittest.main()
