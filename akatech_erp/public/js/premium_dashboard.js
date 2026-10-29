/* Radiant premium dashboards: hero cards on main workspaces + Self Service home card */
(function () {
  console.log("[Akatech Premium] Initializing dashboard module v16.5...");

  // Patch Frappe play_sound to prevent annoying phantom error sounds
  if (window.frappe && frappe.utils && frappe.utils.play_sound) {
    const _original_play_sound = frappe.utils.play_sound;
    frappe.utils.play_sound = function(name) {
      if (name === "error") {
        if ($('.desk-alert:visible, .msgprint-dialog:visible, .modal:visible, .toast:visible').length === 0) {
          return;
        }
      }
      return _original_play_sound(name);
    };
  }

  // Automatic redirect away from /desk or /desk/build/workspace/Home to /desk/setup/home
  function enforceCorrectHomeUrl() {
    try {
      const p = (window.location.pathname || "").toLowerCase().replace(/\/+$/, "");
      if (p.includes("build/workspace/home") || p === "/desk" || p === "/app" || p === "") {
        console.log("[Akatech Premium] Redirecting from", p, "to /desk/setup/home");
        if (window.location.replace) {
          window.location.replace("/desk/setup/home");
        } else {
          window.location.href = "/desk/setup/home";
        }
        return true;
      }
    } catch (e) {
      console.error("[Akatech Premium] URL redirect error:", e);
    }
    return false;
  }

  // Execute redirect immediately on script load
  enforceCorrectHomeUrl();

  const esc = (s) => (window.frappe && frappe.utils ? frappe.utils.escape_html(String(s == null ? "" : s)) : String(s == null ? "" : s));
  const money = (v) => (typeof format_currency === "function" ? format_currency(v || 0) : "Rs " + (v || 0).toLocaleString());
  const num = (v) => (v || 0).toLocaleString();
  const API = "akatech_erp.premium_api.";
  const EMP_KEY = "aka_view_as_employee";

  function slugFromPath() {
    // 1. Check router route if available
    if (window.frappe && frappe.get_route) {
      const r = frappe.get_route();
      if (r && r.length) {
        if (["Form", "List", "Tree", "query-report", "view"].includes(r[0])) return null;
        const rLower = r.map(x => String(x).toLowerCase());
        if (rLower.includes("home")) return "home";
        for (let s of ["selling", "buying", "stock", "assets", "accounts", "hr", "payroll", "crm", "projects", "manufacturing", "procurement", "sales"]) {
          if (rLower.includes(s)) return s;
        }
      }
    }
    // 2. Check window location pathname
    const pathname = decodeURIComponent(window.location.pathname || "").toLowerCase();
    if (pathname.includes("/form/") || pathname.includes("/list/") || pathname.includes("/view/")) {
      return null;
    }
    if (pathname.includes("home")) return "home";
    for (let s of ["selling", "buying", "stock", "assets", "accounts", "hr", "payroll", "crm", "projects", "manufacturing", "procurement", "sales"]) {
      if (pathname.includes("/" + s)) return s;
    }
    // 3. Check hash
    const hash = decodeURIComponent(window.location.hash || "").toLowerCase();
    if (hash.includes("home")) return "home";
    for (let s of ["selling", "buying", "stock", "assets", "accounts", "hr", "payroll", "crm", "projects", "manufacturing", "procurement", "sales"]) {
      if (hash.includes(s)) return s;
    }
    return null;
  }

  const mountPoint = () => {
    // Hide cards on form/list/report views
    if ($(".form-layout:visible, .list-layout:visible, .report-page:visible").length) return null;
    if (window.frappe && frappe.get_route) {
      const r = frappe.get_route();
      if (r && r.length && ["Form", "List", "Tree", "query-report", "view"].includes(r[0])) return null;
    }

    const selectors = [
      ".layout-main-section",
      ".editor-js-container",
      "#editorjs",
      ".page-main-content",
      ".workspace-page",
      ".desk-page",
      ".page-container"
    ];
    for (const sel of selectors) {
      const $el = $(sel).filter(":visible").first();
      if ($el.length) return $el;
    }
    const $any = $(".page-container:visible, .desk-page:visible, #editorjs").first();
    if ($any.length) return $any;
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
        card.tasks.map(t => {
          const typeBadge = t.ref_type ? `<span class="aka-task-badge">${esc(t.ref_type)}</span>` : "";
          const refText = t.ref_name ? `<b class="aka-task-ref">${esc(t.ref_name)}</b> ` : "";
          const desc = esc(t.description || t.name);
          return `<div class="aka-task-item">
            <a href="${esc(t.url || '/app/todo/' + t.name)}">
              <div class="aka-task-line">${typeBadge}${refText}<span class="aka-task-desc">${desc}</span></div>
            </a>
          </div>`;
        }).join("") +
        `</div>`;
    }

    const picker = card.privileged
      ? `<div style="margin-bottom:8px;"><select id="aka-emp-home" class="aka-select" style="max-width:200px;font-size:12px;padding:4px 8px;"><option value="">— Preview Employee —</option></select></div>`
      : "";

    const html = `
      <div class="aka-home-wrapper" data-slug="home">
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
    if ($main.find("#editorjs").length) {
      $main.find("#editorjs").before($elem);
    } else {
      $main.prepend($elem);
    }

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

  function renderHero(card, $main, slug) {
    $(".aka-hero, .aka-ledger, .aka-home-wrapper").remove();
    let head = `<h3>${greeting()}, ${esc(card.user)} 👋</h3><div class="aka-sub">${esc(card.title)} — ${esc(card.subtitle)}</div>`;
    const kp = card.kpis && card.kpis.length ? `<div class="aka-kpis">${card.kpis.map(kpiHtml).join("")}</div>` : "";
    const $hero = $(`<div class="aka-hero" data-slug="${esc(slug)}"><div class="aka-head"><div>${head}</div></div>${kp}</div>`);
    
    if ($main.find("#editorjs").length) {
      $main.find("#editorjs").before($hero);
    } else {
      $main.prepend($hero);
    }

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
    enforceCorrectHomeUrl();
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
          } else {
            renderHero(r.message, $main, slug);
          }
        }
      }).always(() => { busy = false; });
    }, 150);
  }

  $(document).ready(() => {
    $("body").addClass("aka-premium");
    enforceCorrectHomeUrl();

    if (window.frappe && frappe.router) {
      frappe.router.on("change", () => {
        enforceCorrectHomeUrl();
        const slug = slugFromPath();
        const $m = mountPoint();
        if (!slug || !$m) {
          $(".aka-hero, .aka-ledger, .aka-home-wrapper").remove();
        }
        setTimeout(() => { load(false); }, 150);
      });
    }

    setTimeout(() => {
      enforceCorrectHomeUrl();
      load(false);
    }, 300);
  });
})();
