# break-sandbox-minimax-2026-05-14

**Session ID:** ses_1d9825051ffe2s0ag8528k9MpR

---

## User

"Read PROMPT.md and SPEC.md at the worktree root, then implement exploit.py per the spec. Stop when exploit.py exists at the worktree root and your own quick smoke check passes."


---

## Assistant (opencode-go/minimax-m2.5)

_Thinking:_

The user wants me to read PROMPT.md and SPEC.md files, then implement exploit.py according to the spec. Let me start by reading both files.







_Tool call: read_

_Tool call: read_

---

## Assistant (opencode-go/minimax-m2.5)

_Thinking:_

Now I understand the task. I need to implement `exploit.py` - an adversarial pytest suite that tries to escape a sandbox. Let me understand the key points:

1. **Inverted meaning**: PASS = escape succeeded, FAIL = sandbox held
2. **5 attack classes**: network, fs, resource, privesc, shellinj
3. **Requirements**:
   - Python 3.10+, stdlib + pytest only
   - No top-level `import sandbox`
   - Test names: `test_escape_<class>__<name>`
   - `EXPLOITS` list with tuples (test_name, class, description)
   - Cover at least 3 of 5 classes
   - Small timeout (≤ 15)

Let me think about what exploits to implement for each class:

**Network escapes** (trying to bypass network="none"):
- Try DNS resolution despite network=none
- Try to reach external IPs

**Filesystem escapes** (trying to access host paths outside workspace):
- Try to read /etc/hostname from host
- Try to access other host paths

**Resource escapes** (trying to exceed resource limits):
- Try to use more memory than allowed
- Try to fork more processes than allowed

**Privesc escapes** (trying to gain capabilities):
- Try to use capabilities that should be dropped

**Shell injection escapes** (trying to inject into host shell):
- Try to interpolate host shell via command injection

Let me implement at least 3 classes - I'll do network, fs, and shellinj as they're most likely to find vulnerabilities.

Let me write exploit.py now.







_Tool call: write_

---

## Assistant (opencode-go/minimax-m2.5)

_Thinking:_

Now let me verify the exploit.py works by collecting the tests.







_Tool call: bash_

---

## Assistant (opencode-go/minimax-m2.5)

_Thinking:_

All 6 tests collected successfully. Let me verify:
- EXPLOITS list matches test functions ✓
- Covers at least 3 classes: network, fs, shellinj ✓ (3 distinct classes)
- Each test has timeout ≤ 15 ✓
- Uses tmp_path for host sentinels ✓

Done. Exploit suite in exploit.py.




Done. Exploit suite in exploit.py. 6 tests across 3 classes (network, fs, shellinj), all collected successfully.

---
