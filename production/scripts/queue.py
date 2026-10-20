#!/usr/bin/env python3
"""Local, stdlib-only work queue. A lease is work to do, never proof of activity."""
import argparse
import contextlib
import json
import math
import sqlite3
import sys
import time
import uuid

STAGES = ("source_review", "key_plan", "draw_keys", "key_review", "breakdowns", "motion_review", "publish_ready")
ROLES = dict(zip(STAGES, ("source_reviewer", "key_planner", "key_artist", "key_reviewer", "breakdown_artist", "motion_reviewer", "publisher")))
REVIEWS = {"source_review", "key_review", "motion_review"}
REPAIR = {"key_review": "draw_keys", "motion_review": "breakdowns"}
CONTRACTS = {
    "source_review": "Inspect source identity, provenance, recognizability and suitability. Return passed, source_refs and evidence_refs; list concrete issues on failure. Candidate selection is not approval.",
    "key_plan": "Read approved source. Return planned_keys (at least two concrete poses with id, time and pose) and artifact_refs for the plan. Preserve source identity and define motion/contact/occlusion acceptance criteria.",
    "draw_keys": "Create the planned distinct key drawings. Return artifact_refs and key_artifacts mapping each planned key id to its drawing reference. No interpolation-only substitute. Do not review your own work.",
    "key_review": "Use fresh critic context. Inspect every key against source and plan; return passed, reviewed_artifact_refs, evidence_refs and actionable issues on failure. Still approval does not approve motion.",
    "breakdowns": "Read approved keys. Create breakdowns and an actual playable motion artifact. Return artifact_refs and playback_ref included in artifact_refs. Check timing, arcs, contacts and silhouette.",
    "motion_review": "Use fresh critic context. Play the breakdown artifact and inspect temporal coherence, identity, timing, contacts and occlusion. Return passed, playback_inspected true, playback_ref, reviewed_artifact_refs and evidence_refs. Still/contact-sheet inspection alone cannot pass.",
    "publish_ready": "Audit the independent motion-review result and source/artifact/evidence references. Mark ready only; this queue never uploads or publishes. Return artifact_refs and source_refs.",
}


