/* PTCG Pocket 卡牌瀏覽器 — 對 cards.json 做 client-side 搜尋/篩選/排序。
   零依賴。以批次渲染,讓 3000+ 張卡仍保持流暢。 */
'use strict';

const CARDS_URL = '../data/cards.json';
const BATCH = 60;
const ENERGY = {
  G: ['Grass', '#63bb5b'], R: ['Fire', '#e8564f'], W: ['Water', '#4a9ee6'],
  L: ['Lightning', '#d9ab27'], P: ['Psychic', '#b46fc9'], F: ['Fighting', '#c9773f'],
  D: ['Darkness', '#566072'], M: ['Metal', '#8f9bab'], N: ['Dragon', '#c9a83c'],
  Y: ['Fairy', '#e58fc0'], C: ['Colorless', '#b9b7ae'],
};

const state = { all: [], filtered: [], rendered: 0 };
const el = (id) => document.getElementById(id);
const grid = el('grid');

// --- 資料載入 ----------------------------------------------------------------
async function load() {
  try {
    const res = await fetch(CARDS_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.all = await res.json();
  } catch (err) {
    el('status').textContent =
      `Could not load card data (${err.message}). Serve the project over HTTP ` +
      `(e.g. "python -m http.server") and open /web/.`;
    return;
  }
  el('status').hidden = true;
  buildFilters();
  bindEvents();
  apply();
}

// --- 篩選選項清單 ------------------------------------------------------------
function uniqueSorted(key) {
  return [...new Set(state.all.map((c) => c[key]).filter(Boolean))].sort();
}
function fillSelect(id, values, allLabel) {
  const sel = el(id);
  sel.innerHTML = `<option value="">${allLabel}</option>` +
    values.map((v) => `<option value="${v}">${v}</option>`).join('');
}
function buildFilters() {
  fillSelect('f-set', uniqueSorted('set_id'), '全部卡包');
  fillSelect('f-type', ['pokemon', 'trainer'], '全部種類');
  fillSelect('f-element', uniqueSorted('element'), '全部屬性');
  fillSelect('f-rarity', uniqueSorted('rarity'), '全部稀有度');
  fillSelect('f-pack', uniqueSorted('pack'), '全部卡包系列');
}

// --- 篩選 + 排序 -------------------------------------------------------------
function cardText(c) {
  const atk = (c.attacks || []).map((a) => `${a.name} ${a.effect}`).join(' ');
  return `${c.name} ${c.ability_name} ${c.ability_text} ${atk} ${c.effect}`.toLowerCase();
}
function apply() {
  const q = el('search').value.trim().toLowerCase();
  const fSet = el('f-set').value, fType = el('f-type').value;
  const fEl = el('f-element').value, fRar = el('f-rarity').value, fPack = el('f-pack').value;

  let out = state.all.filter((c) =>
    (!fSet || c.set_id === fSet) &&
    (!fType || c.card_type === fType) &&
    (!fEl || c.element === fEl) &&
    (!fRar || c.rarity === fRar) &&
    (!fPack || c.pack === fPack) &&
    (!q || cardText(c).includes(q))
  );

  const sort = el('f-sort').value;
  const hp = (c) => (typeof c.hp === 'number' ? c.hp : -1);
  const collator = new Intl.Collator();
  out = [...out].sort((a, b) => {
    if (sort === 'name') return collator.compare(a.name, b.name);
    if (sort === 'hp-desc') return hp(b) - hp(a);
    if (sort === 'hp-asc') return hp(a) - hp(b);
    // 預設:先依卡包 id,再依卡牌編號數值
    return a.set_id === b.set_id
      ? (Number(a.number) || 0) - (Number(b.number) || 0)
      : collator.compare(a.set_id, b.set_id);
  });

  state.filtered = out;
  state.rendered = 0;
  grid.innerHTML = '';
  el('count').textContent = `${out.length} card${out.length === 1 ? '' : 's'}`;
  el('status').hidden = out.length !== 0;
  if (out.length === 0) {
    el('status').hidden = false;
    el('status').className = 'empty';
    el('status').textContent = 'No cards match your filters.';
  }
  renderMore();
}

// --- 渲染（批次） ------------------------------------------------------------
function cardTile(c, i) {
  const div = document.createElement('div');
  div.className = `card type-${c.element || 'Colorless'}`;
  div.setAttribute('role', 'listitem');
  div.dataset.i = i;
  const rarity = c.rarity || '—';
  div.innerHTML = `
    <img loading="lazy" src="${c.image_url}" alt="${escapeHtml(c.name)}"
         onerror="this.style.visibility='hidden'">
    <div class="card-body">
      <div class="card-name">${escapeHtml(c.name)}</div>
      <div class="card-meta">
        <span class="badge">${c.set_id} · ${c.number}</span>
        <span>${escapeHtml(rarity)}</span>
      </div>
    </div>`;
  div.addEventListener('click', () => openModal(c));
  return div;
}
function renderMore() {
  const next = state.filtered.slice(state.rendered, state.rendered + BATCH);
  const frag = document.createDocumentFragment();
  next.forEach((c, k) => frag.appendChild(cardTile(c, state.rendered + k)));
  grid.appendChild(frag);
  state.rendered += next.length;
}

// --- 詳情 modal --------------------------------------------------------------
function energyPips(cost) {
  return (cost || []).map((e) => {
    const [name, color] = ENERGY[e] || [e, '#b9b7ae'];
    return `<span class="energy" style="background:${color}" title="${name}">${e}</span>`;
  }).join('');
}
function openModal(c) {
  const modal = el('modal');
  modal.className = `modal type-${c.element || 'Colorless'}`;
  const attacks = (c.attacks || []).map((a) => `
    <div class="attack">
      <div class="attack-head"><span>${energyPips(a.cost)} ${escapeHtml(a.name)}</span>
        <span>${escapeHtml(a.damage || '')}</span></div>
      ${a.effect ? `<div class="attack-effect">${escapeHtml(a.effect)}</div>` : ''}
    </div>`).join('');
  const ability = c.ability_name ? `
    <div class="section-title">Ability</div>
    <div class="ability"><div class="attack-head">${escapeHtml(c.ability_name)}</div>
      <div class="attack-effect">${escapeHtml(c.ability_text)}</div></div>` : '';
  const stats = c.card_type === 'pokemon' ? `
    <div class="stat-row">
      ${c.hp != null ? `<span><b>HP</b> ${c.hp}</span>` : ''}
      ${c.element ? `<span><b>Type</b> ${c.element}</span>` : ''}
      ${c.stage ? `<span><b>Stage</b> ${escapeHtml(c.stage)}</span>` : ''}
      ${c.evolves_from ? `<span><b>Evolves from</b> ${escapeHtml(c.evolves_from)}</span>` : ''}
      ${c.weakness ? `<span><b>Weakness</b> ${escapeHtml(c.weakness)}</span>` : ''}
      <span><b>Retreat</b> ${c.retreat_cost}</span>
    </div>` : `<div class="stat-row"><span><b>Trainer</b> ${escapeHtml(c.trainer_type || '')}</span></div>`;

  el('modal-content').innerHTML = `
    <div class="modal-head">
      <img src="${c.image_url}" alt="${escapeHtml(c.name)}" onerror="this.style.display='none'">
      <div>
        <h2 class="modal-title">${escapeHtml(c.name)}</h2>
        <div class="modal-sub">${escapeHtml(c.set_name)} (${c.set_id}) · #${c.number}
          · ${escapeHtml(c.rarity || '—')}${c.pack ? ` · ${escapeHtml(c.pack)} pack` : ''}</div>
        ${stats}
      </div>
    </div>
    <div class="modal-body">
      ${ability}
      ${attacks ? `<div class="section-title">Attacks</div>${attacks}` : ''}
      ${c.effect ? `<div class="section-title">Effect</div><p>${escapeHtml(c.effect)}</p>` : ''}
      ${c.illustrator ? `<div class="section-title">Illustrator</div><p>${escapeHtml(c.illustrator)}</p>` : ''}
      <p><a href="${c.url}" target="_blank" rel="noopener">View on limitlesstcg ↗</a></p>
    </div>`;
  el('modal-backdrop').hidden = false;
}
function closeModal() { el('modal-backdrop').hidden = true; }

// --- 輔助函式 + 事件 ---------------------------------------------------------
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (m) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}
function debounce(fn, ms) {
  let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
function bindEvents() {
  el('search').addEventListener('input', debounce(apply, 150));
  ['f-set', 'f-type', 'f-element', 'f-rarity', 'f-pack', 'f-sort']
    .forEach((id) => el(id).addEventListener('change', apply));
  el('reset').addEventListener('click', () => {
    el('search').value = '';
    ['f-set', 'f-type', 'f-element', 'f-rarity', 'f-pack'].forEach((id) => (el(id).value = ''));
    el('f-sort').value = 'default';
    apply();
  });
  el('modal-close').addEventListener('click', closeModal);
  el('modal-backdrop').addEventListener('click', (e) => {
    if (e.target === el('modal-backdrop')) closeModal();
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

  new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && state.rendered < state.filtered.length) renderMore();
  }, { rootMargin: '400px' }).observe(el('sentinel'));
}

load();