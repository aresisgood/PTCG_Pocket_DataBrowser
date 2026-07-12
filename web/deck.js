/* 牌組實驗室 — 組牌、存牌(/api/decks)、勝率預測(/api/predict)。 */
'use strict';

const CARDS_URL = '/data/cards.json';
const MAX_COPIES = 2;   // Pocket:同名卡最多 2 張
const DECK_SIZE = 20;   // 一副牌 20 張

const state = { cards: [], byId: {}, deck: [], editingId: null };
const el = (id) => document.getElementById(id);
const cardId = (c) => `${c.set_id || c.set}-${c.number}`;

// --- 載入 --------------------------------------------------------------------
async function load() {
  try {
    const res = await fetch(CARDS_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.cards = await res.json();
  } catch (err) {
    el('status').textContent = `無法載入卡牌資料(${err.message})。請以 FastAPI 啟動:uvicorn api.main:app`;
    return;
  }
  state.byId = Object.fromEntries(state.cards.map((c) => [cardId(c), c]));
  el('status').textContent = `${state.cards.length} 張卡`;
  buildFilters();
  applyPicker();
  renderDeck();
  loadSavedDecks();
  loadMeta();
  bindEvents();
}

// --- 篩選選項清單 ------------------------------------------------------------
function uniqueSorted(key) {
  return [...new Set(state.cards.map((c) => c[key]).filter(Boolean))].sort();
}
function fillSelect(id, options, allLabel) {
  el(id).innerHTML = `<option value="">${allLabel}</option>` +
    options.map(([v, label]) => `<option value="${v}">${escapeHtml(label)}</option>`).join('');
}
function buildFilters() {
  const pair = (v) => [v, v];
  fillSelect('f-set', uniqueSorted('set_id').map(pair), '全部系列');
  fillSelect('f-type', [['pokemon', '寶可夢'], ['trainer', '訓練家']], '全部種類');
  fillSelect('f-element', uniqueSorted('element').map(pair), '全部屬性');
  fillSelect('f-rarity', uniqueSorted('rarity').map(pair), '全部稀有度');
  fillSelect('f-pack', uniqueSorted('pack').map(pair), '全部卡包');
}

// --- 卡庫 picker -------------------------------------------------------------
function applyPicker() {
  const q = el('search').value.trim().toLowerCase();
  const fSet = el('f-set').value, fType = el('f-type').value;
  const fEl = el('f-element').value, fRar = el('f-rarity').value, fPack = el('f-pack').value;
  const list = state.cards.filter((c) =>
    (!fSet || c.set_id === fSet) &&
    (!fType || c.card_type === fType) &&
    (!fEl || c.element === fEl) &&
    (!fRar || c.rarity === fRar) &&
    (!fPack || c.pack === fPack) &&
    (!q || c.name.toLowerCase().includes(q))
  ).slice(0, 120);
  const grid = el('picker-grid');
  grid.innerHTML = '';
  const frag = document.createDocumentFragment();
  for (const c of list) {
    const div = document.createElement('div');
    div.className = `card type-${c.element || 'Colorless'}`;
    div.innerHTML = `
      <img loading="lazy" src="${c.image_url}" alt="${escapeHtml(c.name)}"
           onerror="this.style.visibility='hidden'">
      <div class="card-body"><div class="card-name">${escapeHtml(c.name)}</div></div>`;
    div.addEventListener('click', () => addCard(c));
    frag.appendChild(div);
  }
  grid.appendChild(frag);
}

// --- 牌組狀態 ----------------------------------------------------------------
function deckTotal() {
  return state.deck.reduce((n, c) => n + c.count, 0);
}
function addCard(card) {
  const id = cardId(card);
  const existing = state.deck.find((c) => cardId(c) === id);
  if (existing) {
    if (existing.count < MAX_COPIES) existing.count += 1;
  } else {
    state.deck.push({
      set: card.set_id || card.set, number: card.number,
      name: card.name, count: 1,
    });
  }
  renderDeck();
}
function changeCount(id, delta) {
  const c = state.deck.find((x) => cardId(x) === id);
  if (!c) return;
  c.count += delta;
  if (c.count <= 0) state.deck = state.deck.filter((x) => cardId(x) !== id);
  renderDeck();
}
function renderDeck() {
  const total = deckTotal();
  const counter = el('deck-count');
  counter.textContent = `${total} / ${DECK_SIZE}`;
  counter.className = 'deck-count' + (total === DECK_SIZE ? ' full' : total > DECK_SIZE ? ' over' : '');

  const listEl = el('deck-list');
  if (state.deck.length === 0) {
    listEl.innerHTML = '<div class="deck-empty">點左側卡牌加入牌組</div>';
    return;
  }
  listEl.innerHTML = '';
  for (const c of state.deck) {
    const id = cardId(c);
    const row = document.createElement('div');
    row.className = 'deck-row';
    row.innerHTML = `
      <span class="dr-count">${c.count}×</span>
      <span class="dr-name">${escapeHtml(c.name)} <span class="dr-set">${c.set}·${c.number}</span></span>
      <button data-act="minus">−</button>
      <button data-act="plus">＋</button>`;
    row.querySelector('[data-act="minus"]').onclick = () => changeCount(id, -1);
    row.querySelector('[data-act="plus"]').onclick = () => changeCount(id, +1);
    listEl.appendChild(row);
  }
}

// --- 存/讀牌組(API) --------------------------------------------------------
async function saveDeck() {
  const name = el('deck-name').value.trim() || '未命名牌組';
  const payload = { name, cards: state.deck };
  const url = state.editingId ? `/api/decks/${state.editingId}` : '/api/decks';
  const method = state.editingId ? 'PUT' : 'POST';
  const res = await fetch(url, {
    method, headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (res.ok) {
    const saved = await res.json();
    state.editingId = saved.id;
    loadSavedDecks();
    flash(el('btn-save'), '已儲存');
  }
}
async function loadSavedDecks() {
  const res = await fetch('/api/decks');
  if (!res.ok) return;
  const decks = await res.json();
  const sel = el('saved-decks');
  sel.innerHTML = '<option value="">— 已存牌組 —</option>' +
    decks.map((d) => `<option value="${d.id}">${escapeHtml(d.name)} (${d.cards.reduce((n, c) => n + (c.count || 0), 0)})</option>`).join('');
}
async function openSaved(id) {
  if (!id) return;
  const res = await fetch(`/api/decks/${id}`);
  if (!res.ok) return;
  const deck = await res.json();
  state.editingId = deck.id;
  state.deck = deck.cards.map((c) => ({ ...c }));
  el('deck-name').value = deck.name;
  renderDeck();
  el('predict-result').innerHTML = '';
}
async function deleteSaved() {
  const id = el('saved-decks').value;
  if (!id) return;
  await fetch(`/api/decks/${id}`, { method: 'DELETE' });
  if (String(state.editingId) === id) newDeck();
  loadSavedDecks();
}
function newDeck() {
  state.deck = [];
  state.editingId = null;
  el('deck-name').value = '';
  el('predict-result').innerHTML = '';
  el('saved-decks').value = '';
  renderDeck();
}

// --- 預測 --------------------------------------------------------------------
async function predict() {
  const box = el('predict-result');
  if (state.deck.length === 0) { box.innerHTML = '<div class="predict-msg">牌組是空的。</div>'; return; }
  box.innerHTML = '<div class="predict-msg">計算中…</div>';
  const res = await fetch('/api/predict', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cards: state.deck }),
  });
  if (!res.ok) { box.innerHTML = '<div class="predict-msg">預測失敗。</div>'; return; }
  renderPrediction(await res.json());
}
function wrClass(pct) { return pct >= 55 ? 'good' : pct >= 48 ? 'mid' : 'bad'; }
function mlLine(r) {
  if (r.ml_win_rate == null) return '';
  const p = (r.ml_win_rate * 100).toFixed(1);
  return `<div class="wr-sub">🤖 ML 模型估計:<b>${p}%</b>(以牌組內容預測,獨立於查表)</div>`;
}

