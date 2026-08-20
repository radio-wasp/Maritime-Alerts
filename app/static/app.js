// Maritime Alerts - Interactive Live Map Client Logic

let map;
let markersGroup;
let allIncidents = [];
let activeCategory = 'all';
let activeRegion = 'all';
let refreshIntervalSeconds = 300;
let refreshCountdown = refreshIntervalSeconds;

const REGION_BOUNDS = {
  "all": { coords: [46.0000, -64.5000], zoom: 7, label: "All Maritimes (NS, NB, PEI)" },
  "Halifax": { coords: [44.6488, -63.5752], zoom: 11, label: "Halifax (HRM)" },
  "Moncton": { coords: [46.0878, -64.7782], zoom: 11, label: "Moncton / Dieppe (NB)" },
  "Saint John": { coords: [45.2733, -66.0633], zoom: 11, label: "Saint John (NB)" },
  "Fredericton": { coords: [45.9636, -66.6431], zoom: 11, label: "Fredericton (NB)" },
  "PEI": { coords: [46.2382, -63.1311], zoom: 10, label: "Charlottetown & PEI" },
  "Cape Breton": { coords: [46.1368, -60.1942], zoom: 10, label: "Cape Breton (CBRM)" },
  "Annapolis Valley": { coords: [45.0772, -64.4950], zoom: 10, label: "Annapolis Valley" },
  "South Shore": { coords: [44.3770, -64.5170], zoom: 10, label: "South Shore" },
  "North Shore": { coords: [45.3647, -63.2796], zoom: 10, label: "North Shore" }
};

const CATEGORY_COLORS = {
  "Structure Fire": { bg: "#EF4444", text: "#FCA5A5", border: "rgba(239, 68, 68, 0.4)" },
  "Highway Incident": { bg: "#38BDF8", text: "#BAE6FD", border: "rgba(56, 189, 248, 0.4)" },
  "Power Outage": { bg: "#FACC15", text: "#FEF08A", border: "rgba(250, 204, 21, 0.4)" },
  "Medical": { bg: "#3B82F6", text: "#93C5FD", border: "rgba(59, 130, 246, 0.4)" },
  "Rescue": { bg: "#F59E0B", text: "#FDE68A", border: "rgba(245, 158, 11, 0.4)" },
  "Alarm Activation": { bg: "#8B5CF6", text: "#DDD6FE", border: "rgba(139, 92, 246, 0.4)" },
  "Outside Fire": { bg: "#10B981", text: "#6EE7B7", border: "rgba(16, 185, 129, 0.4)" },
  "Hazmat": { bg: "#EC4899", text: "#FBCFE8", border: "rgba(236, 72, 153, 0.4)" },
  "Police Activity": { bg: "#94A3B8", text: "#CBD5E1", border: "rgba(148, 163, 184, 0.4)" },
  "General Fire": { bg: "#F97316", text: "#FDBA74", border: "rgba(249, 115, 22, 0.4)" }
};

document.addEventListener("DOMContentLoaded", () => {
  initIcons();
  initMap();
  bindEvents();
  loadData();
  startTimer();
});

function initIcons() {
  if (window.lucide) {
    lucide.createIcons();
  }
}

function initMap() {
  map = L.map("map", {
    center: REGION_BOUNDS["all"].coords,
    zoom: REGION_BOUNDS["all"].zoom,
    zoomControl: false
  });

  L.control.zoom({ position: "bottomright" }).addTo(map);

  const cartoTiles = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
  });

  const osmTiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19
  });

  cartoTiles.addTo(map);

  cartoTiles.on('tileerror', function() {
    if (!map.hasLayer(osmTiles)) {
      osmTiles.addTo(map);
    }
  });

  markersGroup = L.layerGroup().addTo(map);

  setTimeout(() => {
    map.invalidateSize();
  }, 250);

  window.addEventListener("resize", () => {
    map.invalidateSize();
  });
}

