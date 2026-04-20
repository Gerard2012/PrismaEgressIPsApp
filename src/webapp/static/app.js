function setLoading(isLoading) {
  const spinner = document.getElementById("loading");
  const loadingText = document.getElementById("loadingText");
  const refreshBtn = document.getElementById("refreshBtn");
  const regionSelect = document.getElementById("regionSelect");

  if (isLoading) {
    spinner.classList.remove("hidden");
    loadingText.classList.remove("hidden");
    if (refreshBtn) refreshBtn.disabled = true;
    if (regionSelect) regionSelect.disabled = true;
  } else {
    spinner.classList.add("hidden");
    loadingText.classList.add("hidden");
    if (refreshBtn) refreshBtn.disabled = false;
    if (regionSelect) regionSelect.disabled = false;
  }
}

async function refreshData() {
  try {
    setLoading(true);

    const regionSelect = document.getElementById("regionSelect");
    const region = regionSelect ? regionSelect.value : "global";

    const response = await fetch(`/api/egress-ips?region=${encodeURIComponent(region)}`);

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();

    const table = document.getElementById("egressTable");
    table.innerHTML = "";

    data.forEach(row => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.zone ?? ""}</td>
        <td>${row.service_type ?? ""}</td>
        <td>${row.node_names ?? ""}</td>
        <td>${row.address ?? ""}</td>
      `;
      table.appendChild(tr);
    });

  } catch (err) {
    console.error(err);
    alert("Failed to load data. Check logs for details.");
  } finally {
    setLoading(false);
  }
}

// Initial load
document.addEventListener("DOMContentLoaded", refreshData);