const listEl = document.getElementById("list");
const summaryEl = document.getElementById("summary");
const groupByEl = document.getElementById("group-by");
const sortEl = document.getElementById("sort");
const formEl = document.getElementById("add-form");
const offersInputs = document.getElementById("offers-inputs");
const addOfferRowBtn = document.getElementById("add-offer-row");

const MARKETPLACE_LABELS = {
  wb: "Wildberries",
  ozon: "Ozon",
  yandex: "Яндекс Маркет",
};

function makeOfferRow() {
  const row = document.createElement("div");
  row.className = "row offer-row";
  row.innerHTML = `
    <input class="offer-url" placeholder="Ссылка" required>
    <select class="offer-marketplace">
      <option value="wb">Wildberries</option>
      <option value="ozon">Ozon</option>
      <option value="yandex">Яндекс Маркет</option>
    </select>
    <input class="offer-price" type="number" step="0.01" placeholder="Цена, ₽" required>
    <button type="button" class="remove-row">Удалить</button>
  `;
  row.querySelector(".remove-row").addEventListener("click", () => {
    if (offersInputs.children.length > 1) row.remove();
  });
  return row;
}

offersInputs.appendChild(makeOfferRow());
addOfferRowBtn.addEventListener("click", () => offersInputs.appendChild(makeOfferRow()));

async function load() {
  const params = new URLSearchParams({
    group_by: groupByEl.value,
    sort: sortEl.value,
  });
  const r = await fetch("/api/items?" + params);
  const data = await r.json();
  render(data);
}

function render(data) {
  const s = data.summary;
  summaryEl.textContent =
    `Всего: ${s.total_items} · на сумму от ${s.total_min_price} ₽ · пора брать: ${s.target_hits}`;

  if (!data.groups.length) {
    listEl.innerHTML = "<p>Пока пусто. Добавь первый товар.</p>";
    return;
  }

  listEl.innerHTML = data.groups.map(g => `
    <section class="group">
      <h2>${g.label}</h2>
      ${g.items.map(cardHtml).join("")}
    </section>
  `).join("");
}

function cardHtml(item) {
  const price = item.min_price ? `${item.min_price} ₽` : "цена не указана";
  const hitBadge = item.is_target_hit ? `<span class="badge hit">пора брать</span>` : "";
  const target = item.target_price ? ` · Цель: ${item.target_price} ₽` : "";
  const note = item.note ? ` · ${escapeHtml(item.note)}` : "";

  return `
    <div class="card ${item.is_target_hit ? "hit" : ""}">
      <div class="card-main">
        <h3>${escapeHtml(item.title)}</h3>
        <div class="meta">
          <span class="badge ${item.priority}">${priorityLabel(item.priority)}</span>
          ${hitBadge}${target}${note}
        </div>
        <div class="offers-list">
          ${item.offers.map(offerHtml).join("")}
        </div>
      </div>
      <div class="price">${price}</div>
    </div>
  `;
}

function offerHtml(offer) {
  const price = offer.last_price ? `${offer.last_price} ₽` : "—";
  return `
    <div class="offer" data-offer-id="${offer.id}">
      <span class="badge ${offer.marketplace}">${MARKETPLACE_LABELS[offer.marketplace] || offer.marketplace}</span>
      <a href="${offer.url}" target="_blank" rel="noopener">ссылка</a>
      <span class="offer-price-current">${price}</span>
      <input class="price-input" type="number" step="0.01" placeholder="Новая цена">
      <button class="save-price">Сохранить</button>
    </div>
  `;
}

function priorityLabel(p) {
  return p === "high" ? "высокий" : p === "low" ? "низкий" : "средний";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

groupByEl.addEventListener("change", load);
sortEl.addEventListener("change", load);

listEl.addEventListener("click", async (e) => {
  if (!e.target.classList.contains("save-price")) return;
  const offerEl = e.target.closest(".offer");
  const offerId = offerEl.dataset.offerId;
  const input = offerEl.querySelector(".price-input");
  const value = input.value;
  if (!value) return;

  const r = await fetch(`/api/offers/${offerId}/price`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ price: value }),
  });
  if (!r.ok) {
    alert("Не получилось сохранить: " + (await r.text()));
    return;
  }
  await load();
});

formEl.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(formEl);
  const offers = [];
  document.querySelectorAll(".offer-row").forEach(row => {
    const url = row.querySelector(".offer-url").value.trim();
    if (!url) return;
    offers.push({
      url,
      marketplace: row.querySelector(".offer-marketplace").value,
      price: row.querySelector(".offer-price").value || null,
    });
  });
  if (!offers.length) {
    alert("Добавь хотя бы одну ссылку");
    return;
  }
  const body = {
    title: fd.get("title"),
    note: fd.get("note") || null,
    priority: fd.get("priority"),
    target_price: fd.get("target_price") || null,
    offers,
  };
  const r = await fetch("/api/items", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    alert("Не получилось: " + (await r.text()));
    return;
  }
  formEl.reset();
  offersInputs.innerHTML = "";
  offersInputs.appendChild(makeOfferRow());
  await load();
});

load();
