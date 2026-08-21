document.getElementById("submit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("word-input");
  const status = document.getElementById("submit-status");
  const word = input.value.trim();
  if (!word) return;

  status.textContent = "Sending…";
  try {
    const res = await fetch(SUBMIT_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ word }),
    });
    const data = await res.json();
    if (data.status === "accepted") {
      status.textContent = `Accepted — "${word}" is queued for the studio's next design.`;
      input.value = "";
    } else if (data.status === "rejected") {
      status.textContent = `Not accepted: ${data.reason || "didn't pass review"}.`;
    } else {
      status.textContent = data.error || "Something went wrong.";
    }
  } catch (err) {
    status.textContent = "Couldn't reach the studio right now — try again in a moment.";
  }
});
