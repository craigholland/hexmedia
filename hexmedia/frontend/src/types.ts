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
export interface TagRead {
  id: string
  name: string
  slug?: string | null | undefined
}

// --- Assets ---
export interface MediaAssetRead {
  id: string
  kind: string // e.g. 'thumb' | 'collage' | 'video' | ...
  url: string
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
