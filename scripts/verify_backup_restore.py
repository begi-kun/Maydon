"""Read-only Railway snapshot backup; restore only into a fresh local cluster.

Requires psycopg, Railway CLI, and matching PostgreSQL binaries. Source credentials
stay inside Railway. The private archive contains customer data: never commit it.
"""
import argparse
import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time
from datetime import datetime, timezone

import psycopg
from PIL import Image
from psycopg import sql


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, timeout=kwargs.pop('timeout', 180), **kwargs)
    if result.returncode:
        # Never echo stderr from credential-bearing commands or SQL data.
        raise RuntimeError(f'{Path(command[0]).name} failed (exit {result.returncode}); private command output suppressed')
    return result.stdout


def fingerprint(conn):
    result = {}
    conn.execute("SET TIME ZONE 'UTC'")
    conn.execute("SET extra_float_digits = 3")
    conn.execute("SET bytea_output = 'hex'")
    for schema, table in conn.execute("SELECT schemaname,tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall():
        count, digest = conn.execute(sql.SQL("SELECT count(*), md5(coalesce(string_agg(md5(to_jsonb(t)::text), '' ORDER BY md5(to_jsonb(t)::text)), '')) FROM {}.{} t").format(sql.Identifier(schema), sql.Identifier(table))).fetchone()
        result[table] = {'rows': count, 'digest': digest}
    return result


def snapshot_command():
    # psql exports one REPEATABLE READ snapshot. pg_dump imports that snapshot,
    # then table fingerprints are evaluated before that source transaction ends.
    return r"""set -eu
umask 077
task_dir=$(mktemp -d /tmp/maydon-recovery.XXXXXX)
trap 'rm -f "$task_dir/backup.dump" "$task_dir/manifest.jsonl" "$task_dir/version"; rmdir "$task_dir"' EXIT
export MAYDON_DUMP_PATH="$task_dir/backup.dump"
export MAYDON_MANIFEST_PATH="$task_dir/manifest.jsonl"
PGOPTIONS='-c default_transaction_read_only=on' psql -XqAt -P pager=off -v ON_ERROR_STOP=1 <<'SQL'
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET statement_timeout='120s';
SET lock_timeout='5s';
SET TIME ZONE 'UTC';
SET extra_float_digits=3;
SET bytea_output='hex';
SELECT pg_export_snapshot() AS snapshot \gset
\setenv MAYDON_SNAPSHOT :snapshot
\! pg_dump --format=custom --compress=0 --no-owner --no-privileges --lock-wait-timeout=5s --snapshot="$MAYDON_SNAPSHOT" --file="$MAYDON_DUMP_PATH"
\if :SHELL_ERROR
\quit 3
\endif
\getenv manifest MAYDON_MANIFEST_PATH
\o :manifest
SELECT json_build_object('server_version',current_setting('server_version_num')::int,'database_identity',md5(current_database()||(SELECT system_identifier FROM pg_control_system())::text));
SELECT format('SELECT json_build_object(''table'',%L,''rows'',count(*),''digest'',md5(coalesce(string_agg(md5(to_jsonb(t)::text),'''' ORDER BY md5(to_jsonb(t)::text)),''''))) FROM %I.%I t;',tablename,schemaname,tablename) FROM pg_tables WHERE schemaname='public' ORDER BY tablename \gexec
\o
ROLLBACK;
SQL
printf '\nMAYDON_MANIFEST_BEGIN\n'
cat "$task_dir/manifest.jsonl"
printf 'MAYDON_MANIFEST_END\nMAYDON_DUMP_BEGIN\n'
base64 "$task_dir/backup.dump"
printf '\nMAYDON_DUMP_END\n'
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pg-bin', required=True, type=Path)
    parser.add_argument('--backup-dir', type=Path, default=Path('.backups'))
    parser.add_argument('--report', type=Path)
    parser.add_argument('--capture-only', action='store_true', help='Capture a private backup without marking recovery verified')
    parser.add_argument('--project')
    parser.add_argument('--from-backup', type=Path, help='Verify an existing private archive directory without connecting to Railway')
    parser.add_argument('--environment', default='production')
    parser.add_argument('--service', default='Postgres')
    parser.add_argument('--api-service', default='Maydon', help='Live API service whose database identity must match')
    args = parser.parse_args()
    if not args.capture_only and not args.report:
        parser.error('--report is required for restore verification')
    started = time.monotonic()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if args.from_backup:
        archive_dir = args.from_backup.resolve()
        metadata = json.loads((archive_dir / 'metadata.json').read_text())
        backup_file = archive_dir / 'backup.dump'
        archive = backup_file.read_bytes()
        if hashlib.sha256(archive).hexdigest() != metadata['archive_sha256']:
            raise RuntimeError('Backup archive checksum mismatch')
        version = metadata['server_version']
        expected = json.loads((archive_dir / 'source-manifest.json').read_text())
    else:
        if not args.project:
            parser.error('--project is required when capturing a new backup')
        args.backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        if args.backup_dir.is_symlink():
            raise RuntimeError('Backup directory must not be a symlink')
        os.chmod(args.backup_dir, 0o700)
        archive_dir = args.backup_dir / stamp
        archive_dir.mkdir(mode=0o700)
        remote = 'sh -c ' + shlex.quote(snapshot_command())
        output = run(['railway', 'ssh', '--project', args.project, '--environment', args.environment,
                      '--service', args.service, remote], timeout=240).decode('ascii').replace('\r', '')
        manifest_text = output.split('MAYDON_MANIFEST_BEGIN\n', 1)[1].split('MAYDON_MANIFEST_END', 1)[0]
        records = [json.loads(line) for line in manifest_text.splitlines() if line.strip()]
        version = records[0]['server_version']
        identity = records[0]['database_identity']
        probe = "from app import main\nwith main.db() as conn:\n conn.execute('SET TRANSACTION READ ONLY')\n print('MAYDON_DATABASE_IDENTITY:'+conn.execute(\"SELECT md5(current_database()||(SELECT system_identifier FROM pg_control_system())::text) AS identity\").fetchone()['identity'])\n"
        api_output = run(['railway', 'ssh', '--project', args.project, '--environment', args.environment,
                          '--service', args.api_service, 'python -c '+shlex.quote(probe)], timeout=60).decode().replace('\r','')
        if ('MAYDON_DATABASE_IDENTITY:'+identity+'\n') not in api_output:
            raise RuntimeError('Backup source does not match live API database')
        expected = {r['table']: {'rows': r['rows'], 'digest': r['digest']} for r in records[1:]}
        if not {'bookings', 'venues', 'venue_photos'}.issubset(expected):
            raise RuntimeError('Required source tables missing')
        encoded = output.split('MAYDON_DUMP_BEGIN\n', 1)[1].split('MAYDON_DUMP_END', 1)[0]
        archive = base64.b64decode(''.join(encoded.split()), validate=True)
        if not archive.startswith(b'PGDMP'):
            raise RuntimeError('Invalid PostgreSQL custom archive')
        backup_file = archive_dir / 'backup.dump'
        backup_file.write_bytes(archive)
        os.chmod(backup_file, 0o600)
        (archive_dir / 'source-manifest.json').write_text(json.dumps(expected, indent=2)+'\n')
        os.chmod(archive_dir / 'source-manifest.json', 0o600)
        metadata = {'server_version': version, 'archive_sha256': hashlib.sha256(archive).hexdigest(),
                    'database_identity': identity, 'matches_live_api_at_capture': True}
        (archive_dir / 'metadata.json').write_text(json.dumps(metadata)+'\n')
        os.chmod(archive_dir / 'metadata.json', 0o600)
    print('PASS: private consistent-snapshot archive ready', flush=True)

    if args.capture_only:
        print('Private backup directory: '+str(archive_dir), flush=True)
        print('Restore verification is still required.', flush=True)
        return

    pg = lambda tool: str(args.pg_bin / tool)
    local_version = run([pg('postgres'), '--version']).decode()
    if not re.search(rf'\b{version // 10000}\.', local_version):
        raise RuntimeError('Local PostgreSQL major version does not match source')
    # No user-supplied destination DSN. A unique directory/socket and random local
    # database name guarantee that pg_restore cannot target the production server.
    with tempfile.TemporaryDirectory(prefix='maydon-restore-', dir='/private/tmp') as temp:
        temp = Path(temp)
        os.chmod(temp, 0o700)
        data, socket = temp/'data', temp/'socket'
        socket.mkdir(mode=0o700)
        run([pg('initdb'), '-D', str(data), '-A', 'trust', '--no-locale', '--encoding=UTF8'])
        active = False
        try:
            options = f"-k {socket} -c listen_addresses='' -c max_connections=10 -c shared_buffers=16MB"
            run([pg('pg_ctl'), '-D', str(data), '-l', str(temp/'server.log'), '-o', options, '-w', 'start'])
            active = True
            conninfo = {'host': str(socket), 'dbname': 'postgres', 'connect_timeout': 5}
            with psycopg.connect(**conninfo, autocommit=True) as conn:
                dbname = 'restore_' + stamp.lower()
                conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(dbname)))
            env = {k:v for k,v in os.environ.items() if not k.startswith('PG')}
            env.update(PGHOST=str(socket), PGDATABASE=dbname)
            run([pg('pg_restore'), '--exit-on-error', '--single-transaction', '--no-owner', '--no-privileges',
                 '--dbname', dbname, str(backup_file)], env=env, timeout=180)
            with psycopg.connect(**{**conninfo, 'dbname': dbname}) as conn:
                actual = fingerprint(conn)
                if actual != expected:
                    raise RuntimeError('Restored table counts/content fingerprints differ from source snapshot')
                foreign_keys = conn.execute("SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' AND c.contype='f' AND c.convalidated").fetchone()[0]
                # Verify restored sequence state can allocate IDs beyond existing rows.
                checked_sequences = 0
                columns = conn.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public' AND column_default LIKE 'nextval(%'").fetchall()
                for table, column in columns:
                    seq = conn.execute('SELECT pg_get_serial_sequence(%s,%s)', ('public.'+table, column)).fetchone()[0]
                    sequence = sql.SQL('.').join(map(sql.Identifier, seq.split('.')))
                    last, called = conn.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sequence)).fetchone()
                    maximum = conn.execute(sql.SQL('SELECT max({}) FROM {}').format(sql.Identifier(column), sql.Identifier(table))).fetchone()[0]
                    if maximum is not None and (last < maximum or (last == maximum and not called)):
                        raise RuntimeError('Restored sequence would collide with an existing ID')
                    checked_sequences += 1
                photos = conn.execute('SELECT count(*),coalesce(sum(octet_length(image)),0) FROM venue_photos').fetchone()
                decoded_photos = 0
                for (image,) in conn.execute('SELECT image FROM venue_photos'):
                    with Image.open(BytesIO(bytes(image))) as restored_image:
                        restored_image.verify()
                    decoded_photos += 1
            print('PASS: every public table count and content fingerprint matches', flush=True)
            print('PASS: booking/photo contents, foreign keys and ID sequences restored', flush=True)
        finally:
            if active:
                run([pg('pg_ctl'), '-D', str(data), '-m', 'fast', '-w', 'stop'])
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'source_service': args.service,
              'source_postgres_version': version, 'archive_sha256': hashlib.sha256(archive).hexdigest(),
              'archive_bytes': len(archive), 'backup_relative_path': str(backup_file),
              'snapshot_consistent': True, 'source_database_identity': metadata.get('database_identity'),
              'source_matches_live_api_at_capture': metadata.get('matches_live_api_at_capture', False),
              'tables_verified': len(expected),
              'table_counts': {name: row['rows'] for name,row in expected.items()},
              'all_table_content_fingerprints_match': True, 'validated_foreign_keys': foreign_keys,
              'sequences_checked': checked_sequences, 'photo_count': photos[0], 'photo_bytes': photos[1], 'photos_decoded': decoded_photos,
              'isolated_local_cluster_stopped_and_removed': True,
              'elapsed_seconds': round(time.monotonic()-started, 2),
              'limits': 'Fresh logical backup drill; does not verify a scheduled Railway volume backup or establish RPO/RTO. No bot/API attached to restored database.'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print('PASS: sanitized recovery evidence saved; private archive retained in .backups', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not leak credentials, SQL rows, or raw subprocess output.
        print('FAIL: restore verification did not complete ('+type(error).__name__+'). Private data and command output suppressed.')
        raise SystemExit(1)
