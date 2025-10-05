# Hexmedia Feature List

_This living document tracks everything shipped (Group A) and everything targeted for v1.0 (Group B). As we finish an item in Group B, we’ll move it to Group A. Items in Group B are ordered by priority._

---

## A) Shipped / Usable in the UX (✅)

### Core UX & Routing
- ✅ App shell with header, main content container, dark mode-friendly styles.
- ✅ Client-side routing: `/buckets`, `/bucket/:bucket`, `/bucket/:bucket/item/:id`, `/tools/ingest`, `/tools/thumbs`, `/settings/tags`.
- ✅ Route error boundary with friendly fallbacks.

### Media Browsing
- ✅ Buckets index & bucket view (uses ordered buckets + counts).
- ✅ Media grid cards with thumbnail, title, file path, compact tech line, and star rating control.
- ✅ Item Detail view with collage/video display, technical info strip, prev/next navigation.

### Ratings
- ✅ Frontend star rating (optimistic) on MediaCard and Item Detail.
- ✅ Backend rating endpoint wired (PUT `/api/ratings/media-items/:id`) and FE hooked up.
- ✅ Toast feedback on success/failure.

### Tagging (Media)
- ✅ Tag Groups CRUD in Settings > Tags (create, edit, delete, parent nesting, cardinality SINGLE/MULTI).
- ✅ Tags CRUD within a selected group (name, slug, description, optional parent).
- ✅ Tagging Panel on Item Detail:
  - ✅ SINGLE groups: dropdown add, chip remove.
  - ✅ MULTI groups: **MultiSelect popover** with search/filter and keyboard support.
  - ✅ Freeform (ungrouped) tags: typeahead search, create-on-enter, attach; chip remove.
- ✅ Optimistic attach/detach with cache reconciliation for bucket cards.

### Ingest & Thumbnails
- ✅ Ingest planning (preview list) and run; basic results summary (created/skipped paths).
- ✅ Thumbnail plan and run with options (regenerate, include_missing, policy).

### DevEx & Polish
- ✅ React Query caching + devtools.
- ✅ Global toast system (success/error) for key mutations and network failures.
- ✅ Favicon added to avoid 404s.
- ✅ API health probe hook.

---

## B) v1.0 Backlog / Prioritized (🚧)

### 1) People Domain & API (Foundations)
- [ ] **DB models**: `people`, `person_aliases`.
- [ ] **CRUD API**: create/read/update/delete Person, manage aliases.
- [ ] **Avatar/face-crop plumbing**: optional link to `media_assets` or dedicated table.
- _DoD_: endpoints with pydantic schemas, migrations, unit tests.

### 2) Tag Group **Scope** Model (Scalable)
- [ ] **Entity types** catalog (seed `media_item`, `person`).
- [ ] **tag_group_entity_types** M:N mapping (no brittle BOTH flag).
- [ ] (Optional) **tag_entity_types** for freeform tags.
- [ ] Validation: enforce scope at attach time.
- _DoD_: migrations, repo & service checks, regression tests; backfill existing groups → `media_item`.

### 3) Person Tagging (Person Metadata)
- [ ] **person_tags** junction table; service layer validation for cardinality.
- [ ] Add **PersonMeta** TagGroup example (scoped to `person`): sex, hair, age, etc.
- [ ] CRUD in Settings works for person-scoped groups/tags.
- _DoD_: attach/detach flows covered by tests; FE will consume in next item.

### 4) People ↔ Media Linking (UX)
- [ ] Item Detail sidebar **People** panel: search/add existing person, create new person, chip remove.
- [ ] Person detail drawer/page: show aliases, avatar, and **person tags** editor using MultiSelect popover.
- [ ] Optimistic cache updates; toasts.
- _DoD_: usable end‑to‑end linking and person tagging from the UI.

### 5) Search & Filters (Media + Person Attributes)
- [ ] Backend query endpoints to filter media by:
  - [ ] Direct media tags (by group/slug).
  - [ ] **Person attributes** via `media_people` → `person_tags` (AND semantics across selected attributes).
