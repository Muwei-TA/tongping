"""Operator-only club provisioning; not an unauthenticated admin HTTP API."""
import argparse
from .db import initialize, closing_connection, transaction
from .errors import audit, new_id, require


def create_club(db, owner_id, name, summary, rules):
    with transaction(db):
        require(db.execute("SELECT 1 FROM users WHERE id=?", (owner_id,)).fetchone() is not None,
                404, "OWNER_NOT_FOUND", "Owner must first sign in using the mini-program")
        cid = new_id()
        db.execute("INSERT INTO clubs VALUES(?,?,?,?,?)", (cid, name, summary, rules, owner_id))
        db.execute("INSERT INTO memberships VALUES(?,?,'active','Operator provisioned')", (cid, owner_id))
        audit(db, cid, owner_id, "club.provision", cid)
        return cid


def main():
    parser = argparse.ArgumentParser(description="Provision one real club after verifying the owner")
    parser.add_argument("--db", required=True)
    parser.add_argument("--owner", required=True, help="Internal id returned by GET /api/v1/me")
    parser.add_argument("--name", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--rules", required=True)
    args = parser.parse_args()
    if not all(value.strip() for value in (args.name, args.summary, args.rules)):
        parser.error("Club fields must not be blank")
    initialize(args.db)
    with closing_connection(args.db) as db:
        print(create_club(db, args.owner, args.name, args.summary, args.rules))


if __name__ == "__main__":
    main()
