import { useMemo } from "react";
import type { TagRead } from "@/types";
import TagChip from "./TagChip";

type Props = {
  tags?: TagRead[] | null;
  maxLines?: number; // UI-only cap converted to chip count
  maxChips?: number; // direct chip cap; default ~2 lines worth
};

export default function TagChipList({ tags, maxChips = 6 }: Props) {
  const list = tags ?? [];
  const visible = useMemo(() => list.slice(0, maxChips), [list, maxChips]);
  const overflow = Math.max(0, list.length - visible.length);

  if (!list.length) return null;

  return (
    <div className="flex flex-wrap gap-1">
      {visible.map((t) => (
        <TagChip key={String(t.id)} tag={t} />
      ))}
      {overflow > 0 && (
        <span className="inline-flex items-center rounded-full border border-gray-200 px-2 py-0.5 text-xs text-gray-500">
          +{overflow} more
        </span>
      )}
    </div>
  );
}
