# sandbox.py — implementation spec (v0.1)

A Python module that wraps Podman (or Docker) to run commands inside
ephemeral, network-isolated, resource-capped containers. Stdlib only.

## Public function

```python
def sandbox_run(
    command: str,
    workspace: str | None = None,   # host dir to bind r/w at /workspace; None = no mount
    image: str = "debian:stable-slim",
    timeout: int = 60,
    network: str = "none",          # "none" | "bridge"
    memory: str = "2g",
    pids: int = 512,
    cpus: float = 2.0,
) -> str:
```

### Behaviour

- Runs `command` inside an ephemeral container of `image`.
- If `workspace` is a path, it is bind-mounted read-write at `/workspace`,
  and the container's working directory is set to `/workspace`. If
  `workspace` is `None`, no host directory is mounted.
- Container is destroyed after the command exits (`--rm`).
- Network: `none` (default) means no DNS, no outbound. `bridge` enables
  default networking.
- Resource limits applied on every run: `--memory`, `--pids-limit`, `--cpus`,
  `--cap-drop=ALL`, `--security-opt=no-new-privileges`.
- Subprocess invocation uses an argv list with `shell=False`. The `command`
  string is passed as an argument to `sh -c` *inside the container*. The
  host shell must never interpolate it.
- Wall-clock timeout enforced via `subprocess.run(timeout=...)`. On timeout,
  the container is terminated and the returned string indicates a timeout.
- Combined output (stdout + stderr) is truncated to 50,000 bytes total
  before being returned. Truncation is silent (no error), but a clear
  marker like `... [truncated]` may be appended.
- First-call latency is allowed: `--pull=missing` is fine for v0.1.

### Return format

A single string:

```
exit=<n>
--- stdout ---
<stdout bytes, decoded>
--- stderr ---
<stderr bytes, decoded>
```

Where `<n>` is the container's exit code (or `124` on timeout, matching
GNU `timeout` convention). Decoding errors are replaced (`errors="replace"`).

## Podman invocation (reference)

```
podman run --rm --pull=missing \
    --network=<network> \
    --memory=<memory> \
    --pids-limit=<pids> \
    --cpus=<cpus> \
    --cap-drop=ALL \
    --security-opt=no-new-privileges \
    [-v <workspace>:/workspace:rw -w /workspace] \
    <image> sh -c "<command>"
```

If `podman` is not on PATH, fall back to `docker`. If neither is present,
raise a clear `RuntimeError` mentioning both.

## Standalone CLI

`sandbox.py` must be runnable directly:

```
python sandbox.py [--image IMAGE] [--timeout N] [--network none|bridge]
                  [--memory SIZE] [--pids N] [--cpus N] [--workspace DIR]
                  -- COMMAND [ARG ...]
```

- Use `argparse`.
- The `--` separator divides flags from the command. Everything after `--`
  is joined with a single space and passed as `command`.
- Default `workspace` for the CLI is `os.getcwd()` (so the user's working
  dir is mounted by default when invoked from the shell).
- The script prints the formatted output string to stdout.
- Exit code matches the container's exit code (so the CLI is composable
  with shell pipelines). Timeout exits with code 124.

## Example

Library use:
```python
from sandbox import sandbox_run
print(sandbox_run("echo hi"))
# exit=0
# --- stdout ---
# hi
# --- stderr ---
```

CLI use:
```
$ python sandbox.py -- echo hi
exit=0
--- stdout ---
hi
--- stderr ---

$ echo $?
0
```

## Out of scope (do not implement)

- Persistent sandboxes (`sandbox_create` / `sandbox_exec` / `sandbox_destroy`)
- Image allowlist / trusted registries
- Concurrent sandbox pooling
- tmpfs-only workspace mode
- Mia harness integration files (`tools/sandbox.py` etc.)