- [ ] Bucket view filters UI: facets by group; support person-attribute filters.
- [ ] URL-serializable filter state.
- _DoD_: performant queries with necessary indexes; UX responds quickly with loading state.

### 6) Multi‑Video Viewer & External Window Launch
- [ ] **Pop‑out player**: open the selected media item’s video in a separate browser window (same‑origin) with minimal chrome, via `window.open` and a lightweight player route.
- [ ] **Multi‑window support**: allow launching multiple videos at once for side‑by‑side viewing (no global singleton lock).
- [ ] **Controls integration**: play/pause/seek within each window; (Phase 2) optional “sync all” control to play/pause/seek across all open popouts.
- [ ] **Autoplay policies**: respect browser rules (require user gesture); offer muted‑autoplay toggle where helpful.
- [ ] **Navigation hooks**: add "Open in new window" to Item Detail and MediaCard context/actions.
- [ ] **State passing**: initial timestamp and poster passed via URL params/state; reconnect to item by ID for fresh data.
- [ ] **Resilience**: graceful fallback to new tab if pop‑up blocked; toast feedback.
- [ ] **Accessibility**: keyboard shortcuts for play/pause, seek, volume; articulate ARIA labels.
- [ ] **Security**: constrain window.opener access (`noopener,noreferrer`), same‑origin route only.
- _DoD_: multiple pop‑out windows can be opened and independently controlled; item loads reliably; blocked‑popup fallback works; documented limitations.

### 7) Pagination / Infinite Scroll in Bucket View
- [ ] Backend pagination (cursor or offset); FE infinite loader.
- [ ] Maintain filter/sort state across pages.
- _DoD_: smooth scroll, no layout thrash; measured rendering budget.

### 8) Group Tree Enhancements in Settings
- [ ] **Move/Re-parent** Tag Groups (use existing `useMoveTagGroup` endpoint).
- [ ] Reorder siblings; persist order.
- [ ] Scope editor (select entity types a group applies to).
- _DoD_: drag & drop or explicit controls; toasts; optimistic updates.

### 9) Performance & Prefetch
- [ ] Preload next/prev Item Detail assets.
- [ ] Memoization/virtualization in large tag lists.
- [ ] Fine-grained React Query cache timings for heavy endpoints.
- _DoD_: Lighthouse/React profiler deltas documented.

### 10) Bulk Operations
- [ ] Multi-select in bucket view and **bulk tag attach/detach** (use existing `useAttachTagsBulk`).
- [ ] Bulk move between buckets (if supported by backend).
- _DoD_: cohesive selection model; progress UI & error handling.

### 11) Error/Empty/Skeleton States Coverage
- [ ] Consistent empty states and skeleton loaders across routes.
- [ ] Centralized network error presentation.
- _DoD_: documented component patterns; no raw exceptions in UX.

### 12) Admin/Debug Utilities
- [ ] Ratings reset/remove endpoint + UI affordance.
- [ ] System status panel (API health + version/build info).
- _DoD_: gated under /settings or dev-only flag.

### 13) Tests & Migrations
- [ ] DB migrations for new tables with rollback scripts.
- [ ] Service tests for scope enforcement and cardinality.
- [ ] Basic FE E2E happy-path: tagging, rating, linking people.
- _DoD_: green CI, reproducible test seeds.

---

## Parking Lot (Nice-to-haves, post‑v1.0)
- Vector similarity for face crops (assist person linking).
- Saved searches & smart playlists.
- Keyboard shortcuts (J/K nav, quick-tagging hotkeys).
- Media asset management: download/originals and derived artifacts lifecycle.
- Import/export of tags, persons, and mappings (JSON/CSV).

---

## Legend / Notes
- **SINGLE vs MULTI** group cardinality: enforced FE+BE.
- **Scope**: Tag groups apply to entity types via mapping; freeform tags may declare scope directly.
- **Definition of Done (DoD)**: implementation + tests + UX polish + toasts + docs update.

---

## How we maintain this doc
- When a backlog item ships, move it under **Group A** with a ✅.
- Keep Group B ordered by priority. Adjust as architecture or product needs change.

