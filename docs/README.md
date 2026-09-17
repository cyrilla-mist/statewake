# STATEWAKE Documentation

Documentation for the completed 2026 STATEWAKE hackathon project snapshot.

## Start Here

- [`../README.md`](../README.md) — product overview, project status, demo flow, runtime setup, and limitations.
- [`architecture.md`](architecture.md) — annotated system architecture and component relationships.
- [`../DEPLOYMENT.md`](../DEPLOYMENT.md) — Cloud Run deployment shape and safe redeployment outline.

## Repository Relationship

The main source repository is [`cyrilla-mist/statewake`](https://github.com/cyrilla-mist/statewake).

The separate [`statewake-demo-project`](https://github.com/cyrilla-mist/statewake-demo-project) repository is **external demo evidence**, not another copy of the STATEWAKE implementation.

## Product Baseline

The frozen core principle is **Validate before Recover**:

```text
read trusted working state
  → gather current evidence
  → assess VALID / INVALID / AMBIGUOUS
  → require human authority when consequential
  → commit a new trusted state only when justified
```

Future documentation should distinguish post-hackathon continuation from the submitted project snapshot rather than rewriting historical demo behavior as if it were unfinished work.
