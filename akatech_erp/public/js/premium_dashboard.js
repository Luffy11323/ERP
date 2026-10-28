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

  function autoRouteToHome() {
    if (!window.frappe || !frappe.boot || !frappe.boot.akatech_premium) return;
    const path = (window.location.pathname || "").replace(/\/+$/, "");
    const hash = (window.location.hash || "").replace(/^#\/?/, "");
    // If on top-level /desk, /app, or redirected to /desk/build/workspace/Home, auto route to setup/home
    if (
      (path === "/desk" || path === "" || path === "/desk/build/workspace/Home" || path === "/app") &&
      (!hash || hash === "desk")
    ) {
      if (frappe.set_route) {
        frappe.set_route("setup", "home");
      } else {
        window.location.pathname = "/desk/setup/home";
      }
    }
  }

  function slugFromPath() {
    // 1. Try frappe router
    if (window.frappe && frappe.get_route) {
      const r = frappe.get_route();
      if (r && r.length) {
        if (["Form", "List", "Tree", "query-report", "view"].includes(r[0])) return null;
        if (r[0] === "setup" && r[1] === "home") return "home";
        if (r[0] === "workspace" && r[1]) return r[1].toLowerCase();
        if (r[0] === "private" && r[1]) return r[1].toLowerCase();
        if (r[0] === "app" && r[1]) return r[1].toLowerCase();
        if (r.length === 1 && r[0] !== "desk") return r[0].toLowerCase();
      }
    }
    // 2. Try window hash
    const hash = (window.location.hash || "").replace(/^#\/?/, "").split("/").filter(Boolean);
    if (hash.length) {
      if (hash.length >= 2 && hash[0] === "setup" && hash[1] === "home") return "home";
      if (hash[0] === "workspace" && hash[1]) return hash[1].toLowerCase();
      if (hash[0] === "private" && hash[1]) return hash[1].toLowerCase();
      if (hash.length === 1 && hash[0] !== "desk") return hash[0].toLowerCase();
    }
    // 3. Fallback to pathname
    const p = decodeURIComponent(window.location.pathname).split("/").filter(Boolean);
    if (p.length) {
      if (p.includes("Form") || p.includes("List") || p.includes("view")) return null;
      if (p.length >= 2 && p[p.length - 2] === "setup" && p[p.length - 1] === "home") return "home";
      const last = p[p.length - 1].toLowerCase();
      if (["home", "selling", "buying", "stock", "assets", "accounts", "hr", "payroll", "crm", "projects", "manufacturing"].includes(last)) {
        return last;
      }
      if (p[0] === "app" || p[0] === "desk") {
        if (p[1] === "workspace" && p[2]) return p[2].toLowerCase();
        if (p[1] === "private" && p[2]) return p[2].toLowerCase();
        if (p.length === 2 && p[1] !== "desk") return p[1].toLowerCase();
        if (p.length === 1 && p[0] === "app") return "home";
      }
    }
    return null;
  }

  const mountPoint = () => {
    if ($(".form-layout:visible, .list-layout:visible, .report-page:visible, .standard-filter-section:visible, .form-page:visible").length) return null;
    if (window.frappe && frappe.get_route) {
      const r = frappe.get_route();
      if (r && r.length && ["Form", "List", "Tree", "query-report", "view"].includes(r[0])) return null;
    }
    const $m = $(".layout-main-section").filter(":visible").first();
    if ($m.length) return $m;
    const $w = $(".workspace-page:visible, .page-container:visible, .desk-page:visible").find(".layout-main-section").filter(":visible").first();
    if ($w.length) return $w;
    return null;
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

  /* Render Home Self-Service card (User Photo, Stats & My Tasks) */
  function renderHomeSelfCard(card, $main) {
    $(".aka-hero, .aka-ledger, .aka-home-wrapper").remove();

    const empImage = card.employee_image
      ? `<img src="${esc(card.employee_image)}" class="aka-home-avatar" alt="Avatar" />`
      : `<div class="aka-home-avatar-initial">${esc(card.employee_name ? card.employee_name.charAt(0) : "U")}</div>`;

    const checkinBtnText = card.is_checked_in ? "Check-out" : "Check-in";

    let tasksHtml = `<div class="aka-no-tasks">No open tasks. You are all caught up.</div>`;
    if (card.tasks && card.tasks.length > 0) {
      tasksHtml = `<div class="aka-task-list">` +
        card.tasks.map(t => `<div class="aka-task-item"><a href="/app/todo/${encodeURIComponent(t.name)}">${esc(t.description)}</a></div>`).join("") +
        `</div>`;
    }

    const picker = card.privileged
      ? `<div style="margin-bottom:8px;"><select id="aka-emp-home" class="aka-select" style="max-width:200px;font-size:12px;padding:4px 8px;"><option value="">— Preview Employee —</option></select></div>`
      : "";

    const html = `
      <div class="aka-home-wrapper">
        <div class="aka-self-card">
          <div class="aka-self-avatar-col">
            ${empImage}
          </div>
          <div class="aka-self-info-col">
            <h2 class="aka-self-name">${esc(card.employee_name)}</h2>
            <div class="aka-self-id">Employee #: ${esc(card.employee_id)}</div>
            <div class="aka-self-time">Logged in: <b>${esc(card.login_time)}</b></div>
            <div class="aka-self-time">Last OUT: <b>${esc(card.last_out_time)}</b></div>
            <div class="aka-self-attendance">Present: <b>${card.present_days} / ${card.total_work_days} work days</b></div>
            <div class="aka-self-badges">
              <span class="aka-badge-absent">Absent: ${card.absent_days}</span>
              <span class="aka-badge-leaves">Leaves: ${card.leave_days}</span>
            </div>
            <div class="aka-self-hours">Total Hours: <b>${Number(card.total_hours).toFixed(1)} / ${Number(card.expected_hours).toFixed(1)} hrs</b></div>
          </div>
          <div class="aka-self-action-col">
            ${picker}
            <div class="aka-self-month">${esc(card.month_label)}</div>
            <button class="aka-btn-checkin" id="aka-home-checkin-btn">${esc(checkinBtnText)}</button>
          </div>
        </div>

        <div class="aka-tasks-card">
          <div class="aka-tasks-head">
            <span class="aka-tasks-title">My Tasks</span>
            <a href="/app/todo" class="aka-tasks-viewall">View all</a>
          </div>
          <div class="aka-tasks-body">
            ${tasksHtml}
          </div>
        </div>
      </div>
    `;

    const $elem = $(html);
    $main.prepend($elem);

    $elem.find("#aka-home-checkin-btn").on("click", function () {
      frappe.confirm(`Record your ${checkinBtnText} now?`, () => {
        frappe.call({
          method: API + "toggle_checkin",
          args: { employee: viewAs() },
          freeze: true
        }).then((r) => {
          frappe.show_alert({ message: `Successfully recorded ${r.message.log_type}`, indicator: "green" });
          load(true);
        });
      });
    });

    if (card.privileged) {
      frappe.call({ method: API + "get_employee_options" }).then((r) => {
        const $s = $elem.find("#aka-emp-home"), cur = viewAs();
        if (r.message && $s.length) {
          r.message.forEach((e) => {
            $s.append(`<option value="${esc(e.name)}"${e.name === cur ? " selected" : ""}>${esc(e.employee_name)}</option>`);
          });
          $s.on("change", function () {
            const v = $(this).val();
            if (v) sessionStorage.setItem(EMP_KEY, v);
            else sessionStorage.removeItem(EMP_KEY);
            load(true);
          });
        }
      });
    }
  }

  function renderHero(card, $main) {
    $(".aka-hero, .aka-ledger, .aka-home-wrapper").remove();
    let head = `<h3>${greeting()}, ${esc(card.user)} 👋</h3><div class="aka-sub">${esc(card.title)} — ${esc(card.subtitle)}</div>`;
    const kp = card.kpis && card.kpis.length ? `<div class="aka-kpis">${card.kpis.map(kpiHtml).join("")}</div>` : "";
    const $hero = $(`<div class="aka-hero"><div class="aka-head"><div>${head}</div></div>${kp}</div>`);
    $main.prepend($hero);

    $hero.on("click", ".aka-kpi", function () {
      const r = $(this).data("route");
      if (r) {
        if (window.frappe && frappe.set_route) {
          frappe.set_route(r);
        } else {
          window.location.href = "/app/" + r;
        }
      }
    });
  }

  let busy = false;
  function load(force) {
    if (!frappe.boot || !frappe.boot.akatech_premium) return;
    const slug = slugFromPath();
    const $mainCheck = mountPoint();
    if (!slug || !$mainCheck) {
      $(".aka-hero, .aka-ledger, .aka-home-wrapper").remove();
      return;
    }
    const currentMountedSlug = $(".aka-hero").data("slug") || $(".aka-home-wrapper").data("slug");
    if (!force && currentMountedSlug === slug) return;
    if (busy) return;
    busy = true;
    let tries = 0;
    const wait = setInterval(() => {
      const $main = mountPoint();
      if (!$main && ++tries < 30) return;
      clearInterval(wait);
      if (!$main) { busy = false; return; }
      frappe.call({ method: API + "get_card", args: { slug, employee: viewAs() } }).then((r) => {
        if (slugFromPath() !== slug) return;
        $(".aka-hero, .aka-ledger, .aka-home-wrapper").remove();
        if (r.message) {
          if (r.message.type === "home_self") {
            renderHomeSelfCard(r.message, $main);
            $(".aka-home-wrapper").data("slug", slug);
          } else {
            renderHero(r.message, $main);
            $(".aka-hero").data("slug", slug);
          }
        }
      }).always(() => { busy = false; });
    }, 150);
  }

  $(document).ready(() => {
    if (!frappe.boot || !frappe.boot.akatech_premium) return;
    $("body").addClass("aka-premium");
    autoRouteToHome();
    frappe.router.on("change", () => {
      autoRouteToHome();
      const slug = slugFromPath();
      const $m = mountPoint();
      if (!slug || !$m) {
        $(".aka-hero, .aka-ledger, .aka-home-wrapper").remove();
      }
      setTimeout(() => { load(false); }, 150);
    });
    setTimeout(() => {
      autoRouteToHome();
      load(false);
    }, 500);
  });
})();
