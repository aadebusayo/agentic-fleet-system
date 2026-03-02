# ADR 0001: Polyglot Monorepo with Contract-First Shared Layer

## Status

Accepted

## Context

Platform services have distinct runtime needs:

- policy and protocol gateway ergonomics in TypeScript
- orchestration and AI workflows in Python
- low-overhead fleet operations in Go

## Decision

Adopt a polyglot monorepo with strict shared contracts in `shared/`.

## Consequences

- Better fit-for-purpose implementation per service.
- Strong schema governance required at boundaries.