function bindEvents() {
  const regionSelect = document.getElementById("region-select");
  if (regionSelect) {
    regionSelect.addEventListener("change", (e) => {
      activeRegion = e.target.value;
      const targetRegion = REGION_BOUNDS[activeRegion] || REGION_BOUNDS["all"];
      map.flyTo(targetRegion.coords, targetRegion.zoom, { duration: 1.5 });
      document.getElementById("region-label").textContent = targetRegion.label;
      loadData();
    });
  }

  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      const target = e.currentTarget;
      target.classList.add("active");
      activeCategory = target.getAttribute("data-category");
      renderIncidents();
    });
  });

  document.getElementById("btn-refresh").addEventListener("click", () => {
    const icon = document.getElementById("refresh-icon");
    icon.classList.add("animate-spin");
    fetch("/api/refresh", { method: "POST" })
      .then(() => loadData())
      .finally(() => {
        setTimeout(() => icon.classList.remove("animate-spin"), 600);
      });
  });

  const tabMap = document.getElementById("tab-map");
  const tabFeed = document.getElementById("tab-feed");
  const mapContainer = document.getElementById("map-container");
  const sidebar = document.getElementById("sidebar");

  if (tabMap && tabFeed) {
    tabMap.addEventListener("click", () => {
      tabMap.className = "flex-1 py-2 text-center text-xs font-semibold text-sky-400 border-b-2 border-sky-500";
      tabFeed.className = "flex-1 py-2 text-center text-xs font-semibold text-slate-400";
      mapContainer.classList.remove("hidden");
      sidebar.classList.add("hidden");
      setTimeout(() => map.invalidateSize(), 150);
    });

    tabFeed.addEventListener("click", () => {
      tabFeed.className = "flex-1 py-2 text-center text-xs font-semibold text-sky-400 border-b-2 border-sky-500";
      tabMap.className = "flex-1 py-2 text-center text-xs font-semibold text-slate-400";
      sidebar.classList.remove("hidden");
      mapContainer.classList.add("hidden");
    });
  }
}

function loadData() {
  const regionParam = activeRegion === "all" ? "all" : activeRegion;
  Promise.all([
    fetch(`/api/incidents?region=${encodeURIComponent(regionParam)}`).then(r => r.json()),
    fetch("/api/burn-status").then(r => r.json())
  ])
  .then(([incidentsRes, burnRes]) => {
    if (incidentsRes.status === "success") {
      allIncidents = incidentsRes.data || [];
      document.getElementById("count-all").textContent = allIncidents.length;
      renderIncidents();
    }
    if (burnRes.status === "success" && burnRes.data) {
      document.getElementById("burn-status-text").textContent = burnRes.data.status;
    }
  })
  .catch(err => console.error("Data load error:", err));
}

