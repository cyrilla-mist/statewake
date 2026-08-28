# STATEWAKE — Validate-before-Recover Agent Architecture

```mermaid
flowchart TD
    U[User / Browser] --> UI[STATEWAKE Web UI]
    UI --> API[Google Cloud Run / FastAPI]
    API --> WF[Re-entry Workflow]
    WF --> ADK[Google ADK Agent]
    ADK --> GEM[Gemini 3.5 Flash on Vertex AI]
    ADK --> TS[Firestore Trusted Project State]
    ADK --> MEM[Collaboration Memory]
    ADK --> GH[Read-only GitHub project evidence]
    ADK --> INT[Agent interpretation]
    INT --> DB{Decision Boundary}
    DB -->|VALID| KEEP[Preserve Trusted State / no new checkpoint]
    DB -->|AMBIGUOUS consequential| GATE[Human Decision Gate]
    GATE --> AUTH[Explicit authorization]
    AUTH --> WR[prepare_resume_state / sole Trusted State writer]
    WR --> COMMIT[Firestore atomic checkpoint commit]
    COMMIT --> RES[Resume State]
```

Evidence is observed. Findings are inferred. Trusted State is committed.
Memory is interpretation context only; it cannot override Trusted State or
authorize recovery. Evidence never replaces the human authority boundary.
