import { useMemo } from "react";
import { useGroupTags } from "@/lib/hooks"; // from your updated hooks.ts
import MultiSelectPopover from "./MultiSelectPopover";
import type { TagRead } from "@/types";

export default function GroupMultiSelector({
  groupId,
  selectedTags,
  onChangeSelectedIds,
  className,
}: {
  groupId: string;
  selectedTags: TagRead[];
  onChangeSelectedIds: (ids: string[]) => void; // do your optimistic attach/detach here
  className?: string;
}) {
  const { items, isLoading, q, setQ, fetchNext, hasMore } = useGroupTags(groupId, { limit: 50 });

  const selectedIds = useMemo(() => selectedTags.map((t) => String(t.id)), [selectedTags]);

  return (
    <div className={className}>
      <MultiSelectPopover
        items={items}
        selectedIds={selectedIds}
        onChange={onChangeSelectedIds}
        loading={isLoading}
        searchValue={q}
        onSearchChange={setQ}
        trigger={({ open }) => (
          <button
            type="button"
            onClick={open}
            className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm hover:bg-gray-50"
          >
            Add / Edit tags
          </button>
        )}
      />
      {hasMore && (
        <button
          type="button"
          onClick={fetchNext}
          className="ml-2 rounded-lg border border-gray-300 px-2 py-1.5 text-xs hover:bg-gray-50"
        >
          Load more
        </button>
      )}
    </div>
  );
}
