// src/types.ts
export interface Asset {
  id: string
  kind:
    | 'video'
    | 'proxy'
    | 'thumb'
    | 'collage'
    | 'contact'
    | 'contact_sheet'
    | 'contactsheet'
  url: string
  // ...rest
}
// --- Buckets ---
export type BucketsCount = Record<string, number>

// --- Identity ---
export interface MediaIdentityOut {
  media_folder: string
  identity_name: string
  video_ext: string
}

// --- People ---
export interface PersonRead {
  id: string
  display_name: string
  normalized_name?: string | null
}

// --- Tags ---
export type Cardinality = 'SINGLE' | 'MULTI'

export type TagGroupRead = {
  id: string
  parent_id?: string | null
  key: string
  display_name: string
  description?: string | null
  cardinality: Cardinality
  path?: string
  depth?: number
  children?: TagGroupRead[]
}

export type TagGroupCreate = {
  parent_id?: string | null
  key: string
  display_name: string
  description?: string | null
  cardinality?: Cardinality
}

export type TagGroupUpdate = Partial<TagGroupCreate>
// When fetching a tree, each node is a group with nested children.
export type TagGroupNode = TagGroupRead & { children: TagGroupNode[] }

// Move semantics can vary by backend. This flexible type satisfies the FE:
// - Move under a new parent (inside)
// - Or position relative to a sibling
export type TagGroupMove = {
  new_parent_id?: string | null
  position?: 'before' | 'after' | 'inside'
  sibling_id?: string | null
}

export type TagRead = {
  id: string
  group_id?: string | null
    group_path?: string | null
  name: string
  slug: string
  description?: string | null
  parent_id?: string | null
    parent_path?: string | null
}

export type TagCreate = {
  group_id?: string | null
  name: string
  slug?: string
  description?: string | null
  parent_id?: string | null
}

export type TagUpdate = Partial<TagCreate>


// --- Assets ---
export interface MediaAssetRead {
  id: string
  kind: string // e.g. 'thumb' | 'collage' | 'video' | ...
  url: string
    rel_path?: string | null
  width?: number | null
  height?: number | null
}

// --- Cards (what /media-items/by-bucket returns) ---
export interface MediaItemCardRead {
  id: string
  bucket?: string
  title?: string | null
  release_year?: number | null

  identity: MediaIdentityOut

  duration_sec?: number | null
  width?: number | null
  height?: number | null
  rating?: number | null

  thumb_url?: string | null
  assets?: MediaAssetRead[] | null

  persons?: PersonRead[] | null
  tags?: TagRead[] | null
}

// --- Ingest / Thumbs (lightweight placeholders so hooks compile) ---
export interface IngestPlanItem { [k: string]: any }
export interface IngestRunResponse { [k: string]: any }
export interface ThumbPlanItem { [k: string]: any }
export interface ThumbResponse { [k: string]: any }
