# Hexmedia Design Document

## 1. Purpose

Hexmedia is a **media ingestion and management platform** project
following SOLID principles and Clean Hexagonal Architecture. It serves
as a structured evolution of lessons learned from a previous media
project (xvideo), with an emphasis on modularity, testability, and
long-term maintainability.

## 2. Goals

-   Enforce **strict separation of concerns** across layers (common,
    domain, services, infrastructure).
-   Support **media ingestion** with hashing, duplicate detection,
    metadata extraction (ffprobe), and persistence.
-   Provide a **scalable foundation** for tagging, relationships,
    ratings, and query APIs.
-   Ensure that **tests are first-class citizens**, with temporary
    database containers and domain invariant tests.
-   Optimize for **extensibility** (new services, new ingest policies,
    etc.) without rewriting core code.

## 3. Architecture Overview

Hexmedia follows a **Clean Architecture / Hexagonal Architecture**
approach:

-   **Common Layer**: Abstracts, utilities, helpers, cross-cutting
    concerns (e.g., logging, concurrency).
-   **Domain Layer**: Pure business rules, entities, invariants,
    policies, ports.
-   **Application Layer (Services)**: Orchestrates use cases, interacts
    with domain ports.
-   **Infrastructure Layer**: Database repositories, file system
    adapters, external services.
-   **Presentation Layer**: REST API (FastAPI), schemas for
    request/response.

```{=html}
<!-- -->
```
    +------------------+
    |  Presentation    |  -> FastAPI, schemas
    +------------------+
    |  Application     |  -> Service classes, use cases
    +------------------+
    |  Domain          |  -> Entities, Policies, Ports (Protocols/ABCs)
    +------------------+
    |  Common          |  -> Concurrency, logging, helpers
    +------------------+
    |  Infrastructure  |  -> Database, ffprobe, filesystem
    +------------------+

## 4. Key Common Utilities

-   **Concurrency → ThreadManager class**:

    -   Provides a reusable, bounded thread-pool manager tailored for
        I/O-bound workloads like media ingestion and probing.
    -   Supports cooperative cancellation via stop events.
    -   Provides methods like `submit()`, `map()`, and
        `imap_unordered()` for flexible parallel execution.
    -   Enforces backpressure to avoid overwhelming the system with too
        many tasks.
    -   Guarantees proper cleanup: pending tasks are cancelled if the
        context manager exits.
    -   Extensively tested for ordering guarantees, error propagation,
        and worker leak prevention.
    -   **Intended role**: ThreadManager is the backbone for
        parallelizing work across the system. Any long-running or
        blocking job (e.g., hashing, ffprobe) is delegated to it so the
        main API loop remains responsive.

-   **Naming → random_slug()**: Configurable utility that generates
    short, filesystem-friendly slugs.

-   **Path utilities (safe.py)**: Common filesystem path helpers.

-   **Logging**: Centralized structured logging facility.

## 5. Key Domain Entities

-   **MediaItem**: Core unit (identified by triplet: `media_folder`,
    `identity_name`, `video_ext`).
-   **MediaAsset**: Associated files (thumbnails, previews, subtitles,
    etc.).
-   **Tag**: Hierarchical tagging system for classification.
-   **Person**: Actors, directors, creators, etc.
-   **Rating**: Single rating per media item.
-   

## 6. Domain Ports (Interfaces)

-   **MediaQueryPort**: Read-only queries for media items.
-   **MediaMutationPort**: Create/update/delete operations.
-   **MediaAssetWriter**: Specialized for asset management.
-   **MediaArtifactWriter**: Specialized for tags and persons.
-   **FileOpsPort**: Abstraction over file system operations.
-   **HashingPort**: Abstraction over hashing implementations.

## 7. Infrastructure Adapters

-   **SQLAlchemy Repositories**: Implement domain ports against
    Postgres.
-   **FFProbe Adapter**: Extracts metadata from media files.
-   **FileOps Adapter**: Wraps `shutil` and `pathlib` safely.
-   **Hashing Adapter**: Provides file hashing (e.g., SHA-256).

## 8. Services / Use Cases

-   **IngestWorker**: Executes ingestion plans, moves files, checks
    duplicates, persists items.
-   **ThreadManager**: Manages concurrency for long-running ingest
    tasks.
    -   **In practice**: IngestWorker may delegate hashing and ffprobe
        probing to ThreadManager. For example, it can `submit()`
        multiple file-hashing jobs in parallel, collect results, and
        only proceed once all are finished. This balances speed
        (parallelism) with system safety (backpressure, cancellation).
-   **API Routers**: Expose CRUD for MediaItems, Tags, People, Ratings.

## 9. Data Flow Example (Ingestion)

1.  **Plan**: IngestPlanner creates an `IngestPlan` with
    `IngestPlanItems`.
2.  **Execute**: IngestWorker runs the plan.
    -   Hash file (potentially via ThreadManager in parallel).
    -   Query repo to check duplicates.
    -   Move file into media folder.
    -   Persist MediaItem and related data.
3.  **Report**: IngestWorker returns an `IngestReport`.

## 10. Testing Strategy

-   **Database Tests**: Run against throwaway Postgres containers via
    `testcontainers`.
-   **Domain Tests**: Verify invariants, side-effect-free policies, and
    serialization round-trips.
-   **Service Tests**: End-to-end API tests via FastAPI TestClient.
-   **Concurrency Tests**: Validate ThreadManager ordering,
    cancellation, backpressure.

## 11. File & Folder Structure

    hexmedia/
      common/
        concurrency/thread_manager.py
        logging.py
        abstracts/worker.py (BaseWorker abstract)
        utils/
      domain/
        entities/
        policies/
        ports/
        enums/
      services/
        api/routers/
        ingest/
      database/
        models/
        repositories/
        alembic/
      tests/
        domain/
        database/
        services/

## 12. External Tools & Dependencies

-   **FastAPI** -- API framework.
-   **SQLAlchemy** -- ORM & database abstraction.
-   **Alembic** -- Migrations.
-   **Pydantic v2** -- Schemas & validation.
-   **Testcontainers** -- Ephemeral DBs for tests.
-   **ffprobe (via subprocess)** -- Media metadata extraction.

## 13. Future Extensions

-   Pluggable storage backends (local FS, S3, etc.).
-   Background job queue for ingest (Celery / RQ / custom thread
    manager).
-   Advanced search (e.g., vector DB for perceptual hashes).
-   Frontend integration for browsing and tagging.
