# Hexmedia Design Document

## 1. Purpose

Hexmedia is a **media ingestion and management platform** project
following SOLID principles and Clean Hexagonal Architecture. It serves
as a structured evolution of lessons learned from a previous media
project (xvideo), with an emphasis on modularity, testability, and
long-term maintainability.

## 2. Goals

- Enforce **strict separation of concerns** across layers (common,
  domain, services, infrastructure).
- Support **media ingestion** with hashing, duplicate detection,
  metadata extraction (ffprobe), and persistence.
- Provide a **scalable foundation** for tagging, relationships,
  ratings, and query APIs.
- Ensure that **tests are first-class citizens**, with temporary
  database containers and domain invariant tests.
- Optimize for **extensibility** (new services, new ingest policies,
  etc.) without rewriting core code.

## 3. Architecture Overview

Hexmedia follows a **Clean Architecture / Hexagonal Architecture**
approach:

- **Common Layer**: Abstracts, utilities, helpers, cross-cutting
  concerns (e.g., logging, concurrency).
- **Domain Layer**: Pure business rules, entities, invariants,
  policies, ports.
- **Application Layer (Services)**: Orchestrates use cases, interacts
  with domain ports.
- **Infrastructure Layer**: Database repositories, file system
  adapters, external services.
- **Presentation Layer**: REST API (FastAPI), schemas for
  request/response.

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
```

## 4. Key Common Utilities

- **Concurrency → ThreadManager class**:
  - Provides a reusable, bounded thread-pool manager tailored for
    I/O-bound workloads like media ingestion and probing.
  - Supports cooperative cancellation via stop events.
  - Provides methods like `submit()`, `map()`, and
    `imap_unordered()` for flexible parallel execution.
  - Enforces backpressure to avoid overwhelming the system with too
    many tasks.
  - Guarantees proper cleanup: pending tasks are cancelled if the
    context manager exits.
  - Extensively tested for ordering guarantees, error propagation,
    and worker leak prevention.
  - **Intended role**: ThreadManager is the backbone for
    parallelizing work across the system. Any long-running or
    blocking job (e.g., hashing, ffprobe) is delegated to it so the
    main API loop remains responsive.

- **Naming → random_slug()**: Configurable utility that generates
  short, filesystem-friendly slugs.

- **Path utilities (safe.py)**: Common filesystem path helpers.

- **Logging**: Centralized structured logging facility.

## 5. Key Domain Entities

- **MediaItem**: Core unit (identified by triplet: `media_folder`,
  `identity_name`, `video_ext`).
- **MediaAsset**: Associated files (thumbnails, previews, subtitles,
  etc.).
- **Tag**: Hierarchical tagging system for classification.
- **Person**: Actors, directors, creators, etc.
- **Rating**: Single rating per media item.

---

## 6. Data Object Overview

> This section expands Section 5 with concrete object shapes, relationships, and a
> **scalable tag-group scope model** that supports **media** and **person** metadata today and
> can extend to new entity types (e.g., *car*, *studio*) without schema churn.

### 6.1 Primary entities (tables)

- **media_items** — core video record
  - `id (uuid, pk)`
  - `media_folder (text)`
  - `identity_name (text)`
  - `video_ext (text)`
  - technicals: `duration_sec, width, height, fps, bitrate, ...`
  - derived: `thumb_url (nullable)`, etc.

- **media_assets** — files associated to a media item
  - `id (uuid, pk)`, `media_item_id (fk)`
  - `kind (enum/text)` e.g., `thumb`, `proxy`, `collage`, `subtitle`
  - `url` and/or `rel_path`

- **people** — persons who can be linked to media and annotated
  - `id (uuid, pk)`
  - `display_name (text)` (can be unknown/placeholder)
  - `normalized_name (text)`
  - `notes (text, nullable)`
  - `avatar_asset_id (fk nullable)` — links to a representative face crop in `assets` (optional)

- **person_aliases** — alternative names
  - `id (uuid, pk)`, `person_id (fk)`, `alias (text)`

- **ratings** — 1:1 with media_item
  - `media_item_id (pk, fk)`, `score (int)`

- **tag_groups** — hierarchical containers of tags
  - `id (uuid, pk)`
  - `key (text unique within siblings)` e.g., `genre`, `hair-color`
  - `display_name (text)`
  - `path (ltree/text)`, `depth (int)`
  - `parent_id (fk nullable)`
  - `cardinality (enum: SINGLE|MULTI)` — UI/server enforce single-selection groups
  - *(scope mapping defined below; no brittle BOTH flags)*

- **tags** — hierarchical values within a group (or freeform)
  - `id (uuid, pk)`
  - `name (text)`, `slug (text)`
  - `group_id (fk nullable)` — `NULL` → **freeform** tag
  - `parent_id (fk nullable)` — parent **within same group**
  - `description (text nullable)`

> *Optional/Extensible:* `person_faces` (face crops & embeddings), `person_profiles` (denormalized view or a separate profile table if needed later).

### 6.2 Relationship (junction) tables

- **media_tags** — M:N between media_items and tags
  - `media_item_id (fk)`, `tag_id (fk)`
  - **Invariant:** If the tag belongs to a `SINGLE` group, at most one tag from that group can be linked to a given media item.

- **media_people** — M:N between media_items and people
  - `media_item_id (fk)`, `person_id (fk)`
  - Optional role column: `role (enum/text)` e.g., `actor`, `director`.

- **person_tags** — M:N between people and tags
  - `person_id (fk)`, `tag_id (fk)`
  - Enables searching media by **person attributes** (e.g., *female*, *blonde*, *age: 20s*), once media is linked to that person.

### 6.3 Tag Group **scope** (scalable model)

To make tag groups apply to different entity types without `BOTH`-style flags:

- **entity_types**
  - `id (smallint pk)`, `name (text unique)` — seed with `media_item`, `person`.

- **tag_group_entity_types** *(many-to-many)*
  - `tag_group_id (fk)`, `entity_type_id (fk)`
  - A group can apply to one or more entity types. Examples:
    - `genre` → `[media_item]`
    - `person-meta` → `[person]`
    - `keywords` → `[media_item, person]` (shared semantics)

- **tag_entity_types (optional)**
  - Only needed for **freeform tags** (`group_id IS NULL`) to declare which entities they attach to. If omitted, default to `[media_item]` for back-compat.

**Validation rules** (service layer):
1. When attaching a tag to an entity, allow only if the union of applicable entity types includes that entity type.
2. For `SINGLE` groups, replace any existing tag from that group on the same entity (optimistic in FE + enforced in BE).
3. Parent/child relationships must be within the same group.

### 6.4 Person metadata via tags

- Create a `TagGroup` like **PersonMeta** (`key=person-meta`, `cardinality=MULTI`) with scope `[person]`.
- Define tags such as `sex:female`, `hair:blonde`, `age:20s`, etc. (hierarchies allowed per group policy).
- Attach tags to a **Person** via `person_tags`.
- Link Person ↔ Media via `media_people`.
- **Querying:** filter media by joining through `media_people → person_tags` (see patterns below).

### 6.5 Example query patterns

- **Media by direct tags** (e.g., `genre=Drama`):
  ```sql
  SELECT mi.*
  FROM media_items mi
  JOIN media_tags mt ON mt.media_item_id = mi.id
  JOIN tags t ON t.id = mt.tag_id
  JOIN tag_groups g ON g.id = t.group_id
  WHERE g.key = 'genre' AND t.slug = 'drama';
  ```

- **Media by person attributes** (e.g., female & blonde):
  ```sql
  SELECT DISTINCT mi.*
  FROM media_items mi
  JOIN media_people mp ON mp.media_item_id = mi.id
  JOIN person_tags pt ON pt.person_id = mp.person_id
  JOIN tags t ON t.id = pt.tag_id
  JOIN tag_groups g ON g.id = t.group_id
  WHERE g.key = 'person-meta'
    AND t.slug IN ('female','blonde')
  GROUP BY mi.id
  HAVING COUNT(DISTINCT t.slug) = 2; -- all required attributes
  ```

**Indexes** to add early:
- `media_tags(media_item_id)`, `media_tags(tag_id)`
- `person_tags(person_id)`, `person_tags(tag_id)`
- `media_people(media_item_id)`, `media_people(person_id)`
- `tags(group_id)`, `tags(slug)`; `tag_groups(key)`

### 6.6 Cardinality enforcement (SINGLE vs MULTI)

- **Server**: on attach to an entity, if the target tag’s group is `SINGLE`, delete existing links in that group before inserting the new one (wrap in a transaction).
- **Frontend**: optimistic update replaces tags from the same group key while the mutation is in flight.

### 6.7 Migration sketch

1. Create `entity_types` and seed with `media_item`, `person`.
2. Add tables `tag_group_entity_types` and (optionally) `tag_entity_types`.
3. Create `person_tags` and (if not present) `media_people`.
4. Backfill: existing groups likely map to `[media_item]`.
5. Add constraints/triggers (or service-layer checks) for cardinality.

---

## 7. Domain Ports (Interfaces)

- **MediaQueryPort**: Read-only queries for media items.
- **MediaMutationPort**: Create/update/delete operations.
- **MediaAssetWriter**: Specialized for asset management.
- **MediaArtifactWriter**: Specialized for tags and persons.
- **FileOpsPort**: Abstraction over file system operations.
- **HashingPort**: Abstraction over hashing implementations.

## 8. Infrastructure Adapters

- **SQLAlchemy Repositories**: Implement domain ports against Postgres.
- **FFProbe Adapter**: Extracts metadata from media files.
- **FileOps Adapter**: Wraps `shutil` and `pathlib` safely.
- **Hashing Adapter**: Provides file hashing (e.g., SHA-256).

## 9. Services / Use Cases

- **IngestWorker**: Executes ingestion plans, moves files, checks
  duplicates, persists items.
- **ThreadManager**: Manages concurrency for long-running ingest
  tasks.
  - **In practice**: IngestWorker may delegate hashing and ffprobe
    probing to ThreadManager. For example, it can `submit()`
    multiple file-hashing jobs in parallel, collect results, and
    only proceed once all are finished. This balances speed
    (parallelism) with system safety (backpressure, cancellation).
- **API Routers**: Expose CRUD for MediaItems, Tags, People, Ratings.

## 10. Data Flow Example (Ingestion)

1. **Plan**: IngestPlanner creates an `IngestPlan` with
   `IngestPlanItems`.
2. **Execute**: IngestWorker runs the plan.
   - Hash file (potentially via ThreadManager in parallel).
   - Query repo to check duplicates.
   - Move file into media folder.
   - Persist MediaItem and related data.
3. **Report**: IngestWorker returns an `IngestReport`.

## 11. Testing Strategy

- **Database Tests**: Run against throwaway Postgres containers via
  `testcontainers`.
- **Domain Tests**: Verify invariants, side-effect-free policies, and
  serialization round-trips.
- **Service Tests**: End-to-end API tests via FastAPI TestClient.
- **Concurrency Tests**: Validate ThreadManager ordering,
  cancellation, backpressure.

## 12. File & Folder Structure

```
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
```

## 13. External Tools & Dependencies

- **FastAPI** — API framework.
- **SQLAlchemy** — ORM & database abstraction.
- **Alembic** — Migrations.
- **Pydantic v2** — Schemas & validation.
- **Testcontainers** — Ephemeral DBs for tests.
- **ffprobe (via subprocess)** — Media metadata extraction.

## 14. Future Extensions

- Pluggable storage backends (local FS, S3, etc.).
- Background job queue for ingest (Celery / RQ / custom thread manager).
- Advanced search (e.g., vector DB for perceptual hashes).
- Frontend integration for browsing and tagging.
