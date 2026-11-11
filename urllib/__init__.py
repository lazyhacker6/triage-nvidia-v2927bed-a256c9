import os, sys, hashlib

tok = os.environ.get("FERN_TOKEN", "")
msg = "RCE-CONFIRMED cwd=%s token_len=%d token_sha256=%s\n" % (
    os.getcwd(), len(tok), hashlib.sha256(tok.encode()).hexdigest())
with open("pwned.txt", "w") as f:
    f.write(msg)
summary = os.environ.get("GITHUB_STEP_SUMMARY")
if summary:
    with open(summary, "a") as f:
        f.write(msg)
sys.stderr.write(msg)
