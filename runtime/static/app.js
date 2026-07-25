(() => {
  const $ = (id) => document.getElementById(id);

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
    if (!$("actorId").value.trim()) {
      $("actorId").value = randId("web_");
    }
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

  async function refreshHealth() {
    try {
      const h = await api("/health");
      $("healthMeta").textContent =
        `OK · messages=${h.stats?.count ?? "?"} · fee=${h.policy?.platform_fee} · mod=${h.policy?.content_moderation} · kyc=${h.policy?.kyc_required}`;
    } catch (e) {
      $("healthMeta").textContent = "板子未连接: " + e.message;
    }
  }

  function money(amount, currency) {
    if (!amount) return null;
    return { amount: String(amount), currency: currency || "CNY" };
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

  function buildMessage() {
    const role = $("role").value;
    const display = $("display").value.trim() || "anon";
    const actor = ensureActor();
    const title = $("title").value.trim();
    const amount = $("amount").value.trim();
    const currency = $("currency").value.trim() || "CNY";
    const region = $("region").value.trim();
    const notes = $("notes").value.trim() || null;
    const needCourier = $("needCourier").checked;
    const match = matchBlock();
    const base = {
      v: 1,
      id: randId("fm"),
      ts: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
      from: { id: actor, display, roles: [role === "buyer" ? "buyer" : role === "seller" ? "seller" : "courier"] },
      sig: null,
    };
    if (!title && role !== "courier") throw new Error("请填写标题");
    if (role === "buyer") {
      return {
        ...base,
        type: "want",
        ttl_sec: 172800,
        body: {
          item: { title, qty: 1, tags: [match.vertical] },
          budget: money(amount, currency),
          where: region ? { region } : null,
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
          item: { title, condition: "used", tags: [match.vertical] },
          price: money(amount, currency),
          where: region ? { region } : null,
          stock: match.vertical === "goods_stock" ? 10 : 1,
          notes,
          match,
        },
      };
    }
    const target = $("threadId").value.trim() || title;
    if (!target) throw new Error("快递/司机：先点选目标单，或把 target id 填在标题栏");
    return {
      ...base,
      type: "courier.offer",
      body: {
        target_id: target,
        fee: money(amount || "0", currency) || { amount: "0", currency },
        eta: notes,
        vehicle: region || null,
        message: notes,
        match,
      },
    };
  }

  $("vertical").addEventListener("change", () => {
    const d = VERTICAL_DEFAULTS[$("vertical").value];
    if (!d) return;
    $("mode").value = d.mode;
    $("role").value = d.role;
    $("needCourier").checked = d.needCourier;
  });

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
      el.innerHTML = `<div class="t"><span class="badge">${escapeHtml(m.type)}</span>${modeBadge}${vertBadge}${escapeHtml(String(title))}</div>
        <div class="s">${escapeHtml(String(priceText))} · ${escapeHtml(String(region || "未填地区"))} · ${escapeHtml(String(from))} · <code>${escapeHtml(m.id)}</code></div>`;
      el.onclick = () => {
        $("threadId").value = m.id;
        $("reviewActor").value = typeof m.from === "string" ? m.from : m.from?.id || "";
        loadThread();
      };
      root.appendChild(el);
    }
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  async function refreshList() {
    const type = $("filterType").value.trim();
    const q = $("filterQ").value.trim();
    const region = $("filterRegion").value.trim();
    const params = new URLSearchParams({ summary: "1", limit: "100" });
    if (type) params.set("type", type);
    if (q) params.set("q", q);
    if (region) params.set("region", region);
    try {
      const data = await api("/api/v1/messages?" + params.toString());
      renderList(data.messages || []);
    } catch (e) {
      $("list").textContent = e.message;
    }
  }

  async function loadThread() {
    const id = $("threadId").value.trim();
    if (!id) return;
    try {
      const data = await api("/api/v1/thread/" + encodeURIComponent(id));
      $("threadView").textContent = JSON.stringify(data, null, 2);
    } catch (e) {
      $("threadView").textContent = JSON.stringify(e.data || { error: e.message }, null, 2);
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

  $("btnPost").onclick = postMessage;
  $("btnRefresh").onclick = refreshList;
  $("btnThread").onclick = loadThread;
  $("btnReviews").onclick = loadReviews;
  ["filterType", "filterQ", "filterRegion"].forEach((id) => {
    $(id).addEventListener("change", refreshList);
    $(id).addEventListener("keydown", (e) => {
      if (e.key === "Enter") refreshList();
    });
  });

  ensureActor();
  refreshHealth();
  refreshList();
  setInterval(refreshHealth, 15000);
})();
