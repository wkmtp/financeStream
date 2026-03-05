const discussing = document.getElementById('discussing');
const male = document.getElementById('male');
const female = document.getElementById('female');
const risk = document.getElementById('risk');
const focus = document.getElementById('focus');
const queue = document.getElementById('queue');
const form = document.getElementById('req-form');

const chartCtx = document.getElementById('curve');
const chart = new Chart(chartCtx, {
  type: 'line',
  data: { labels: [], datasets: [] },
  options: { animation: false, responsive: true }
});

async function refreshState() {
  const res = await fetch('/api/live/state');
  const data = await res.json();
  discussing.innerText = data.discussing;
  male.innerText = data.packet.male_script;
  female.innerText = data.packet.female_script;
  risk.innerText = data.packet.risk_disclaimer;
  focus.innerHTML = data.packet.chart_focus_points.map(x => `<li>${x}</li>`).join('');

  const ts = new Date().toLocaleTimeString();
  chart.data.labels.push(ts);
  if (chart.data.labels.length > 15) chart.data.labels.shift();

  chart.data.datasets = data.snapshots.slice(0, 4).map((s, idx) => {
    const old = chart.data.datasets[idx]?.data || [];
    old.push(s.change_pct);
    if (old.length > 15) old.shift();
    return { label: s.symbol, data: old, borderWidth: 2 };
  });
  chart.update();
}

async function refreshQueue() {
  const res = await fetch('/api/audience/request');
  const data = await res.json();
  queue.innerHTML = data.items.slice(-8).reverse().map(x => `<li>${x.requested_by}: ${x.symbol}</li>`).join('');
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const symbol = document.getElementById('symbol').value;
  const user = document.getElementById('user').value || 'anonymous';
  await fetch('/api/audience/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, user })
  });
  form.reset();
  refreshQueue();
});

refreshState();
refreshQueue();
setInterval(refreshState, 4000);
setInterval(refreshQueue, 5000);
