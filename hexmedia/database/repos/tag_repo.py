from __future__ import annotations
from typing import Optional, List, Iterable, Dict
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from hexmedia.database.models.taxonomy import Tag, TagGroup, MediaTag
from hexmedia.common.naming.slugger import slugify
from hexmedia.domain.enums import Cardinality


class TagRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve_group_path(self, path: str) -> Optional[TagGroup]:
        """
        Resolve 'vehicles/automobile/exterior_color' to a TagGroup by exact path.
        """
        norm = "/".join([slugify(p) for p in path.split("/") if p.strip()])
        stmt = select(TagGroup).where(TagGroup.path == norm).limit(1)
        return self.db.execute(stmt).scalars().first()

    def get_group(self, group_id: UUID) -> Optional[TagGroup]:
        return self.db.get(TagGroup, group_id)

    def list_group_tree(self) -> List[TagGroup]:
        """
        Return all groups; router can nest into a tree on the fly.
        (Small size expected; otherwise we can do recursive CTE ordering.)
        """
        stmt = select(TagGroup).order_by(TagGroup.path.asc())
        return self.db.execute(stmt).scalars().all()

    # ---------- Group mutations ----------

    def _compute_path(self, key: str, parent: Optional[TagGroup]) -> tuple[str, int]:
        skey = slugify(key)
        if parent is None:
            return skey, 0
        return f"{parent.path}/{skey}", parent.depth + 1

    def create_group(
        self,
        *,
        key: str,
        display_name: Optional[str] = None,
        cardinality: Cardinality = Cardinality.MULTI,
        description: Optional[str] = None,
        parent_id: Optional[UUID] = None,
        parent_path: Optional[str] = None,
    ) -> TagGroup:
        parent: Optional[TagGroup] = None
        if parent_id:
            parent = self.get_group(parent_id)
            if not parent:
                raise ValueError("Parent group not found")
        elif parent_path:
            parent = self.resolve_group_path(parent_path)
            if not parent and parent_path.strip():
                raise ValueError("Parent group path not found")

        path, depth = self._compute_path(key, parent)
        obj = TagGroup(
            parent_id=parent.id if parent else None,
            key=slugify(key),
            display_name=display_name or key.title(),
            cardinality=cardinality,
            description=description,
            path=path,
            depth=depth,
        )
        self.db.add(obj)
        return obj

    def rename_group(self, group_id: UUID, *, new_key: str, new_display_name: Optional[str] = None) -> TagGroup:
        grp = self.get_group(group_id)
        if not grp:
            raise ValueError("Group not found")
        parent = grp.parent
        new_path, _ = self._compute_path(new_key, parent)

        old_prefix = grp.path + "/"
        grp.key = slugify(new_key)
        grp.display_name = new_display_name or grp.display_name
        grp.path = new_path

        # Update descendants' paths
        descendants = self.db.execute(
            select(TagGroup).where(TagGroup.path.like(f"{old_prefix}%"))
        ).scalars().all()
        for d in descendants:
            d.path = d.path.replace(old_prefix, new_path + "/", 1)
            d.depth = d.path.count("/")  # recompute

        return grp

    def move_group(self, group_id: UUID, *, new_parent_id: Optional[UUID] = None, new_parent_path: Optional[str] = None) -> TagGroup:
        grp = self.get_group(group_id)
        if not grp:
            raise ValueError("Group not found")

        new_parent: Optional[TagGroup] = None
        if new_parent_id:
            new_parent = self.get_group(new_parent_id)
            if not new_parent and new_parent_id is not None:
                raise ValueError("New parent not found")
        elif new_parent_path:
            new_parent = self.resolve_group_path(new_parent_path)
            if not new_parent and new_parent_path.strip():
                raise ValueError("New parent path not found")

        # Prevent cycles (basic guard)
        if new_parent and (new_parent.id == grp.id or new_parent.path.startswith(grp.path + "/")):
            raise ValueError("Cannot move a group under its own descendant")

        grp.parent_id = new_parent.id if new_parent else None
        new_path, new_depth = self._compute_path(grp.key, new_parent)
        old_prefix = grp.path + "/"
        grp.path = new_path
        grp.depth = new_depth

        # Update descendants
        descendants = self.db.execute(
            select(TagGroup).where(TagGroup.path.like(f"{old_prefix}%"))
        ).scalars().all()
        for d in descendants:
            d.path = d.path.replace(old_prefix, new_path + "/", 1)
            d.depth = d.path.count("/")

        return grp

    # ---------- Tags (same as before, but allow group by path) ----------

    def get_group_for_tag_ops(self, group_key: Optional[str], group_path: Optional[str]) -> Optional[TagGroup]:
        if group_path:
            grp = self.resolve_group_path(group_path)
            if not grp:
                raise ValueError("TagGroup (by path) not found")
            return grp
        if group_key:
            # resolve by (parent_id, key) requires parent context; prefer path for uniqueness.
            # As a fallback, resolve by unique path when parent unknown:
            stmt = select(TagGroup).where(func.lower(TagGroup.key) == slugify(group_key)).limit(2)
            rows = self.db.execute(stmt).scalars().all()
            if len(rows) == 1:
                return rows[0]
            raise ValueError("Ambiguous group key; use group_path or id")
        return None

    def create_tag(
        self,
        *,
        name: str,
        group_key: Optional[str] = None,
        group_path: Optional[str] = None,
        parent_id: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> Tag:
        grp = self.get_group_for_tag_ops(group_key, group_path)
        group_id = grp.id if grp else None

        t = Tag(name=name, slug=slugify(name), group_id=group_id, parent_id=parent_id, description=description)
        self.db.add(t)
        return t

    # def find_or_create_path(self, group_path: str, path: Iterable[str]) -> Tag:
    #     grp = self.resolve_group_path(group_path)
    #     if not grp:
    #         raise ValueError("TagGroup not found")
    #     parent = None
    #     for part in path:
    #         s = slugify(part)
    #         stmt = select(Tag).where(and_(Tag.group_id == grp.id, Tag.slug == s, Tag.parent_id == (parent.id if parent else None))).limit(1)
    #         existing = self.db.execute(stmt).scalars().first()
    #         if existing:
    #             parent = existing
    #         else:
    #             parent = Tag(group_id=grp.id, name=part, slug=s, parent_id=(parent.id if parent else None))
    #             self.db.add(parent)
    #             self.db.flush()
    #     return parent


    def list_groups(self) -> List[TagGroup]:
        stmt = select(TagGroup).order_by(TagGroup.key.asc())
        return self.db.execute(stmt).scalars().all()

    def get_group_by_key(self, key: str) -> Optional[TagGroup]:
        stmt = select(TagGroup).where(func.lower(TagGroup.key) == key.lower())
        return self.db.execute(stmt).scalars().first()

    # ----- tags -----
    def list_tags(self, group_key: Optional[str] = None) -> List[Tag]:
        stmt = select(Tag)
        if group_key:
            grp = self.get_group_by_key(group_key)
            if not grp:
                return []
            stmt = stmt.where(Tag.group_id == grp.id)
        return self.db.execute(stmt.order_by(Tag.slug.asc())).scalars().all()

    def find_or_create_path(self, group_key: str, path: Iterable[str]) -> Tag:
        """Ensure a hierarchical tag path exists under group; returns leaf tag."""
        grp = self.get_group_by_key(group_key)
        if not grp:
            raise ValueError("TagGroup not found")
        parent = None
        for part in path:
            s = slugify(part)
            stmt = select(Tag).where(and_(Tag.group_id == grp.id, Tag.slug == s, Tag.parent_id == (parent.id if parent else None))).limit(1)
            existing = self.db.execute(stmt).scalars().first()
            if existing:
                parent = existing
            else:
                parent = Tag(group_id=grp.id, name=part, slug=s, parent_id=(parent.id if parent else None))
                self.db.add(parent)
                self.db.flush()
        return parent

    # ----- media links -----
    def list_tags_for_media(self, media_item_id: UUID) -> List[Tag]:
        stmt = (
            select(Tag)
            .join(MediaTag, MediaTag.tag_id == Tag.id)
            .where(MediaTag.media_item_id == media_item_id)
            .order_by(Tag.slug.asc())
        )
        return self.db.execute(stmt).scalars().all()

    def add_tag_to_media(self, media_item_id: UUID, tag_id: UUID) -> None:
        # uniqueness enforced by constraint; rely on db to dedup
        self.db.add(MediaTag(media_item_id=media_item_id, tag_id=tag_id))

    def remove_tag_from_media(self, media_item_id: UUID, tag_id: UUID) -> None:
        from sqlalchemy import delete
        self.db.execute(delete(MediaTag).where(and_(MediaTag.media_item_id == media_item_id, MediaTag.tag_id == tag_id)))

    def list_for_media(self, media_item_id: UUID) -> List[Tag]:
        """
        Tags for a single media item.
        """
        stmt = (
            select(Tag)
            .join(MediaTag, MediaTag.tag_id == Tag.id)
            .where(MediaTag.media_item_id == media_item_id)
            .order_by(Tag.name.asc())
        )
        return [row[0] for row in self.db.execute(stmt).all()]

    def batch_tags_for_items(self, media_item_ids: Iterable[UUID]) -> Dict[UUID, List[Tag]]:
        """
        Map of media_item_id -> [Tag] for a list of items.
        """
        ids = list(media_item_ids)
        if not ids:
            return {}
        stmt = (
            select(MediaTag.media_item_id, Tag)
            .join(Tag, Tag.id == MediaTag.tag_id)
            .where(MediaTag.media_item_id.in_(ids))
            .order_by(MediaTag.media_item_id.asc(), Tag.name.asc())
        )
        out: Dict[UUID, List[Tag]] = {}
        for mid, tag in self.db.execute(stmt).all():
            out.setdefault(mid, []).append(tag)
        return out