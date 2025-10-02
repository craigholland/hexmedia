export default function SkeletonCard() {
  return (
    <article
      style={{
        display: "grid",
        gridTemplateRows: "auto 1fr",
        gap: 8,
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 8,
        background: "#fff",
      }}
    >
      <div style={{ height: 180, background: "#f3f4f6", borderRadius: 6 }} />
      <div>
        <div style={{ height: 16, width: "70%", background: "#f3f4f6", borderRadius: 4, marginBottom: 6 }} />
        <div style={{ display: "flex", gap: 6 }}>
          <div style={{ height: 16, width: 80, background: "#f3f4f6", borderRadius: 999 }} />
          <div style={{ height: 16, width: 60, background: "#f3f4f6", borderRadius: 999 }} />
          <div style={{ height: 16, width: 90, background: "#f3f4f6", borderRadius: 999 }} />
        </div>
      </div>
    </article>
  );
}
