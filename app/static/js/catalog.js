/**
 * Каталог: поиск и пагинация без перезагрузки, синхронизация фильтра и «чипов» категорий.
 */
(function () {
  var catalogEl = document.getElementById("catalog-products");
  var searchForm = document.getElementById("catalog-search-form");
  var searchInput = searchForm && searchForm.querySelector('input[name="search"]');
  var categorySelect = searchForm && searchForm.querySelector('select[name="category"]');
  var paginationWrap = document.getElementById("catalog-pagination-wrap");
  var categoryPills = document.getElementById("category-pills");
  var catalogSection = document.getElementById("catalog");
  var resetLink = searchForm && searchForm.querySelector("a.btn-ghost[href]");

  if (!catalogEl || !searchForm) return;

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") || "" : "";
  }

  function getQuery() {
    return searchInput ? searchInput.value.trim() : "";
  }
  function getCategory() {
    return categorySelect ? categorySelect.value || "" : "";
  }

  function escapeHtml(s) {
    if (!s) return "";
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function buildProductCard(item) {
    var summary = item.summary || "";
    var csrf = getCsrfToken();
    var catHtml =
      '<div class="product-card__category-line">' +
      (item.category_name
        ? '<span class="product-category">' + escapeHtml(item.category_name) + "</span>"
        : "") +
      "</div>";
    var descHtml =
      '<div class="card-desc-wrap">' +
      (summary
        ? '<p class="card-desc">' + escapeHtml(summary) + "</p>"
        : '<p class="card-desc card-desc--empty" aria-hidden="true">&nbsp;</p>') +
      "</div>";
    var stock = item.stock_qty != null ? item.stock_qty : "";
    return (
      '<div class="product-card js-product-card" data-product-id="' +
      item.id +
      '" data-product-url="' +
      escapeHtml(item.url) +
      '">' +
      '<div class="product-img-wrap">' +
      '<img src="' +
      escapeHtml(item.image || "") +
      '" class="card-img-top" alt="' +
      escapeHtml(item.name) +
      '" loading="lazy">' +
      "</div>" +
      '<div class="card-body">' +
      '<div class="product-card__align">' +
      catHtml +
      "<h5 class=\"card-title\">" +
      escapeHtml(item.name) +
      "</h5>" +
      descHtml +
      "</div>" +
      '<div class="card-footer-row">' +
      "<span class=\"price\">" +
      item.price +
      " ₽</span>" +
      '<span class="stock-badge">' +
      stock +
      " шт.</span></div>" +
      '<div class="card-actions">' +
      '<a href="' +
      item.url +
      '" class="btn btn-outline-primary">Подробнее</a>' +
      '<form method="post" action="/cart/add/' +
      item.id +
      '" class="js-add-to-cart-form" data-product-id="' +
      item.id +
      '" style="flex:1;">' +
      '<input type="hidden" name="csrf_token" value="' +
      escapeHtml(csrf) +
      '">' +
      '<input type="hidden" name="quantity" value="1">' +
      '<button type="submit" class="btn btn-primary w-100"><i class="bi bi-bag-plus"></i> В корзину</button>' +
      "</form></div></div></div>"
    );
  }

  function buildPagination(page, pages) {
    if (pages <= 1) return "";
    var arr = [];
    for (var p = 1; p <= pages; p++) {
      var active = p === page ? " active" : "";
      arr.push(
        '<li class="page-item' +
          active +
          '">' +
          '<a class="page-link js-catalog-page" href="#" data-page="' +
          p +
          '">' +
          p +
          "</a></li>"
      );
    }
    return (
      '<nav aria-label="Страницы каталога" class="mt-5">' +
      '<ul class="pagination justify-content-center flex-wrap gap-1">' +
      arr.join("") +
      "</ul></nav>"
    );
  }

  function syncPillsToCategory(cat) {
    if (!categoryPills) return;
    categoryPills.querySelectorAll("a.category-pill").forEach(function (a) {
      var v = a.getAttribute("data-category") || "";
      var match = (cat === "" && v === "") || String(cat) === v;
      a.classList.toggle("active", match);
    });
  }

  function applyCategoryFromPillValue(cat) {
    if (categorySelect) categorySelect.value = cat;
    syncPillsToCategory(cat);
  }

  function updateUrl() {
    var u = new URL(window.location.origin + window.location.pathname);
    var q = getQuery();
    var c = getCategory();
    if (q) u.searchParams.set("search", q);
    else u.searchParams.delete("search");
    if (c) u.searchParams.set("category", c);
    else u.searchParams.delete("category");
    u.searchParams.delete("page");
    var qs = u.searchParams.toString();
    var path = u.pathname + (qs ? "?" + qs : "");
    if (path !== window.location.pathname + window.location.search) {
      history.pushState({ catalog: 1 }, "", path);
    }
  }

  var scrollLockY = 0;

  function render(data) {
    var html = "";
    if (data.items.length) {
      data.items.forEach(function (item) {
        html += buildProductCard(item);
      });
    } else {
      html =
        '<div style="grid-column:1/-1">' +
        '<div class="catalog-empty-state rounded-theme px-4 py-5 text-center">' +
        '<i class="bi bi-inbox d-block mb-3 text-primary" style="font-size: 2rem; opacity: 0.85;" aria-hidden="true"></i>' +
        '<p class="fw-semibold mb-2" style="font-family: var(--font-heading);">Ничего не нашлось</p>' +
        '<p class="text-muted small mb-4 mb-md-0" style="max-width: 22rem; margin-left: auto; margin-right: auto;">' +
        "Попробуйте другой запрос или сбросьте фильтры — полный каталог откроется без ограничений." +
        "</p>" +
        '<button type="button" class="btn btn-primary mt-md-2 js-catalog-show-all">Показать весь каталог</button>' +
        "</div></div>";
    }
    catalogEl.innerHTML = html;
    if (paginationWrap) {
      paginationWrap.innerHTML = buildPagination(data.page, data.pages);
    }
    var btn = catalogEl.querySelector(".js-catalog-show-all");
    if (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        if (searchInput) searchInput.value = "";
        applyCategoryFromPillValue("");
        loadCatalog(1);
      });
    }
    syncPillsToCategory(getCategory());
    requestAnimationFrame(function () {
      window.scrollTo(0, scrollLockY);
    });
  }

  function loadCatalog(page) {
    page = page || 1;
    scrollLockY = window.scrollY;
    var params = new URLSearchParams();
    params.set("page", page);
    if (getQuery()) params.set("query", getQuery());
    if (getCategory()) params.set("category", getCategory());
    fetch("/api/products?" + params.toString())
      .then(function (r) {
        return r.text().then(function (t) {
          try {
            return JSON.parse(t);
          } catch (e) {
            throw new Error("bad json");
          }
        });
      })
      .then(function (data) {
        render(data);
        updateUrl();
      })
      .catch(function () {
        scrollLockY = window.scrollY;
        catalogEl.innerHTML =
          '<div style="grid-column:1/-1">' +
          '<div class="alert alert-danger rounded-theme py-4 text-center mb-0">' +
          '<p class="fw-semibold mb-2">Не удалось обновить каталог</p>' +
          '<p class="small mb-3 mb-md-0 opacity-90">Проверьте соединение и обновите страницу.</p>' +
          '<a href="' +
          window.location.pathname +
          window.location.search +
          '" class="btn btn-light btn-sm mt-2">Повторить</a>' +
          "</div></div>";
        requestAnimationFrame(function () {
          window.scrollTo(0, scrollLockY);
        });
      });
  }

  searchForm.addEventListener("submit", function (e) {
    e.preventDefault();
    loadCatalog(1);
  });

  if (categorySelect) {
    categorySelect.addEventListener("change", function () {
      syncPillsToCategory(getCategory());
      loadCatalog(1);
    });
  }

  if (categoryPills) {
    categoryPills.addEventListener("click", function (e) {
      var a = e.target.closest("a.category-pill");
      if (!a || !categoryPills.contains(a)) return;
      e.preventDefault();
      var v = a.getAttribute("data-category");
      v = v === null || v === "" ? "" : String(v);
      applyCategoryFromPillValue(v);
      loadCatalog(1);
    });
  }

  if (resetLink) {
    resetLink.addEventListener("click", function (e) {
      e.preventDefault();
      if (searchInput) searchInput.value = "";
      applyCategoryFromPillValue("");
      loadCatalog(1);
    });
  }

  if (catalogEl) {
    catalogEl.addEventListener("click", function (e) {
      if (e.target.closest(".js-add-to-cart-form") || e.target.closest(".card-actions")) {
        return;
      }
      var card = e.target.closest(".js-product-card");
      if (!card || !catalogEl.contains(card)) return;
      var u = card.getAttribute("data-product-url");
      if (u) {
        window.location.href = u;
      }
    });
  }

  if (paginationWrap) {
    paginationWrap.addEventListener("click", function (e) {
      var a = e.target.closest(".js-catalog-page");
      if (a) {
        e.preventDefault();
        loadCatalog(parseInt(a.getAttribute("data-page"), 10));
      }
    });
  }
})();
