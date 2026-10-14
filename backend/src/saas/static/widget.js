/* GroundTruth Customer Support widget — vanilla JS, no framework on the host page.
 *
 * Usage:
 *   <script src="https://example.com/static/widget.js"
 *           data-public-key="pk_xxx"
 *           data-api="https://your-api.example"></script>
 *
 * The script tag's data-attributes configure the widget. The widget mounts a
 * floating bubble that opens a chat panel; messages stream from the backend
 * via SSE. End-user sessions are persisted in localStorage so conversation
 * history survives reloads.
 */
(function () {
  "use strict";
  var script = document.currentScript;
  if (!script) { console.error("[groundtruth-widget] currentScript not found"); return; }
  var PUBLIC_KEY = script.getAttribute("data-public-key");
  var API = (script.getAttribute("data-api") || "").replace(/\/$/, "");
  if (!PUBLIC_KEY || !API) { console.error("[groundtruth-widget] data-public-key and data-api required"); return; }

  var SESSION_KEY = "sw_session_" + PUBLIC_KEY;
  var CONV_KEY = "sw_conv_" + PUBLIC_KEY;
  var HIST_KEY = "sw_hist_" + PUBLIC_KEY;

  function $(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === "style") for (var s in attrs.style) el.style[s] = attrs.style[s];
      else if (k === "html") el.innerHTML = attrs[k];
      else el.setAttribute(k, attrs[k]);
    }
    if (children) for (var i = 0; i < children.length; i++) el.appendChild(children[i]);
    return el;
  }

  // Inject styles once.
  var style = document.createElement("style");
  style.textContent = [
    ".sw-fab{position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;background:#0ea5e9;color:#fff;border:0;font-size:24px;cursor:pointer;box-shadow:0 6px 24px rgba(0,0,0,.25);z-index:2147483646;}",
    ".sw-panel{position:fixed;right:20px;bottom:88px;width:360px;max-height:560px;display:flex;flex-direction:column;background:#0f172a;color:#e2e8f0;border:1px solid #1e293b;border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,.4);z-index:2147483647;font-family:system-ui,sans-serif;}",
    ".sw-header{padding:10px 12px;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:space-between;font-weight:600;}",
    ".sw-body{flex:1;overflow-y:auto;padding:10px 12px;font-size:14px;}",
    ".sw-msg{margin:6px 0;padding:8px 10px;border-radius:8px;line-height:1.4;white-space:pre-wrap;}",
    ".sw-user{background:#0ea5e9;color:#fff;text-align:right;}",
    ".sw-bot{background:#1e293b;color:#e2e8f0;}",
    ".sw-form{display:flex;border-top:1px solid #1e293b;}",
    ".sw-input{flex:1;background:transparent;border:0;outline:0;padding:10px 12px;color:#e2e8f0;font:inherit;}",
    ".sw-send{background:transparent;color:#0ea5e9;border:0;padding:0 12px;cursor:pointer;font-weight:600;}",
    ".sw-cites{font-size:11px;color:#94a3b8;margin-top:4px;}",
    ".sw-close{background:transparent;border:0;color:#94a3b8;cursor:pointer;font-size:18px;}",
  ].join("");
  document.head.appendChild(style);

  var fab = $("button", { class: "sw-fab", "aria-label": "Open GroundTruth chat" });
  fab.textContent = "💬";

  var panel = null;
  var body = null;
  var input = null;

  function getHistory() {
    try { return JSON.parse(localStorage.getItem(HIST_KEY) || "[]"); }
    catch (_) { return []; }
  }
  function pushHistory(role, content, cites) {
    var hist = getHistory();
    hist.push({ role: role, content: content, cites: cites || [] });
    localStorage.setItem(HIST_KEY, JSON.stringify(hist.slice(-50)));
  }
  function renderHistory() {
    body.innerHTML = "";
    var hist = getHistory();
    for (var i = 0; i < hist.length; i++) appendMessage(hist[i].role, hist[i].content, hist[i].cites);
  }

  function appendMessage(role, text, cites) {
    var d = $("div", { class: "sw-msg " + (role === "user" ? "sw-user" : "sw-bot") });
    d.textContent = text;
    body.appendChild(d);
    if (cites && cites.length) {
      var c = $("div", { class: "sw-cites" });
      c.textContent = "Sources: " + cites.map(function (x) { return x.filename; }).join(", ");
      body.appendChild(c);
    }
    body.scrollTop = body.scrollHeight;
    return d;
  }

  function buildPanel() {
    var closeBtn = $("button", { class: "sw-close", "aria-label": "Close" });
    closeBtn.textContent = "✕";
    closeBtn.onclick = function () { panel.remove(); panel = null; };
    var header = $("div", { class: "sw-header" }, [
      document.createTextNode("Help"),
      closeBtn,
    ]);
    body = $("div", { class: "sw-body" });
    input = $("input", { class: "sw-input", placeholder: "Ask a question…", autocomplete: "off" });
    var send = $("button", { class: "sw-send", type: "submit" });
    send.textContent = "Send";
    var form = $("form", { class: "sw-form" }, [input, send]);
    form.onsubmit = function (e) { e.preventDefault(); var q = input.value.trim(); if (q) { input.value = ""; ask(q); } };
    panel = $("div", { class: "sw-panel" }, [header, body, form]);
    document.body.appendChild(panel);
    renderHistory();
    input.focus();
  }

  function ask(query) {
    appendMessage("user", query);
    pushHistory("user", query);
    var botEl = appendMessage("bot", "");
    var collected = "";
    var cites = [];
    var sessionId = localStorage.getItem(SESSION_KEY);
    var convId = localStorage.getItem(CONV_KEY);

    fetch(API + "/widget/chat?public_key=" + encodeURIComponent(PUBLIC_KEY), {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
      body: JSON.stringify({ query: query, session_id: sessionId, conversation_id: convId }),
    }).then(function (resp) {
      if (!resp.ok || !resp.body) { botEl.textContent = "Sorry, the assistant is unavailable."; return; }
      var reader = resp.body.getReader();
      var dec = new TextDecoder();
      var buf = "";
      function pump() {
        return reader.read().then(function (r) {
          if (r.done) {
            pushHistory("bot", collected, cites);
            return;
          }
          buf += dec.decode(r.value, { stream: true });
          // sse-starlette emits \r\n between fields, so events can be separated
          // by either \n\n or \r\n\r\n.
          var sepRe = /\r?\n\r?\n/;
          var m;
          while ((m = sepRe.exec(buf))) {
            var raw = buf.slice(0, m.index);
            buf = buf.slice(m.index + m[0].length);
            handle(raw);
          }
          return pump();
        });
      }
      return pump();
    }).catch(function (e) { console.error("[groundtruth-widget]", e); botEl.textContent = "Network error."; });

    function handle(raw) {
      var ev = "message", data = "";
      var lines = raw.split("\n");
      for (var i = 0; i < lines.length; i++) {
        if (lines[i].indexOf("event:") === 0) ev = lines[i].slice(6).trim();
        else if (lines[i].indexOf("data:") === 0) data += lines[i].slice(5).trim();
      }
      if (!data) return;
      try { var obj = JSON.parse(data); }
      catch (_) { return; }
      if (ev === "session" && obj.session_id) localStorage.setItem(SESSION_KEY, obj.session_id);
      else if (ev === "open" && obj.conversation_id) localStorage.setItem(CONV_KEY, obj.conversation_id);
      else if (ev === "token" && obj.text) { collected += obj.text; botEl.textContent = collected; body.scrollTop = body.scrollHeight; }
      else if (ev === "citations" && obj.citations) {
        cites = obj.citations;
        var c = $("div", { class: "sw-cites" });
        c.textContent = "Sources: " + cites.map(function (x) { return x.filename; }).join(", ");
        botEl.parentNode.insertBefore(c, botEl.nextSibling);
      }
      else if (ev === "error" && obj.detail) { botEl.textContent = "⚠ " + obj.detail; }
    }
  }

  fab.onclick = function () { if (panel) panel.remove(), panel = null; else buildPanel(); };
  document.body.appendChild(fab);
})();
