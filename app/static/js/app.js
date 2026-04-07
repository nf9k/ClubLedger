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
    if (zip.length < 5) { hintEl.innerHTML = ''; return; }

    fetch('/zip-lookup/' + encodeURIComponent(zip))
      .then(r => r.json())
      .then(results => {
        hintEl.innerHTML = '';
        if (!results.length) return;

        if (!cityEl.value.trim()) {
          // Auto-fill with first result
          cityEl.value  = results[0].city;
          stateEl.value = results[0].state;
          // Show alternates (if any) as badges
          if (results.length > 1) {
            hintEl.innerHTML = 'Alternates: ' + results.slice(1).map(r => badge(r)).join(' ');
          }
        } else {
          // City already filled — show all as clickable suggestions
          hintEl.innerHTML = 'ZIP suggestions: ' + results.map(r => badge(r)).join(' ');
        }
      })
      .catch(() => {});
  });

  function badge(r) {
    const label = r.city + ', ' + r.state;
    return `<a href="#" class="badge bg-secondary text-decoration-none me-1"
               onclick="event.preventDefault();
                        document.getElementById('${cityId}').value='${r.city.replace(/'/g,"\\'")}';
                        document.getElementById('${stateId}').value='${r.state}';
                        document.getElementById('${hintId}').innerHTML='';"
            >${label}</a>`;
  }
}
