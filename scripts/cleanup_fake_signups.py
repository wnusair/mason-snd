#!/usr/bin/env python3
"""
Safely clean up fake Tournament_Signups that were auto-created when tournaments
were added (or otherwise exist) but where the user never actually completed the
signup form (no Form_Responses).

Usage:
  python scripts/cleanup_fake_signups.py --tournament-id 2        # dry-run
  python scripts/cleanup_fake_signups.py --tournament-id 2 --apply --yes  # delete
  python scripts/cleanup_fake_signups.py --all --apply --yes    # apply to all tournaments

Safety:
  - Default mode is dry-run. No data is modified unless `--apply` is supplied.
  - For destructive operations, you must also supply `--yes` (or set both
    flags) to avoid accidental deletions (especially on production DB).
  - The script prints a summary before performing deletions.

Behavior:
  For each selected tournament, this script will delete all `Tournament_Signups`
  rows where the user does NOT have any `Form_Responses` for that tournament.
  It will also remove related `Tournament_Judges` rows referencing deleted users
  for the same tournament.
"""

import argparse
import os
import sys
from pprint import pprint

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.tournaments import Tournament, Tournament_Signups, Form_Responses, Tournament_Judges
from mason_snd.models.auth import User


def parse_args():
    p = argparse.ArgumentParser(description="Cleanup fake tournament signups")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--tournament-id', type=int, help='Tournament ID to process')
    group.add_argument('--all', action='store_true', help='Process all tournaments')

    p.add_argument('--apply', action='store_true', help='Actually perform deletions (default is dry-run)')
    p.add_argument('--yes', action='store_true', help='Skip confirmation prompt (required with --apply)')
    p.add_argument('--sample', type=int, default=10, help='Number of sample deleted users to display')
    return p.parse_args()


def warn_and_check_prod(app, apply_flag):
    # Try to detect if the app is using the instance DB file (likely production)
    uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
    if 'instance/db.sqlite3' in uri or 'instance/db' in uri or os.path.exists(os.path.join(app.root_path, 'instance', 'db.sqlite3')):
        print('\n⚠️  PRODUCTION DATABASE IDENTIFIED: instance/db.sqlite3')
        if apply_flag:
            print('You passed --apply; destructive operations will modify the database.')
        else:
            print('Dry-run mode: no data will be modified.')


def main():
    args = parse_args()
    app = create_app()

    warn_and_check_prod(app, args.apply)

    with app.app_context():
        # Determine tournaments to process
        if args.all:
            tournaments = Tournament.query.order_by(Tournament.id).all()
        else:
            t = Tournament.query.get(args.tournament_id)
            if not t:
                print(f"Tournament id {args.tournament_id} not found")
                sys.exit(2)
            tournaments = [t]

        overall = []

        for tournament in tournaments:
            tid = tournament.id
            # Get users who submitted form responses for this tournament
            user_rows = db.session.query(Form_Responses.user_id).filter_by(tournament_id=tid).distinct().all()
            user_ids_with_responses = [r[0] for r in user_rows]

            # Find signups where user NOT in user_ids_with_responses
            if user_ids_with_responses:
                signups_to_delete = Tournament_Signups.query.filter(
                    Tournament_Signups.tournament_id == tid,
                    ~Tournament_Signups.user_id.in_(user_ids_with_responses)
                ).all()
            else:
                # No form responses at all -> delete all signups for tournament
                signups_to_delete = Tournament_Signups.query.filter_by(tournament_id=tid).all()

            delete_user_ids = sorted(list({s.user_id for s in signups_to_delete if s.user_id is not None}))

            overall.append({
                'tournament_id': tid,
                'tournament_name': tournament.name,
                'total_signups': Tournament_Signups.query.filter_by(tournament_id=tid).count(),
                'users_with_responses': len(user_ids_with_responses),
                'signups_to_delete_count': len(signups_to_delete),
                'sample_delete_user_ids': delete_user_ids[:args.sample],
            })

        # Print summary
        print('\nSUMMARY:')
        pprint(overall)

        if not args.apply:
            print('\nDry-run mode: no changes were made. To delete the signups, re-run with --apply --yes')
            return

        # Require --yes to proceed
        if not args.yes:
            print('\nTo prevent accidental data loss, pass --yes to confirm deletions.')
            return

        # Proceed with deletions
        print('\nProceeding to delete signups...')
        total_deleted = 0
        for entry in overall:
            tid = entry['tournament_id']
            # recompute signups query to perform delete
            user_rows = db.session.query(Form_Responses.user_id).filter_by(tournament_id=tid).distinct().all()
            user_ids_with_responses = [r[0] for r in user_rows]

            if user_ids_with_responses:
                # delete signups where user not in responses
                q = Tournament_Signups.__table__.delete().where(
                    (Tournament_Signups.__table__.c.tournament_id == tid) &
                    (~Tournament_Signups.__table__.c.user_id.in_(user_ids_with_responses))
                )
                res = db.session.execute(q)
                deleted = res.rowcount if hasattr(res, 'rowcount') else 0
            else:
                # delete all signups for tournament
                q = Tournament_Signups.__table__.delete().where(Tournament_Signups.__table__.c.tournament_id == tid)
                res = db.session.execute(q)
                deleted = res.rowcount if hasattr(res, 'rowcount') else 0

            total_deleted += deleted

            # Also delete Tournament_Judges rows referencing deleted users for this tournament
            # Find deleted user ids (approximate by recalculating leftover signups)
            # Simpler: delete Tournament_Judges where tournament_id == tid AND (child_id NOT IN users_with_responses OR judge_id NOT IN users_with_responses)
            if user_ids_with_responses:
                tj_q = Tournament_Judges.__table__.delete().where(
                    (Tournament_Judges.__table__.c.tournament_id == tid) & (
                        (~Tournament_Judges.__table__.c.child_id.in_(user_ids_with_responses)) | (~Tournament_Judges.__table__.c.judge_id.in_(user_ids_with_responses))
                    )
                )
            else:
                tj_q = Tournament_Judges.__table__.delete().where(Tournament_Judges.__table__.c.tournament_id == tid)

            db.session.execute(tj_q)

        db.session.commit()
        print(f"\nDone. Total Tournament_Signups rows deleted (approx): {total_deleted}")


if __name__ == '__main__':
    main()
