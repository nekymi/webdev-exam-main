/**
 * Добавление в корзину без перезагрузки (AJAX) + обновление badge + toast
 */
(function () {
  var csrfToken = document.querySelector('meta[name="csrf-token"]') && document.querySelector('meta[name="csrf-token"]').getAttribute('content');
  var cartBadge = document.querySelector('.js-cart-badge');
  var toastContainer = document.getElementById('toast-container');

  function showToast(message, type) {
    type = type || 'success';
    if (!toastContainer) return;
    var toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-bg-' + type + ' border-0';
    toastEl.setAttribute('role', 'alert');
    var closeClass =
      type === 'success' || type === 'danger' ? 'btn-close btn-close-white' : 'btn-close';
    toastEl.innerHTML =
      '<div class="d-flex"><div class="toast-body">' +
      escapeHtml(message) +
      '</div><button type="button" class="' +
      closeClass +
      ' me-2 m-auto" data-bs-dismiss="toast" aria-label="Закрыть"></button></div>';
    toastContainer.appendChild(toastEl);
    var toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', function () { toastEl.remove(); });
  }

  function escapeHtml(s) {
    var div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function updateBadge(count) {
    if (!cartBadge) return;
    cartBadge.textContent = count;
    if (count > 0) {
      cartBadge.classList.remove('d-none');
    } else {
      cartBadge.classList.add('d-none');
    }
  }

  function formatMoney(total) {
    if (total == null || isNaN(total)) return '0\u00a0₽';
    var n = Number(total);
    var hasFraction = Math.abs(n % 1) > 0.001;
    return (
      new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: hasFraction ? 2 : 0,
        maximumFractionDigits: 2
      }).format(n) + '\u00a0₽'
    );
  }

  function updateCartTotals(count, total) {
    document.querySelectorAll('.js-cart-total').forEach(function (el) {
      el.textContent = formatMoney(total);
    });
    document.dispatchEvent(
      new CustomEvent('shop:cart-updated', { detail: { count: count, total: total } })
    );
  }

  function syncRowStepper(row, qty, maxQty) {
    var dec = row.querySelector('.js-cart-qty-dec');
    var inc = row.querySelector('.js-cart-qty-inc');
    if (dec) dec.disabled = qty <= 1;
    if (inc) inc.disabled = maxQty > 0 && qty >= maxQty;
  }

  function parseResponseJson(r) {
    return r.text().then(function (t) {
      var d = {};
      if (t) {
        try {
          d = JSON.parse(t);
        } catch (e) {
          d = { ok: false, message: 'Не удалось разобрать ответ сервера' };
        }
      }
      return { statusOk: r.ok, d: d };
    });
  }

  function applyCartPageState(state) {
    if (!state || !state.ok) return;
    updateBadge(state.cart_count);
    updateCartTotals(state.cart_count, state.cart_total);
    var nLine = document.querySelector('.js-cart-line-count');
    if (nLine) nLine.textContent = String(state.line_count);
    var nPie = document.querySelector('.js-cart-pieces');
    if (nPie) nPie.textContent = String(state.cart_count);
    var tbody = document.getElementById('js-cart-tbody');
    if (!tbody) return;
    var byId = {};
    (state.lines || []).forEach(function (L) {
      byId[L.product_id] = L;
    });
    tbody.querySelectorAll('tr[data-js-cart-row]').forEach(function (row) {
      var pid = parseInt(row.getAttribute('data-product-id'), 10);
      var L = byId[pid];
      if (!L) {
        row.remove();
        return;
      }
      var val = row.querySelector('.js-cart-qty-value');
      if (val) val.textContent = String(L.qty);
      var lt = row.querySelector('.js-line-total');
      if (lt) lt.textContent = formatMoney(L.line_total);
      row.setAttribute('data-max-qty', String(L.max_qty));
      syncRowStepper(row, L.qty, L.max_qty);
    });
    if (!state.lines || state.lines.length === 0) {
      window.location.reload();
    }
  }

  function showWarnings(warnings) {
    (warnings || []).forEach(function (w) {
      if (w) showToast(w, 'warning');
    });
  }

  function initCartPage() {
    var root = document.getElementById('js-cart-page');
    if (!root) return;
    var api = root.getAttribute('data-cart-api-line') || '/cart/api/line';
    var table = document.getElementById('js-cart-tbody');
    if (!table) return;
    var busy = false;
    function headersJson() {
      var h = { 'Content-Type': 'application/json' };
      if (csrfToken) h['X-CSRFToken'] = csrfToken;
      return h;
    }
    function postLine(productId, qty) {
      if (busy) return;
      busy = true;
      table.setAttribute('aria-busy', 'true');
      fetch(api, {
        method: 'POST',
        headers: headersJson(),
        body: JSON.stringify({ product_id: productId, qty: qty }),
      })
        .then(parseResponseJson)
        .then(function (res) {
          if (res.statusOk && res.d.ok) {
            applyCartPageState(res.d);
            showWarnings(res.d.warnings);
          } else {
            showToast((res.d && res.d.message) || 'Не удалось обновить корзину', 'danger');
          }
        })
        .catch(function () {
          showToast('Ошибка сети. Попробуйте ещё раз.', 'danger');
        })
        .finally(function () {
          busy = false;
          table.removeAttribute('aria-busy');
        });
    }
    root.addEventListener('click', function (e) {
      var target = e.target;
      if (!target) return;
      var rm = target.closest && target.closest('.js-cart-remove');
      if (rm) {
        e.preventDefault();
        e.stopPropagation();
        var removePid = rm.getAttribute('data-product-id');
        if (removePid) postLine(parseInt(removePid, 10), 0);
        return;
      }
      var t = target && target.closest && target.closest('.js-cart-qty-dec, .js-cart-qty-inc');
      var tr = target.closest && target.closest('tr[data-js-cart-row]');
      if (!t || !tr) return;
      e.preventDefault();
      e.stopPropagation();
      var pid = parseInt(tr.getAttribute('data-product-id'), 10);
      var maxQ = parseInt(tr.getAttribute('data-max-qty'), 10) || 999;
      var vEl = tr.querySelector('.js-cart-qty-value');
      var cur = vEl ? parseInt(vEl.textContent, 10) : 1;
      if (isNaN(cur) || cur < 1) cur = 1;
      if (t.classList.contains('js-cart-qty-dec')) {
        postLine(pid, cur <= 1 ? 0 : cur - 1);
        return;
      }
      if (t.classList.contains('js-cart-qty-inc') && cur < maxQ) {
        postLine(pid, cur + 1);
      }
    });
  }

  function initProductQtyStepper() {
    document.querySelectorAll('.js-qty-stepper').forEach(function (step) {
      var min = Math.max(1, parseInt(step.getAttribute('data-min'), 10) || 1);
      var max = parseInt(step.getAttribute('data-max'), 10);
      if (isNaN(max) || max < 1) max = 999;
      var h = step.querySelector('.js-qty-input');
      var v = step.querySelector('.js-qty-value');
      if (!h || !v) return;
      var bDec = step.querySelector('.js-qty-dec');
      var bInc = step.querySelector('.js-qty-inc');
      function read() {
        var q = parseInt(h.value, 10);
        if (isNaN(q) || q < min) q = min;
        if (q > max) q = max;
        h.value = String(q);
        v.textContent = String(q);
        if (bDec) bDec.disabled = q <= min;
        if (bInc) bInc.disabled = q >= max;
      }
      if (bDec) {
        bDec.addEventListener('click', function (e) {
          e.preventDefault();
          var q = parseInt(h.value, 10) || min;
          if (q > min) h.value = String(q - 1);
          read();
        });
      }
      if (bInc) {
        bInc.addEventListener('click', function (e) {
          e.preventDefault();
          var q = parseInt(h.value, 10) || min;
          if (q < max) h.value = String(q + 1);
          read();
        });
      }
      read();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initCartPage();
      initProductQtyStepper();
    });
  } else {
    initCartPage();
    initProductQtyStepper();
  }

  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || !form.classList.contains('js-add-to-cart-form')) return;
    e.preventDefault();

    var productId = form.getAttribute('data-product-id') || form.querySelector('[name="product_id"]') && form.querySelector('[name="product_id"]').value;
    var qtyInput = form.querySelector('.js-qty-input') || form.querySelector('[name="quantity"]');
    var qty = qtyInput ? parseInt(qtyInput.value, 10) : 1;
    if (isNaN(qty) || qty < 1) qty = 1;

    if (!productId) return;
    var body = JSON.stringify({ product_id: parseInt(productId, 10), qty: qty });
    var headers = { 'Content-Type': 'application/json' };
    if (csrfToken) headers['X-CSRFToken'] = csrfToken;

    fetch(form.action.replace(/\/add\/\d+/, '/api/add'), {
      method: 'POST',
      headers: headers,
      body: body,
    })
      .then(parseResponseJson)
      .then(function (result) {
        if (result.statusOk && result.d.ok) {
          updateBadge(result.d.cart_count);
          if (result.d.cart_total != null) {
            updateCartTotals(result.d.cart_count, result.d.cart_total);
          }
          showToast(result.d.message || 'Добавлено в корзину', 'success');
        } else {
          showToast((result.d && result.d.message) || 'Ошибка', 'danger');
        }
      })
      .catch(function () {
        showToast('Ошибка сети. Попробуйте ещё раз.', 'danger');
      });
  });
})();
