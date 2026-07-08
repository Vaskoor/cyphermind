"""Sample vulnerable Flask app for SAST/taint testing."""
from flask import request
import os
import subprocess


def exec_cmd():
    cmd = request.args.get("cmd", "")
    return os.system(cmd)


def sql_query(db):
    user = request.form.get("user")
    return db.execute(f"SELECT * FROM users WHERE name = '{user}'")


def safe_cmd():
    import shlex
    cmd = request.args.get("cmd", "")
    safe = shlex.quote(cmd)
    subprocess.run(["echo", safe], check=False)
