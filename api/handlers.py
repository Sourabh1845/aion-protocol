import subprocess
import sys

def _run(script, args=None):
    cmd = [sys.executable, script]
    if args:
        cmd.extend(args)
    subprocess.run(cmd, check=False)

def issue():
    _run("issue.py")

def verify(authority_id):
    _run("verify.py", [authority_id])

def enforce(authority_id):
    _run("enforce.py", [authority_id])

def revoke(authority_id):
    _run("revoke.py", [authority_id])

def list_authorities():
    _run("list_authorities.py")
