# ADR 0001: Clean Pipeline Architecture

## Status

Accepted

## Context

The assignment requires multiple input formats, runtime projection, ML-assisted matching, API, CLI, and strong testability. A monolithic script would couple parsing, matching, transport, and validation.

## Decision

Use a clean pipeline with typed domain models and stage-specific services. API and CLI call the same `CandidateTransformer` application service.

## Consequences

The codebase has more files than a script, but each file has a narrow reason to change. Tests can exercise stages independently and also cover the full pipeline.
