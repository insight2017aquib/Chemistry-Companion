/** Shared workbench helpers for dashboard + analysis pages */
document.querySelectorAll('.example-pick').forEach((btn) => {
  btn.addEventListener('click', () => {
    const ta = document.getElementById('input_text');
    if (!ta) return;
    ta.value = btn.dataset.smiles;
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
  const smi = document.getElementById('input_text')?.value.trim();
  const box = document.getElementById('structure-preview');
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

const ta = document.getElementById('input_text');
if (ta) {
  ta.addEventListener('input', typeof debounce === 'function' ? debounce(updateStructurePreview, 500) : updateStructurePreview);
}

const params = new URLSearchParams(window.location.search);
if (params.get('smiles') && ta) {
  ta.value = params.get('smiles');
  updateStructurePreview();
}
