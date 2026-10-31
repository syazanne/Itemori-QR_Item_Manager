// Enhance the existing table without replacing Streamlit's record actions.
(() => {
  const host = window.parent, doc = host.document;
  host.itemoriDisposeTable?.();
  const storageKey = 'itemori.column-widths.v1', minWidth = 90, maxWidth = 800;
  let saved = host.itemoriColumnWidths || {};
  try { saved = JSON.parse(host.localStorage.getItem(storageKey) || '{}') || {}; } catch (_) {}
  if (typeof saved !== 'object' || Array.isArray(saved)) saved = {};
  let table, observer, frame, disposed = false;
  const clamp = (n, minimum = minWidth) => Math.min(maxWidth, Math.max(minimum, Math.round(n)));
  const save = (cols, widths) => {
    cols.forEach((col, i) => { saved[col.dataset.columnId] = widths[i]; });
    host.itemoriColumnWidths = saved;
    try { host.localStorage.setItem(storageKey, JSON.stringify(saved)); } catch (_) {}
  };
  const alignRows = () => {
    if (!table?.isConnected) return;
    const rows = [table.tHead.rows[0], ...table.tBodies[0].rows];
    rows.forEach((row, i) => {
      const key = i ? 'delete_slot_' + row.dataset.recordId : 'manage_add_slot';
      const slot = doc.querySelector('.st-key-' + CSS.escape(key));
      if (slot) {
        const height = row.getBoundingClientRect().height + 'px';
        slot.style.height = height;
        slot.style.minHeight = height;
        const wrapper = slot.closest('[data-testid="stLayoutWrapper"]');
        if (wrapper) {
          wrapper.style.height = height;
          wrapper.style.minHeight = height;
          wrapper.style.flex = '0 0 ' + height;
        }
      }
    });
  };
  const attach = () => {
    frame = null;
    if (disposed) return;
    const next = doc.querySelector('table.manage-records');
    if (!next || next === table) { alignRows(); return; }
    observer?.disconnect();
    table = next;
    const cols = [...table.querySelectorAll('col')];
    const headings = [...table.tHead.rows[0].cells];
    if (!cols.length) return;
    const minimum = i => cols[i].dataset.columnId === 'row_number' ? 48 : minWidth;
    let widths = cols.map((col, i) => Number.isFinite(saved[col.dataset.columnId])
      ? clamp(saved[col.dataset.columnId], minimum(i))
      : col.dataset.columnId === 'row_number' ? 56
      : Math.max(120, Math.floor((table.parentElement.clientWidth - 56) / (cols.length - 1))));
    const apply = () => {
      cols.forEach((col, i) => { col.style.width = widths[i] + 'px'; });
      table.style.width = widths.reduce((a, b) => a + b, 0) + 'px';
      headings.forEach((heading, i) => heading.querySelector('[role="separator"]')?.setAttribute('aria-valuenow', widths[i]));
      alignRows();
    };
    headings.forEach((heading, i) => {
      const handle = doc.createElement('span');
      handle.className = 'manage-column-resizer';
      handle.tabIndex = 0;
      handle.setAttribute('role', 'separator');
      handle.setAttribute('aria-orientation', 'vertical');
      handle.setAttribute('aria-label', 'Resize ' + heading.textContent + ' column');
      handle.setAttribute('aria-valuemin', minimum(i));
      handle.setAttribute('aria-valuemax', maxWidth);
      let drag = null;
      handle.addEventListener('pointerdown', event => {
        if (event.button !== 0) return;
        event.preventDefault();
        handle.focus();
        drag = {x: event.clientX, width: widths[i]};
        handle.setPointerCapture(event.pointerId);
      });
      handle.addEventListener('pointermove', event => {
        if (!drag) return;
        widths[i] = clamp(drag.width + event.clientX - drag.x, minimum(i));
        apply();
      });
      const finish = () => { if (drag) { drag = null; save(cols, widths); } };
      handle.addEventListener('pointerup', finish);
      handle.addEventListener('pointercancel', finish);
      handle.addEventListener('lostpointercapture', finish);
      handle.addEventListener('keydown', event => {
        if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
        event.preventDefault();
        widths[i] = clamp(widths[i] + (event.key === 'ArrowRight' ? 10 : -10), minimum(i));
        apply(); save(cols, widths);
      });
      heading.appendChild(handle);
    });
    apply();
    observer = new ResizeObserver(alignRows);
    observer.observe(table);
    for (const row of table.rows) observer.observe(row);
  };
  const changes = new MutationObserver(() => {
    if (!frame) frame = requestAnimationFrame(attach);
  });
  changes.observe(doc.body, {childList: true, subtree: true});
  const dispose = () => {
    disposed = true; changes.disconnect(); observer?.disconnect();
    if (frame) cancelAnimationFrame(frame);
    table?.querySelectorAll('.manage-column-resizer').forEach(handle => handle.remove());
  };
  host.itemoriDisposeTable = dispose;
  window.addEventListener('pagehide', dispose, {once: true});
  attach();
})();
