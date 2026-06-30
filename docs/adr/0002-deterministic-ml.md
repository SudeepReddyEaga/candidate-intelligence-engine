# ADR 0002: Deterministic ML Features

## Status

Accepted

## Context

The system needs embeddings, fuzzy matching, skill canonicalization, duplicate detection, and semantic matching without training deep learning models.

## Decision

Support pretrained SentenceTransformer embeddings through an interface, while defaulting to a deterministic hash embedding backend in CI and Docker. Combine embeddings with RapidFuzz and exact identifiers.

## Consequences

Production deployments can enable `sentence-transformers` by setting `CANDIDATE_TRANSFORMER_EMBEDDING_BACKEND=sentence-transformer`. Tests stay offline, fast, and repeatable.
