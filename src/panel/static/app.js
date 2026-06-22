/* SakaiBot Control Panel — vanilla SPA (no build step). */
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
    // health is open; status validates the token
    try {
      await api("/status");
      sessionStorage.setItem("panel_token", token);
      $("#gate").classList.add("hidden");
      $("#app").classList.remove("hidden");
      boot();
      return true;
    } catch (e) {
      $("#gate-err").textContent = e.status === 401 ? "Invalid token." : (e.message || "Failed");
      return false;
    }
  }

  function initGate() {
    const saved = tokenFromUrl() || sessionStorage.getItem("panel_token") || "";
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
          el("div", { class: "sub", text: it.username || ("id " + it.id) }),
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

  // ---- entity view ----
  async function selectEntity(it) {
    State.entity = it;
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
    sub.appendChild(el("span", { class: "faint", text: "id " + it.id }));
    $("#ev-avatar").src = avatarUrl(it.id, true);
    switchEvTab("commands");
    renderCommands(it);
  }

  function initEntityTabs() {
    $$("#ev-tabs .tab").forEach((t) =>
      t.addEventListener("click", () => switchEvTab(t.dataset.ev))
    );
  }
  function switchEvTab(name) {
    $$("#ev-tabs .tab").forEach((t) => t.classList.toggle("active", t.dataset.ev === name));
    $("#ev-commands").classList.toggle("hidden", name !== "commands");
    $("#ev-messages").classList.toggle("hidden", name !== "messages");
    $("#ev-media").classList.toggle("hidden", name !== "media");
    if (name === "messages") loadMessages();
    if (name === "media") loadMedia();
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

  function renderCommands(it) {
    const pane = $("#ev-commands");
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
      { key: "text", type: "textarea", label: "Text", ph: "متن برای ترجمه…" },
    ], (v, btn) => runCommand("translate", { text: v.text, target_lang: v.target_lang, source: "auto" }, "Translate", btn)));

    grid.appendChild(card("Image", "🎨", "Generate an image — rendered inline.", [
      { key: "model", type: "select", label: "Model", options: [{ v: "flux", t: "Flux (fast)" }, { v: "sdxl", t: "SDXL (photoreal)" }] },
      { key: "prompt", type: "textarea", label: "Prompt", ph: "sunset over snowy mountains, cinematic" },
    ], (v, btn) => runCommand("image", { model: v.model, prompt: v.prompt }, "Image", btn)));

    grid.appendChild(card("Text-to-Speech", "🔊", "Generate audio — plays inline.", [
      { key: "voice", label: "Voice (optional)", ph: "e.g. Orus" },
      { key: "text", type: "textarea", label: "Text", ph: "Hello from SakaiBot" },
    ], (v, btn) => runCommand("tts", { text: v.text, voice: v.voice || null }, "TTS", btn)));

    pane.appendChild(grid);
  }

  // ---- messages (with scroll-up pagination) ----
  const PAGE = 30;
  let msgState = { oldestId: null, loading: false, hasMore: true };

  function messageBubble(m) {
    const bubble = el("div", { class: "msg" + (m.out ? " out" : "") }, [
      el("div", { class: "who", dir: "auto", text: `${m.sender} · ${fmtTime(m.timestamp)}` }),
      el("div", { class: "body", dir: "auto", text: m.text || (m.has_media ? "[media]" : "") }),
    ]);
    if (m.is_voice) {
      bubble.appendChild(el("button", {
        class: "btn voice-btn", text: "🎤 Transcribe (STT)",
        onclick: () => runCommand("stt", { entity_id: State.entity.id, message_id: m.id }, "STT", null),
      }));
    }
    return bubble;
  }

  async function loadMessages() {
    const pane = $("#ev-messages");
    pane.innerHTML = "";
    msgState = { oldestId: null, loading: false, hasMore: true };
    const top = el("div", { class: "msg-top muted", text: "Loading…" });
    const scroll = el("div", { class: "msg-scroll" }, [top]);
    pane.appendChild(scroll);
    scroll.addEventListener("scroll", () => {
      if (scroll.scrollTop < 60) loadOlderMessages(scroll, top);
    });
    await loadOlderMessages(scroll, top, true);
    scroll.scrollTop = scroll.scrollHeight; // start at the newest (bottom)
  }

  async function loadOlderMessages(scroll, top, initial = false) {
    if (msgState.loading || !msgState.hasMore) return;
    msgState.loading = true;
    if (!initial) top.textContent = "Loading older…";
    try {
      const cursor = msgState.oldestId ? `&before_id=${msgState.oldestId}` : "";
      const data = await api(`/entity/${State.entity.id}/history?limit=${PAGE}${cursor}`);
      if (!data.items.length) {
        msgState.hasMore = false;
        top.textContent = initial ? "No messages." : "";
        return;
      }
      const older = data.items.slice().reverse(); // oldest -> newest
      const prevH = scroll.scrollHeight;
      const frag = document.createDocumentFragment();
      for (const m of older) frag.appendChild(messageBubble(m));
      top.after(frag); // older page sits just below the indicator, above existing
      msgState.oldestId = data.oldest_id;
      if (data.items.length < PAGE) { msgState.hasMore = false; top.textContent = "Beginning of chat"; }
      else { top.textContent = "↑ scroll for older"; }
      if (!initial) scroll.scrollTop = scroll.scrollTop + (scroll.scrollHeight - prevH);
    } catch (e) {
      top.textContent = e.message;
    } finally {
      msgState.loading = false;
    }
  }

  // ---- media ----
  async function loadMedia() {
    const pane = $("#ev-media");
    pane.innerHTML = "<div class='muted'>Loading media…</div>";
    try {
      const data = await api(`/entity/${State.entity.id}/media?kind=all&limit=24`);
      pane.innerHTML = "";
      if (!data.items.length) { pane.innerHTML = "<div class='muted'>No media in this chat.</div>"; return; }
      const grid = el("div", { class: "media-grid" });
      for (const m of data.items) {
        const fileUrl = mediaUrl(`/api/entity/${State.entity.id}/media/${m.message_id}/file`);
        const tile = el("div", { class: "media-tile", onclick: () => window.open(fileUrl, "_blank") },
          el("span", { class: "badge2", text: m.kind }));
        if (m.kind === "photo" || m.kind === "video") {
          tile.appendChild(el("img", { loading: "lazy", src: mediaUrl(`/api/entity/${State.entity.id}/media/${m.message_id}/thumb`) }));
        } else {
          tile.appendChild(el("div", { class: "doc", text: m.file_name || m.mime || m.kind }));
        }
        grid.appendChild(tile);
      }
      pane.appendChild(grid);
    } catch (e) { pane.innerHTML = `<div class='muted'>${esc(e.message)}</div>`; }
  }

  // ---- run command + results ----
  async function runCommand(kind, payload, title, btn) {
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
    $$(".dash-nav .chip").forEach((c) => c.addEventListener("click", () => openDash(c.dataset.dash)));
    $("#modal-close").addEventListener("click", () => $("#modal").classList.add("hidden"));
    $("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); });
    $("#rail-clear").addEventListener("click", () => {
      $("#rail-body").innerHTML = '<div class="rail-empty">Command results appear here.</div>';
      updateRailCount();
    });
    $("#theme-toggle").addEventListener("click", () => {
      const root = document.documentElement;
      root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
      localStorage.setItem("panel_theme", root.dataset.theme);
    });
  }

  async function openDash(which) {
    const modal = $("#modal"); const body = $("#modal-body");
    $("#modal-title").textContent = { keys: "API Key Health", models: "Model Matrix", auth: "Authorized Users", help: "Help" }[which] || which;
    body.innerHTML = "<div class='muted'>Loading…</div>";
    modal.classList.remove("hidden");
    try {
      if (which === "keys") body.replaceChildren(renderKeys(await api("/keys")));
      else if (which === "models") body.replaceChildren(renderModels(await api("/models")));
      else if (which === "help") body.replaceChildren(renderHelp(await api("/help")));
      else if (which === "auth") await renderAuth(body);
    } catch (e) { body.innerHTML = `<div class='err'>${esc(e.message)}</div>`; }
  }

  function renderKeys(d) {
    const wrap = el("div");
    for (const p of d.providers) {
      wrap.appendChild(el("div", { class: "auth-row" }, [
        el("strong", { class: "grow", text: p.name }),
        el("span", { class: "muted", text: `${p.configured_keys} key(s)` }),
        p.is_primary ? el("span", { class: "pill good", text: "primary" }) : el("span", { class: "pill neutral", text: "fallback" }),
      ]));
    }
    if (d.live && d.live.keys) {
      const table = el("table", { class: "keytable" }, [
        el("tr", {}, [el("th", { text: "#" }), el("th", { text: "Status" }), el("th", { text: "Available" }), el("th", { text: "Errors" })]),
        ...d.live.keys.map((k) => el("tr", {}, [
          el("td", { text: "#" + (k.index + 1) + (k.is_current ? " ◀" : "") }),
          el("td", {}, [el("span", { class: "pill " + (k.status === "healthy" ? "good" : k.status === "exhausted" ? "bad" : "warn"), text: k.status })]),
          el("td", { text: k.available ? "yes" : "no" }),
          el("td", { text: String(k.error_count) }),
        ])),
      ]);
      wrap.appendChild(el("h3", { text: "Live key health", style: "margin-top:14px" }));
      wrap.appendChild(table);
    }
    return wrap;
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

  // ---- helpers ----
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }
  function fmtTime(iso) { if (!iso) return ""; try { return new Date(iso).toLocaleString(); } catch (_) { return iso; } }

  // ---- boot ----
  async function boot() {
    const theme = localStorage.getItem("panel_theme");
    if (theme) document.documentElement.dataset.theme = theme;
    await loadStatus();
    try { const s = await api("/status"); realPhotosEnabled = !!(s.panel && s.panel.real_photos); } catch (_) {}
    await loadDialogs();
  }

  function init() {
    initGate();
    initSidebar();
    initEntityTabs();
    initDashboards();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
