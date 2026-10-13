// Fills the mock pages from window.ROUNDUP_MOCK (real API responses). Formatting only: no figure is computed here.
(function () {
  const D = window.ROUNDUP_MOCK;
  const { money, longDate } = window.fmt;
  const $ = (s) => document.querySelector(s);
  const sign = (s) => (s.startsWith("-") ? money(s) : "+" + money(s));
  const count = (s) => String(s).replace(/\B(?=(\d{3})+(?!\d))/g, ",");   // "3606" -> "3,606" (formatting only)
  const STRATEGY = {
    threshold: "Invest each time round-ups reach $5",
    next_session: "Invest after every purchase day",
    weekly: "Invest once a week",
    monthly: "Invest once a month",
  };
  const scen = (id) => D.scenarios.scenarios.find((s) => s.id === id);
  const styleName = (id, st) => scen(id).styles.find((x) => x.style === st).name;

  // ---------------------------------------------------------------- assumptions (rail + mobile dialog)
  function assumptions(target) {
    const items = D.assumptions.assumptions.map((a) =>
      `<dt>${a.title} <span class="rule-id">(${a.id})</span></dt><dd>${a.text}</dd>`).join("");
    target.innerHTML = `<h2 id="${target.id}-h">Assumptions</h2>
      <p class="small muted">The rules behind every number on this page. Rule numbers refer to the published
      finance rules.</p><dl>${items}</dl>
      <p class="small muted" style="margin-top:16px">${D.assumptions.disclaimer}</p>`;
    target.setAttribute("aria-labelledby", target.id + "-h");
  }
  document.querySelectorAll("[data-assumptions]").forEach(assumptions);
  const dlg = $("#assumptions-dialog"), openBtn = $("#open-assumptions");
  if (dlg && openBtn) {
    openBtn.addEventListener("click", () => dlg.showModal());
    dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
  }

  // ---------------------------------------------------------------- setup
  if (document.body.dataset.page === "setup") {
    $("#scenario-options").innerHTML = D.scenarios.scenarios.map((s, i) => `
      <label class="option"><input type="radio" name="scenario" value="${s.id}" ${i === 1 ? "checked" : ""}>
        <span class="title">${s.name}</span><span class="desc">${s.description}</span></label>`).join("");
  }

  // ---------------------------------------------------------------- results
  function chartBlock(result, mount, opts) {
    const tip = mount.querySelector(".tooltip");
    const first = result.series[0], last = result.series[result.series.length - 1];
    window.drawChart(mount.querySelector(".chart-mount"), Object.assign({
      points: result.series, tooltipEl: tip,
      summaryLabel: `Line chart from ${longDate(first.date)} to ${longDate(last.date)}. Value rises from ` +
        `${money(first.value)} to ${money(last.value)}; round-ups added rise from ${money(first.added)} to ` +
        `${money(last.added)}. Use the arrow keys to read values; a table version follows the chart.`,
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

  if (document.body.dataset.page === "results") {
    const r = D.results.result, s = r.summary, req = D.request;
    const more = !s.gain.startsWith("-");
    $("#headline").innerHTML = `Your <strong>${money(s.contributed)}</strong> of round-ups would have been worth
      <strong>${money(s.ending_value)}</strong> on ${longDate(s.as_of)} in this synthetic scenario. That is
      <strong>${money(s.gain.replace("-", ""))} ${more ? "more" : "less"}</strong> than the round-ups added.`;
    $("#stats").innerHTML = `
      <div class="stat"><dt><span class="term" title="The spare change set aside. Your own money going in, not growth.">Round-ups added</span></dt>
        <dd><span class="stat-value">${money(s.contributed)}</span><span class="stat-note">${count(r.transactions_used)} purchases</span></dd></div>
      <div class="stat"><dt><span class="term" title="What the shares and any waiting cash would have been worth on the last date.">Value at end</span></dt>
        <dd><span class="stat-value">${money(s.ending_value)}</span><span class="stat-note">on ${longDate(s.as_of)}</span></dd></div>
      <div class="stat"><dt><span class="term" title="Cash paid by the fund from what its holdings earned.">Dividends earned</span></dt>
        <dd><span class="stat-value">${money(s.dividends_earned)}</span><span class="stat-note">${s.dividend_buys} reinvested</span></dd></div>
      <div class="stat"><dt><span class="term" title="Value at end minus round-ups added. It can be negative.">Difference</span></dt>
        <dd><span class="stat-value">${sign(s.gain)}</span><span class="stat-note">${s.gain_pct}% of round-ups added</span></dd></div>`;
    $("#chips").innerHTML = [`${count(r.transactions_used)} sample purchases`, `${scen(req.scenario_id).name}, ${styleName(req.scenario_id, req.style).replace(" (synthetic)", "").toLowerCase()}`,
      STRATEGY.threshold, "Dividends reinvested", `${longDate(req.start)} – ${longDate(req.end)}`]
      .map((c) => `<li>${c}</li>`).join("") + `<li><a href="setup.html">Edit</a></li>`;
    $("#detail").textContent = `${s.roundup_buys} round-up purchases and ${s.dividend_buys} dividend ` +
      `reinvestments. ${money(s.uninvested_cash)} was still waiting to be invested on the last date.`;
    chartBlock(r, $("#chart"), { valueLabel: "Value" });
    $("#table").innerHTML = table(r);
    $("#meta").textContent = `Scenario ${D.results.meta.scenario_id} (seed ${D.results.meta.scenario_seed}, ` +
      `${D.results.meta.model_version}) · engine ${D.results.meta.engine_version} · input checksum ` +
      `${D.results.meta.input_checksum.slice(0, 12)}…`;
  }

  // ---------------------------------------------------------------- compare
  if (document.body.dataset.page === "compare") {
    const C = D.compare, a = C.a.summary, b = C.b.summary, d = C.difference;
    const rows = [
      ["Round-ups added", money(a.contributed), money(b.contributed), "same input"],
      ["Value at end", money(a.ending_value), money(b.ending_value), sign(d.ending_value)],
      ["Difference (value minus round-ups added)", sign(a.gain), sign(b.gain), sign(d.gain)],
      ["Dividends earned", money(a.dividends_earned), money(b.dividends_earned), sign(d.dividends_earned)],
      ["Cash not yet invested", money(a.uninvested_cash), money(b.uninvested_cash), sign(d.uninvested_cash)],
      ["Round-up purchases", a.roundup_buys, b.roundup_buys, d.roundup_buys.startsWith("-") ? "−" + d.roundup_buys.slice(1) : "+" + d.roundup_buys],
      ["Dividend reinvestments", a.dividend_buys, b.dividend_buys, d.dividend_buys.startsWith("-") ? "−" + d.dividend_buys.slice(1) : "+" + d.dividend_buys],
    ];
    $("#cmp-body").innerHTML = rows.map(([k, x, y, z]) =>
      `<tr><th scope="row">${k}</th><td>${x}</td><td>${y}</td><td>${z}</td></tr>`).join("");
    const top = Math.max(...[...C.a.series, ...C.b.series].map((p) => Math.max(+p.value, +p.added)));
    const p10 = Math.pow(10, Math.floor(Math.log10(top)));
    const yMax = [1, 2, 5, 10].map((m) => m * p10).find((v) => v >= top);   // shared axis for both panels
    chartBlock(C.a, $("#chart-a"), { yMax, height: 260, valueLabel: "A" });
    chartBlock(C.b, $("#chart-b"), { yMax, height: 260, cls: "b", valueLabel: "B" });
    $("#compare-rule").textContent = C.a.series_rule;
  }

  // ---------------------------------------------------------------- saved
  if (document.body.dataset.page === "saved") {
    $("#saved-list").innerHTML = D.saved.map((x) => `
      <li class="card saved-item"><div>
        <h2 style="font-size:16px;margin:0 0 4px">${x.name}</h2>
        <p class="small muted" style="margin:0">${scen(x.scenario_id).name} · ${styleName(x.scenario_id, x.style)} ·
          ${STRATEGY[x.strategy]} · dividends ${x.reinvest ? "reinvested" : "kept as cash"}</p>
        <p class="small" style="margin:4px 0 0">Round-ups added ${money(x.summary.contributed)} · value at end
          ${money(x.summary.ending_value)} on ${longDate(x.summary.as_of)}</p></div>
        <div class="btn-row"><a class="btn" href="results.html" aria-label="Open ${x.name}">Open</a>
          <button class="btn" type="button" aria-label="Delete ${x.name}">Delete</button></div></li>`).join("");
    const tabs = document.querySelectorAll("[data-state]");
    tabs.forEach((t) => t.addEventListener("click", () => {
      tabs.forEach((u) => u.setAttribute("aria-pressed", String(u === t)));
      document.querySelectorAll("[data-panel]").forEach((p) => { p.hidden = p.dataset.panel !== t.dataset.state; });
    }));
  }
})();
