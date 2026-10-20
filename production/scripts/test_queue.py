#!/usr/bin/env python3
"""Run with: python3 -m unittest discover -s scripts -p test_queue.py -v"""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = pathlib.Path(__file__).with_name("queue.py")
SPEC = importlib.util.spec_from_file_location("archive_queue", SCRIPT)
q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(q)


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(pathlib.Path(self.tmp.name) / "queue.sqlite")
        self.db = q.connect(self.path)
        q.init(self.db)
        q.seed(self.db, [{"id": "clip-1", "source_refs": ["data/source.json"], "status": "approved"}])

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def claim(self, stage, worker=None):
        return q.claim(self.db, worker or stage + "-worker", q.ROLES[stage])

    def finish(self, item, result):
        self.assertIsNotNone(item)
        return q.complete(self.db, item["job_id"], item["worker"], item["token"], result)

    def source(self):
        self.finish(self.claim("source_review"), {"passed": True, "source_refs": ["data/source.json"], "evidence_refs": ["reviews/source.json"]})

    def plan(self):
        self.source()
        self.finish(self.claim("key_plan"), {"artifact_refs": ["plans/clip.json"], "planned_keys": [{"id": "a", "time": 0, "pose": "contact pose"}, {"id": "b", "time": 1, "pose": "up pose"}]})

    def keys(self):
        self.plan()
        self.finish(self.claim("draw_keys", "artist"), {"artifact_refs": ["keys/a.svg", "keys/b.svg"], "key_artifacts": {"a": "keys/a.svg", "b": "keys/b.svg"}})

    def breakdowns(self):
        self.keys()
        self.finish(self.claim("key_review", "critic"), {"passed": True, "reviewed_artifact_refs": ["keys/a.svg", "keys/b.svg"], "evidence_refs": ["reviews/keys.json"]})
        self.finish(self.claim("breakdowns", "animator"), {"artifact_refs": ["motion/clip.webm", "motion/frames.json"], "playback_ref": "motion/clip.webm"})

    def test_seed_is_unreviewed_idempotent_and_atomic(self):
        self.assertEqual(q.status(self.db)["candidates"][0]["state"], "candidate")
        self.assertEqual(q.seed(self.db, {"candidates": [{"id": "clip-1"}]})["created"], 0)
        with self.assertRaises(ValueError):
            q.seed(self.db, [{"id": "new"}, {}])
        self.assertEqual(self.db.execute("SELECT count(*) FROM candidates").fetchone()[0], 1)
        self.assertIsNone(self.claim("publish_ready"))

    def test_real_process_concurrency_has_one_winner(self):
        # Distinct processes and SQLite connections compete for a single ready job.
        workers = [subprocess.Popen([sys.executable, str(SCRIPT), "claim", "--db", self.path, "--worker", "process-" + str(i), "--role", "source_reviewer"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(8)]
        items = []
        for process in workers:
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, stderr)
            items.append(json.loads(stdout)["work_item"])
        self.assertEqual(sum(item is not None for item in items), 1)
        self.assertEqual(self.db.execute("SELECT attempts FROM jobs WHERE stage='source_review'").fetchone()[0], 1)

    def test_lease_expiry_recovery_and_stale_token(self):
        old = self.claim("source_review", "worker")
        self.db.execute("UPDATE jobs SET lease_until=? WHERE id=?", (time.time() - 1, old["job_id"]))
        new = self.claim("source_review", "worker")
        self.assertNotEqual(new["token"], old["token"])
        with self.assertRaisesRegex(ValueError, "stale"):
            self.finish(old, {"passed": True, "source_refs": ["s"], "evidence_refs": ["r"]})
        self.finish(new, {"passed": True, "source_refs": ["s"], "evidence_refs": ["r"]})

    def test_expired_lease_cannot_complete_even_before_reclaimed(self):
        item = self.claim("source_review")
        with self.assertRaisesRegex(ValueError, "expired"):
            q.complete(self.db, item["job_id"], item["worker"], item["token"], {}, now=item["lease_until"])

    def test_self_review_refused_for_keys_and_motion(self):
        self.keys()
        self.assertIsNone(self.claim("key_review", "artist"))
        self.assertIsNone(self.claim("key_review", "key_plan-worker"))
        self.finish(self.claim("key_review", "critic"), {"passed": True, "reviewed_artifact_refs": ["keys/a.svg", "keys/b.svg"], "evidence_refs": ["review"]})
        self.finish(self.claim("breakdowns", "animator"), {"artifact_refs": ["motion.webm"], "playback_ref": "motion.webm"})
        for worker in ("artist", "animator", "key_plan-worker"):
            self.assertIsNone(self.claim("motion_review", worker))
        self.assertIsNotNone(self.claim("motion_review", "fresh-critic"))

    def test_no_still_only_motion_pass_and_no_early_publish(self):
        self.breakdowns()
        self.assertIsNone(self.claim("publish_ready"))
        item = self.claim("motion_review")
        result = {"passed": True, "reviewed_artifact_refs": ["motion/clip.webm", "motion/frames.json"], "evidence_refs": ["contact-sheet.png"]}
        with self.assertRaisesRegex(ValueError, "playback"):
            self.finish(item, result)
        self.assertIsNone(self.claim("publish_ready"))
        result.update(playback_inspected=True, playback_ref="motion/clip.webm", evidence_refs=["reviews/playback-observations.json"])
        self.finish(item, result)
        pub = self.claim("publish_ready")
        with self.assertRaisesRegex(ValueError, "source_refs"):
            self.finish(pub, {"artifact_refs": ["motion/clip.webm", "motion/frames.json"]})
        self.assertEqual(self.finish(pub, {"artifact_refs": ["motion/clip.webm", "motion/frames.json"], "source_refs": ["data/source.json"]})["state"], "publish_ready")
        self.assertEqual(q.status(self.db)["candidates"][0]["state"], "publish_ready")

    def test_failed_key_review_repairs_and_invalidates_downstream(self):
        self.keys()
        outcome = self.finish(self.claim("key_review", "critic"), {"passed": False, "issues": ["pose b loses source beak"], "evidence_refs": ["reviews/keys-fail.json"]})
        self.assertEqual(outcome["next_stage"], "draw_keys")
        repair = self.claim("draw_keys", "artist-2")
        self.assertIn("pose b loses", repair["input"]["repair_feedback"])
        self.assertIn("keys/b.svg", repair["input"]["repair_feedback"])
        self.assertNotIn("draw_keys", repair["input"]["prior_results"])
        self.assertIsNone(self.claim("breakdowns"))
        self.finish(repair, {"artifact_refs": ["keys/a2.svg", "keys/b2.svg"], "key_artifacts": {"a": "keys/a2.svg", "b": "keys/b2.svg"}})
        self.assertIsNone(self.claim("key_review", "artist"))
        self.assertIsNone(self.claim("key_review", "artist-2"))
        self.assertIsNotNone(self.claim("key_review", "critic-2"))

    def test_repair_budget_exhausts_without_approval(self):
        self.db.execute("UPDATE candidates SET max_repairs=0")
        self.keys()
        result = self.finish(self.claim("key_review"), {"passed": False, "issues": ["identity drift"], "evidence_refs": ["review"]})
        self.assertEqual(result["state"], "exhausted")
        self.assertIsNone(self.claim("draw_keys"))
        self.assertIsNone(self.claim("publish_ready"))

    def test_expired_attempt_budget_exhausts(self):
        self.db.execute("UPDATE candidates SET max_attempts=1")
        item = self.claim("source_review")
        self.db.execute("UPDATE jobs SET lease_until=0 WHERE id=?", (item["job_id"],))
        self.assertIsNone(self.claim("source_review"))
        self.assertEqual(q.status(self.db)["candidates"][0]["state"], "exhausted")

    def test_requeue_requires_current_token_and_bounded_attempts(self):
        self.db.execute("UPDATE candidates SET max_attempts=1")
        item = self.claim("source_review")
        with self.assertRaises(ValueError):
            q.requeue(self.db, item["job_id"], item["worker"], "wrong", "tool unavailable")
        self.assertEqual(q.requeue(self.db, item["job_id"], item["worker"], item["token"], "tool unavailable")["state"], "exhausted")

    def test_source_failure_is_rejection(self):
        result = self.finish(self.claim("source_review"), {"passed": False, "issues": ["source identity unverifiable"], "evidence_refs": ["source-review"]})
        self.assertEqual(result["state"], "rejected")
        self.assertIsNone(self.claim("key_plan"))

    def test_source_builder_cannot_self_review(self):
        self.db.execute("UPDATE candidates SET metadata=?", (json.dumps({"id": "clip-1", "source_builder": "source-author"}),))
        self.assertIsNone(self.claim("source_review", "source-author"))
        self.assertIsNotNone(self.claim("source_review", "source-critic"))

    def test_motion_failure_repairs_then_requires_current_playback(self):
        self.breakdowns()
        old_review = self.claim("motion_review", "motion-critic")
        outcome = self.finish(old_review, {"passed": False, "issues": ["foot slides at 0.5 seconds"], "evidence_refs": ["reviews/motion-fail.json"]})
        self.assertEqual(outcome["next_stage"], "breakdowns")
        self.assertIsNone(self.claim("publish_ready"))
        repaired = self.claim("breakdowns", "animator-2")
        self.assertIn("motion/clip.webm", repaired["input"]["repair_feedback"])
        self.finish(repaired, {"artifact_refs": ["motion/clip-v2.webm"], "playback_ref": "motion/clip-v2.webm"})
        self.assertIsNone(self.claim("motion_review", "animator"))
        self.assertIsNone(self.claim("motion_review", "animator-2"))
        review = self.claim("motion_review", "motion-critic-2")
        result = {"passed": True, "playback_inspected": True, "playback_ref": "motion/clip.webm", "reviewed_artifact_refs": ["motion/clip-v2.webm"], "evidence_refs": ["reviews/v2.json"]}
        with self.assertRaisesRegex(ValueError, "current playback_ref"):
            self.finish(review, result)
        result["playback_ref"] = "motion/clip-v2.webm"
        self.finish(review, result)
        self.assertIsNotNone(self.claim("publish_ready"))

    def test_key_map_and_artifact_coverage_required(self):
        self.plan()
        item = self.claim("draw_keys")
        with self.assertRaisesRegex(ValueError, "key_artifacts"):
            self.finish(item, {"artifact_refs": ["one.svg"]})
        with self.assertRaisesRegex(ValueError, "key_artifacts"):
            self.finish(item, {"artifact_refs": ["one.svg", "two.svg"], "key_artifacts": {"a": [], "b": "two.svg"}})
        self.finish(item, {"artifact_refs": ["one.svg", "two.svg"], "key_artifacts": {"a": "one.svg", "b": "two.svg"}})
        reviewer = self.claim("key_review")
        with self.assertRaisesRegex(ValueError, "every current"):
            self.finish(reviewer, {"passed": True, "reviewed_artifact_refs": ["one.svg"], "evidence_refs": ["review"]})


if __name__ == "__main__":
    unittest.main()
