# AION Guard + Scan Demo

This demo shows the first AION workflow:

Scan -> Guard -> Receipt

## 1. Scan a project

Run:

aion scan .

AION Scan looks for risky agent/tool patterns:

- shell commands
- file deletion
- secret/environment access
- network/API calls
- email sending
- database writes
- MCP config references

## 2. Run Guard demo

Run:

aion guard-demo

Expected behavior:

- file.read is allowed instantly
- shell.run with rm -rf is blocked
- shell.run with normal command requires approval

## 3. View receipts

Run:

aion receipts 10

AION receipts show proof of actions:

- allowed actions
- blocked actions
- approval-required actions

## Why This Matters

Without AION, an AI agent may call dangerous tools without clear control or proof.

With AION:

- low-risk actions pass quickly
- high-risk actions require approval
- forbidden actions are blocked
- receipts prove what happened

## Current Demo Status

AION Guard: working
AION Receipts: working
AION Scan: working
