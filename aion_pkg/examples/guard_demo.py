from aion.guard import AIONApprovalRequired, AIONBlockedError, guard


@guard(
    scope="file.read",
    agent="demo-agent",
    metadata_factory=lambda path: {"path": path},
)
def read_file(path):
    return f"read {path}"


@guard(
    scope="shell.run",
    agent="demo-agent",
    metadata_factory=lambda command: {"command": command},
)
def run_shell(command):
    return f"executed {command}"


def main():
    print("\n--- Low-risk action: file.read ---")
    print(read_file("README.md"))

    print("\n--- Forbidden action: shell.run rm -rf ---")
    try:
        print(run_shell("rm -rf important"))
    except AIONBlockedError as exc:
        print(f"Blocked correctly: {exc}")

    print("\n--- High-risk action: shell.run normal command ---")
    try:
        print(run_shell("echo hello"))
    except AIONApprovalRequired as exc:
        print(f"Approval required correctly: {exc}")


if __name__ == "__main__":
    main()
