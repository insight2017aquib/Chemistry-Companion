const fs = require('fs');

(async () => {
    const fetch = (await import('node-fetch')).default;
    const res = await fetch('https://cdn.jsdelivr.net/npm/molstar@5.4.2/build/viewer/molstar.js');
    const text = await res.text();
    
    const idx = text.indexOf('loadMvsData');
    if (idx !== -1) {
        console.log("loadMvsData snippet:", text.slice(Math.max(0, idx - 100), idx + 200));
    }
    
    // Also search for "replaceExisting"
    const idx2 = text.indexOf('replaceExisting');
    if (idx2 !== -1) {
        console.log("replaceExisting snippet:", text.slice(Math.max(0, idx2 - 100), idx2 + 200));
    }
    
    // Search for Box
    const boxIdx = text.indexOf('kind:"box"');
    if (boxIdx !== -1) {
        console.log("Box MVS snippet:", text.slice(Math.max(0, boxIdx - 100), boxIdx + 200));
    }
})();
