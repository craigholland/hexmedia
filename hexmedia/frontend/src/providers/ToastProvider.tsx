import { createContext, useCallback, useContext, useMemo, useState } from "react";

type Toast = { id: string; kind: "success" | "error" | "info"; message: string };
type Ctx = {
  toasts: Toast[];
  push: (t: Omit<Toast, "id">) => void;
  remove: (id: string) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
};

const ToastCtx = createContext<Ctx | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const remove = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = `${t.kind}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setToasts((prev) => [...prev, { ...t, id }]);
    if (t.kind !== "error") {
      // auto-dismiss successes/infos
      setTimeout(() => remove(id), 2500);
    }
  }, [remove]);

  const success = useCallback((message: string) => push({ kind: "success", message }), [push]);
  const error   = useCallback((message: string) => push({ kind: "error", message }), [push]);
  const info    = useCallback((message: string) => push({ kind: "info", message }), [push]);

  const value = useMemo<Ctx>(() => ({ toasts, push, remove, success, error, info }), [toasts, push, remove, success, error, info]);

  return (
    <ToastCtx.Provider value={value}>
      {children}
      {/* Simple renderer; replace with your design system if you like */}
      <div className="fixed right-4 top-4 z-[9999] flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`rounded-lg border px-3 py-2 text-sm shadow ${
              t.kind === "error" ? "border-red-300 bg-red-50 text-red-700" :
              t.kind === "success" ? "border-green-300 bg-green-50 text-green-700" :
              "border-gray-300 bg-white text-gray-800"
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="font-medium capitalize">{t.kind}</span>
              <span className="flex-1">{t.message}</span>
              <button onClick={() => remove(t.id)} className="ml-2 text-xs text-gray-500 hover:underline">Dismiss</button>
            </div>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToasts() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToasts must be used within <ToastProvider>");
  return ctx;
}
