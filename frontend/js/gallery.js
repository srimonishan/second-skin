async function loadGallery() {
  const el = document.getElementById("gallery");
  try {
    const res = await fetch(MANIFEST_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`manifest fetch failed: ${res.status}`);
    const manifest = await res.json();
    const designs = manifest.designs || [];

    if (designs.length === 0) {
      el.innerHTML = '<p class="empty-state">The studio hasn\'t opened yet — check back after the first daily run.</p>';
      return;
    }

    el.innerHTML = designs.map(renderCard).join("");
  } catch (err) {
    el.innerHTML = `<p class="empty-state">Couldn't load the studio right now (${escapeHtml(err.message)}). Try refreshing.</p>`;
  }
}

function renderCard(d) {
  const badge = d.status === "partial-fallback" ? '<span class="badge">fallback day</span>' : "";
  return `
    <a class="card" href="detail.html?date=${encodeURIComponent(d.date)}">
      <div class="swatch" style="background-image: url('${d.imageUrl}')"></div>
      <div class="card-body">
        <div class="date">${escapeHtml(d.date)} · ${escapeHtml(d.dayOfWeek || "")}</div>
        <div class="meta">${escapeHtml((d.brief && d.brief.mood) || "")} · ${escapeHtml(d.weatherSummary || "")}</div>
        ${badge}
      </div>
    </a>`;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

loadGallery();
