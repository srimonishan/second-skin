async function loadDetail() {
  const el = document.getElementById("detail-content");
  const params = new URLSearchParams(window.location.search);
  const date = params.get("date");

  if (!date) {
    el.innerHTML = '<p class="empty-state">No date specified.</p>';
    return;
  }

  try {
    const res = await fetch(MANIFEST_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`manifest fetch failed: ${res.status}`);
    const manifest = await res.json();
    const d = (manifest.designs || []).find((item) => item.date === date);

    if (!d) {
      el.innerHTML = '<p class="empty-state">No design found for that date.</p>';
      return;
    }

    const brief = d.brief || {};
    const badge = d.status === "partial-fallback"
      ? '<span class="badge">published via fallback — part of the pipeline had an off day</span>' : "";

    el.innerHTML = `
      <div class="detail-tile" style="background-image: url('${d.imageUrl}')"></div>
      <h2 class="detail-title">${escapeHtml(d.date)}</h2>
      <div class="detail-badges">
        <span class="badge">${escapeHtml(d.dayOfWeek || "")}</span>
        <span class="badge">${escapeHtml(d.weatherSummary || "")}</span>
        <span class="badge">${escapeHtml(brief.palette || "")}</span>
        <span class="badge">${escapeHtml(brief.motif || "")}</span>
        <span class="badge">${escapeHtml(brief.mood || "")}</span>
        ${d.communityWordUsed ? `<span class="badge">community word: ${escapeHtml(d.communityWordUsed)}</span>` : ""}
        ${badge}
      </div>
      <p class="detail-note">${escapeHtml(d.designerNote || "")}</p>
      <p class="detail-style-note">${escapeHtml(d.styleNote || "")}</p>
      <a class="download-link" href="${d.imageUrl}" target="_blank" rel="noopener">Download this tile ↗</a>
    `;
  } catch (err) {
    el.innerHTML = `<p class="empty-state">Couldn't load this design (${escapeHtml(err.message)}).</p>`;
  }
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

loadDetail();