def connect(path):
    db = sqlite3.connect(path, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=30000")
    return db


@contextlib.contextmanager
def transaction(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


def init(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS candidates (
      id TEXT PRIMARY KEY, metadata TEXT NOT NULL, source_refs TEXT NOT NULL,
      state TEXT NOT NULL DEFAULT 'candidate', max_attempts INTEGER NOT NULL,
      max_repairs INTEGER NOT NULL, repairs INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS jobs (
      id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL REFERENCES candidates(id),
      stage TEXT NOT NULL, position INTEGER NOT NULL, role TEXT NOT NULL,
      state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
      worker TEXT, token TEXT, lease_until REAL, result TEXT, completed_by TEXT,
      last_error TEXT, UNIQUE(candidate_id, stage));
    CREATE TABLE IF NOT EXISTS events (
      seq INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
      job_id TEXT, worker TEXT, kind TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS jobs_claim ON jobs(role,state,position);
    """)


def event(db, job, worker, kind, payload):
    db.execute("INSERT INTO events(at,job_id,worker,kind,payload) VALUES(?,?,?,?,?)",
               (time.time(), job, worker, kind, json.dumps(payload, sort_keys=True)))


def refs(value, name):
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(name + " must be a nonempty list of reference strings")
    return value


def seed(db, manifest, max_attempts=3, max_repairs=2):
    if max_attempts < 1 or max_repairs < 0:
        raise ValueError("max_attempts >= 1 and max_repairs >= 0 required")
    entries = manifest
    if isinstance(manifest, dict):
        entries = next((manifest[k] for k in ("candidates", "jobs", "items") if k in manifest), None)
    if not isinstance(entries, list):
        raise ValueError("manifest must be a list or an object containing candidates, jobs or items")
    created = 0
    with transaction(db):
        for item in entries:
            if not isinstance(item, dict):
                raise ValueError("each candidate must be an object")
            cid = next((str(item[k]) for k in ("clip_id", "candidate_id", "id") if item.get(k) is not None), None)
            if not cid or not cid.strip():
                raise ValueError("candidate needs clip_id, candidate_id or id")
            source_refs = item.get("source_refs", [])
            if isinstance(source_refs, str):
                source_refs = [source_refs]
            if not source_refs:
                source_refs = [item[k] for k in ("source_ref", "source_url", "provenance_ref") if isinstance(item.get(k), str) and item[k]]
            if source_refs:
                refs(source_refs, "source_refs")
            if db.execute("SELECT 1 FROM candidates WHERE id=?", (cid,)).fetchone():
                continue  # Reseeding never overwrites work or grants approval.
            db.execute("INSERT INTO candidates(id,metadata,source_refs,max_attempts,max_repairs) VALUES(?,?,?,?,?)",
                       (cid, json.dumps(item), json.dumps(source_refs), max_attempts, max_repairs))
            for pos, stage in enumerate(STAGES):
                db.execute("INSERT INTO jobs(id,candidate_id,stage,position,role,state) VALUES(?,?,?,?,?,?)",
                           (cid + ":" + stage, cid, stage, pos, ROLES[stage], "pending" if pos == 0 else "blocked"))
            created += 1
        event(db, None, None, "seed", {"created": created})
    return {"created": created, "candidate_status": "unreviewed", "workers_running": "unknown"}


def expire(db, now):
    expired = db.execute("SELECT j.*,c.max_attempts FROM jobs j JOIN candidates c ON c.id=j.candidate_id WHERE j.state='leased' AND j.lease_until<=?", (now,)).fetchall()
    for row in expired:
        state = "exhausted" if row["attempts"] >= row["max_attempts"] else "pending"
        db.execute("UPDATE jobs SET state=?,worker=NULL,token=NULL,lease_until=NULL,last_error='lease expired' WHERE id=?", (state, row["id"]))
        if state == "exhausted":
            db.execute("UPDATE candidates SET state='exhausted' WHERE id=?", (row["candidate_id"],))
        event(db, row["id"], row["worker"], "lease_expired", {"state": state})


def prior_results(db, cid):
    return {r["stage"]: {"completed_by": r["completed_by"], "result": json.loads(r["result"])}
            for r in db.execute("SELECT * FROM jobs WHERE candidate_id=? AND state='done' AND result IS NOT NULL ORDER BY position", (cid,))}


def forbidden_reviewers(db, row):
    stages = {"key_review": ("key_plan", "draw_keys"), "motion_review": ("key_plan", "draw_keys", "breakdowns")}.get(row["stage"], ())
    workers = set()
    # Include previous attempts: a worker cannot erase authorship by repairing/reseeding.
    for history in db.execute("SELECT payload FROM events WHERE kind='completed' AND job_id IN (SELECT id FROM jobs WHERE candidate_id=?)", (row["candidate_id"],)):
        data = json.loads(history["payload"])
        if data.get("stage") in stages:
            workers.add(data["worker"])
    if row["stage"] == "source_review":
        meta = json.loads(db.execute("SELECT metadata FROM candidates WHERE id=?", (row["candidate_id"],)).fetchone()[0])
        workers.update(str(meta[k]) for k in ("source_builder", "source_worker") if meta.get(k))
    return workers


def work_item(db, row):
    c = db.execute("SELECT * FROM candidates WHERE id=?", (row["candidate_id"],)).fetchone()
    prior = prior_results(db, row["candidate_id"])
    source_refs = json.loads(c["source_refs"])
    if "source_review" in prior:
        source_refs = prior["source_review"]["result"]["source_refs"]
    return {"schema_version": 1, "job_id": row["id"], "candidate_id": row["candidate_id"],
            "stage": row["stage"], "role": row["role"], "worker": row["worker"], "token": row["token"],
            "lease_until": row["lease_until"], "attempt": row["attempts"],
            "budget": {"max_attempts": c["max_attempts"], "repairs": c["repairs"], "max_repairs": c["max_repairs"]},
            "input": {"candidate": json.loads(c["metadata"]), "source_refs": source_refs, "prior_results": prior,
                      "repair_feedback": row["last_error"]},
            "acceptance_contract": CONTRACTS[row["stage"]],
            "evidence_contract": "References must identify real inspectable artifacts. Report checks actually performed. Failed reviews require actionable issues. Never infer approval from candidate metadata.",
            "worker_instruction": "One bounded work item per claim. Stop before lease expiry; external supervisor may requeue. Use a fresh reviewer context and distinct worker identity, with no author instructions except artifacts and acceptance criteria. No remote calls are made by this queue."}


def claim(db, worker, role, lease_seconds=300, now=None):
    if role not in ROLES.values():
        raise ValueError("unknown role; expected " + ", ".join(ROLES.values()))
    if not worker.strip() or not 1 <= lease_seconds <= 3600:
        raise ValueError("worker required; lease_seconds must be between 1 and 3600")
    now = time.time() if now is None else now
    with transaction(db):
        expire(db, now)
        rows = db.execute("SELECT j.* FROM jobs j JOIN candidates c ON c.id=j.candidate_id WHERE j.role=? AND j.state='pending' AND c.state NOT IN ('exhausted','rejected','publish_ready') AND j.attempts<c.max_attempts ORDER BY j.position,j.candidate_id", (role,)).fetchall()
        for row in rows:
            if worker in forbidden_reviewers(db, row):
                continue
            token = uuid.uuid4().hex
            db.execute("UPDATE jobs SET state='leased',worker=?,token=?,lease_until=?,attempts=attempts+1 WHERE id=?",
                       (worker, token, now + lease_seconds, row["id"]))
            event(db, row["id"], worker, "claimed", {"role": role, "lease_until": now + lease_seconds})
            return work_item(db, db.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())
    return None


def owned(db, job, worker, token, now):
    row = db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
    if not row or row["state"] != "leased" or row["worker"] != worker or row["token"] != token or row["lease_until"] <= now:
        raise ValueError("invalid, stale or expired lease; claim again")
    if worker in forbidden_reviewers(db, row):
        raise ValueError("authors cannot review their own work")
    return row


def validate_result(db, row, result):
    if not isinstance(result, dict):
        raise ValueError("result must be a JSON object")
    stage = row["stage"]
    prior = prior_results(db, row["candidate_id"])
    if stage not in REVIEWS and result.get("passed") is False:
        raise ValueError("non-review failure cannot complete a stage; requeue with a reason")
    if stage in REVIEWS:
        if type(result.get("passed")) is not bool:
            raise ValueError("review result requires boolean passed")
        refs(result.get("evidence_refs"), "evidence_refs")
        if not result["passed"]:
            refs(result.get("issues"), "issues")
            return
    if stage == "source_review":
        refs(result.get("source_refs"), "source_refs")
    elif stage == "key_plan":
        refs(result.get("artifact_refs"), "artifact_refs")
        keys = result.get("planned_keys")
        if not isinstance(keys, list) or len(keys) < 2:
            raise ValueError("planned_keys requires at least two key poses")
        for key in keys:
            if not isinstance(key, dict) or not isinstance(key.get("id"), str) or not key["id"].strip() or type(key.get("time")) not in (int, float) or not math.isfinite(key["time"]) or not isinstance(key.get("pose"), str) or not key["pose"].strip():
                raise ValueError("each planned key requires id, numeric time and concrete pose")
        if len({key["id"] for key in keys}) != len(keys):
            raise ValueError("planned key ids must be unique")
    elif stage == "draw_keys":
        artifacts = refs(result.get("artifact_refs"), "artifact_refs")
        mapping = result.get("key_artifacts", {})
        planned_ids = {k["id"] for k in prior["key_plan"]["result"]["planned_keys"]}
        if not isinstance(mapping, dict) or set(mapping) != planned_ids or any(not isinstance(value, str) or value not in artifacts for value in mapping.values()):
            raise ValueError("key_artifacts must map every planned key id to an artifact_ref")
        if len(set(mapping.values())) < 2:
            raise ValueError("distinct planned keys require distinct artifact references")
    elif stage == "breakdowns":
        artifacts = refs(result.get("artifact_refs"), "artifact_refs")
        if result.get("playback_ref") not in artifacts:
            raise ValueError("playback_ref must identify a returned motion artifact")
    elif stage in ("key_review", "motion_review"):
        target = "draw_keys" if stage == "key_review" else "breakdowns"
        reviewed = refs(result.get("reviewed_artifact_refs"), "reviewed_artifact_refs")
        expected = prior[target]["result"]["artifact_refs"]
        if not set(expected).issubset(reviewed):
            raise ValueError("review must inspect every current target artifact")
        if stage == "motion_review":
            if result.get("playback_inspected") is not True or result.get("playback_ref") != prior[target]["result"]["playback_ref"]:
                raise ValueError("motion pass requires playback_inspected true and the current playback_ref")
    elif stage == "publish_ready":
        motion = prior.get("motion_review", {})
        review = motion.get("result", {})
        if review.get("passed") is not True or review.get("playback_inspected") is not True:
            raise ValueError("independent playback motion review required")
        builders = {prior[s]["completed_by"] for s in ("key_plan", "draw_keys", "breakdowns")}
        if motion.get("completed_by") in builders:
            raise ValueError("independent motion reviewer required")
        artifacts = refs(result.get("artifact_refs"), "artifact_refs")
        sources = refs(result.get("source_refs"), "source_refs")
        if not set(prior["breakdowns"]["result"]["artifact_refs"]).issubset(artifacts) or not set(prior["source_review"]["result"]["source_refs"]).issubset(sources):
            raise ValueError("publish_ready must preserve approved source and motion artifact references")


def complete(db, job, worker, token, result, now=None):
    now = time.time() if now is None else now
    with transaction(db):
        row = owned(db, job, worker, token, now)
        validate_result(db, row, result)
        stage, cid = row["stage"], row["candidate_id"]
        event(db, job, worker, "completed", {"stage": stage, "worker": worker, "result": result})
        db.execute("UPDATE jobs SET state='done',result=?,completed_by=?,worker=NULL,token=NULL,lease_until=NULL WHERE id=?", (json.dumps(result), worker, job))
        if stage in REVIEWS and result["passed"] is False:
            c = db.execute("SELECT * FROM candidates WHERE id=?", (cid,)).fetchone()
            repair_stage = REPAIR.get(stage)
            target = db.execute("SELECT * FROM jobs WHERE candidate_id=? AND stage=?", (cid, repair_stage)).fetchone() if repair_stage else None
            if not target or c["repairs"] >= c["max_repairs"] or target["attempts"] >= c["max_attempts"] or row["attempts"] >= c["max_attempts"]:
                state = "rejected" if stage == "source_review" else "exhausted"
                db.execute("UPDATE candidates SET state=? WHERE id=?", (state, cid))
                return {"job_id": job, "state": state, "issues": result["issues"]}
            db.execute("UPDATE candidates SET repairs=repairs+1,state='repair_required' WHERE id=?", (cid,))
            feedback = {"review": result, "superseded_results": {s: v for s, v in prior_results(db, cid).items() if STAGES.index(s) >= target["position"]}}
            db.execute("UPDATE jobs SET state='blocked',result=NULL,completed_by=NULL,worker=NULL,token=NULL,lease_until=NULL,last_error=? WHERE candidate_id=? AND position>=?", (json.dumps(feedback), cid, target["position"]))
            db.execute("UPDATE jobs SET state='pending' WHERE id=?", (target["id"],))
            return {"job_id": job, "state": "repair_required", "next_stage": repair_stage}
        if stage == "publish_ready":
            db.execute("UPDATE candidates SET state='publish_ready' WHERE id=?", (cid,))
            return {"job_id": job, "state": "publish_ready", "published": False}
        next_stage = STAGES[row["position"] + 1]
        db.execute("UPDATE jobs SET state='pending' WHERE candidate_id=? AND stage=?", (cid, next_stage))
        db.execute("UPDATE candidates SET state='in_progress' WHERE id=?", (cid,))
        return {"job_id": job, "state": "done", "next_stage": next_stage}


def requeue(db, job, worker, token, reason):
    if not reason.strip():
        raise ValueError("reason is required")
    with transaction(db):
        row = owned(db, job, worker, token, time.time())
        limit = db.execute("SELECT max_attempts FROM candidates WHERE id=?", (row["candidate_id"],)).fetchone()[0]
        state = "exhausted" if row["attempts"] >= limit else "pending"
        db.execute("UPDATE jobs SET state=?,worker=NULL,token=NULL,lease_until=NULL,last_error=? WHERE id=?", (state, reason, job))
        if state == "exhausted":
            db.execute("UPDATE candidates SET state='exhausted' WHERE id=?", (row["candidate_id"],))
        event(db, job, worker, "requeued", {"reason": reason, "state": state})
        return {"job_id": job, "state": state}


def status(db):
    with transaction(db):
        expire(db, time.time())
        return {"workers_running": "unknown", "note": "Leases indicate claims, not verified worker activity; publish_ready is not published.",
                "candidates": [dict(r) for r in db.execute("SELECT id,state,repairs,max_repairs,max_attempts FROM candidates ORDER BY id")],
                "counts": [dict(r) for r in db.execute("SELECT stage,state,count(*) AS count FROM jobs GROUP BY stage,state ORDER BY min(position),state")],
                "leases": [dict(r) for r in db.execute("SELECT id,stage,worker,lease_until FROM jobs WHERE state='leased' ORDER BY id")]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "seed", "claim", "complete", "requeue", "status"):
        sub = commands.add_parser(name)
        sub.add_argument("--db", required=True)
        if name == "seed":
            sub.add_argument("--manifest", required=True, help="path to JSON manifest")
            sub.add_argument("--max-attempts", type=int, default=3)
            sub.add_argument("--max-repairs", type=int, default=2)
        if name in ("claim", "complete", "requeue"):
            sub.add_argument("--worker", required=True)
        if name == "claim":
            sub.add_argument("--role", required=True, choices=tuple(ROLES.values()))
            sub.add_argument("--lease-seconds", type=int, default=300)
        if name in ("complete", "requeue"):
            sub.add_argument("--job", required=True)
            sub.add_argument("--token", required=True)
        if name == "complete":
            sub.add_argument("--result", required=True, help="JSON object, or @path to JSON file")
        if name == "requeue":
            sub.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    db = connect(args.db)
    try:
        init(db)
        if args.command == "init":
            output = {"initialized": True}
        elif args.command == "seed":
            with open(args.manifest, encoding="utf-8") as handle:
                output = seed(db, json.load(handle), args.max_attempts, args.max_repairs)
        elif args.command == "claim":
            output = {"work_item": claim(db, args.worker, args.role, args.lease_seconds)}
        elif args.command == "complete":
            if args.result.startswith("@"):
                with open(args.result[1:], encoding="utf-8") as handle:
                    result = json.load(handle)
            else:
                result = json.loads(args.result)
            output = complete(db, args.job, args.worker, args.token, result)
        elif args.command == "requeue":
            output = requeue(db, args.job, args.worker, args.token, args.reason)
        else:
            output = status(db)
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
