/* Aigram Control Panel — vanilla SPA (no build step). */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === "class") node.className = v;
      else if (k === "html") node.innerHTML = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined) node.setAttribute(k, v);
    }
    for (const c of [].concat(children)) {
      if (c == null) continue;
      node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    }
    return node;
  }

  // ---- token / state ----
  const State = {
    token: "",
    kind: "all",
    query: "",
    entity: null, // {id, kind, display_name, ...}
  };

  function tokenFromUrl() {
    const m = new URLSearchParams(location.search).get("token");
    return m || "";
  }

  // ---- api ----
  async function api(path, { method = "GET", body = null } = {}) {
    const opts = { method, headers: { Authorization: "Bearer " + State.token } };
    if (body) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
    const res = await fetch("/api" + path, opts);
    let data = null;
    try { data = await res.json(); } catch (_) { data = null; }
    if (!res.ok) {
      const msg = (data && data.error) || `Request failed (${res.status})`;
      const err = new Error(msg); err.status = res.status; err.retry_after = data && data.retry_after;
      throw err;
    }
    return data;
  }

  function mediaUrl(path) {
    const sep = path.includes("?") ? "&" : "?";
    return path + sep + "t=" + encodeURIComponent(State.token);
  }
  function avatarUrl(id, real) {
    return mediaUrl(`/api/avatar/${id}?real=${real ? 1 : 0}`);
  }

  // ---- toast ----
  let toastTimer = null;
  function toast(msg, bad = false) {
    const t = $("#toast");
    t.textContent = msg;
    t.className = "toast show" + (bad ? " bad" : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.className = "toast"; }, 3200);
  }

  // ---- gate ----
  async function tryUnlock(token) {
    State.token = token;
    // /setup/status validates the token and tells us whether to run the wizard
    try {
      const su = await api("/setup/status");
      localStorage.setItem("panel_token", token);  // persist for installed PWA
      $("#gate").classList.add("hidden");
      $("#app").classList.remove("hidden");
      if (su.needs_setup) renderWizard();
      else boot();
      return true;
    } catch (e) {
      if (e.status === 401) {
        // A stale saved token (e.g. the panel rotated it) must not auto-fail
        // forever — drop it so the gate is usable and a fresh ?token= works.
        localStorage.removeItem("panel_token");
        sessionStorage.removeItem("panel_token");
      }
      $("#gate-err").textContent = e.status === 401 ? "Invalid token." : (e.message || "Failed");
      return false;
    }
  }

  function initGate() {
    const saved = tokenFromUrl() || localStorage.getItem("panel_token") || sessionStorage.getItem("panel_token") || "";
    $("#gate-go").addEventListener("click", () => tryUnlock($("#gate-token").value.trim()));
    $("#gate-token").addEventListener("keydown", (e) => { if (e.key === "Enter") tryUnlock($("#gate-token").value.trim()); });
    if (saved) { $("#gate-token").value = saved; tryUnlock(saved); }
  }

  // ---- status / account ----
  async function loadStatus() {
    try {
      const s = await api("/status");
      const nameEl = $("#me-name");
      nameEl.textContent = s.account.name || s.account.username || "Account";
      nameEl.setAttribute("dir", "auto");
      const connected = s.client === "connected";
      $("#me-dot").className = "status-dot" + (connected ? " online" : "");
      $("#me-status").textContent =
        (connected ? "online" : "degraded") +
        (s.monitoring ? " · bot live" : "") + " · " + (s.provider || "");
      const me = s.account.id;
      if (me) $("#me-avatar").src = avatarUrl(me, true);
      if (!connected) showBanner("Bot not connected — showing cached data only.");
    } catch (e) { /* token gate handles */ }
  }

  function showBanner(text) {
    if ($("#banner")) return;
    const b = el("div", { id: "banner", class: "banner", text });
    $("#app").insertBefore(b, $(".topbar").nextSibling);
  }

  // ---- sidebar / dialogs ----
  let searchTimer = null;
  function initSidebar() {
    $$("#kind-tabs .tab").forEach((t) =>
      t.addEventListener("click", () => {
        $$("#kind-tabs .tab").forEach((x) => x.classList.remove("active"));
        t.classList.add("active");
        State.kind = t.dataset.kind;
        loadDialogs();
      })
    );
    $("#search").addEventListener("input", (e) => {
      clearTimeout(searchTimer);
      State.query = e.target.value.trim();
      searchTimer = setTimeout(loadDialogs, 250);
    });
    $("#refresh").addEventListener("click", async () => {
      $("#refresh").textContent = "…";
      try { await api("/dialogs/refresh?type=" + State.kind, { method: "POST" }); await loadDialogs(); toast("Refreshed from Telegram"); }
      catch (e) { toast(e.message, true); }
      finally { $("#refresh").textContent = "⟳"; }
    });
  }

  function skeletonList() {
    const list = $("#dialog-list");
    list.innerHTML = "";
    for (let i = 0; i < 8; i++) list.appendChild(el("div", { class: "skel" }));
  }

  async function loadDialogs() {
    skeletonList();
    try {
      const q = State.query ? "&q=" + encodeURIComponent(State.query) : "";
      const data = await api(`/dialogs?type=${State.kind}${q}`);
      renderDialogs(data.items);
    } catch (e) {
      $("#dialog-list").innerHTML = "";
      $("#dialog-list").appendChild(el("div", { class: "muted", style: "padding:14px", text: e.message }));
    }
  }

  function renderDialogs(items) {
    const list = $("#dialog-list");
    list.innerHTML = "";
    if (!items.length) {
      list.appendChild(el("div", { class: "muted", style: "padding:18px;text-align:center", text: "No chats found." }));
      return;
    }
    for (const it of items) {
      const img = el("img", { class: "avatar md", alt: "", src: avatarUrl(it.id, false) });
      // lazy-upgrade to real photo if available
      maybeRealAvatar(img, it);
      const row = el("div", { class: "dialog-row", onclick: () => selectEntity(it) }, [
        img,
        el("div", { class: "meta" }, [
          el("div", { class: "name", dir: "auto", text: it.display_name || String(it.id) }),
          el("div", { class: "sub", dir: "auto", text: it.preview || it.username || ("id " + it.id) }),
        ]),
        el("span", { class: "kind-badge kind-" + it.kind, text: it.kind }),
      ]);
      row.dataset.id = it.id;
      list.appendChild(row);
    }
  }

  // Lazy real-photo upgrade (only when enabled + visible). Ban-safe: viewport only.
  let realPhotosEnabled = false;
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting && realPhotosEnabled) {
        const img = e.target;
        if (img.dataset.upgraded) continue;
        img.dataset.upgraded = "1";
        const real = new Image();
        real.onload = () => { img.src = real.src; };
        real.src = avatarUrl(img.dataset.eid, true);
        io.unobserve(img);
      }
    }
  });
  function maybeRealAvatar(img, it) {
    if (!it.has_photo) return;
    img.dataset.eid = it.id;
    io.observe(img);
  }

  // ---- entity view (chat) ----
  async function selectEntity(it) {
    State.entity = it;
    closeDrawers();
    clearReply();
    $$(".dialog-row").forEach((r) => r.classList.toggle("active", r.dataset.id == it.id));
    $("#empty-main").classList.add("hidden");
    $("#entity-view").classList.remove("hidden");
    const nameEl = $("#ev-name");
    nameEl.textContent = it.display_name || String(it.id);
    nameEl.setAttribute("dir", "auto");
    const sub = $("#ev-sub");
    sub.innerHTML = "";
    sub.appendChild(el("span", { class: "kind-badge kind-" + it.kind, text: it.kind }));
    if (it.username) sub.appendChild(el("span", { text: it.username }));
    const wrap0 = $("#ev-avatar").parentElement;
    const oldDot = wrap0.querySelector(".status-dot"); if (oldDot) oldDot.remove();
    $("#ev-avatar").src = avatarUrl(it.id, true);
    loadEntityHeader(it);  // presence / members (1 throttled RPC), async
    const input = $("#composer-input");
    input.value = "";
    autoGrow(input);
    setSendEnabled(false);
    await loadChat();
    input.focus();
  }

  // ---- presence / header detail ----
  function lastSeen(iso) {
    const d = new Date(iso), now = new Date();
    const diff = (now - d) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return Math.floor(diff / 60) + "m ago";
    if (sameDay(d, now)) return "at " + clockTime(iso);
    if (diff < 172800) return "yesterday";
    return d.toLocaleDateString();
  }
  function presenceLabel(p) {
    if (!p) return null;
    switch (p.state) {
      case "online": return { text: "online", cls: "online" };
      case "recently": return { text: "last seen recently", cls: "recently" };
      case "last_week": return { text: "last seen within a week", cls: "recently" };
      case "last_month": return { text: "last seen within a month", cls: "offline" };
      case "offline": return { text: p.was_online ? "last seen " + lastSeen(p.was_online) : "offline", cls: "offline" };
      default: return null;
    }
  }
  async function loadEntityHeader(it) {
    let d;
    try { d = await api(`/entity/${it.id}`); } catch (_) { return; }
    if (!State.entity || State.entity.id !== it.id) return;  // user switched chats
    State.entityDetail = d;
    const sub = $("#ev-sub");
    sub.innerHTML = "";
    sub.appendChild(el("span", { class: "kind-badge kind-" + it.kind, text: it.kind }));
    const wrap = $("#ev-avatar").parentElement;
    let dot = wrap.querySelector(".status-dot");
    const pl = presenceLabel(d.presence);
    if (pl) {
      if (!dot) { dot = el("span", { class: "status-dot" }); wrap.appendChild(dot); }
      dot.className = "status-dot " + pl.cls;
      sub.appendChild(el("span", { class: "pres " + pl.cls, text: pl.text }));
    } else {
      if (dot) dot.remove();
      if ((it.kind === "group" || it.kind === "channel") && d.member_count) {
        const noun = it.kind === "channel" ? " subscribers" : " members";
        sub.appendChild(el("span", { text: d.member_count.toLocaleString() + noun }));
      } else if (it.username || d.username) {
        sub.appendChild(el("span", { text: it.username || d.username }));
      }
    }
    if (d.is_bot) sub.appendChild(el("span", { class: "faint", text: "bot" }));
  }

  function initEntityActions() {
    $("#ev-ai-btn").addEventListener("click", openAi);
    $("#composer-ai").addEventListener("click", openAi);
    $("#ev-media-btn").addEventListener("click", openProfile);
    $("#ev-name").addEventListener("click", openProfile);
    $("#ev-avatar").addEventListener("click", openProfile);
    const input = $("#composer-input");
    input.addEventListener("input", () => { autoGrow(input); setSendEnabled(input.value.trim().length > 0); });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (input.value.trim()) sendMessage(); }
    });
    $("#composer-send").addEventListener("click", sendMessage);
  }

  function setSendEnabled(on) { $("#composer-send").disabled = !on; }
  function autoGrow(t) { t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 168) + "px"; }

  // AI commands + shared media open as overlays over the chat
  function openModal(title, render) {
    const modal = $("#modal"), body = $("#modal-body");
    $("#modal-title").textContent = title;
    body.innerHTML = "<div class='muted'>Loading…</div>";
    modal.classList.remove("hidden");
    Promise.resolve()
      .then(() => render(body))
      .catch((e) => { body.innerHTML = `<div class='err'>${esc(e.message)}</div>`; });
  }
  function openAi() {
    if (!State.entity) return;
    openModal("✨ AI · " + (State.entity.display_name || State.entity.id), (body) => { body.innerHTML = ""; renderCommands(body, State.entity); });
  }
  // ---- profile drawer (info card + Telegram-style shared-media tabs) ----
  const PROFILE_TABS = [
    { key: "media", label: "Media" },
    { key: "document", label: "Files" },
    { key: "voice", label: "Voice" },
    { key: "music", label: "Music" },
    { key: "gif", label: "GIFs" },
    { key: "url", label: "Links" },
  ];
  function openProfile() {
    if (!State.entity) return;
    openModal(State.entity.display_name || String(State.entity.id), (body) => renderProfile(body, State.entity));
  }
  async function renderProfile(body, it) {
    body.innerHTML = "";
    const card = el("div", { class: "profile-card" });
    card.appendChild(el("img", { class: "avatar lg", alt: "", src: avatarUrl(it.id, true) }));
    const info = el("div", { class: "profile-info" });
    info.appendChild(el("div", { class: "profile-name", dir: "auto", text: it.display_name || String(it.id) }));
    const subline = el("div", { class: "profile-sub" });
    const bio = el("div", { class: "profile-bio", dir: "auto" });
    info.appendChild(subline);
    info.appendChild(bio);
    card.appendChild(info);
    body.appendChild(card);

    const tabbar = el("div", { class: "profile-tabs tabs" });
    const pane = el("div", { class: "profile-pane" });
    let active = "media";
    PROFILE_TABS.forEach((t) => {
      const b = el("button", {
        class: "tab" + (t.key === active ? " active" : ""), text: t.label,
        onclick: () => {
          active = t.key;
          $$(".tab", tabbar).forEach((x) => x.classList.toggle("active", x === b));
          loadProfileTab(pane, it, t.key);
        },
      });
      tabbar.appendChild(b);
    });
    body.appendChild(tabbar);
    body.appendChild(pane);
    loadProfileTab(pane, it, active);

    try {
      const p = await api(`/entity/${it.id}/profile`);
      subline.innerHTML = "";
      if (p.username) subline.appendChild(el("span", { text: p.username }));
      const pl = presenceLabel(p.presence);
      if (pl) subline.appendChild(el("span", { class: "pres " + pl.cls, text: pl.text }));
      else if (p.member_count) {
        const noun = it.kind === "channel" ? " subscribers" : " members";
        subline.appendChild(el("span", { text: p.member_count.toLocaleString() + noun }));
      }
      subline.appendChild(el("span", { class: "faint", text: "id " + it.id }));
      if (p.about) bio.textContent = p.about;
    } catch (_) { /* info is best-effort */ }
  }

  function firstUrl(text) {
    const m = (text || "").match(/https?:\/\/[^\s]+/);
    return m ? m[0] : null;
  }
  function fmtSize(b) {
    if (!b) return "";
    const u = ["B", "KB", "MB", "GB"]; let i = 0, n = b;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return n.toFixed(n < 10 && i > 0 ? 1 : 0) + u[i];
  }
  async function loadProfileTab(pane, it, kind) {
    pane.innerHTML = "<div class='muted'>Loading…</div>";
    try {
      const data = await api(`/entity/${it.id}/media?kind=${kind}&limit=40`);
      pane.innerHTML = "";
      if (!data.items.length) { pane.innerHTML = "<div class='muted'>Nothing here yet.</div>"; return; }
      const fileOf = (m) => mediaUrl(`/api/entity/${it.id}/media/${m.message_id}/file`);
      const thumbOf = (m) => mediaUrl(`/api/entity/${it.id}/media/${m.message_id}/thumb`);
      if (kind === "media" || kind === "gif") {
        const grid = el("div", { class: "media-grid" });
        for (const m of data.items) {
          const tile = el("div", { class: "media-tile", onclick: () => window.open(fileOf(m), "_blank") },
            el("span", { class: "badge2", text: m.kind }));
          tile.appendChild(el("img", { loading: "lazy", src: thumbOf(m) }));
          grid.appendChild(tile);
        }
        pane.appendChild(grid);
      } else if (kind === "voice" || kind === "music") {
        const list = el("div", { class: "profile-list" });
        for (const m of data.items) {
          list.appendChild(el("div", { class: "profile-li" }, [
            el("span", { class: "li-name", dir: "auto", text: m.file_name || (kind === "voice" ? "Voice message" : "Audio") }),
            el("audio", { class: "m-audio", controls: "", preload: "none", src: fileOf(m) }),
          ]));
        }
        pane.appendChild(list);
      } else if (kind === "url") {
        const list = el("div", { class: "profile-list" });
        for (const m of data.items) {
          list.appendChild(el("a", { class: "profile-li link", href: firstUrl(m.text) || "#", target: "_blank", rel: "noopener", dir: "auto", text: m.text }));
        }
        pane.appendChild(list);
      } else {
        const list = el("div", { class: "profile-list" });
        for (const m of data.items) {
          list.appendChild(el("a", { class: "profile-li", href: fileOf(m), target: "_blank", rel: "noopener" }, [
            el("span", { class: "li-ic", text: "📄" }),
            el("span", { class: "li-name", dir: "auto", text: m.file_name || m.mime || "File" }),
            m.size ? el("span", { class: "li-size", text: fmtSize(m.size) }) : null,
          ]));
        }
        pane.appendChild(list);
      }
    } catch (e) { pane.innerHTML = `<div class='muted'>${esc(e.message)}</div>`; }
  }

  // command cards
  function card(title, icon, desc, fields, run) {
    const inputs = {};
    const fieldWrap = el("div", { class: "fields" });
    const toggles = [];
    for (const f of fields) {
      let input;
      if (f.type === "check") {
        input = el("input", { type: "checkbox" });
        inputs[f.key] = input;
        toggles.push(el("label", { class: "toggle" }, [
          input,
          el("span", { class: "track" }, el("span", { class: "thumb" })),
          el("span", { class: "toggle-label", text: f.label }),
        ]));
        continue;
      }
      if (f.type === "textarea") input = el("textarea", { placeholder: f.ph || "", dir: "auto" });
      else if (f.type === "select") input = el("select", {}, f.options.map((o) => el("option", { value: o.v, text: o.t })));
      else input = el("input", { type: "text", placeholder: f.ph || "", value: f.value || "", dir: "auto" });
      inputs[f.key] = input;
      fieldWrap.appendChild(el("div", { class: "field" }, [
        f.label ? el("label", { class: "field-label", text: f.label }) : null,
        input,
      ]));
    }
    const btn = el("button", { class: "btn btn-primary", onclick: () => {
      const vals = {};
      for (const [k, inp] of Object.entries(inputs)) vals[k] = inp.type === "checkbox" ? inp.checked : inp.value;
      run(vals, btn);
    }}, [el("span", { text: "Run" }), el("span", { class: "btn-arrow", html: "&rarr;" })]);
    const foot = el("div", { class: "card-foot" }, [el("div", { class: "toggles" }, toggles), btn]);
    return el("div", { class: "card" }, [
      el("div", { class: "card-head" }, [el("span", { class: "card-icon", text: icon }), el("h3", { text: title })]),
      el("p", { class: "desc", text: desc }),
      fieldWrap,
      foot,
    ]);
  }

  function renderCommands(pane, it) {
    pane.innerHTML = "";
    const grid = el("div", { class: "card-cmds" });
    const chatScoped = it.kind === "pv" || it.kind === "group" || it.kind === "channel";

    if (chatScoped) {
      grid.appendChild(card("Analyze chat", "📊", "Analyze the last N messages of this chat — privately.", [
        { key: "count", label: "Messages", value: "100" },
        { key: "mode", type: "select", label: "Mode", options: [{ v: "general", t: "General" }, { v: "fun", t: "Fun (roast)" }, { v: "romance", t: "Romance" }] },
        { key: "language", type: "select", label: "Language", options: [{ v: "persian", t: "Persian" }, { v: "english", t: "English" }] },
        { key: "think", type: "check", label: "Deep thinking" },
      ], (v, btn) => runCommand("analyze", { entity_id: it.id, count: +v.count || 100, mode: v.mode, language: v.language, think: v.think }, `Analyze · ${it.display_name}`, btn)));

      grid.appendChild(card("Ask about chat", "💬", "Answer a question from this chat's history.", [
        { key: "count", label: "Messages", value: "100" },
        { key: "question", type: "textarea", label: "Question", ph: "What do they argue about most?" },
        { key: "think", type: "check", label: "Deep thinking" },
        { key: "web", type: "check", label: "Web search" },
      ], (v, btn) => runCommand("tellme", { entity_id: it.id, count: +v.count || 100, question: v.question, think: v.think, web: v.web }, `Tellme · ${it.display_name}`, btn)));
    }

    grid.appendChild(card("Prompt", "✨", "Ask the AI anything.", [
      { key: "text", type: "textarea", label: "Prompt", ph: "Explain quantum tunneling simply…" },
      { key: "think", type: "check", label: "Deep thinking" },
      { key: "web", type: "check", label: "Web search" },
    ], (v, btn) => runCommand("prompt", { text: v.text, think: v.think, web: v.web }, "Prompt", btn)));

    grid.appendChild(card("Translate", "🌐", "Translate with Persian phonetics.", [
      { key: "target_lang", label: "Target language", value: "en" },
      { key: "source", label: "Source language", value: "auto" },
      { key: "text", type: "textarea", label: "Text", ph: "متن برای ترجمه…" },
    ], (v, btn) => runCommand("translate", { text: v.text, target_lang: v.target_lang, source: v.source || "auto" }, "Translate", btn)));

    grid.appendChild(card("Image", "🎨", "Generate an image — rendered inline.", [
      { key: "model", type: "select", label: "Model", options: [{ v: "flux", t: "Flux (fast)" }, { v: "sdxl", t: "SDXL (photoreal)" }] },
      { key: "prompt", type: "textarea", label: "Prompt", ph: "sunset over snowy mountains, cinematic" },
    ], (v, btn) => runCommand("image", { model: v.model, prompt: v.prompt }, "Image", btn)));

    grid.appendChild(card("Text-to-Speech", "🔊", "Generate audio — plays inline.", [
      (State.voices && State.voices.length)
        ? { key: "voice", type: "select", label: "Voice", options: [{ v: "", t: "default" }, ...State.voices.map((v) => ({ v, t: v }))] }
        : { key: "voice", label: "Voice (optional)", ph: "e.g. Orus" },
      { key: "text", type: "textarea", label: "Text", ph: "Hello from Aigram" },
    ], (v, btn) => runCommand("tts", { text: v.text, voice: v.voice || null }, "TTS", btn)));

    pane.appendChild(grid);
  }

  // ---- chat engine (full re-render; media nodes cached per message id) ----
  const PAGE = 30;
  let chat = { items: [], oldestId: null, loading: false, hasMore: true };
  const mediaNodes = new Map(); // msgId -> cached media element (survives re-renders, no re-fetch)
  const newIds = new Set();     // ids to animate in ONCE (only genuinely new messages)

  function sameDay(a, b) {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  }
  function dayLabel(iso) {
    const d = new Date(iso), now = new Date(), y = new Date(now);
    y.setDate(now.getDate() - 1);
    if (sameDay(d, now)) return "Today";
    if (sameDay(d, y)) return "Yesterday";
    const opts = { month: "short", day: "numeric" };
    if (d.getFullYear() !== now.getFullYear()) opts.year = "numeric";
    return d.toLocaleDateString([], opts);
  }
  function clockTime(iso) {
    if (!iso) return "";
    try { return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); } catch (_) { return ""; }
  }

  async function loadChat() {
    stopPolling();
    const scroll = $("#chat-scroll");
    scroll.innerHTML = "<div class='chat-top muted'>Loading…</div>";
    chat = { items: [], oldestId: null, loading: false, hasMore: true };
    mediaNodes.clear();
    scroll.onscroll = () => { if (scroll.scrollTop < 80) loadOlder(); };
    await loadOlder(true);
    scroll.scrollTop = scroll.scrollHeight;
    startPolling();
  }

  // ---- live updates (visibility-aware polling; ban-safe, throttled server-side) ----
  const POLL_MS = 6000;
  let pollTimer = null;
  function newestNumericId() {
    for (let i = chat.items.length - 1; i >= 0; i--) {
      if (typeof chat.items[i].id === "number") return chat.items[i].id;
    }
    return null;
  }
  function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }
  function startPolling() { stopPolling(); pollTimer = setInterval(pollNew, POLL_MS); }
  async function pollNew() {
    if (!State.entity || document.hidden || chat.loading) return;
    const after = newestNumericId();
    if (!after) return;
    try {
      const data = await api(`/entity/${State.entity.id}/history?limit=20&after_id=${after}`);
      const known = new Set(chat.items.map((x) => x.id));
      const fresh = (data.items || []).filter((m) => typeof m.id === "number" && !known.has(m.id));
      if (!fresh.length) return;
      fresh.reverse(); // newest-first -> chronological
      fresh.forEach((m) => newIds.add(m.id));
      chat.items.push(...fresh);
      renderChat();
    } catch (_) { /* transient network blip; next tick retries */ }
  }
  document.addEventListener("visibilitychange", () => { if (!document.hidden && State.entity) pollNew(); });

  async function loadOlder(initial = false) {
    if (chat.loading || !chat.hasMore) return;
    chat.loading = true;
    const scroll = $("#chat-scroll");
    const top = scroll.querySelector(".chat-top");
    if (top && !initial) top.textContent = "Loading older…";
    try {
      const cursor = chat.oldestId ? `&before_id=${chat.oldestId}` : "";
      const data = await api(`/entity/${State.entity.id}/history?limit=${PAGE}${cursor}`);
      const older = (data.items || []).slice().reverse(); // oldest -> newest
      if (!older.length) { chat.hasMore = false; renderChat(); return; }
      const prevH = scroll.scrollHeight;
      chat.items = older.concat(chat.items);
      chat.oldestId = data.oldest_id;
      if (data.items.length < PAGE) chat.hasMore = false;
      renderChat();
      if (!initial) scroll.scrollTop = scroll.scrollTop + (scroll.scrollHeight - prevH);
    } catch (e) {
      const t = scroll.querySelector(".chat-top");
      if (t) t.textContent = e.message;
    } finally {
      chat.loading = false;
    }
  }

  function renderChat() {
    const scroll = $("#chat-scroll");
    const prevTop = scroll.scrollTop;
    const atBottom = scroll.scrollHeight - prevTop - scroll.clientHeight < 48;
    scroll.innerHTML = "";
    const topText = !chat.hasMore ? "Beginning of chat" : "↑ scroll up for older";
    scroll.appendChild(el("div", { class: "chat-top muted", text: chat.items.length ? topText : "No messages yet." }));
    let prev = null;
    const isGroupChat = State.entity && State.entity.kind === "group"; // multi-sender only
    for (const m of chat.items) {
      const cur = new Date(m.timestamp);
      if (!prev || !sameDay(new Date(prev.timestamp), cur)) {
        scroll.appendChild(el("div", { class: "day-sep" }, el("span", { text: dayLabel(m.timestamp) })));
      }
      const grouped = prev && prev.out === m.out && prev.sender === m.sender &&
        sameDay(new Date(prev.timestamp), cur) && (cur - new Date(prev.timestamp)) < 5 * 60 * 1000;
      scroll.appendChild(bubbleRow(m, !grouped, isGroupChat, newIds.has(m.id)));
      prev = m;
    }
    newIds.clear(); // each message animates in only once
    // keep the viewport anchored: pin to bottom if we were there, else hold place
    scroll.scrollTop = atBottom ? scroll.scrollHeight : prevTop;
  }

  function bubbleRow(m, groupStart, isGroupChat, fresh) {
    const media = renderMedia(m);
    let cls = "bubble" + (m.out ? " out" : "") + (groupStart ? " gstart" : "") + (fresh ? " just-in" : "");
    if (media && !m.text) {
      if (m.media_kind === "sticker") cls += " sticker-bubble";
      else if (m.media_kind !== "audio") cls += " media-only";
    }
    const bubble = el("div", { class: cls });
    if (groupStart && !m.out && isGroupChat) bubble.appendChild(el("div", { class: "b-sender", dir: "auto", text: m.sender }));
    if (m.reply) bubble.appendChild(replyPreview(m.reply));
    if (media) bubble.appendChild(media);
    if (m.text) bubble.appendChild(el("div", { class: "b-text", dir: "auto", text: m.text }));
    if (m.media_kind === "audio") bubble.appendChild(el("button", {
      class: "stt-btn", title: "Transcribe with AI",
      onclick: () => runCommand("stt", { entity_id: State.entity.id, message_id: m.id }, "STT", null),
    }, el("span", { text: "🎤 Transcribe" })));
    bubble.appendChild(el("div", { class: "b-meta" }, [
      el("span", { text: clockTime(m.timestamp) }),
      m.out ? el("span", { class: "tick" + (m.pending ? " pending" : ""), text: m.pending ? "🕓" : "✓" }) : null,
    ]));
    const children = [];
    // Group chats: a small sender avatar next to incoming runs (like Telegram).
    if (isGroupChat && !m.out) {
      if (groupStart && m.sender_id) {
        children.push(el("img", { class: "avatar xs", alt: "", loading: "lazy", src: avatarUrl(m.sender_id, true) }));
      } else {
        children.push(el("div", { class: "avatar xs avatar-spacer" }));
      }
    }
    children.push(bubble);
    if (typeof m.id === "number") {
      children.push(el("button", { class: "row-reply", title: "Reply", text: "↩", onclick: () => setReply(m) }));
    }
    const row = el("div", { class: "msg-row" + (m.out ? " out" : "") + (groupStart ? " gstart" : "") }, children);
    return row;
  }

  const MEDIA_LABEL = { sticker: "Sticker", photo: "Photo", video: "Video", gif: "GIF", audio: "Audio", document: "File" };
  const MEDIA_ICON = { sticker: "🩷", photo: "📷", video: "🎬", gif: "🎞️", audio: "🎤", document: "📄" };
  function mediaFallback(kind) {
    return el("div", { class: "m-fallback" }, [
      el("span", { class: "m-fb-ic", text: MEDIA_ICON[kind] || "📄" }),
      el("span", { text: MEDIA_LABEL[kind] || "Media" }),
    ]);
  }
  // Swap a broken media element for a clean labelled placeholder (never show
  // a browser's broken-image glyph or raw alt text).
  function withFallback(img, node, kind) {
    img.addEventListener("error", () => node.replaceChildren(mediaFallback(kind)));
    return img;
  }

  function renderMedia(m) {
    if (!m.has_media) return null;
    if (typeof m.id === "number" && mediaNodes.has(m.id)) return mediaNodes.get(m.id);
    const fileUrl = mediaUrl(`/api/entity/${State.entity.id}/media/${m.id}/file`);
    const thumbUrl = mediaUrl(`/api/entity/${State.entity.id}/media/${m.id}/thumb`);
    let node;
    switch (m.media_kind) {
      case "photo":
        node = el("div", { class: "m-photo", onclick: () => window.open(fileUrl, "_blank") });
        node.appendChild(withFallback(el("img", { loading: "lazy", src: thumbUrl, alt: "" }), node, "photo"));
        break;
      case "sticker":
        // Stickers may be .tgs (Lottie) / .webm — not <img>-renderable. The static
        // THUMBNAIL always is, so use it (with a tidy placeholder on failure).
        node = el("div", { class: "m-sticker" });
        node.appendChild(withFallback(el("img", { loading: "lazy", src: thumbUrl, alt: "" }), node, "sticker"));
        break;
      case "video":
      case "gif":
        node = el("div", { class: "m-photo m-video", onclick: () => window.open(fileUrl, "_blank") });
        node.appendChild(withFallback(el("img", { loading: "lazy", src: thumbUrl, alt: "" }), node, "video"));
        node.appendChild(el("span", { class: "play", html: "&#9658;" }));
        break;
      case "audio":
        node = el("audio", { class: "m-audio", controls: "", preload: "none", src: fileUrl });
        break;
      default:
        node = el("a", { class: "m-doc", href: fileUrl, target: "_blank", rel: "noopener" }, [
          el("span", { class: "m-doc-ic", text: "📄" }),
          el("span", { class: "m-doc-name", dir: "auto", text: m.file_name || m.mime || "file" }),
        ]);
    }
    if (typeof m.id === "number") mediaNodes.set(m.id, node);
    return node;
  }

  // ---- reply ----
  function setReply(m) {
    State.replyTo = { id: m.id, sender: m.sender, text: m.text || mediaLabel(m) };
    const bar = $("#reply-bar");
    bar.innerHTML = "";
    bar.appendChild(el("div", { class: "reply-acc" }));
    bar.appendChild(el("div", { class: "reply-meta" }, [
      el("div", { class: "reply-to", dir: "auto", text: "↩ " + State.replyTo.sender }),
      el("div", { class: "reply-snip", dir: "auto", text: (State.replyTo.text || "").slice(0, 90) }),
    ]));
    bar.appendChild(el("button", { class: "reply-x", title: "Cancel reply", text: "✕", onclick: clearReply }));
    bar.classList.remove("hidden");
    $("#composer-input").focus();
  }
  function clearReply() { State.replyTo = null; const b = $("#reply-bar"); if (b) { b.classList.add("hidden"); b.innerHTML = ""; } }
  function mediaLabel(m) {
    return { photo: "📷 Photo", video: "🎬 Video", sticker: "🩷 Sticker", audio: "🎤 Voice", gif: "GIF", document: "📄 File" }[m.media_kind] || (m.has_media ? "Media" : "");
  }
  function replyPreview(r) {
    return el("div", { class: "b-reply" }, [
      el("div", { class: "b-reply-to", dir: "auto", text: r.sender || "" }),
      el("div", { class: "b-reply-snip", dir: "auto", text: (r.text || "").slice(0, 90) }),
    ]);
  }

  // ---- send (write to Telegram) ----
  async function sendMessage() {
    const input = $("#composer-input");
    const text = input.value.trim();
    if (!text || !State.entity) return;
    const replyTo = State.replyTo ? State.replyTo.id : null;
    const replySnap = State.replyTo ? { sender: State.replyTo.sender, text: State.replyTo.text } : null;
    setSendEnabled(false);
    input.value = ""; autoGrow(input);
    const optimistic = {
      id: "pending-" + Date.now(), out: true, sender: "You", text,
      timestamp: new Date().toISOString(), has_media: false, media_kind: null, pending: true, reply: replySnap,
    };
    chat.items.push(optimistic);
    newIds.add(optimistic.id);
    clearReply();
    renderChat();
    const scroll = $("#chat-scroll"); scroll.scrollTop = scroll.scrollHeight;
    try {
      const data = await api(`/entity/${State.entity.id}/send`, { method: "POST", body: { text, reply_to: replyTo } });
      const idx = chat.items.findIndex((x) => x.id === optimistic.id);
      if (idx >= 0) {
        const real = data.message || Object.assign(optimistic, { pending: false });
        if (optimistic.reply && !real.reply) real.reply = optimistic.reply; // echo lacks reply preview
        chat.items[idx] = real;
      }
      renderChat();
      scroll.scrollTop = scroll.scrollHeight;
    } catch (e) {
      const idx = chat.items.findIndex((x) => x.id === optimistic.id);
      if (idx >= 0) chat.items.splice(idx, 1);
      renderChat();
      input.value = text; autoGrow(input); setSendEnabled(true);
      toast(e.message, true);
    }
  }

  // ---- run command + results ----
  async function runCommand(kind, payload, title, btn) {
    $("#modal").classList.add("hidden"); // reveal the results rail behind the AI sheet
    if (btn) { btn.disabled = true; btn.dataset.html = btn.innerHTML; btn.innerHTML = '<span class="spin"></span><span>Running…</span>'; }
    const card = addResultCard(title);
    try {
      const data = await api("/cmd/" + kind, { method: "POST", body: payload });
      fillResult(card, data, title);
    } catch (e) {
      $(".tname .spin", card)?.remove();
      card.classList.add("error");
      const retry = e.retry_after ? ` (retry in ~${e.retry_after}s)` : "";
      $(".rbody", card).innerHTML = `<div class="rhtml">⚠️ ${esc(e.message)}${retry}</div>`;
      toast(e.message, true);
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.html; }
    }
  }

  function updateRailCount() {
    const n = $$("#rail-body .result").length;
    $("#rail-count").textContent = n ? `(${n})` : "";
  }

  function addResultCard(title) {
    const body = $("#rail-body");
    if ($(".rail-empty", body)) body.innerHTML = "";
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const card = el("div", { class: "result" }, [
      el("div", { class: "rtitle" }, [
        el("span", { class: "tname" }, [el("span", { class: "spin" }), el("span", { text: title })]),
        el("span", { class: "rtime faint", text: time }),
      ]),
      el("div", { class: "rbody" }),
    ]);
    body.insertBefore(card, body.firstChild);
    updateRailCount();
    openRailMobile();
    return card;
  }

  function fillResult(card, data, title) {
    $(".tname .spin", card)?.remove();
    const body = $(".rbody", card);
    body.innerHTML = "";
    if (data.kind === "image") {
      body.appendChild(el("img", { class: "rimg", src: mediaUrl(data.media_url) }));
      if (data.meta && data.meta.enhanced_prompt) body.appendChild(metaChips({ prompt: data.meta.enhanced_prompt }));
    } else if (data.kind === "audio") {
      body.appendChild(el("audio", { controls: "", src: mediaUrl(data.media_url) }));
    } else {
      // The server HTML already carries its own metadata footer (model/time/
      // tokens + badges) for AI commands, so we don't duplicate it with chips.
      body.appendChild(el("div", { class: "rhtml", dir: "auto", html: data.html || "" }));
      if (data.media_url) body.appendChild(el("audio", { controls: "", src: mediaUrl(data.media_url) }));
    }
  }

  function metaParts(m) {
    const parts = [];
    if (m.model) parts.push(m.model);
    if (m.provider) parts.push(m.provider);
    if (m.latency) parts.push((m.latency.toFixed ? m.latency.toFixed(1) : m.latency) + "s");
    if (m.output_tokens) parts.push((m.input_tokens ? m.input_tokens + "/" : "") + m.output_tokens + " tok");
    if (m.messages) parts.push(m.messages + " msgs");
    if (m.mode) parts.push(m.mode);
    if (m.prompt) parts.push("prompt: " + m.prompt);
    if (m.provider_fallback) parts.push("⤵ fallback");
    return parts;
  }

  function metaChips(m) {
    const wrap = el("div", { class: "meta" });
    for (const p of metaParts(m)) wrap.appendChild(el("span", { class: "mchip", text: p }));
    return wrap;
  }

  // ---- dashboards ----
  function initDashboards() {
    // Wire every dashboard entry point — topbar nav AND the mobile drawer footer.
    $$("[data-dash]").forEach((c) =>
      c.addEventListener("click", () => { closeDrawers(); openDash(c.dataset.dash); })
    );
    $("#modal-close").addEventListener("click", () => $("#modal").classList.add("hidden"));
    $("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); });
    $("#rail-clear").addEventListener("click", () => {
      $("#rail-body").innerHTML = '<div class="rail-empty">Command results appear here.</div>';
      updateRailCount();
    });
    const toggleTheme = () => {
      const root = document.documentElement;
      root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
      localStorage.setItem("panel_theme", root.dataset.theme);
    };
    [$("#theme-toggle"), $("#theme-toggle-m")].forEach((b) => b && b.addEventListener("click", toggleTheme));
  }

  async function openDash(which) {
    const modal = $("#modal"); const body = $("#modal-body");
    $("#modal-title").textContent = { keys: "Keys & Providers", routing: "Categorization & Routing", models: "Model Matrix", auth: "Authorized Users", help: "Help" }[which] || which;
    body.innerHTML = "<div class='muted'>Loading…</div>";
    modal.classList.remove("hidden");
    try {
      if (which === "keys") await renderKeys(body);
      else if (which === "routing") await renderRouting(body);
      else if (which === "models") body.replaceChildren(renderModels(await api("/models")));
      else if (which === "help") body.replaceChildren(renderHelp(await api("/help")));
      else if (which === "auth") await renderAuth(body);
    } catch (e) { body.innerHTML = `<div class='err'>${esc(e.message)}</div>`; }
  }

  async function renderKeys(body) {
    const d = await api("/keys");
    body.innerHTML = "";

    // provider selector
    const mkSel = (id, val, opts) =>
      el("select", { id }, opts.map((o) => el("option", { value: o, selected: o === val ? "" : null, text: o })));
    const primarySel = mkSel("k-primary", d.primary, ["gemini", "openrouter"]);
    const fallbackSel = mkSel("k-fallback", d.fallback || "none", ["none", "gemini", "openrouter"]);
    body.appendChild(el("div", { class: "field-row", style: "align-items:flex-end;margin-bottom:16px" }, [
      el("div", { class: "field" }, [el("label", { class: "field-label", text: "Primary" }), primarySel]),
      el("div", { class: "field" }, [el("label", { class: "field-label", text: "Fallback" }), fallbackSel]),
      el("button", { class: "btn btn-primary", text: "Save", onclick: async () => {
        try { await api("/keys/provider", { method: "PUT", body: { primary: primarySel.value, fallback: fallbackSel.value } });
          toast("Provider updated"); renderKeys(body); }
        catch (e) { toast(e.message, true); }
      }}),
    ]));

    for (const p of d.providers) {
      const card = el("div", { class: "card", style: "margin-bottom:14px" });
      card.appendChild(el("div", { class: "card-head" }, [
        el("strong", { class: "grow", text: p.provider }),
        p.is_primary ? el("span", { class: "pill good", text: "primary" }) : null,
        p.is_fallback ? el("span", { class: "pill warn", text: "fallback" }) : null,
      ]));
      for (const s of p.slots) {
        const row = el("div", { class: "auth-row" }, [
          el("span", { class: "faint", text: "#" + s.index }),
          el("code", { class: "grow key-mask", title: s.present ? s.masked : "", text: s.present ? s.masked : "— empty —" }),
        ]);
        if (s.present) {
          const status = el("span", {});
          row.appendChild(el("button", { class: "btn btn-sm", text: "Test", onclick: async (e) => {
            const b = e.target; b.disabled = true; b.textContent = "…";
            try {
              const r = await api("/keys/test", { method: "POST", body: { provider: p.provider, index: s.index } });
              status.className = "pill " + (r.ok ? "good" : "bad");
              status.textContent = r.ok ? `✓ ${r.latency_ms}ms` : `✗ ${r.error || "failed"}`;
            } finally { b.disabled = false; b.textContent = "Test"; }
          }}));
          row.appendChild(status);
          row.appendChild(el("button", { class: "icon-btn", text: "✕", title: "Remove", onclick: async () => {
            try { await api(`/keys/${p.provider}/${s.index}`, { method: "DELETE" }); toast("Key removed"); renderKeys(body); }
            catch (e) { toast(e.message, true); }
          }}));
        }
        card.appendChild(row);
      }
      const inp = el("input", { type: "password", placeholder: `Paste a ${p.provider} API key…`, autocomplete: "off" });
      card.appendChild(el("div", { class: "field-row", style: "margin-top:12px;align-items:flex-end" }, [
        el("span", { class: "grow" }, [inp]),
        el("button", { class: "btn btn-sm", text: "Test", onclick: async (e) => {
          const v = inp.value.trim(); if (!v) return; const b = e.target; b.disabled = true; b.textContent = "…";
          try { const r = await api("/keys/test", { method: "POST", body: { provider: p.provider, key: v } });
            toast(r.ok ? `✓ key works (${r.latency_ms}ms)` : `✗ ${r.error || "failed"}`, !r.ok); }
          finally { b.disabled = false; b.textContent = "Test"; }
        }}),
        el("button", { class: "btn btn-primary btn-sm", text: "Add", onclick: async () => {
          const v = inp.value.trim(); if (!v) return;
          try { await api("/keys", { method: "POST", body: { provider: p.provider, key: v } }); toast("Key added & applied"); renderKeys(body); }
          catch (e) { toast(e.message, true); }
        }}),
      ]));
      body.appendChild(card);
    }

    if (d.live && d.live.keys) {
      body.appendChild(el("h3", { text: "Live key health", style: "margin:14px 0 6px" }));
      body.appendChild(el("table", { class: "keytable" }, [
        el("tr", {}, [el("th", { text: "#" }), el("th", { text: "Status" }), el("th", { text: "Available" }), el("th", { text: "Errors" })]),
        ...d.live.keys.map((k) => el("tr", {}, [
          el("td", { text: "#" + (k.index + 1) + (k.is_current ? " ◀" : "") }),
          el("td", {}, [el("span", { class: "pill " + (k.status === "healthy" ? "good" : k.status === "exhausted" ? "bad" : "warn"), text: k.status })]),
          el("td", { text: k.available ? "yes" : "no" }),
          el("td", { text: String(k.error_count) }),
        ])),
      ]));
    }
  }

  function renderModels(d) {
    const kv = el("div", { class: "kv" });
    const add = (k, v) => { kv.appendChild(el("div", { class: "k", text: k })); kv.appendChild(el("div", { text: v == null ? "—" : String(v) })); };
    add("Provider", d.provider);
    for (const [t, m] of Object.entries(d.tasks || {})) add(t, m);
    add("Web search", d.web_search_model);
    add("TTS model", d.tts_model);
    add("TTS voice", d.tts_voice);
    add("Flux worker", d.flux_worker ? "configured" : "—");
    add("SDXL worker", d.sdxl_worker ? "configured" : "—");
    return kv;
  }

  function renderHelp(d) {
    const wrap = el("div");
    wrap.appendChild(el("p", { class: "muted", text: d.note }));
    for (const c of d.commands) {
      wrap.appendChild(el("div", { class: "auth-row" }, [
        el("code", { text: "/" + c.cmd }),
        el("span", { class: "grow", text: c.desc }),
        el("span", { class: "pill " + (c.scope === "chat" ? "warn" : "neutral"), text: c.scope }),
      ]));
    }
    return wrap;
  }

  async function renderAuth(body) {
    const data = await api("/auth");
    body.innerHTML = "";
    const addRow = el("div", { class: "row" }, [
      el("span", { class: "grow" }, [el("input", { id: "auth-id", placeholder: "@username or numeric id" })]),
      el("button", { class: "btn btn-primary", text: "Add", onclick: async () => {
        const v = $("#auth-id").value.trim(); if (!v) return;
        try { const r = await api("/auth", { method: "POST", body: { identifier: v } }); toast("Added " + (r.added.display_name || r.added.id)); renderAuth(body); }
        catch (e) { toast(e.message, true); }
      }}),
    ]);
    body.appendChild(addRow);
    body.appendChild(el("p", { class: "muted", text: "Note: new users take effect on next panel/monitor start." }));
    if (!data.items.length) body.appendChild(el("div", { class: "muted", text: "No authorized users." }));
    for (const u of data.items) {
      body.appendChild(el("div", { class: "auth-row" }, [
        el("strong", { class: "grow", text: u.display_name || ("id " + u.id) }),
        el("span", { class: "muted", text: u.username || ("id " + u.id) }),
        el("button", { class: "icon-btn", text: "✕", onclick: async () => {
          try { await api("/auth/" + u.id, { method: "DELETE" }); toast("Removed"); renderAuth(body); }
          catch (e) { toast(e.message, true); }
        }}),
      ]));
    }
  }

  async function renderRouting(body) {
    body.innerHTML = "";
    const [groups, st] = await Promise.all([api("/groups"), api("/groups/state")]);
    body.appendChild(el("p", { class: "muted", text:
      "Map a /command → forum topic. Reply to a message with that command and the bot files it into the topic. Mapping changes apply on the next bot start." }));

    const curTarget = st.target && st.target.id;
    const gSel = el("select", { id: "rt-group" }, [
      el("option", { value: "", text: "— select target group —" }),
      ...groups.items.map((g) => el("option", { value: g.id, selected: g.id === curTarget ? "" : null,
        text: g.title + (g.is_forum ? "" : " (no topics)") })),
    ]);
    body.appendChild(el("div", { class: "field-row", style: "align-items:flex-end;margin:10px 0 16px" }, [
      el("div", { class: "field" }, [el("label", { class: "field-label", text: "Target group" }), gSel]),
      el("button", { class: "btn btn-primary", text: "Set", onclick: async () => {
        if (!gSel.value) return;
        try { await api("/groups/target", { method: "PUT", body: { group_id: +gSel.value } }); toast("Target group set"); renderRouting(body); }
        catch (e) { toast(e.message, true); }
      }}),
    ]));

    const topicsById = {};
    if (curTarget) {
      const tWrap = el("div", { html: "<div class='muted'>Loading topics…</div>" });
      body.appendChild(tWrap);
      try {
        const topics = (await api(`/groups/${curTarget}/topics`)).items;
        topics.forEach((t) => { topicsById[t.id] = t.title; });
        tWrap.innerHTML = "";
        if (!topics.length) {
          tWrap.appendChild(el("div", { class: "muted", text: "This group has no forum topics (enable Topics in Telegram)." }));
        } else {
          const topicSel = el("select", {}, topics.map((t) => el("option", { value: t.id, text: t.title })));
          const cmdInp = el("input", { placeholder: "command (e.g. meme)" });
          tWrap.appendChild(el("div", { class: "field-row", style: "align-items:flex-end" }, [
            el("div", { class: "field" }, [el("label", { class: "field-label", text: "Command" }), cmdInp]),
            el("div", { class: "field" }, [el("label", { class: "field-label", text: "Topic" }), topicSel]),
            el("button", { class: "btn btn-primary", text: "Add", onclick: async () => {
              if (!cmdInp.value.trim()) return;
              try { await api("/groups/mappings", { method: "POST", body: { command: cmdInp.value.trim(), topic_id: +topicSel.value } });
                toast("Mapping added"); renderRouting(body); }
              catch (e) { toast(e.message, true); }
            }}),
          ]));
        }
      } catch (e) { tWrap.innerHTML = `<div class='muted'>${esc(e.message)}</div>`; }
    }

    body.appendChild(el("h3", { text: "Mappings", style: "margin:16px 0 6px" }));
    if (!st.mappings.length) body.appendChild(el("div", { class: "muted", text: "No command → topic mappings yet." }));
    for (const m of st.mappings) {
      body.appendChild(el("div", { class: "auth-row" }, [
        el("code", { text: "/" + m.command }),
        el("span", { class: "faint", text: "→" }),
        el("span", { class: "grow", text: topicsById[m.topic_id] || ("topic " + m.topic_id) }),
        el("button", { class: "icon-btn", text: "✕", title: "Remove", onclick: async () => {
          try { await api("/groups/mappings/" + encodeURIComponent(m.command), { method: "DELETE" }); toast("Removed"); renderRouting(body); }
          catch (e) { toast(e.message, true); }
        }}),
      ]));
    }
    if (st.mappings.length) {
      body.appendChild(el("button", { class: "btn btn-sm", style: "margin-top:12px", text: "Clear all mappings", onclick: async () => {
        try { await api("/groups/mappings", { method: "DELETE" }); toast("Cleared"); renderRouting(body); }
        catch (e) { toast(e.message, true); }
      }}));
    }
  }

  // ---- onboarding wizard ----
  function renderWizard() {
    let ov = $("#wizard");
    if (!ov) { ov = el("div", { id: "wizard", class: "gate" }); document.body.appendChild(ov); }
    ov.classList.remove("hidden");
    const card = el("div", { class: "gate-card", style: "width:440px;text-align:left" });
    ov.replaceChildren(card);
    const head = (t) => el("div", { class: "brand" }, [el("span", { class: "brand-mark", text: "A" }), " " + t]);
    const field = (id, label, ph, type) => [
      el("label", { class: "field-label", text: label }),
      el("input", { id, type: type || "text", placeholder: ph || "", autocomplete: "off" }),
    ];
    const sel = (id, label, opts) => [
      el("label", { class: "field-label", text: label }),
      el("select", { id }, opts.map((o) => el("option", { value: o.v, text: o.t }))),
    ];
    const setMsg = (m) => { const e = $(".wz-msg", card); if (e) e.textContent = m || ""; };
    const run = async (b, fn) => { b.disabled = true; setMsg(""); try { await fn(); } catch (e) { setMsg(e.message); b.disabled = false; } };

    function step1() {
      card.replaceChildren(
        head("Set up Aigram"),
        el("p", { class: "muted", text: "Get your API ID & hash from my.telegram.org, then log in with your phone." }),
        ...field("wz-id", "API ID", "12345678"),
        ...field("wz-hash", "API hash", "0123abc…"),
        ...field("wz-phone", "Phone (with country code)", "+98…"),
        el("div", { class: "wz-msg err" }),
        el("button", { class: "btn btn-primary", text: "Send login code", onclick: (e) => run(e.target, async () => {
          const r = await api("/setup/start", { method: "POST", body: {
            api_id: $("#wz-id").value.trim(), api_hash: $("#wz-hash").value.trim(), phone: $("#wz-phone").value.trim() } });
          r.authorized ? step3() : step2();
        })}),
      );
    }
    function step2() {
      card.replaceChildren(
        head("Enter code"),
        el("p", { class: "muted", text: "Telegram sent a login code to your account." }),
        ...field("wz-code", "Login code", "1 2 3 4 5"),
        el("div", { class: "wz-msg err" }),
        el("button", { class: "btn btn-primary", text: "Verify", onclick: (e) => run(e.target, async () => {
          const r = await api("/setup/code", { method: "POST", body: { code: $("#wz-code").value.trim() } });
          r.needs_password ? step2b() : step3();
        })}),
      );
    }
    function step2b() {
      card.replaceChildren(
        head("Two-step password"),
        el("p", { class: "muted", text: "Your account has two-step verification enabled." }),
        ...field("wz-pw", "Password", "", "password"),
        el("div", { class: "wz-msg err" }),
        el("button", { class: "btn btn-primary", text: "Verify", onclick: (e) => run(e.target, async () => {
          await api("/setup/password", { method: "POST", body: { password: $("#wz-pw").value } }); step3();
        })}),
      );
    }
    function step3() {
      card.replaceChildren(
        head("AI provider"),
        el("p", { class: "muted", text: "Add at least one LLM key. Gemini is recommended; OpenRouter works as a fallback." }),
        ...sel("wz-prov", "Provider", [{ v: "gemini", t: "Gemini" }, { v: "openrouter", t: "OpenRouter" }]),
        ...field("wz-key", "API key", "paste a key", "password"),
        el("div", { class: "wz-msg err" }),
        el("button", { class: "btn btn-primary", text: "Finish setup", onclick: (e) => run(e.target, async () => {
          await api("/setup/finalize", { method: "POST", body: { llm: { provider: $("#wz-prov").value, keys: [$("#wz-key").value.trim()] } } });
          step4();
        })}),
      );
    }
    function step4() {
      card.replaceChildren(
        head("All set 🎉"),
        el("p", { class: "muted", text: "Aigram is configured and you're logged in. Restart it with the normal command to open the full panel:" }),
        el("code", { text: "sakaibot panel" }),
      );
    }
    step1();
  }

  // ---- helpers ----
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }
  function fmtTime(iso) { if (!iso) return ""; try { return new Date(iso).toLocaleString(); } catch (_) { return iso; } }

  // ---- mobile drawers ----
  function closeDrawers() {
    $(".sidebar") && $(".sidebar").classList.remove("open");
    $(".rail") && $(".rail").classList.remove("open");
    $("#scrim") && $("#scrim").classList.remove("show");
  }
  function toggleDrawer(sel) {
    const node = $(sel);
    if (!node) return;
    const willOpen = !node.classList.contains("open");
    closeDrawers();
    if (willOpen) { node.classList.add("open"); $("#scrim").classList.add("show"); }
  }
  function openRailMobile() {
    if (window.innerWidth <= 1180 && $("#rail-btn") && getComputedStyle($("#rail-btn")).display !== "none") {
      $(".rail").classList.add("open"); $("#scrim").classList.add("show");
    }
  }
  function initMobile() {
    $("#menu-btn") && $("#menu-btn").addEventListener("click", () => toggleDrawer(".sidebar"));
    $("#rail-btn") && $("#rail-btn").addEventListener("click", () => toggleDrawer(".rail"));
    $("#scrim") && $("#scrim").addEventListener("click", closeDrawers);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawers(); });
  }

  // ---- PWA install (Android prompt + iOS hint) ----
  let deferredInstall = null;
  function isStandalone() {
    return window.matchMedia && window.matchMedia("(display-mode: standalone)").matches
      || window.navigator.standalone === true;
  }
  function initInstall() {
    const btn = $("#install-btn");
    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
      deferredInstall = e;
      if (btn && !isStandalone()) btn.classList.remove("hidden");
    });
    if (btn) {
      btn.addEventListener("click", async () => {
        if (!deferredInstall) return;
        deferredInstall.prompt();
        try { await deferredInstall.userChoice; } catch (_) {}
        deferredInstall = null;
        btn.classList.add("hidden");
      });
    }
    window.addEventListener("appinstalled", () => {
      deferredInstall = null;
      if (btn) btn.classList.add("hidden");
    });
    maybeIosInstallHint();
  }

  function maybeIosInstallHint() {
    const ua = navigator.userAgent || "";
    const isIos = /iphone|ipad|ipod/i.test(ua) || (/Macintosh/.test(ua) && "ontouchend" in document);
    const isSafari = isIos && !/crios|fxios|edgios/i.test(ua);
    if (!isSafari || isStandalone() || localStorage.getItem("ios_install_dismissed")) return;
    const hint = el("div", { id: "ios-install", class: "ios-hint" }, [
      el("span", { html: "Install Aigram — tap <b>Share</b> then <b>Add to Home Screen</b>." }),
      el("button", {
        class: "ios-hint-x", "aria-label": "Dismiss", text: "✕",
        onclick: () => { hint.remove(); localStorage.setItem("ios_install_dismissed", "1"); },
      }),
    ]);
    document.body.appendChild(hint);
  }

  // ---- service worker (PWA) ----
  function registerSW() {
    if (!("serviceWorker" in navigator)) return;
    // Returning users only: if a NEW worker takes control (we shipped fresh
    // assets), reload once so they immediately run the latest app. Skip on the
    // very first install (no prior controller) to avoid a needless reload.
    const hadController = !!navigator.serviceWorker.controller;
    let reloaded = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (reloaded || !hadController) return;
      reloaded = true;
      location.reload();
    });
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").then((reg) => reg.update()).catch(() => {});
    });
  }

  // ---- boot ----
  async function boot() {
    const theme = localStorage.getItem("panel_theme");
    if (theme) document.documentElement.dataset.theme = theme;
    await loadStatus();
    try { const s = await api("/status"); realPhotosEnabled = !!(s.panel && s.panel.real_photos); } catch (_) {}
    try { State.voices = (await api("/tts/voices")).voices; } catch (_) {}
    await loadDialogs();
  }

  function init() {
    registerSW();
    initGate();
    initSidebar();
    initEntityActions();
    initDashboards();
    initMobile();
    initInstall();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