function renderIncidents() {
  markersGroup.clearLayers();
  const feedContainer = document.getElementById("incident-feed");
  feedContainer.innerHTML = "";

  const filtered = activeCategory === "all"
    ? allIncidents
    : allIncidents.filter(inc => inc.category === activeCategory);

  document.getElementById("feed-count").textContent = filtered.length;

  if (filtered.length === 0) {
    feedContainer.innerHTML = `
      <div class="text-center py-12 text-slate-500 font-mono text-xs">
        No active incidents in this category.
      </div>
    `;
    return;
  }

  filtered.forEach(inc => {
    const colorInfo = CATEGORY_COLORS[inc.category] || CATEGORY_COLORS["General Fire"];
    const prov = inc.province || "NS";

    const customIcon = L.divIcon({
      className: "custom-map-marker",
      html: `
        <div style="
          background-color: ${colorInfo.bg};
          width: 22px;
          height: 22px;
          border-radius: 50%;
          border: 2px solid white;
          box-shadow: 0 0 10px ${colorInfo.bg};
          display: flex;
          align-items: center;
          justify-content: center;
        "></div>
      `,
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });

    const popupHtml = `
      <div class="space-y-1.5 font-sans">
        <div class="flex items-center justify-between gap-2 border-b border-slate-700 pb-1">
          <div class="flex items-center gap-1">
            <span class="text-[10px] font-mono font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-800 text-sky-400 border border-slate-700">${prov}</span>
            <span class="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded" style="background: ${colorInfo.bg}33; color: ${colorInfo.bg}; border: 1px solid ${colorInfo.bg}66;">
              ${inc.category}
            </span>
          </div>
          <span class="text-[10px] font-mono text-slate-400">${formatTimeAgo(inc.timestamp)}</span>
        </div>
        <h3 class="font-bold text-sm text-slate-100">${escapeHtml(inc.title)}</h3>
        <p class="text-xs text-slate-300 flex items-center gap-1">
          <span class="font-mono text-[11px] text-slate-400">📍 ${escapeHtml(inc.location)}</span>
        </p>
        <div class="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1 border-t border-slate-800">
          <span>${escapeHtml(inc.neighborhood || inc.region)}</span>
          <span class="text-amber-400 font-semibold">${inc.units} unit${inc.units > 1 ? 's' : ''}</span>
        </div>
      </div>
    `;

    const marker = L.marker([inc.lat, inc.lng], { icon: customIcon }).addTo(markersGroup);
    marker.bindPopup(popupHtml);

    marker.on("click", () => {
      highlightCard(inc.guid);
    });

    const card = document.createElement("div");
    card.id = `card-${inc.guid}`;
    card.className = "bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-xl p-3.5 transition-all cursor-pointer space-y-2 group";
    card.style.borderLeft = `4px solid ${colorInfo.bg}`;

    card.innerHTML = `
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-1.5">
          <span class="text-[10px] font-mono font-bold uppercase px-1.5 py-0.5 rounded bg-slate-900 text-sky-400 border border-slate-700">${prov}</span>
          <span class="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded" style="background: ${colorInfo.bg}22; color: ${colorInfo.bg}; border: 1px solid ${colorInfo.bg}44;">
            ${inc.category}
          </span>
        </div>
        <span class="text-[11px] font-mono text-slate-400 tabular-nums">${formatTimeAgo(inc.timestamp)}</span>
      </div>
      <h3 class="font-bold text-sm text-slate-100 group-hover:text-sky-400 transition-colors">${escapeHtml(inc.title)}</h3>
      <div class="text-xs text-slate-400 font-mono flex items-center gap-1.5">
        <i data-lucide="map-pin" class="w-3.5 h-3.5 text-slate-500 shrink-0"></i>
        <span class="truncate">${escapeHtml(inc.location)}</span>
      </div>
      <div class="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1.5 border-t border-slate-700/50">
        <span class="text-slate-300 font-medium">${escapeHtml(inc.neighborhood || inc.region)}</span>
        <span class="text-slate-400 bg-slate-900 px-2 py-0.5 rounded text-[10px]">${escapeHtml(inc.source)}</span>
      </div>
    `;

    card.addEventListener("click", () => {
      map.flyTo([inc.lat, inc.lng], 14, { duration: 1.2 });
      marker.openPopup();
      highlightCard(inc.guid);
    });

    feedContainer.appendChild(card);
  });

  initIcons();
  setTimeout(() => map.invalidateSize(), 100);
}

function highlightCard(guid) {
  document.querySelectorAll("#incident-feed > div").forEach(c => c.classList.remove("card-selected"));
  const card = document.getElementById(`card-${guid}`);
  if (card) {
    card.classList.add("card-selected");
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function formatTimeAgo(isoString) {
  if (!isoString) return "just now";
  const date = new Date(isoString);
  const now = new Date();
  const diffSec = Math.floor((now - date) / 1000);

  if (diffSec < 60) return "now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} min`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} hr`;
  return `${Math.floor(diffSec / 86400)} d`;
}

function startTimer() {
  setInterval(() => {
    refreshCountdown--;
    if (refreshCountdown <= 0) {
      refreshCountdown = refreshIntervalSeconds;
      loadData();
    }
    const mins = Math.floor(refreshCountdown / 60);
    const secs = String(refreshCountdown % 60).padStart(2, "0");
    const timerElem = document.getElementById("refresh-timer");
    if (timerElem) timerElem.textContent = `Refreshing in ${mins}:${secs}`;
  }, 1000);
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
