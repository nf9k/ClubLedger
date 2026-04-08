/**
 * attachZipLookup — auto-fill city/state from ZIP via /zip-lookup/<zip>
 *
 * zipId   — id of the zip input
 * cityId  — id of the city input
 * stateId — id of the state input
 * hintId  — id of a <div> below zip for badge suggestions
 *
 * Behaviour:
 *  - If city is empty: auto-fills city + state silently.
 *  - If city is already filled: renders clickable badge suggestions without
 *    overwriting; clicking a badge fills city + state.
 *  - Multiple results shown as alternates.
 *  - No-op if ZIP returns no results.
 */
function attachZipLookup(zipId, cityId, stateId, hintId) {
  const zipEl   = document.getElementById(zipId);
  const cityEl  = document.getElementById(cityId);
  const stateEl = document.getElementById(stateId);
  const hintEl  = document.getElementById(hintId);
  if (!zipEl || !cityEl || !stateEl || !hintEl) return;

  zipEl.addEventListener('blur', function () {
    const zip = zipEl.value.trim();
    if (zip.length < 5) { hintEl.textContent = ''; return; }

    fetch('/zip-lookup/' + encodeURIComponent(zip))
      .then(r => r.json())
      .then(results => {
        hintEl.textContent = '';
        if (!results.length) return;

        if (!cityEl.value.trim()) {
          cityEl.value  = results[0].city;
          stateEl.value = results[0].state;
          if (results.length > 1) {
            hintEl.textContent = '';
            const prefix = document.createTextNode('Alternates: ');
            hintEl.appendChild(prefix);
            results.slice(1).forEach(r => hintEl.appendChild(makeBadge(r, cityEl, stateEl, hintEl)));
          }
        } else {
          const prefix = document.createTextNode('ZIP suggestions: ');
          hintEl.appendChild(prefix);
          results.forEach(r => hintEl.appendChild(makeBadge(r, cityEl, stateEl, hintEl)));
        }
      })
      .catch(() => {});
  });

  function makeBadge(r, cityEl, stateEl, hintEl) {
    const a = document.createElement('a');
    a.href = '#';
    a.className = 'badge bg-secondary text-decoration-none me-1';
    a.textContent = r.city + ', ' + r.state;
    a.addEventListener('click', function (e) {
      e.preventDefault();
      cityEl.value = r.city;
      stateEl.value = r.state;
      hintEl.textContent = '';
    });
    return a;
  }
}
