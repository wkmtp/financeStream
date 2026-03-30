const discussing = document.getElementById('discussing');
const male = document.getElementById('male');
const female = document.getElementById('female');
const risk = document.getElementById('risk');
const focus = document.getElementById('focus');
const queue = document.getElementById('queue');
const addList = document.getElementById('add-list');
const reduceList = document.getElementById('reduce-list');
const adviceResult = document.getElementById('advice-result');
const dialogueList = document.getElementById('dialogue-list');
const platformStatus = document.getElementById('platform-status');
const platformMessages = document.getElementById('platform-messages');

const reqForm = document.getElementById('req-form');
const adviceForm = document.getElementById('advice-form');
const platformReplyForm = document.getElementById('platform-reply-form');

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
  dialogueList.innerHTML = data.dialogues.map(x => `<li>[${x.role}] ${x.text}</li>`).join('');
  platformMessages.innerHTML = data.platform_messages.map(x => `<li>[${x.platform}] ${x.user}: ${x.text}</li>`).join('');

  const ts = new Date().toLocaleTimeString();
  chart.data.labels.push(ts);
  if (chart.data.labels.length > 18) chart.data.labels.shift();
  chart.data.datasets = data.snapshots.slice(0, 4).map((s, idx) => {
    const old = chart.data.datasets[idx]?.data || [];
    old.push(s.change_pct);
    if (old.length > 18) old.shift();
    return { label: s.symbol, data: old, borderWidth: 2 };
  });
  chart.update();
}

async function refreshPlatformStatus() {
  const res = await fetch('/api/platform/status');
  const data = await res.json();
  platformStatus.innerText = data.items.map(x => `${x.platform}:${x.live ? 'LIVE' : 'OFF'}(${x.room_id})`).join(' | ');
}

async function refreshQueue() {
  const res = await fetch('/api/audience/request');
  const data = await res.json();
  queue.innerHTML = data.items.slice(-8).reverse().map(x => `<li>${x.requested_by}: ${x.symbol}</li>`).join('');
}

async function refreshRecommendations() {
  const res = await fetch('/api/recommendations');
  const data = await res.json();
  addList.innerHTML = data.add_positions.map(x => `<li>${x.symbol} | ${x.action} | ${x.reason}</li>`).join('');
  reduceList.innerHTML = data.reduce_positions.map(x => `<li>${x.symbol} | ${x.action} | ${x.reason}</li>`).join('');
}

reqForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const symbol = document.getElementById('symbol').value;
  const user = document.getElementById('user').value || 'anonymous';
  await fetch('/api/audience/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, user })
  });
  reqForm.reset();
  refreshQueue();
});

adviceForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const symbol = document.getElementById('advice-symbol').value;
  const res = await fetch(`/api/advice/${encodeURIComponent(symbol)}`);
  const data = await res.json();
  adviceResult.innerText = `${data.symbol}：${data.action}（score=${data.score}）- ${data.reason}`;
});

platformReplyForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const platform = document.getElementById('reply-platform').value;
  const user = document.getElementById('reply-user').value;
  const text = document.getElementById('reply-text').value;
  await fetch('/api/platform/reply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ platform, user, text })
  });
  platformReplyForm.reset();
  refreshState();
});

refreshState();
refreshPlatformStatus();
refreshQueue();
refreshRecommendations();
setInterval(refreshState, 3500);
setInterval(refreshPlatformStatus, 10000);
setInterval(refreshQueue, 4500);
setInterval(refreshRecommendations, 12000);
