import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TagRead } from "@/types";

type Item = TagRead; // expects { id: string; name: string; ... }

type MultiSelectPopoverProps = {
  items: Item[];
  selectedIds: string[];
  onChange: (nextSelectedIds: string[]) => void;

  // Button/trigger provided by caller
  trigger: (args: { open: () => void; isOpen: boolean }) => JSX.Element;

  // Optional
  getItemKey?: (item: Item) => string;
  getItemLabel?: (item: Item) => string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  loading?: boolean;
  emptyLabel?: string;
  className?: string;
  onOpenChange?: (open: boolean) => void;
  disabled?: boolean;
};

export default function MultiSelectPopover(props: MultiSelectPopoverProps) {
  const {
    items,
    selectedIds,
    onChange,
    trigger,
    getItemKey = (i) => (i as any).id,
    getItemLabel = (i) => (i as any).name ?? (i as any).label ?? "",
    searchValue,
    onSearchChange,
    searchPlaceholder = "Filter…",
    loading = false,
    emptyLabel = "No results",
    className = "",
    onOpenChange,
    disabled = false,
  } = props;

  const [isOpen, setIsOpen] = useState(false);
  const [internalSearch, setInternalSearch] = useState("");
  const search = searchValue ?? internalSearch;
  const setSearch = onSearchChange ?? setInternalSearch;

  const popoverRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  const [activeIndex, setActiveIndex] = useState<number>(-1);

  useEffect(() => {
    onOpenChange?.(isOpen);
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 0);
    else setActiveIndex(-1);
  }, [isOpen, onOpenChange]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => getItemLabel(it).toLowerCase().includes(q));
  }, [items, search, getItemLabel]);

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const toggle = useCallback(
    (id: string) => {
      const next = new Set(selectedSet);
      next.has(id) ? next.delete(id) : next.add(id);
      onChange(Array.from(next));
    },
    [selectedSet, onChange]
  );

  // click outside to close
  useEffect(() => {
    if (!isOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (!popoverRef.current) return;
      if (popoverRef.current.contains(e.target as Node)) return;
      setIsOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [isOpen]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) return;
    const max = filtered.length - 1;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => (i < max ? i + 1 : 0));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => (i > 0 ? i - 1 : max));
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      if (activeIndex >= 0 && activeIndex <= max) {
        e.preventDefault();
        const item = filtered[activeIndex];
        toggle(getItemKey(item));
      }
      return;
    }
    if (e.key === "Escape" || e.key === "Tab") setIsOpen(false);
  };

  const open = () => {
    if (!disabled) setIsOpen(true);
  };

  return (
    <div className={`relative inline-block text-left ${className}`} ref={popoverRef} onKeyDown={onKeyDown}>
      {trigger({ open, isOpen })}

      {isOpen && (
        <div className="absolute z-50 mt-2 w-72 rounded-xl border border-gray-200 bg-white shadow-lg" role="dialog" aria-modal="true">
          <div className="p-2">
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm outline-none focus:border-gray-400"
              aria-label="Filter tags"
            />
          </div>

          <ul ref={listRef} className="max-h-64 overflow-auto py-1" role="listbox" aria-multiselectable="true">
            {loading && <li className="px-3 py-2 text-sm text-gray-500">Loading…</li>}
            {!loading && filtered.length === 0 && <li className="px-3 py-2 text-sm text-gray-500">{emptyLabel}</li>}
            {!loading &&
              filtered.map((item, idx) => {
                const id = getItemKey(item);
                const label = getItemLabel(item);
                const active = idx === activeIndex;
                const checked = selectedSet.has(id);
                return (
                  <li
                    key={id}
                    role="option"
                    aria-selected={checked}
                    className={`flex cursor-pointer items-center gap-2 px-3 py-2 text-sm ${active ? "bg-gray-100" : ""}`}
                    onMouseEnter={() => setActiveIndex(idx)}
                    onClick={() => toggle(id)}
                    tabIndex={-1}
                  >
                    <input type="checkbox" readOnly checked={checked} className="pointer-events-none h-4 w-4" aria-hidden="true" />
                    <span className="truncate">{label}</span>
                  </li>
                );
              })}
          </ul>

          <div className="flex items-center justify-between border-t border-gray-200 px-3 py-2">
            <button className="rounded-lg px-3 py-1.5 text-sm hover:bg-gray-100" onClick={() => setIsOpen(false)}>
              Done
            </button>
            <button className="rounded-lg px-3 py-1.5 text-sm text-red-600 hover:bg-red-50" onClick={() => onChange([])}>
              Clear all
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
