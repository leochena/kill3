(() => {
  const $ = (id) => document.getElementById(id);

  const state = {
    me: null, // {lat, lon}
    pickMode: false,
    map: null,
    meMarker: null,
    layer: null,
    messages: [],
    config: null,
    pendingImages: [],
  };

  function randId(prefix) {
    const a = new Uint8Array(8);
    crypto.getRandomValues(a);
    return (
      prefix +
      Date.now().toString(16) +
      Array.from(a)
        .map((x) => x.toString(16).padStart(2, "0"))
        .join("")
    );
  }

  function ensureActor() {
    if (!$("actorId").value.trim()) $("actorId").value = randId("web_");
    return $("actorId").value.trim();
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
    if (!res.ok) {
      const err = new Error(data.error || res.statusText || "request failed");
      err.data = data;
      err.status = res.status;
      throw err;
    }
    return data;
  }

  function setLocStatus(text) {
    $("locStatus").textContent = text;
  }

  function applyMeToForm() {
    if (!state.me) return;
    $("lat").value = String(state.me.lat);
    $("lon").value = String(state.me.lon);
  }

  function updateMeMarker() {
    if (!state.map || !state.me) return;
    const ll = [state.me.lat, state.me.lon];
    if (!state.meMarker) {
      state.meMarker = L.circleMarker(ll, {
        radius: 9,
        color: "#3dd6c6",
        fillColor: "#3dd6c6",
        fillOpacity: 0.9,
      })
        .addTo(state.map)
        .bindPopup("我的位置");
    } else {
      state.meMarker.setLatLng(ll);
    }
    state.map.setView(ll, Math.max(state.map.getZoom(), 13));
  }

  function initMap() {
    const tileUrl = state.config?.tile_url || "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
    const attr = state.config?.tile_attribution || "&copy; OpenStreetMap";
    state.map = L.map("map").setView([52.52, 13.405], 11);
    L.tileLayer(tileUrl, { maxZoom: 19, attribution: attr }).addTo(state.map);
    state.layer = L.layerGroup().addTo(state.map);
    state.map.on("click", (e) => {
      if (!state.pickMode) return;
      state.me = { lat: +e.latlng.lat.toFixed(6), lon: +e.latlng.lng.toFixed(6) };
      applyMeToForm();
      updateMeMarker();
      setLocStatus(`Map pick ${state.me.lat}, ${state.me.lon}`);
      state.pickMode = false;
      $("btnMapPick").textContent = "Map pick";
    });
  }

  function locateMe() {
    setLocStatus("定位中…");
    if (!navigator.geolocation) {
      setLocStatus("浏览器不支持定位，请手填或地图选点");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        state.me = {
          lat: +pos.coords.latitude.toFixed(6),
          lon: +pos.coords.longitude.toFixed(6),
        };
        applyMeToForm();
        updateMeMarker();
        setLocStatus(`已定位 ±${Math.round(pos.coords.accuracy || 0)}m`);
        refreshList();
      },
      (err) => {
        setLocStatus("定位失败: " + (err.message || err.code) + "（可地图选点）");
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 10000 }
    );
  }

  const VERTICAL_DEFAULTS = {
    goods_unique: { mode: "one_to_many", role: "seller", needCourier: false },
    goods_stock: { mode: "one_to_many", role: "seller", needCourier: false },
    food_order: { mode: "one_to_many", role: "buyer", needCourier: true },
    ride: { mode: "broadcast_claim", role: "buyer", needCourier: true },
    errand: { mode: "one_to_many", role: "buyer", needCourier: true },
    service: { mode: "one_to_many", role: "buyer", needCourier: false },
    bulk_rfq: { mode: "one_to_many", role: "buyer", needCourier: false },
  };

  function matchBlock() {
    const maxA = Math.max(1, parseInt($("maxAccepts").value || "1", 10));
    return {
      mode: $("mode").value,
      vertical: $("vertical").value,
      max_accepts: maxA,
      exclusive: maxA <= 1,
    };
  }

  function money(amount, currency) {
    if (!amount) return null;
    return { amount: String(amount), currency: currency || "CNY" };
  }

  function guessMime(uri) {
    const u = uri.toLowerCase();
    if (u.endsWith(".png")) return "image/png";
    if (u.endsWith(".webp")) return "image/webp";
    if (u.endsWith(".gif")) return "image/gif";
    if (u.endsWith(".pdf")) return "application/pdf";
    if (u.endsWith(".jpg") || u.endsWith(".jpeg")) return "image/jpeg";
    return "image/jpeg";
  }

  function parseNum(id) {
    const v = $(id).value.trim();
    if (!v) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function buildWhere() {
    const region = $("region").value.trim();
    const lat = parseNum("lat");
    const lon = parseNum("lon");
    const radius = parseNum("placeRadius");
    const privacy = $("privacy").value;
    if (!region && lat == null && lon == null) return null;
    if ((lat == null) !== (lon == null)) throw new Error("纬度/经度需同时填写");
    const where = { privacy };
    if (region) where.region = region;
    if (lat != null && lon != null) {
      where.geo = { lat, lon };
      if (radius != null) where.geo.radius_m = radius;
    }
    return where;
  }

  function buildMessage() {
    const role = $("role").value;
    const display = $("display").value.trim() || "anon";
    const actor = ensureActor();
    const title = $("title").value.trim();
    const amount = $("amount").value.trim();
    const currency = $("currency").value.trim() || "CNY";
    const notes = $("notes").value.trim() || null;
    const needCourier = $("needCourier").checked;
    const match = matchBlock();
    const where = buildWhere();
    const imageUris = ($("imageUris")?.value || "")
      .split(/\n|,/)
      .map((s) => s.trim())
      .filter(Boolean)
      .concat(state.pendingImages || []);
    const attachments = imageUris.map((uri) => ({
      uri,
      mime: guessMime(uri),
      sha256: null,
    }));
    const base = {
      v: 1,
      id: randId("fm"),
      ts: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
      from: {
        id: actor,
        display,
        roles: [role === "buyer" ? "buyer" : role === "seller" ? "seller" : "courier"],
      },
      sig: null,
    };
    if (!title && role !== "courier") throw new Error("Please fill title");
    if (role === "buyer") {
      return {
        ...base,
        type: "want",
        ttl_sec: 172800,
        body: {
          item: {
            title,
            qty: 1,
            tags: [match.vertical],
            description: notes,
            attachments: attachments.length ? attachments : undefined,
          },
          budget: money(amount, currency),
          where,
          need_courier: needCourier || match.vertical === "ride" || match.vertical === "food_order",
          notes,
          match,
        },
      };
    }
    if (role === "seller") {
      return {
        ...base,
        type: "have",
        ttl_sec: 604800,
        body: {
          item: {
            title,
            condition: "used",
            tags: [match.vertical],
            description: notes,
            attachments: attachments.length ? attachments : undefined,
          },
          price: money(amount, currency),
          where,
          stock: match.vertical === "goods_stock" ? 10 : 1,
          notes,
          match,
        },
      };
    }
    const target = $("threadId").value.trim() || title;
    if (!target) throw new Error("快递/司机：先点选目标单");
    return {
      ...base,
      type: "courier.offer",
      body: {
        target_id: target,
        fee: money(amount || "0", currency) || { amount: "0", currency },
        eta: notes,
        vehicle: $("region").value.trim() || null,
        message: notes,
        match,
        where,
      },
    };
  }

  async function postMessage() {
    $("postResult").textContent = "发送中…";
    try {
      const msg = buildMessage();
      const data = await api("/api/v1/messages", { method: "POST", body: JSON.stringify(msg) });
      $("postResult").textContent = JSON.stringify(data, null, 2);
      $("threadId").value = data.id || msg.id;
      await refreshList();
    } catch (e) {
      $("postResult").textContent = JSON.stringify(e.data || { error: e.message }, null, 2);
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function renderList(messages) {
    const root = $("list");
    root.innerHTML = "";
    if (!messages.length) {
      root.innerHTML = '<div class="s">暂无消息</div>';
      return;
    }
    for (const m of messages) {
      const el = document.createElement("div");
      el.className = "item";
      const title = m.title || m.body?.item?.title || m.type;
      const price = m.price || m.body?.price || m.body?.budget || m.body?.fee;
      const priceText = price ? `${price.amount} ${price.currency}` : "-";
      const region = m.region || m.body?.where?.region || "";
      const from = m.display || m.from || "";
      const match = m.body?.match || {};
      const modeBadge = match.mode ? `<span class="badge">${escapeHtml(match.mode)}</span>` : "";
      const vertBadge = match.vertical ? `<span class="badge">${escapeHtml(match.vertical)}</span>` : "";
      const distBadge = m.distance_text
        ? `<span class="badge dist">${escapeHtml(m.distance_text)}</span>`
        : m.lat != null
          ? `<span class="badge">geo</span>`
          : "";
      const imgBadge =
        m.image_count > 0 ? `<span class="badge">${m.image_count} img</span>` : "";
      const thumb =
        m.thumb_uri && String(m.thumb_uri).match(/\.(png|jpe?g|webp|gif)(\?|$)/i)
          ? `<img class="thumb" src="${escapeHtml(m.thumb_uri)}" alt="" />`
          : "";
      el.innerHTML = `<div class="rowish">${thumb}<div><div class="t"><span class="badge">${escapeHtml(m.type)}</span>${distBadge}${imgBadge}${modeBadge}${vertBadge}${escapeHtml(String(title))}</div>
        <div class="s">${escapeHtml(String(priceText))} · ${escapeHtml(String(region || "no region"))} · ${escapeHtml(String(from))} · <code>${escapeHtml(m.id)}</code></div>
        <div class="s">${escapeHtml(String(m.description || "").slice(0, 120))}</div></div></div>`;
      el.onclick = () => {
        $("threadId").value = m.id;
        $("reviewActor").value = typeof m.from === "string" ? m.from : m.from?.id || "";
        if ($("distOtherId").value && $("distOtherId").value !== m.id) {
          /* keep B */
        } else if ($("threadId").dataset.last) {
          $("distOtherId").value = $("threadId").dataset.last;
        }
        $("threadId").dataset.last = m.id;
        loadThread();
        if (m.lat != null && m.lon != null && state.map) {
          state.map.setView([m.lat, m.lon], 14);
        }
      };
      root.appendChild(el);
    }
  }

  function renderMapMarkers(messages) {
    if (!state.layer) return;
    state.layer.clearLayers();
    const bounds = [];
    for (const m of messages) {
      if (m.lat == null || m.lon == null) continue;
      const ll = [m.lat, m.lon];
      bounds.push(ll);
      const title = m.title || m.type;
      const dist = m.distance_text ? `<br/>距你 ${escapeHtml(m.distance_text)}` : "";
      const marker = L.marker(ll).bindPopup(
        `<b>${escapeHtml(title)}</b><br/>${escapeHtml(m.type)} · ${escapeHtml(m.region || "")}${dist}<br/><code>${escapeHtml(m.id)}</code>`
      );
      marker.on("click", () => {
        $("threadId").value = m.id;
      });
      state.layer.addLayer(marker);
    }
    if (state.me) bounds.push([state.me.lat, state.me.lon]);
    if (bounds.length >= 2) {
      try {
        state.map.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
      } catch (_) {}
    }
  }

  async function refreshList() {
    const type = $("filterType").value.trim();
    const q = $("filterQ").value.trim();
    const region = $("filterRegion").value.trim();
    const params = new URLSearchParams({ summary: "1", limit: "100" });
    if (type) params.set("type", type);
    if (q) params.set("q", q);
    if (region) params.set("region", region);
    const sort = $("filterSort").value;
    params.set("sort", sort);
    if ($("onlyGeo").checked) params.set("require_geo", "1");

    const lat = state.me?.lat ?? parseNum("lat");
    const lon = state.me?.lon ?? parseNum("lon");
    const radius = parseNum("filterRadius");
    if (lat != null && lon != null) {
      params.set("near_lat", String(lat));
      params.set("near_lon", String(lon));
      if (radius != null) params.set("radius_m", String(radius));
    }

    try {
      const data = await api("/api/v1/messages?" + params.toString());
      state.messages = data.messages || [];
      renderList(state.messages);
      renderMapMarkers(state.messages);
    } catch (e) {
      $("list").textContent = e.message;
    }
  }

  async function loadThread() {
    const id = $("threadId").value.trim();
    if (!id) return;
    try {
      const data = await api("/api/v1/thread/" + encodeURIComponent(id));
      const st = data.status ? `\nSTATUS: ${data.status.label} (${data.status.status})\n` : "";
      $("threadView").textContent = st + JSON.stringify(data, null, 2);
    } catch (e) {
      $("threadView").textContent = JSON.stringify(e.data || { error: e.message }, null, 2);
    }
  }

  async function loadTrack() {
    const id = $("threadId").value.trim();
    if (!id) return;
    try {
      const data = await api("/api/v1/track/" + encodeURIComponent(id));
      $("threadView").textContent = JSON.stringify(data, null, 2);
    } catch (e) {
      $("threadView").textContent = JSON.stringify(e.data || { error: e.message }, null, 2);
    }
  }

  async function uploadSelectedFile() {
    const input = $("imageFile");
    if (!input?.files?.length) {
      setLocStatus("Choose a file first");
      return;
    }
    const file = input.files[0];
    const buf = await file.arrayBuffer();
    let binary = "";
    const bytes = new Uint8Array(buf);
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    const b64 = btoa(binary);
    try {
      const data = await api("/api/v1/media", {
        method: "POST",
        body: JSON.stringify({
          filename: file.name,
          mime: file.type || "application/octet-stream",
          content_base64: b64,
        }),
      });
      state.pendingImages.push(data.uri);
      const cur = $("imageUris").value.trim();
      $("imageUris").value = cur ? cur + "\n" + data.uri : data.uri;
      setLocStatus("Uploaded " + data.uri);
    } catch (e) {
      setLocStatus("Upload failed: " + e.message);
    }
  }

  async function refreshHealth() {
    try {
      const h = await api("/health");
      state.config = h.maps || state.config;
      $("healthMeta").textContent =
        `OK · msg=${h.stats?.count ?? "?"} · fee=${h.policy?.platform_fee} · boost=${h.policy?.paid_boost} · geo=haversine`;
    } catch (e) {
      $("healthMeta").textContent = "Board offline: " + e.message;
    }
  }

  async function loadReviews() {
    const actor = $("reviewActor").value.trim();
    if (!actor) return;
    try {
      const data = await api("/api/v1/reviews/" + encodeURIComponent(actor));
      $("threadView").textContent = JSON.stringify(data, null, 2);
    } catch (e) {
      $("threadView").textContent = JSON.stringify(e.data || { error: e.message }, null, 2);
    }
  }

  async function distanceAB() {
    const a = $("threadId").value.trim();
    const b = $("distOtherId").value.trim();
    if (!a || !b) {
      $("threadView").textContent = "Need message A and B ids";
      return;
    }
    try {
      const data = await api(
        `/api/v1/distance?from_id=${encodeURIComponent(a)}&to_id=${encodeURIComponent(b)}`
      );
      $("threadView").textContent = JSON.stringify(data, null, 2);
    } catch (e) {
      $("threadView").textContent = JSON.stringify(e.data || { error: e.message }, null, 2);
    }
  }

  async function nlSearch() {
    const nl = ($("nlSearch")?.value || "").trim();
    if (!nl) return;
    // client-side lightweight parse mirroring server heuristics
    const qMatch = nl.replace(/under\s+\d+.*/i, "").replace(/within\s+\d+.*/i, "").trim();
    if (qMatch) $("filterQ").value = qMatch;
    const m = nl.match(/within\s+(\d+(?:\.\d+)?)\s*(km|m)?/i);
    if (m) {
      const val = parseFloat(m[1]);
      const unit = (m[2] || "km").toLowerCase();
      $("filterRadius").value = String(unit === "m" ? val : val * 1000);
    }
    $("filterSort").value = "distance";
    if (!state.me && parseNum("lat") == null) locateMe();
    else refreshList();
  }

  $("btnPost").onclick = postMessage;
  $("btnRefresh").onclick = refreshList;
  $("btnNear").onclick = () => {
    if (!state.me && parseNum("lat") == null) locateMe();
    else refreshList();
  };
  $("btnLocate").onclick = locateMe;
  $("btnMapPick").onclick = () => {
    state.pickMode = !state.pickMode;
    $("btnMapPick").textContent = state.pickMode ? "Click map…(again to cancel)" : "Map pick";
    setLocStatus(state.pickMode ? "Click the map to set coordinates" : "Pick cancelled");
  };
  $("btnThread").onclick = loadThread;
  if ($("btnTrack")) $("btnTrack").onclick = loadTrack;
  if ($("btnUpload")) $("btnUpload").onclick = uploadSelectedFile;
  if ($("btnNlSearch")) $("btnNlSearch").onclick = nlSearch;
  $("btnReviews").onclick = loadReviews;
  $("btnDist").onclick = distanceAB;
  $("vertical").addEventListener("change", () => {
    const d = VERTICAL_DEFAULTS[$("vertical").value];
    if (!d) return;
    $("mode").value = d.mode;
    $("role").value = d.role;
    $("needCourier").checked = d.needCourier;
  });
  ["filterType", "filterQ", "filterRegion", "filterRadius", "filterSort"].forEach((id) => {
    $(id).addEventListener("change", refreshList);
    $(id).addEventListener("keydown", (e) => {
      if (e.key === "Enter") refreshList();
    });
  });
  $("onlyGeo").addEventListener("change", refreshList);

  ensureActor();
  (async () => {
    try {
      state.config = await api("/api/v1/config");
    } catch (_) {
      state.config = null;
    }
    initMap();
    refreshHealth();
    refreshList();
    setInterval(refreshHealth, 15000);
  })();
})();
