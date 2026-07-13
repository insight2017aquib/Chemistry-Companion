/** Shared workbench helpers for dashboard + analysis pages (and any molecule input form).
 * Made defensive to support both the shared component IDs (#input_text + #structure-preview)
 * and dashboard-style IDs (#molecule-input) without duplicating logic.
 * Reuses the single /api/structure.png endpoint + core/visualization_utils.
 */
function _findInputEl() {
  return document.getElementById('input_text') || document.getElementById('molecule-input');
}

function _findPreviewBox() {
  return document.getElementById('structure-preview');
}

document.querySelectorAll('.example-pick, .example-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const ta = _findInputEl();
    if (!ta) return;
    ta.value = btn.dataset.smiles || btn.getAttribute('data-smiles') || '';
    const sm = document.querySelector('input[name="input_method"][value="smiles"]');
    if (sm) sm.checked = true;
    if (btn.dataset.name) {
      const n = document.getElementById('name');
      if (n) n.value = btn.dataset.name;
    }
    if (typeof updateStructurePreview === 'function') updateStructurePreview();
  });
});

function updateStructurePreview() {
  const ta = _findInputEl();
  const smi = ta?.value.trim();
  const box = _findPreviewBox();
  if (!box) return;
  if (!smi) {
    box.innerHTML = '<span class="text-[var(--cc-text-faint)]">Enter SMILES for preview</span>';
    return;
  }
  box.innerHTML =
    '<img src="/api/structure.png?smiles=' +
    encodeURIComponent(smi) +
    '&width=280&height=200" class="max-h-48 mx-auto rounded-lg" alt="preview">';
}

const ta = _findInputEl();
if (ta) {
  ta.addEventListener('input', typeof debounce === 'function' ? debounce(updateStructurePreview, 500) : updateStructurePreview);
}

const params = new URLSearchParams(window.location.search);
if (params.get('smiles') && ta) {
  ta.value = params.get('smiles');
  updateStructurePreview();
}
