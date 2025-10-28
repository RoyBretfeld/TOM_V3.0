"""Nightly synthetic call helper for TOM v3.

The script originates a short FreeSWITCH call (via ``fs_cli``) to ensure the
realtime stack is functional. After a successful run it updates the
``tom_synth_call_last_success_timestamp_seconds`` gauge by calling the
gateway's admin endpoint (``POST /metrics/synth``).
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Optional


LOG = logging.getLogger("synthetic-call")


def run_fs_cli(fs_cli: str, did: str, profile: str, timeout: int) -> None:
    """Trigger a short call via fs_cli."""

    command = [
        fs_cli,
        "-x",
        f"originate {profile}/{did} '&park()'",
    ]
    LOG.debug("Executing fs_cli command: %s", " ".join(command))

    try:
        subprocess.run(
            command,
            check=True,
            timeout=timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"fs_cli timeout after {timeout}s") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"fs_cli failed with exit code {exc.returncode}: {exc.stderr.decode(errors='ignore')}"
        ) from exc


def update_metrics(endpoint: str, token: Optional[str] = None) -> None:
    """Notify the gateway about a successful synthetic call."""

    request = urllib.request.Request(endpoint, method="POST")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=5):
            LOG.debug("Metrics endpoint updated: %s", endpoint)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Failed to update metrics endpoint ({exc.code})") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to reach metrics endpoint: {exc.reason}") from exc


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TOM synthetic call")
    parser.add_argument(
        "--did",
        default=os.getenv("SYNTH_CALL_DID"),
        help="Destination number (E.164)"
    )
    parser.add_argument(
        "--profile",
        default=os.getenv("SYNTH_CALL_PROFILE", "sofia/external"),
        help="FreeSWITCH originate profile"
    )
    parser.add_argument(
        "--timeout",
        default=int(os.getenv("SYNTH_CALL_TIMEOUT", "20")),
        type=int,
        help="Timeout for fs_cli command"
    )
    parser.add_argument(
        "--fs-cli",
        default=os.getenv("SYNTH_CALL_FSCLI", "fs_cli"),
        help="Path to fs_cli executable"
    )
    parser.add_argument(
        "--metrics-endpoint",
        default=os.getenv("SYNTH_CALL_METRICS_ENDPOINT", "http://127.0.0.1:9100/metrics/synth"),
        help="Gateway metrics endpoint for success notification"
    )
    parser.add_argument(
        "--metrics-token",
        default=os.getenv("SYNTH_CALL_METRICS_TOKEN"),
        help="Bearer token for metrics endpoint"
    )
    parser.add_argument(
        "--run-id",
        default=os.getenv("SYNTH_CALL_RUN_ID", "manual"),
        help="Optional run identifier for logging"
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    args = parse_args(argv)

    if not args.did:
        LOG.error("No DID configured (use --did or SYNTH_CALL_DID)")
        return 2

    LOG.info("Synthetic call started (run_id=%s, did=%s)", args.run_id, args.did)

    start = time.time()
    run_fs_cli(args.fs_cli, args.did, args.profile, args.timeout)
    duration = time.time() - start
    LOG.info("Synthetic call finished in %.2fs", duration)

    update_metrics(args.metrics_endpoint, token=args.metrics_token)
    LOG.info("Metrics endpoint updated: %s", args.metrics_endpoint)
    return 0


if __name__ == "__main__":
    sys.exit(main())

