import pathlib
import re
import subprocess
import time


def _run(sandbox_module, *args, **kwargs):
    return sandbox_module.sandbox_run(*args, **kwargs)


def test_simple_echo(sandbox_module):
    out = _run(sandbox_module, "echo hi")
    assert "hi" in out, f"expected 'hi' in output, got: {out!r}"


def test_output_format(sandbox_module):
    out = _run(sandbox_module, "echo hi")
    assert "exit=0" in out, f"missing 'exit=0' marker: {out!r}"
    assert "--- stdout ---" in out, f"missing stdout marker: {out!r}"
    assert "--- stderr ---" in out, f"missing stderr marker: {out!r}"


def test_exit_code_nonzero(sandbox_module):
    out = _run(sandbox_module, "exit 7")
    assert "exit=7" in out, f"expected 'exit=7', got: {out!r}"


def test_timeout(sandbox_module):
    start = time.time()
    out = _run(sandbox_module, "sleep 30", timeout=2)
    elapsed = time.time() - start
    assert elapsed < 15, f"timeout took too long: {elapsed:.1f}s"
    assert "exit=124" in out or "timeout" in out.lower(), (
        f"expected timeout indicator, got: {out!r}"
    )


def test_network_default_isolated(sandbox_module):
    # getent does DNS resolution; works on debian:stable-slim without
    # extra packages. With network=none there is no resolver, so it fails.
    out = _run(
        sandbox_module,
        "getent hosts example.com >/dev/null && echo OK || echo FAIL",
        timeout=20,
    )
    assert "FAIL" in out, (
        f"network=none default should block DNS, got: {out!r}"
    )


def test_network_bridge(sandbox_module):
    out = _run(
        sandbox_module,
        "getent hosts example.com >/dev/null && echo OK || echo FAIL",
        network="bridge",
        timeout=30,
    )
    assert "OK" in out, (
        f"network=bridge should allow DNS, got: {out!r}"
    )


def test_workspace_mount(sandbox_module, tmp_path):
    _run(
        sandbox_module,
        "echo from-container > /workspace/marker.txt",
        workspace=str(tmp_path),
    )
    marker = tmp_path / "marker.txt"
    assert marker.exists(), "workspace mount should let container write host files"
    assert "from-container" in marker.read_text()


def test_truncation(sandbox_module):
    out = _run(sandbox_module, "yes x | head -c 200000", timeout=30)
    assert len(out) <= 51_000, (
        f"output should be truncated to ~50KB, got {len(out)} bytes"
    )


def test_no_host_shell_injection(sandbox_module, tmp_path):
    """A `command` with host-shell metacharacters must not execute on the
    host. We try multiple injection forms that aim to break out of single-
    or double-quoted host-shell contexts. None of them should result in
    the sentinel file being created on the host filesystem."""
    sentinel = tmp_path / "host_pwn.txt"
    payloads = [
        f"x' > {sentinel}; echo '",
        f'x" > {sentinel}; echo "',
        f"x; echo pwned > {sentinel}",
        f"x && echo pwned > {sentinel}",
        f"x`echo pwned > {sentinel}`",
        f"x$(echo pwned > {sentinel})",
    ]
    for payload in payloads:
        if sentinel.exists():
            sentinel.unlink()
        _run(sandbox_module, payload, timeout=10)
        assert not sentinel.exists(), (
            f"host shell executed payload {payload!r} — sentinel "
            f"appeared at {sentinel}"
        )
