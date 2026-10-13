// Fills the mock pages from window.ROUNDUP_MOCK (real API responses). Formatting only: no figure is computed here.
(function () {
  const D = window.ROUNDUP_MOCK;
  const { money, longDate } = window.fmt;
  const $ = (s) => document.querySelector(s);
  const sign = (s) => (s.startsWith("-") ? money(s) : "+" + money(s));
  const signCount = (s) => (s.startsWith("-") ? "−" + s.slice(1) : s === "0" ? "0" : "+" + s);
  const count = (s) => String(s).replace(/\B(?=(\d{3})+(?!\d))/g, ",");   // "3606" -> "3,606" (formatting only)
  const STRATEGY = {
    threshold: "Invest each time round-ups reach $5",
    next_session: "Invest after every purchase day",
    weekly: "Invest once a week",
    monthly: "Invest once a month",
  };
  const DIVIDENDS = (r) => (r ? "Dividends reinvested" : "Dividends kept as cash");
  const scen = (id) => D.scenarios.scenarios.find((s) => s.id === id);
  const styleName = (id, st) => scen(id).styles.find((x) => x.style === st).name.replace(" (synthetic)", "");

  // ---------------------------------------------------------------- assumptions (rail + mobile dialog)
  const KEY_POINTS = [
    ["Made-up prices.", "The scenario is invented. It is not a real fund or a real market."],
    ["Not a forecast.", "It says nothing about what any market will do."],
    ["No fees included.", "Real round-up apps may charge fees that matter a lot for small balances."],
    ["Not advice.", "Nothing here suggests what you should do with your money."],
  ];
  function assumptions(target, inDialog) {
    const A = D.assumptions.assumptions;
    const items = A.map((a) => `<dt>${a.title}</dt><dd>${a.text}</dd>`).join("");
    const refs = A.map((a) => `<li>${a.title}: ${a.id}</li>`).join("");
    const keys = KEY_POINTS.map(([k, t]) => `<li><strong>${k}</strong> ${t}</li>`).join("");
    target.innerHTML = (inDialog ? "" : `<h2 id="${target.id}-h">Key points</h2>`) +
      `<ul class="key-points">${keys}</ul>
      <details class="all-assumptions"><summary>All assumptions (${A.length})</summary><dl>${items}</dl>
        <p class="small muted" style="margin-top:12px">${D.assumptions.disclaimer}</p>
        <details class="refs"><summary>Rule references</summary><ul class="small">${refs}</ul></details>
      </details>`;
    if (!inDialog) target.setAttribute("aria-labelledby", target.id + "-h");
  }
  document.querySelectorAll("[data-assumptions]").forEach((t) => assumptions(t, !!t.closest("dialog")));
  const dlg = $("#assumptions-dialog"), openBtn = $("#open-assumptions");
  if (dlg && openBtn) {
    openBtn.addEventListener("click", () => { dlg.showModal(); dlg.querySelector("h2").focus(); });
    dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
  }
  // planned AI buttons: focusable, announced as unavailable (aria-disabled instead of disabled)
  document.querySelectorAll('[aria-disabled="true"]').forEach((b) => b.addEventListener("click", (e) => e.preventDefault()));
  // term definitions: real buttons that show/hide visible text (no hover-only titles)
  function wireTerms(root) {
    root.querySelectorAll("button.term").forEach((b) => b.addEventListener("click", () => {
      const def = document.getElementById(b.getAttribute("aria-controls"));
      const open = b.getAttribute("aria-expanded") === "true";
      b.setAttribute("aria-expanded", String(!open));
      def.hidden = open;
    }));
  }

  // ---------------------------------------------------------------- setup
  if (document.body.dataset.page === "setup") {
    $("#scenario-options").innerHTML = D.scenarios.scenarios.map((s, i) => `
      <label class="option"><input type="radio" name="scenario" value="${s.id}" ${i === 1 ? "checked" : ""}>
        <span class="title">${s.name}</span><span class="desc">${s.description}</span></label>`).join("");
  }

  // ---------------------------------------------------------------- charts and tables
  function chartBlock(result, mount, opts) {
    const tip = mount.querySelector(".tooltip");
    const first = result.series[0], last = result.series[result.series.length - 1];
    window.drawChart(mount.querySelector(".chart-mount"), Object.assign({
      points: result.series, tooltipEl: tip,
      summaryLabel: `Line chart from ${longDate(first.date)} to ${longDate(last.date)}. The value goes from ` +
        `${money(first.value)} to ${money(last.value)}, with ups and downs in between; round-ups added go from ` +
        `${money(first.added)} to ${money(last.added)}. Use the arrow keys to read values, or open the table version.`,
    }, opts));
    const rule = mount.querySelector(".rule");
    if (rule) rule.textContent = result.series_rule;
  }

  function table(result) {
    const rows = result.series.map((p) => `<tr><td>${longDate(p.date)}</td><td>${money(p.added)}</td>` +
      `<td>${money(p.value)}</td></tr>`).join("");
    return `<div class="table-scroll" tabindex="0" role="region" aria-label="Chart values as a table">
      <table><caption class="visually-hidden">Value and round-ups added at each chart point</caption>
      <thead><tr><th scope="col">Date</th><th scope="col">Round-ups added</th><th scope="col">Value</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
  }

  function dipSentence(d, prefix) {
    const lead = `<strong>${prefix ? prefix + ", lowest" : "Lowest"} point compared with money put in:</strong> `;
    return d ? lead + `on ${longDate(d.date)} the value was ${money(d.value)}, which was ${money(d.below_by)} below ` +
               `the ${money(d.added)} of round-ups added by then.`
             : lead + "the value never fell below the round-ups added in this scenario.";
  }
  const tile = (id, term, def, value, note) => `<div class="stat"><dt><button type="button" class="term"
      aria-expanded="false" aria-controls="def-${id}">${term}</button></dt>
      <dd><span class="stat-value">${value}</span><span class="stat-note">${note}</span>
      <p class="term-def" id="def-${id}" hidden>${def}</p></dd></div>`;

  // ---------------------------------------------------------------- results
  if (document.body.dataset.page === "results") {
    const r = D.results.result, s = r.summary, req = D.request, set = D.results_settings;
    const more = !s.gain.startsWith("-");
    $("#headline").innerHTML = `In this made-up scenario, <strong>${money(s.contributed)}</strong> of sample
      round-ups ends at <strong>${money(s.ending_value)}</strong> on ${longDate(s.as_of)}:
      <strong>${money(s.gain.replace("-", ""))}</strong> ${more ? "more" : "less"} than was put in.`;
    $("#stats").innerHTML =
      tile("added", "Round-ups added", "The spare change set aside from the purchases. This is money going in, not growth.",
           money(s.contributed), `from ${count(r.transactions_used)} sample purchases`) +
      tile("end", "Value at end", "What the shares, any cash waiting to be invested and any dividends kept as cash would be worth on the last day.",
           money(s.ending_value), `on ${longDate(s.as_of)}`) +
      tile("div", "Dividends (simulated)", "Cash the made-up fund paid out from what its holdings earned.",
           money(s.dividends_earned), `${s.dividend_buys} payments reinvested`) +
      tile("diff", "Growth on round-ups", "How far the value at the end is above, or below, the round-ups added. It can be negative.",
           sign(s.gain), `${s.gain_pct.startsWith("-") ? "" : "+"}${s.gain_pct}% compared with the round-ups added`);
    wireTerms($("#stats"));
    $("#chips").innerHTML = [`${count(r.transactions_used)} sample purchases`,
      `${scen(req.scenario_id).name}, ${styleName(req.scenario_id, req.style).toLowerCase()}`,
      STRATEGY[set.strategy], DIVIDENDS(set.reinvest), `${longDate(req.start)} – ${longDate(req.end)}`]
      .map((c) => `<li>${c}</li>`).join("") + `<li><a href="setup.html">Edit settings</a></li>`;
    $("#dip").innerHTML = dipSentence(s.deepest_dip);
    $("#detail").textContent = `On the last day, ${money(s.roundups_waiting)} of round-ups was waiting to be invested ` +
      `and ${money(s.dividends_as_cash)} of dividends was kept as cash. Money was invested ${count(s.roundup_buys)} ` +
      `times from round-ups and ${s.dividend_buys} times from dividends.`;
    chartBlock(r, $("#chart"), { valueLabel: "Value" });
    $("#table").innerHTML = table(r);
    $("#meta").textContent = `Scenario ${D.results.meta.scenario_id}, seed ${D.results.meta.scenario_seed}, ` +
      `${D.results.meta.model_version}; engine ${D.results.meta.engine_version}; input checksum ` +
      `${D.results.meta.input_checksum}. These let anyone reproduce the exact numbers.`;
  }

  // ---------------------------------------------------------------- compare
  if (document.body.dataset.page === "compare") {
    const C = D.compare, a = C.a.summary, b = C.b.summary, d = C.difference, cs = D.compare_settings;
    $("#desc-a").textContent = `${STRATEGY[cs.a.strategy]}. ${DIVIDENDS(cs.a.reinvest)}.`;
    $("#desc-b").textContent = `${STRATEGY[cs.b.strategy]}. ${DIVIDENDS(cs.b.reinvest)}.`;
    const rows = [
      ["Round-ups added", money(a.contributed), money(b.contributed), "same input"],
      ["Value at end", money(a.ending_value), money(b.ending_value), sign(d.ending_value)],
      ["Growth on round-ups", sign(a.gain), sign(b.gain), sign(d.gain)],
      ["Dividends (simulated)", money(a.dividends_earned), money(b.dividends_earned), sign(d.dividends_earned)],
      ["Round-ups waiting to be invested", money(a.roundups_waiting), money(b.roundups_waiting), "shown per side"],
      ["Dividends kept as cash", money(a.dividends_as_cash), money(b.dividends_as_cash), "shown per side"],
      ["Times invested from round-ups", a.roundup_buys, b.roundup_buys, signCount(d.roundup_buys)],
      ["Times invested from dividends", a.dividend_buys, b.dividend_buys, signCount(d.dividend_buys)],
    ];
    $("#cmp-body").innerHTML = rows.map(([k, x, y, z]) => `<tr><th scope="row">${k}</th><td data-label="A">${x}</td>` +
      `<td data-label="B">${y}</td><td data-label="B minus A">${z}</td></tr>`).join("");
    const top = Math.max(...[...C.a.series, ...C.b.series].map((p) => Math.max(+p.value, +p.added)));
    const yMax = window.niceMax(top);              // one shared scale for both panels (drawing only)
    chartBlock(C.a, $("#chart-a"), { yMax, height: 260, valueLabel: "A" });
    chartBlock(C.b, $("#chart-b"), { yMax, height: 260, cls: "b", valueLabel: "B" });
    $("#compare-rule").textContent = C.a.series_rule;
    $("#dip-a").innerHTML = dipSentence(a.deepest_dip, "A");
    $("#dip-b").innerHTML = dipSentence(b.deepest_dip, "B");
  }

  // ---------------------------------------------------------------- saved
  if (document.body.dataset.page === "saved") {
    $("#saved-list").innerHTML = D.saved.map((x) => `
      <li class="card saved-item"><div>
        <h2 style="font-size:16px;margin:0 0 4px">${x.name}</h2>
        <p class="small muted" style="margin:0">Synthetic scenario: ${scen(x.scenario_id).name} ·
          ${styleName(x.scenario_id, x.style).toLowerCase()} · ${STRATEGY[x.strategy]} · ${DIVIDENDS(x.reinvest).toLowerCase()}</p>
        <p class="small" style="margin:4px 0 0">Round-ups added ${money(x.summary.contributed)} · value at end
          ${money(x.summary.ending_value)} on ${longDate(x.summary.as_of)} · engine ${x.meta.engine_version}</p></div>
        <div class="btn-row"><a class="btn" href="results.html" aria-label="Open ${x.name}">Open</a>
          <button class="btn" type="button" aria-label="Delete ${x.name}" aria-haspopup="dialog">Delete</button></div></li>`).join("");
    const tabs = document.querySelectorAll("[data-state]");
    tabs.forEach((t) => t.addEventListener("click", () => {
      tabs.forEach((u) => u.setAttribute("aria-pressed", String(u === t)));
      document.querySelectorAll("[data-panel]").forEach((p) => { p.hidden = p.dataset.panel !== t.dataset.state; });
    }));
  }
})();
