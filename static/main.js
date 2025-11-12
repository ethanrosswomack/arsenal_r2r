// Matrix rain effect
(function(){
  const c = document.getElementById('matrix');
  if (!c) return;
  const ctx = c.getContext('2d');
  function size(){ c.width = window.innerWidth; c.height = window.innerHeight; }
  size(); window.addEventListener('resize', size);
  const chars = 'アァカサタナハマヤャラワガザダバパイィキシチニヒミリヰギジヂビピウゥクスツヌフムユュルグズヅブプエェケセテネヘメレヱゲゼデベペオォコソトノホモヨョロゴゾドボポ0123456789';
  const fontSize = 14;
  let columns = Math.floor(c.width / fontSize);
  let drops = Array(columns).fill(1);
  function draw() {
    ctx.fillStyle = 'rgba(2,11,6,0.08)';
    ctx.fillRect(0,0,c.width,c.height);
    ctx.fillStyle = '#0f0';
    ctx.font = fontSize + 'px monospace';
    drops.forEach((y,i)=>{
      const text = chars[Math.floor(Math.random()*chars.length)];
      const x = i * fontSize;
      ctx.fillText(text, x, y * fontSize);
      if (y * fontSize > c.height && Math.random() > 0.975) drops[i] = 0;
      drops[i] = y + 1;
    });
  }
  setInterval(draw, 35);
})();

// Catalog Renderer
(function() {
  const listEl = document.getElementById('list');
  const q = document.getElementById('q');
  const countEl = document.getElementById('count');

  if (!listEl) return;

  let ALBUMS = [];

  function val(x) { return (x ?? '').toString().trim(); }

  function render() {
    const term = val(q.value).toLowerCase();
    
    let visibleItemCount = 0;
    listEl.innerHTML = ''; // Clear previous results

    ALBUMS.forEach(album => {
      const albumTitle = album.items[0]?.album || 'Untitled Album';

      const matchingItems = album.items.filter(item => {
        const hay = (item.title + ' ' + item.sku + ' ' + item.album).toLowerCase();
        return !term || hay.includes(term);
      });

      if (matchingItems.length === 0 && term) {
        return; // Don't show this album if the search term doesn't match anything in it
      }
      
      visibleItemCount += matchingItems.length;

      const albumSection = document.createElement('section');
      albumSection.className = 'album-group';
      
      let itemsHtml = matchingItems.map(item => `
        <li>
          <a href="/content/${item.key}">
            <span class="item-title">${item.title}</span>
            <span class="item-type">${item.type}</span>
          </a>
        </li>
      `).join('');

      albumSection.innerHTML = `
        <div class="album-header">
          ${album.image_path ? `<img src="${album.image_path}" alt="Cover for ${albumTitle}" class="album-cover">` : ''}
          <h2 class="album-title">${albumTitle}</h2>
        </div>
        <ul class="album-item-list">
          ${itemsHtml}
        </ul>
      `;
      listEl.appendChild(albumSection);
    });

    countEl.textContent = `${visibleItemCount} item(s)`;
  }

  q.addEventListener('input', render);

  async function loadCatalog() {
    try {
      const res = await fetch('/api/albums');
      if (!res.ok) {
        throw new Error(`Failed to load catalog: ${res.status}`);
      }
      ALBUMS = await res.json();
      render();
    } catch (err) {
      listEl.innerHTML = `<p style="color:#f88">${err.message}</p>`;
    }
  }

  loadCatalog();
})();
