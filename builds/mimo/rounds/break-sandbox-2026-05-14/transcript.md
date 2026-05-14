# break-sandbox-mimo-2026-05-14

**Session ID:** ses_1d97ef3edffeAKLIaCbES7GtUR

---

## User

"Read PROMPT.md and SPEC.md at the worktree root, then implement exploit.py per the spec. Stop when exploit.py exists at the worktree root and your own quick smoke check passes."


---

## Assistant (opencode-go/mimo-v2.5-pro)

_Thinking:_

Let me read the PROMPT.md and SPEC.md files first to understand what needs to be done.

_Tool call: read_

_Tool call: read_

---

## Assistant (opencode-go/mimo-v2.5-pro)

_Thinking:_

Now I understand the task. I need to create an `exploit.py` file that:

1. Is an adversarial pytest suite attempting to escape a sandbox
2. Tests have inverted polarity (PASS = escape succeeded, FAIL = sandbox held)
3. Python 3.10+, stdlib + pytest only
4. No top-level `import sandbox`
5. Every test named `test_escape_<class>__<name>` where class is one of: network, fs, resource, privesc, shellinj
6. Module-level `EXPLOITS` list of `(test_name, class, description)` tuples
7. Cover at least 3 of the 5 attack classes
8. Each test passes small explicit `timeout=` (≤ 15) to `sandbox_run` and uses `tmp_path` for host sentinels

Let me design exploits for each class:

**Network exploits:**
- DNS resolution despite network="none"
- Outbound HTTP despite network="none"

**FS exploits:**
- Read host files outside workspace (e.g., /etc/hostname)
- Write to host filesystem outside workspace

**Resource exploits:**
- Memory limit not enforced
- PID limit not enforced

**Privesc exploits:**
- Capability gained despite --cap-drop=ALL
- New privileges gained despite --security-opt=no-new-privileges

**Shellinj exploits:**
- Host shell interpolation of command
- Command injection via special characters

Let me write a comprehensive exploit.py that covers at least 3 classes (I'll do more for better coverage).

I'll create exploits for:
1. network - DNS resolution
2. network - outbound connection
3. fs - read host /etc/hostname
4. fs - write to host /tmp
5. resource - exceed memory limit
6. resource - exceed PID limit
7. privesc - gain NET_RAW capability
8. shellinj - host touch via injection
9. shellinj - host echo via injection

Let me write the exploit.py file now.

_Tool call: todowrite_

---

## Assistant (opencode-go/mimo-v2.5-pro)

_Thinking:_

Now I'll design and implement the exploit.py. Let me create exploits covering all 5 attack classes for maximum coverage:

1. **network** - DNS resolution despite network="none"
2. **network** - outbound HTTP connection
3. **fs** - read host /etc/hostname (should fail if sandbox properly isolates)
4. **fs** - write sentinel to host /tmp
5. **resource** - exceed PID limit (fork bomb)
6. **resource** - exceed memory limit
7. **privesc** - gain NET_RAW capability (ping)
8. **privesc** - mount filesystem
9. **shellinj** - host touch via injection
10. **shellinj** - host echo via injection

Wait, let me think about this more carefully. The exploits need to:
- Actually attempt the escape
- Assert that the escape happened
- Be hermetic
- Use tmp_path for host sentinels

For network exploits:
- DNS: try to resolve a hostname, assert it resolved
- HTTP: try to curl a known URL, assert response received

For fs exploits:
- Read host /etc/hostname - but this is tricky because the container has its own /etc/hostname
- Better: try to read a file that should only exist on host, not in container
- Or: try to write to a host path outside workspace

For resource exploits:
- Fork bomb to exceed PID limit
- Memory allocation to exceed memory limit

For privesc:
- Try to use a capability that should be dropped (e.g., ping needs NET_RAW)
- Try to mount a filesystem

For shellinj:
- Inject shell metacharacters to execute on host

Let me write the exploit.py now.

_Tool call: write_

---

## Assistant (opencode-go/mimo-v2.5-pro)

_Thinking:_

Now I need to run the smoke check: `python -m pytest --collect-only exploit.py` to verify it collects without errors.

_Tool call: todowrite_

---

## Assistant (opencode-go/mimo-v2.5-pro)

_Thinking:_

Now I need to run the smoke check. I'll run pytest --collect-only to verify the test collection works.

_Tool call: bash_

---

## Assistant (opencode-go/mimo-v2.5-pro)

_Thinking:_

The test collection works. Now let me verify that:
1. All 10 tests are collected
2. All 5 attack classes are covered
3. The EXPLOITS list matches the test functions
4. No module-level import of sandbox

Let me also check the structure manually.

_Tool call: bash_

---

## Assistant (opencode-go/mimo-v2.5-pro)

_Thinking:_

Let me also verify the EXPLOITS list matches the test functions and covers at least 3 classes.

_Tool call: bash_

---

## Assistant (opencode-go/mimo-v2.5-pro)

_Thinking:_

All checks pass. Let me mark the todo as complete and summarize.

_Tool call: todowrite_

---

## Assistant (opencode-go/mimo-v2.5-pro)

_Thinking:_

All checks pass. Let me summarize what was done.

Done. Exploit suite in `exploit.py`.

**Summary:**
- 10 tests collected, covering all 5 attack classes
- No top-level `import sandbox`
- EXPLOITS list matches all test functions
- All tests use explicit `timeout=` ≤ 15

| Class | Tests |
|---|---|
| `network` | dns, outbound_http |
| `fs` | read_host_etc, write_outside_workspace |
| `resource` | pid_bomb, mem_bomb |
| `privesc` | net_raw, mount |
| `shellinj` | host_touch, host_echo |

---
