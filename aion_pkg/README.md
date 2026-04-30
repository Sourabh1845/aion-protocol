# AION Protocol

AION is a fast security and authority layer for AI agents.

It helps developers control what autonomous agents are allowed to do before they touch files, APIs, terminals, emails, payments, deployments, or other real-world tools.

## Core Idea

Safe actions should pass instantly.

Risky actions should be logged, approved, or blocked.

```text
Agent wants to act
        |
        v
AION checks policy
        |
        v
allow / log / approval / block
        |
        v
AION creates receipt proof
