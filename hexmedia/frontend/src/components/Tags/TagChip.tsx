import type { TagRead } from "@/types";

export default function TagChip({ tag }: { tag: TagRead }) {
  return (
    <span className="inline-flex items-center rounded-full border border-gray-200 px-2 py-0.5 text-xs text-gray-700">
      {tag.name}
    </span>
  );
}
