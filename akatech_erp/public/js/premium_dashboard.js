/* Radiant premium dashboards: hero cards on main workspaces + Self Service ledger */
(function () {
  // Patch Frappe play_sound to prevent annoying phantom error sounds
  if (window.frappe && frappe.utils && frappe.utils.play_sound) {
    const _original_play_sound = frappe.utils.play_sound;
    frappe.utils.play_sound = function(name) {
      if (name === "error") {
        if ($('.desk-alert:visible, .msgprint-dialog:visible, .modal:visible, .toast:visible').length === 0) {
          console.warn("Muted phantom error sound");
          return;
        }
      }
      return _original_play_sound(name);
    };
  }

  const esc = (s) => frappe.utils.escape_html(String(s == null ? "" : s));
  const money = (v) => format_currency(v || 0);
  const num = (v) => (v || 0).toLocaleString();
  const API = "akatech_erp.premium_api.";
  const EMP_KEY = "aka_view_as_employee";

  const ICONS = [
    [/sales|order|quotation|lead|opportunit/i, "🛒"], [/purchase|po|procure/i, "📦"],
    [/receiv/i, "💰"], [/payable/i, "🧾"], [/overdue/i, "⏰"], [/draft|pending/i, "📝"],
    [/present|active emp|employee/i, "🧑‍💼"], [/absent/i, "🚫"], [/leave/i, "🏖️"],
    [/net pay|pay|salary|slip/i, "💵"], [/deduct/i, "➖"], [/advance/i, "💳"], [/claim|expense/i, "🧮"],
    [/item|stock|delivery|receipt|material/i, "🏷️"], [/project|task/i, "📌"], [/asset/i, "🏢"],
    [/work order|bom/i, "🏭"], [/billed|value|invoice/i, "📈"],
  ];
  const iconFor = (label) => { for (const [re, ic] of ICONS) if (re.test(label)) return ic; return "✨"; };

  function slugFromPath() {
    const p = decodeURIComponent(window.location.pathname).split("/").filter(Boolean);
    if (p[0] !== "app") return null;
    if (p[1] === "workspace" && p[2]) return p[2].toLowerCase(); // /app/workspace/crm
    if (p[1] === "private" && p[2]) return p[2].toLowerCase(); // /app/private/home
    if (p.length === 2) return (p[1] || "home").toLowerCase(); // /app/crm
    return null;
  }
  const mountPoint = () => {
    if ($(".form-layout:visible, .list-layout:visible, .report-page:visible, .standard-filter-section:visible, .form-page:visible").length) return null;
    const $m = $(".layout-main-section").filter(":visible").first();
    return $m.length ? $m : null;
  };
  const viewAs = () => sessionStorage.getItem(EMP_KEY) || null;

  function compact(v) {
    const a = Math.abs(v || 0), s = v < 0 ? "-" : "";
    if (a >= 1e9) return s + (a / 1e9).toFixed(2) + "B";
    if (a >= 1e6) return s + (a / 1e6).toFixed(2) + "M";
    if (a >= 1e5) return s + (a / 1e3).toFixed(0) + "K";
    return s + a.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  function kpiHtml(k) {
    const full = k.fmt === "money" ? money(k.value) : num(k.value);
    const val = k.fmt === "money" ? "Rs " + compact(k.value) : num(k.value);
    return `<div class="aka-kpi" data-route="${esc(k.route || "")}" title="${esc(full)}">
      <div class="l">${esc(k.label)}</div><div class="v">${val}</div></div>`;
  }

  function greeting() {
    const h = new Date().getHours();
    return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
  }

  function renderHero(card, $main) {
    $(".aka-hero, .aka-ledger").remove();
    let head, extra = "";
    if (card.type === "self") {
      const emp = card.employee;
      const picker = card.privileged
        ? `<select id="aka-emp" class="aka-select"><option value="">— View as employee —</option></select>` : "";
      if (!emp) {
        head = `<h3>${greeting()}, ${esc(card.user)} 👋</h3>
          <div class="aka-sub">Your user isn't linked to an Employee record.${card.privileged ? " Pick an employee to preview their Self Service dashboard." : ""}</div>`;
        extra = picker;
      } else {
        const inn = card.checkin && card.checkin.log_type === "IN";
        head = `<h3>${greeting()}, ${esc(emp.employee_name)} 👋</h3>
          <div class="aka-sub">${esc(emp.designation || "")} ${emp.department ? "· " + esc(emp.department) : ""}
          ${card.checkin ? "· Last " + card.checkin.log_type + " at " + esc(card.checkin.time.slice(11, 16)) : "· Not checked in today"}</div>`;
        extra = `<div class="aka-actions">${picker}<button class="aka-btn ${inn ? "out" : ""}" id="aka-checkin">${inn ? "⏹ Check Out" : "▶ Check In"}</button></div>`;
      }
    } else {
      head = `<h3>${greeting()}, ${esc(card.user)} 👋</h3><div class="aka-sub">${esc(card.title)} — ${esc(card.subtitle)}</div>`;
    }
    const kp = card.kpis && card.kpis.length ? `<div class="aka-kpis">${card.kpis.map(kpiHtml).join("")}</div>` : "";
    const $hero = $(`<div class="aka-hero"><div class="aka-head"><div>${head}</div>${extra}</div>${kp}</div>`);
    $main.prepend($hero);

    $hero.on("click", ".aka-kpi", function () {
      const r = $(this).data("route"); if (r) window.location.href = "/app/" + r;
    });
    $hero.find("#aka-checkin").on("click", function () {
      frappe.confirm("Record your attendance now?", () =>
        frappe.call({ method: API + "toggle_checkin", args: { employee: viewAs() }, freeze: true }).then((r) => {
          frappe.show_alert({ message: `Checked ${r.message.log_type}`, indicator: "green" });
          load(true);
        }));
    });
    if (card.privileged) {
      frappe.call({ method: API + "get_employee_options" }).then((r) => {
        const $s = $hero.find("#aka-emp"), cur = viewAs();
        (r.message || []).forEach((e) => $s.append(
          `<option value="${esc(e.name)}" ${e.name === cur ? "selected" : ""}>${esc(e.employee_name)} (${esc(e.name)})</option>`));
      });
      $hero.on("change", "#aka-emp", function () {
        const v = $(this).val();
        v ? sessionStorage.setItem(EMP_KEY, v) : sessionStorage.removeItem(EMP_KEY);
        load(true);
      });
    }
    if (card.type === "self" && card.employee && slugFromPath() !== "home") renderLedger($main, $hero);
  }

  function renderLedger($main, $after) {
    const $l = $(`<div class="aka-ledger"><div class="aka-led-head"><div><h4>📒 My Running Ledger</h4>
      <div class="aka-muted">Salary, advances and expenses — full breakdown. Click a row to expand.</div></div>
      <div class="aka-filters"><label>From <input type="date" id="aka-from"></label>
      <label>To <input type="date" id="aka-to"></label><button id="aka-go">Apply</button>
      <button id="aka-print" class="alt">🖨 Print</button></div></div>
      <div id="aka-led-body" class="aka-muted">Loading ledger…</div></div>`);
    $after.after($l);
    const fetch = () => frappe.call({ method: API + "get_my_ledger",
      args: { from_date: $l.find("#aka-from").val() || null, to_date: $l.find("#aka-to").val() || null, employee: viewAs() } })
      .then((r) => paintLedger($l, r.message));
    $l.find("#aka-go").on("click", fetch);
    $l.find("#aka-print").on("click", () => {
      const printCSS = `body{font-family:'Inter',sans-serif;margin:30px;color:#0f172a;}
        h4, h6 {margin:0} .aka-tot{display:flex;gap:20px;margin:20px 0;border-bottom:2px solid #e2e8f0;padding-bottom:20px}
        .aka-tot div{flex:1} .aka-tot b{display:block;font-size:16px}
        .aka-ledger-blocks{display:flex;flex-direction:column;gap:15px}
        .aka-led-block{border:1px solid #cbd5e1;border-radius:8px;padding:12px;page-break-inside:avoid}
        .led-top{display:flex;justify-content:space-between;margin-bottom:6px;border-bottom:1px solid #f1f5f9;padding-bottom:6px}
        .led-info{font-weight:bold} .led-date{color:#64748b;margin-left:10px;font-weight:normal}
        .led-amts{display:flex;gap:15px} .led-amts .lt b{font-size:14px}
        .led-desc{font-size:12px;color:#334155} .aka-detail{display:none} a{color:inherit;text-decoration:none}`;
      w.document.write("<html><head><title>My Ledger</title><style>" + printCSS + "</style></head><body>" + 
        "<h2>My Running Ledger</h2>" + $l.find("#aka-led-body").html() + "</body></html>");
      w.document.close(); setTimeout(() => w.print(), 200);
    });
    fetch();
  }

  function items(list) {
    if (!list || !list.length) return `<div class="aka-muted">—</div>`;
    return list.map((i) => `<div class="it"><span>${esc(i.c)}</span><b>${money(i.a)}</b></div>`).join("");
  }

  function paintLedger($l, d) {
    $l.find("#aka-from").val(d.from); $l.find("#aka-to").val(d.to);
    const t = d.totals;
    const tot = (label, ic, v, c) => `<div title="${esc(money(v))}"><span>${label}</span><b>${money(v)}</b></div>`;
    let html = `<div class="aka-tot">${tot("Gross Earned", "📈", t.gross, "#6366f1")}${tot("Deductions", "➖", t.deduction, "#f43f5e")}
      ${tot("Net Salary", "💵", t.salary, "#10b981")}${tot("Advances Paid", "💳", t.advance, "#f59e0b")}
      ${tot("Expenses Reimbursed", "🧮", t.expense, "#0ea5e9")}${tot("Total Received", "🏆", t.total, "#a855f7")}</div>`;
    if (!d.rows.length) { $l.find("#aka-led-body").removeClass("aka-muted").html(html + "<p>No entries in this period.</p>"); return; }
    html += `<div class="aka-ledger-blocks">`;
    d.rows.forEach((r, i) => {
      const extra = r.extra ? Object.keys(r.extra).map((k) =>
        `<div class="it"><span>${esc(k)}</span><b>${money(r.extra[k])}</b></div>`).join("") : "";
      html += `<div class="aka-led-block" data-i="${i}">
        <div class="led-top">
          <div class="led-info">
            <span class="aka-pill ${esc(r.type)}">${esc(r.type)}</span>
            <b><a href="/app/${frappe.router.slug(r.doctype)}/${encodeURIComponent(r.ref)}">${esc(r.ref)}</a></b>
            <span class="led-date">${esc(frappe.datetime.str_to_user(r.date))}</span>
          </div>
          <div class="led-amts">
            ${r.gross ? `<span class="lg">Gross: ${money(r.gross)}</span>` : ""}
            ${r.deduction ? `<span class="ld">Ded: ${money(r.deduction)}</span>` : ""}
            <span class="lr">Rec: ${money(r.received)}</span>
            <span class="lt">Total: <b>${money(r.running)}</b></span>
          </div>
        </div>
        <div class="led-desc">${esc(r.desc)}</div>
        <div class="aka-detail" id="aka-d${i}">
          <div class="box">
            <div><h6>${r.type === "Salary" ? "Earnings" : "Items"}</h6>${items(r.earnings)}${extra}</div>
            <div>${r.deductions ? `<h6>Deductions</h6>${items(r.deductions)}` : ""}</div>
          </div>
        </div>
      </div>`;
    });
    $l.find("#aka-led-body").removeClass("aka-muted").html(html + "</div>");
    $l.find(".aka-led-block").on("click", function (e) {
      if ($(e.target).is("a")) return;
      $(this).find(".aka-detail").toggleClass("open");
    });
  }

  let busy = false;
  function load(force) {
    if (!frappe.boot.akatech_premium) return;
    const slug = slugFromPath();
    if (!slug) return;
    if (!force && $(".aka-hero").data("slug") === slug) return;
    if (busy) return; busy = true;
    let tries = 0;
    const wait = setInterval(() => {
      const $main = mountPoint();
      if (!$main && ++tries < 40) return;
      clearInterval(wait);
      if (!$main) { busy = false; return; }
      frappe.call({ method: API + "get_card", args: { slug, employee: viewAs() } }).then((r) => {
        if (slugFromPath() !== slug) return;
        $(".aka-hero, .aka-ledger").remove();
        if (r.message) { renderHero(r.message, $main); $(".aka-hero").data("slug", slug); }
      }).always(() => { busy = false; });
    }, 200);
  }

  $(document).ready(() => {
    if (!frappe.boot.akatech_premium) return;
    $("body").addClass("aka-premium");
    frappe.router.on("change", () => setTimeout(() => { load(false); }, 150));
    setTimeout(() => { load(false); }, 600);
  });
})();