function renderPrediction(r) {
  const box = el('predict-result');

  // 查表認不出:改以 ML 估計為主(誠實標示僅供參考)。
  if (r.win_rate == null) {
    if (r.ml_win_rate != null) {
      const pct = r.ml_win_rate * 100;
      box.innerHTML = `
        <div class="wr-main">
          <span class="wr-value ${wrClass(pct)}">${pct.toFixed(1)}%</span>
          <span class="conf low">ML 估計</span>
        </div>
        <div class="predict-msg">${escapeHtml(r.message || '')}</div>`;
    } else {
      box.innerHTML = `<div class="predict-msg">${escapeHtml(r.message || '無法預測。')}
        <br>(最接近相似度 ${(r.similarity * 100).toFixed(0)}%)</div>`;
    }
    return;
  }

  const pct = r.win_rate * 100;
  box.innerHTML = `
    <div class="wr-main">
      <span class="wr-value ${wrClass(pct)}">${pct.toFixed(1)}%</span>
      <span class="conf ${r.confidence}">信心 ${r.confidence}</span>
    </div>
    <div class="wr-sub">查表:涵蓋當前 Meta ${(r.coverage * 100).toFixed(0)}% · ${r.games} 場對戰樣本</div>
    ${mlLine(r)}
    <div class="arch-name">辨識原型:${escapeHtml(r.archetype.name)}
      <span class="wr-sub">(相似度 ${(r.similarity * 100).toFixed(0)}%)</span></div>
    <div class="mu-title">最有利對戰</div>
    ${r.best.slice(0, 3).map((m) => muRow(m, 'win')).join('')}
    <div class="mu-title">最不利對戰</div>
    ${r.worst.slice(0, 3).map((m) => muRow(m, 'lose')).join('')}`;
}
function muRow(m, kind) {
  const pct = (m.rate * 100).toFixed(0);
  const cls = m.rate >= 0.5 ? 'win' : 'lose';
  return `<div class="mu-row">
    <span>${escapeHtml(m.name)}</span>
    <span><span class="mu-rate ${cls}">${pct}%</span>
    <span class="mu-games"> ${m.games}場</span></span></div>`;
}

