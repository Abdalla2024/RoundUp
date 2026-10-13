"""Runs the migrations and the negative RLS script against a throwaway local Postgres with a Supabase shim.

Skipped if Postgres binaries (initdb, pg_ctl, psql) are not on PATH. This checks the SQL and the policies'
logic; it does not replace running tests/rls_negative_test.sql on the real Supabase project (README.md).
"""

import os
import pathlib
import shutil
import socket
import subprocess
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
PG_BIN = os.environ.get("PG_BIN") or (
    "/Applications/Postgres.app/Contents/Versions/latest/bin"
    if pathlib.Path("/Applications/Postgres.app/Contents/Versions/latest/bin/initdb").exists() else "")
INITDB = shutil.which("initdb", path=PG_BIN or None)
pytestmark = pytest.mark.skipif(not INITDB, reason="Postgres binaries not found")


def _bin(name):
    return str(pathlib.Path(INITDB).parent / name)


@pytest.fixture(scope="module")
def cluster():
    tmp = tempfile.mkdtemp()
    data = pathlib.Path(tmp) / "data"
    subprocess.run([_bin("initdb"), "-D", str(data), "-U", "postgres", "-A", "trust"], check=True,
                   capture_output=True)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    subprocess.run([_bin("pg_ctl"), "-D", str(data), "-o", f"-p {port} -k {tmp}", "-l", f"{tmp}/log", "-w",
                    "start"], check=True, capture_output=True)
    yield {"port": port, "host": tmp}
    subprocess.run([_bin("pg_ctl"), "-D", str(data), "-m", "immediate", "stop"], capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)


def psql(cluster, db, sql=None, file=None):
    args = [_bin("psql"), "-h", cluster["host"], "-p", str(cluster["port"]), "-U", "postgres", "-d", db,
            "-v", "ON_ERROR_STOP=1", "-X", "-q"]
    args += ["-f", str(file)] if file else ["-c", sql]
    return subprocess.run(args, capture_output=True, text=True)


def fresh_db(cluster, name, extra_sql=""):
    assert psql(cluster, "postgres", f"create database {name}").returncode == 0
    for f in [HERE / "local_supabase_shim.sql", ROOT / "migrations/0001_schema.sql", ROOT / "migrations/0002_rls.sql"]:
        r = psql(cluster, name, file=f)
        assert r.returncode == 0, (f.name, r.stderr)
    if extra_sql:
        assert psql(cluster, name, extra_sql).returncode == 0
    return name


def test_negative_script_passes(cluster):
    db = fresh_db(cluster, "rls_ok")
    r = psql(cluster, db, file=HERE / "rls_negative_test.sql")
    assert r.returncode == 0, r.stderr
    assert "ALL RLS CHECKS PASSED" in r.stdout
    assert r.stderr.count("PASS:") == 14 and "FAIL" not in r.stderr


@pytest.mark.parametrize("leak", [
    'create policy "leak" on public.scenarios for select to authenticated using (true)',
    'create policy "leak" on public.scenario_results for update to authenticated using (true); '
    'grant update on public.scenario_results to authenticated',
    'grant select on public.scenarios to anon; create policy "leak" on public.scenarios for select to anon using (true)',
    "alter table public.scenario_results disable row level security",
    "alter table public.scenario_results drop constraint scenario_results_scenario_id_user_id_fkey",
])
def test_script_detects_a_leak(cluster, leak):
    """The negative script must FAIL when a policy, grant or constraint is weakened."""
    db = fresh_db(cluster, f"rls_leak_{abs(hash(leak)) % 10**8}", leak)
    r = psql(cluster, db, file=HERE / "rls_negative_test.sql")
    assert r.returncode != 0 and "FAIL" in r.stderr, (leak, r.stdout, r.stderr)


def test_owner_rename_runs_trigger_and_user_delete_cascades(cluster):
    db = fresh_db(cluster, "rls_owner")
    a = "00000000-0000-0000-0000-00000000000a"
    sql = f"""
    begin;
    set local role authenticated;
    select set_config('request.jwt.claims', '{{"sub":"{a}"}}', true);
    select public.save_scenario('mine', '{{}}', null, 'sideways', 'broad', 'weekly', false, '{{}}', '0.2.0',
      'scenario-model-1', 1303, 'sample', '2026-09-30', repeat('a', 64), repeat('b', 64));
    update public.scenarios set name = 'renamed' where name = 'mine';
    select name, updated_at >= created_at from public.scenarios;
    commit;
    delete from auth.users where id = '{a}';
    select (select count(*) from public.scenarios) + (select count(*) from public.scenario_results);
    """
    r = psql(cluster, db, sql)
    assert r.returncode == 0, r.stderr
    assert "renamed | t" in r.stdout
    assert r.stdout.strip().splitlines()[-2].strip() == "0"      # account deletion removes every row (cascade)


def test_save_scenario_is_atomic(cluster):
    db = fresh_db(cluster, "rls_atomic")
    a = "00000000-0000-0000-0000-00000000000a"
    sql = f"""
    set role authenticated;
    select set_config('request.jwt.claims', '{{"sub":"{a}"}}', false);
    select public.save_scenario('bad result', '{{}}', null, 'sideways', 'NOT-A-STYLE', 'weekly', false, '{{}}',
      '0.2.0', 'scenario-model-1', 1303, 'sample', '2026-09-30', repeat('a', 64), repeat('b', 64));
    """
    r = psql(cluster, db, sql)
    assert r.returncode != 0 and "check constraint" in r.stderr
    count = psql(cluster, db, "select count(*) from public.scenarios")
    assert count.stdout.split()[-3] == "0"                         # the scenario row was rolled back too
