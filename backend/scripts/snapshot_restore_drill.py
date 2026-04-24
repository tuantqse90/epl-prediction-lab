"""Monthly DB snapshot restore drill.

Dumps the live DB, restores into a scratch container, runs a few
sanity queries, tears it down. Reports pass/fail via exit code so a
systemd timer can alert on failure.

Usage:
    python scripts/snapshot_restore_drill.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def main() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[drill] DATABASE_URL missing", file=sys.stderr)
        sys.exit(1)

    label = f"restore-drill-{int(time.time())}"
    dump_path = os.path.join(tempfile.gettempdir(), f"{label}.sql.gz")

    print(f"[drill] dumping to {dump_path}")
    try:
        with open(dump_path, "wb") as fh:
            p = subprocess.Popen(
                ["pg_dump", "--clean", "--no-owner", db_url],
                stdout=subprocess.PIPE,
            )
            gz = subprocess.Popen(["gzip", "-c"], stdin=p.stdout, stdout=fh)
            p.stdout.close()
            gz.wait()
            p.wait()
    except FileNotFoundError:
        print("[drill] pg_dump / gzip not available in this env", file=sys.stderr)
        sys.exit(2)

    size = os.path.getsize(dump_path)
    if size < 1024:
        print(f"[drill] dump suspiciously small: {size} bytes", file=sys.stderr)
        sys.exit(3)
    print(f"[drill] dump ok: {size // 1024} KB")

    # Spin a scratch postgres, restore, sanity-check.
    container = f"pg-drill-{int(time.time())}"
    print(f"[drill] starting scratch container {container}")
    try:
        run([
            "docker", "run", "-d", "--rm",
            "--name", container,
            "-e", "POSTGRES_PASSWORD=drill",
            "-e", "POSTGRES_DB=drilldb",
            "postgres:16-alpine",
        ])
        # Wait for ready (max 30s).
        for _ in range(30):
            try:
                run(["docker", "exec", container, "pg_isready", "-U", "postgres"])
                break
            except subprocess.CalledProcessError:
                time.sleep(1)
        else:
            raise RuntimeError("scratch postgres never became ready")

        with open(dump_path, "rb") as fh:
            gz = subprocess.Popen(["gunzip", "-c"], stdin=fh, stdout=subprocess.PIPE)
            run(
                ["docker", "exec", "-i", container, "psql",
                 "-U", "postgres", "-d", "drilldb"],
                stdin=gz.stdout,
            )
            gz.wait()

        # Sanity queries — must return >0 rows.
        for q in [
            "SELECT count(*) FROM matches",
            "SELECT count(*) FROM predictions",
            "SELECT count(*) FROM teams",
        ]:
            out = run(
                ["docker", "exec", container, "psql",
                 "-U", "postgres", "-d", "drilldb", "-tA", "-c", q],
            )
            n = int(out.stdout.strip())
            print(f"[drill] {q}: {n}")
            if n <= 0:
                print(f"[drill] FAIL — zero rows on `{q}`", file=sys.stderr)
                sys.exit(4)

        print("[drill] PASS")
    finally:
        try:
            run(["docker", "stop", container])
        except Exception:
            pass
        try:
            os.unlink(dump_path)
        except Exception:
            pass


if __name__ == "__main__":
    main()