// --- Meta 列表 ---------------------------------------------------------------
async function loadMeta() {
  const res = await fetch('/api/meta');
  if (!res.ok) return;
  const data = await res.json();
  el('meta-list').innerHTML = data.archetypes.slice(0, 20).map((a) => `
    <div class="meta-row">
      <span>${escapeHtml(a.name)}</span>
      <span class="m-share">${(a.share * 100).toFixed(1)}% · 勝率 ${a.win_rate != null ? (a.win_rate * 100).toFixed(0) + '%' : '—'}</span>
    </div>`).join('');
}

// --- 輔助 --------------------------------------------------------------------
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (m) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}
function debounce(fn, ms) {
  let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
function flash(btn, text) {
  const old = btn.textContent; btn.textContent = text;
  setTimeout(() => { btn.textContent = old; }, 1200);
}
function bindEvents() {
  el('search').addEventListener('input', debounce(applyPicker, 150));
  ['f-set', 'f-type', 'f-element', 'f-rarity', 'f-pack']
    .forEach((id) => el(id).addEventListener('change', applyPicker));
  el('f-reset').addEventListener('click', () => {
    el('search').value = '';
    ['f-set', 'f-type', 'f-element', 'f-rarity', 'f-pack'].forEach((id) => (el(id).value = ''));
    applyPicker();
  });
  el('btn-save').addEventListener('click', saveDeck);
  el('btn-new').addEventListener('click', newDeck);
  el('btn-predict').addEventListener('click', predict);
  el('btn-delete').addEventListener('click', deleteSaved);
  el('saved-decks').addEventListener('change', (e) => openSaved(e.target.value));
}

load();
