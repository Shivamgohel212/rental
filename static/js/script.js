// ══════════════════════════════════════════
// DATA
// ══════════════════════════════════════════
const products = [
  { id:1, name:'Sabyasachi Bridal Lehenga', cat:'Wedding', price:3200, rating:4.9, reviews:128, icon:'👗', badge:'Bestseller', desc:'A breathtaking masterpiece in deep crimson and gold zari work. This Sabyasachi-inspired lehenga features hand-embroidered motifs, a heavily embellished blouse, and a gossamer dupatta that catches every light.', sizes:['XS','S','M','L','XL'] },
  { id:2, name:'Manish Malhotra Gown', cat:'Designer', price:2800, rating:4.8, reviews:96, icon:'✨', badge:'New', desc:'An ethereal floor-length gown with intricate mirror work and sequin embroidery. Perfect for gala dinners and reception events.', sizes:['S','M','L','XL'] },
  { id:3, name:'Anarkali Suit Set', cat:'Ethnic', price:1200, rating:4.7, reviews:210, icon:'🌸', desc:'A regal three-piece Anarkali in deep teal with golden border. Comes with churidar and dupatta.', sizes:['XS','S','M','L','XL','XXL'] },
  { id:4, name:'Sequin Party Dress', cat:'Party', price:1800, rating:4.6, reviews:74, icon:'💫', badge:'Hot', desc:'A show-stopping all-sequin mini dress in champagne gold. Perfect for cocktail parties, birthdays, and New Year celebrations.', sizes:['XS','S','M','L'] },
  { id:5, name:'Banarasi Silk Saree', cat:'Ethnic', price:900, rating:4.9, reviews:312, icon:'🎋', badge:'Classic', desc:'Woven in authentic Banarasi silk with traditional motifs in silver and gold. Paired with a matching blouse piece.', sizes:['Free Size'] },
  { id:6, name:'Indo-Western Sherwani Set', cat:'Designer', price:2200, rating:4.7, reviews:58, icon:'🕴', desc:'A tailored indo-western sherwani in ivory with subtle silver threadwork. Perfect for sangeet, cocktail functions, or receptions.', sizes:['S','M','L','XL','XXL'] },
  { id:7, name:'Georgette Palazzo Set', cat:'Party', price:850, rating:4.5, reviews:145, icon:'💃', desc:'A flowy georgette palazzo set in midnight blue with printed palazzo pants and a crop top blouse. Effortlessly glamorous.', sizes:['XS','S','M','L','XL'] },
  { id:8, name:'Peach Lehenga Choli', cat:'Wedding', price:1600, rating:4.8, reviews:189, icon:'🌹', desc:'A romantic peach lehenga with floral embroidery and a beautiful flared skirt. Perfect for wedding guests and mehendi ceremonies.', sizes:['S','M','L','XL'] },
];

const reviews = [
  { name:'Ananya S.', date:'Jan 2025', rating:5, text:'"Absolutely stunning lehenga — received so many compliments at my cousin\'s wedding. Arrived dry-cleaned and perfectly packed. Will rent again!"' },
  { name:'Meera R.', date:'Dec 2024', rating:5, text:'"The quality exceeded expectations. The gown fit beautifully and the pickup process was seamless. Vêtir has changed how I think about dressing up."' },
  { name:'Pooja K.', date:'Jan 2025', rating:4, text:'"Great experience overall. The outfit was exactly as pictured. Would love a bit more variety in plus sizes but the service was excellent."' },
  { name:'Kavya T.', date:'Feb 2025', rating:5, text:'"Used Vêtir for my best friend\'s bachelorette. All 6 of us rented and the entire process was so smooth. Highly recommend to everyone!"' },
];

let cart = JSON.parse(localStorage.getItem('vetir_cart') || '[]');
let currentProduct = null;
let currentDuration = 1;
let selectedSize = '';
let activeFilters = { search: '', sizes: [] };

// ══════════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════════
function navigate(page, productId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
  
  if (page === 'home') renderFeatured();
  if (page === 'shop') renderShop();
  if (page === 'detail' && productId) openDetail(productId);
  if (page === 'cart') renderCart();
  if (page === 'checkout') renderCheckout();
  updateCartCount();
}

function filterAndShop(cat) {
  navigate('shop');
  setTimeout(() => {
    document.getElementById('shopSearch').value = cat;
    applyFilters();
  }, 100);
}

// ══════════════════════════════════════════
// RENDER HELPERS
// ══════════════════════════════════════════
function starsHTML(rating) {
  const full = Math.floor(rating);
  return '★'.repeat(full) + (rating % 1 >= 0.5 ? '½' : '') + '☆'.repeat(5 - Math.ceil(rating));
}

function productCardHTML(p, extraClass = '') {
  return `
    <div class="product-card ${extraClass}" onclick="navigate('detail', ${p.id})">
      <div class="product-img-wrap">
        <div class="product-img-placeholder" style="background:linear-gradient(145deg,#f0ebe4,#e8e0d5); display:flex; align-items:center; justify-content:center; font-size:5rem;">${p.icon}</div>
        ${p.badge ? `<span class="product-badge">${p.badge}</span>` : ''}
        <button class="product-wishlist" onclick="event.stopPropagation(); wishlist(this)" title="Wishlist">♡</button>
      </div>
      <div class="product-info">
        <span class="product-cat">${p.cat}</span>
        <h4>${p.name}</h4>
        <div class="product-meta">
          <div class="product-price">₹${p.price.toLocaleString()} <span>/ day</span></div>
          <div class="product-rating"><span class="stars">${starsHTML(p.rating)}</span> ${p.rating}</div>
        </div>
        <button class="btn-primary" onclick="event.stopPropagation(); quickAddToCart(${p.id})">Rent Now</button>
      </div>
    </div>`;
}

function renderFeatured() {
  document.getElementById('featuredProducts').innerHTML = products.slice(0,4).map(p => productCardHTML(p)).join('');
}

function renderShop() {
  applyFilters();
}

function applyFilters() {
  const search = (document.getElementById('shopSearch')?.value || '').toLowerCase();
  const sortVal = document.getElementById('sortSelect')?.value || 'default';
  const min = parseFloat(document.getElementById('minPrice')?.value || 0);
  const max = parseFloat(document.getElementById('maxPrice')?.value || 99999);
  const activeSizes = activeFilters.sizes;

  let filtered = products.filter(p => {
    const matchSearch = !search || p.name.toLowerCase().includes(search) || p.cat.toLowerCase().includes(search) || p.desc.toLowerCase().includes(search);
    const matchPrice = p.price >= min && p.price <= max;
    const matchSize = activeSizes.length === 0 || p.sizes.some(s => activeSizes.includes(s));
    return matchSearch && matchPrice && matchSize;
  });

  if (sortVal === 'price-asc') filtered.sort((a,b) => a.price - b.price);
  if (sortVal === 'price-desc') filtered.sort((a,b) => b.price - a.price);
  if (sortVal === 'rating') filtered.sort((a,b) => b.rating - a.rating);

  const grid = document.getElementById('shopGrid');
  if (grid) {
    grid.innerHTML = filtered.length
      ? filtered.map(p => productCardHTML(p)).join('')
      : `<div style="grid-column:1/-1; text-align:center; padding:4rem; color:var(--muted)"><div style="font-size:3rem;margin-bottom:1rem">🔍</div><p>No outfits found. Try adjusting your filters.</p></div>`;
  }

  const cnt = document.getElementById('resultCount');
  if (cnt) cnt.textContent = `${filtered.length} outfits`;
}

function toggleSizeFilter(btn) {
  btn.classList.toggle('active');
  const size = btn.textContent;
  if (btn.classList.contains('active')) {
    activeFilters.sizes.push(size);
  } else {
    activeFilters.sizes = activeFilters.sizes.filter(s => s !== size);
  }
  applyFilters();
}

function clearFilters() {
  document.getElementById('shopSearch').value = '';
  document.getElementById('minPrice').value = 0;
  document.getElementById('maxPrice').value = 10000;
  document.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.filter-option input').forEach(i => i.checked = false);
  activeFilters.sizes = [];
  applyFilters();
}

// ══════════════════════════════════════════
// PRODUCT DETAIL
// ══════════════════════════════════════════
function openDetail(id) {
  currentProduct = products.find(p => p.id === id);
  if (!currentProduct) return;
  currentDuration = 1;
  selectedSize = '';

  document.getElementById('detailCat').textContent = currentProduct.cat;
  document.getElementById('detailName').textContent = currentProduct.name;
  document.getElementById('detailStars').textContent = starsHTML(currentProduct.rating);
  document.getElementById('detailRating').textContent = currentProduct.rating;
  document.getElementById('detailReviewCount').textContent = `${currentProduct.reviews} reviews`;
  document.getElementById('detailPrice').textContent = `₹${currentProduct.price.toLocaleString()}`;
  document.getElementById('detailDesc').textContent = currentProduct.desc;
  document.getElementById('mainProductImg').innerHTML = `<span style="font-size:10rem">${currentProduct.icon}</span>`;

  // Sizes
  document.getElementById('sizeSelector').innerHTML = currentProduct.sizes
    .map(s => `<button class="size-option" onclick="selectDetailSize(this,'${s}')">${s}</button>`)
    .join('');

  // Thumbs
  const thumbColors = ['#f0ebe4','#e8e0d5','#e0d8cf','#d8d0c7'];
  document.getElementById('productThumbs').innerHTML = thumbColors
    .map((c,i) => `<div class="thumb ${i===0?'active':''}" onclick="setThumb(this)" style="background:${c}">${currentProduct.icon}</div>`)
    .join('');

  updatePriceCalc();

  // Reviews
  document.getElementById('reviewGrid').innerHTML = reviews.map(r => `
    <div class="review-card">
      <div class="reviewer">
        <div class="reviewer-avatar">${r.name[0]}</div>
        <div class="reviewer-info">
          <h5>${r.name}</h5>
          <span>${r.date} · ${'★'.repeat(r.rating)}</span>
        </div>
      </div>
      <p class="review-text">${r.text}</p>
    </div>`).join('');
}

function selectDetailSize(btn, size) {
  document.querySelectorAll('.size-option').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  selectedSize = size;
}

function setThumb(el) {
  document.querySelectorAll('.thumb').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
}

function changeDuration(delta) {
  currentDuration = Math.max(1, Math.min(7, currentDuration + delta));
  document.getElementById('durVal').textContent = currentDuration;
  updatePriceCalc();
}

function updatePriceCalc() {
  if (!currentProduct) return;
  const base = currentProduct.price;
  const deposit = Math.round(base * 1.5);
  const subtotal = base * currentDuration;
  const total = subtotal + deposit;
  document.getElementById('basePrice').textContent = `₹${base.toLocaleString()}`;
  document.getElementById('durationLabel').textContent = `${currentDuration} day${currentDuration > 1 ? 's' : ''}`;
  document.getElementById('depositLabel').textContent = `₹${deposit.toLocaleString()}`;
  document.getElementById('totalPrice').textContent = `₹${total.toLocaleString()}`;
}

function addToCartFromDetail(wishlist = false) {
  if (!currentProduct) return;
  if (!selectedSize && currentProduct.sizes.length > 1) {
    showToast('Please select a size first', '⚠️');
    return;
  }
  if (wishlist) { showToast('Added to wishlist!', '♡'); return; }
  addToCart(currentProduct, selectedSize || currentProduct.sizes[0], currentDuration);
}

function quickAddToCart(id) {
  const p = products.find(pr => pr.id === id);
  if (!p) return;
  addToCart(p, p.sizes[0] || 'M', 1);
}

// ══════════════════════════════════════════
// CART
// ══════════════════════════════════════════
function addToCart(product, size, duration) {
  const existing = cart.find(i => i.id === product.id && i.size === size);
  if (existing) {
    existing.duration = duration;
  } else {
    cart.push({ ...product, size, duration });
  }
  saveCart();
  updateCartCount();
  showToast(`${product.name} added to cart!`);
}

function saveCart() { localStorage.setItem('vetir_cart', JSON.stringify(cart)); }

function updateCartCount() {
  document.getElementById('cartCount').textContent = cart.length;
}

function removeFromCart(id, size) {
  cart = cart.filter(i => !(i.id === id && i.size === size));
  saveCart();
  updateCartCount();
  renderCart();
}

function renderCart() {
  const container = document.getElementById('cartItems');
  if (cart.length === 0) {
    container.innerHTML = `
      <div class="empty-cart">
        <span class="big-icon">🛍️</span>
        <h3>Your cart is empty</h3>
        <p>Discover thousands of beautiful outfits waiting to be worn.</p>
        <button class="btn-primary" onclick="navigate('shop')">Browse Outfits</button>
      </div>`;
    document.getElementById('orderSummary').style.display = 'none';
    return;
  }
  document.getElementById('orderSummary').style.display = 'block';

  container.innerHTML = cart.map(item => {
    const subtotal = item.price * item.duration;
    return `
      <div class="cart-item">
        <div class="cart-item-img">${item.icon}</div>
        <div>
          <div class="product-cat">${item.cat}</div>
          <div class="cart-item-name">${item.name}</div>
          <div class="cart-item-meta">Size: ${item.size}</div>
          <div class="cart-item-dur">
            <button style="border:1px solid var(--border);background:none;width:26px;height:26px;cursor:pointer;font-size:1rem;" onclick="changeCartDuration(${item.id},'${item.size}',-1)">−</button>
            <span style="font-family:'Cormorant Garamond',serif;font-size:1.1rem;">${item.duration} day${item.duration > 1?'s':''}</span>
            <button style="border:1px solid var(--border);background:none;width:26px;height:26px;cursor:pointer;font-size:1rem;" onclick="changeCartDuration(${item.id},'${item.size}',1)">+</button>
          </div>
        </div>
        <div>
          <div class="cart-item-price">₹${subtotal.toLocaleString()}</div>
          <div style="font-size:0.72rem;color:var(--muted);text-align:right;">₹${item.price.toLocaleString()}/day</div>
          <button class="cart-item-remove" onclick="removeFromCart(${item.id},'${item.size}')">Remove</button>
        </div>
      </div>`;
  }).join('');

  const subtotal = cart.reduce((s,i) => s + i.price * i.duration, 0);
  const deposit = cart.reduce((s,i) => s + Math.round(i.price * 1.5), 0);
  const shipping = 0;
  const total = subtotal + deposit + shipping;

  document.getElementById('summaryDetails').innerHTML = `
    <div class="summary-row"><span>Rental subtotal</span><span>₹${subtotal.toLocaleString()}</span></div>
    <div class="summary-row"><span>Security deposits</span><span>₹${deposit.toLocaleString()}</span></div>
    <div class="summary-row"><span>Delivery</span><span style="color:var(--success)">Free</span></div>
    <div class="summary-row total"><span>Total</span><span>₹${total.toLocaleString()}</span></div>
    <div style="font-size:0.72rem;color:var(--muted);margin-top:0.5rem;">*Deposits are fully refunded upon return</div>`;
}

function changeCartDuration(id, size, delta) {
  const item = cart.find(i => i.id === id && i.size === size);
  if (item) {
    item.duration = Math.max(1, Math.min(7, item.duration + delta));
    saveCart();
    renderCart();
  }
}

function renderCheckout() {
  const subtotal = cart.reduce((s,i) => s + i.price * i.duration, 0);
  const deposit = cart.reduce((s,i) => s + Math.round(i.price * 1.5), 0);
  const total = subtotal + deposit;

  const container = document.getElementById('checkoutSummary');
  if (!container) return;

  container.innerHTML = cart.map(i => `
    <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:var(--muted); margin-bottom:0.6rem; align-items:center; gap:1rem;">
      <span>${i.icon} ${i.name} <span style="color:var(--gold)">(${i.duration}d)</span></span>
      <span style="white-space:nowrap;">₹${(i.price * i.duration).toLocaleString()}</span>
    </div>`).join('') + `
    <div style="border-top:1px solid var(--border); margin-top:1rem; padding-top:1rem;">
      <div class="summary-row"><span>Subtotal</span><span>₹${subtotal.toLocaleString()}</span></div>
      <div class="summary-row"><span>Deposits</span><span>₹${deposit.toLocaleString()}</span></div>
      <div class="summary-row total"><span>Total</span><span>₹${total.toLocaleString()}</span></div>
    </div>`;
}

// ══════════════════════════════════════════
// CHECKOUT
// ══════════════════════════════════════════
function selectPayment(el, type) {
  document.querySelectorAll('.payment-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');
  el.querySelector('input').checked = true;
  document.getElementById('cardFields').style.display = type === 'card' ? 'grid' : 'none';
}

function formatCard(input) {
  let val = input.value.replace(/\D/g, '').substring(0, 16);
  val = val.replace(/(.{4})/g, '$1 ').trim();
  input.value = val;
}

function confirmBooking() {
  const bookingId = Math.floor(100000 + Math.random() * 900000);
  document.getElementById('bookingId').textContent = bookingId;
  document.getElementById('successModal').classList.add('show');
}

function closeModal() {
  document.getElementById('successModal').classList.remove('show');
  cart = [];
  saveCart();
  updateCartCount();
  navigate('home');
}

// ══════════════════════════════════════════
// AUTH
// ══════════════════════════════════════════
function switchAuthTab(tab) {
  document.querySelectorAll('.auth-tab').forEach((t,i) => {
    t.classList.toggle('active', (i === 0 && tab === 'login') || (i === 1 && tab === 'register'));
  });
  document.getElementById('loginForm').classList.toggle('active', tab === 'login');
  document.getElementById('registerForm').classList.toggle('active', tab === 'register');
}

// ══════════════════════════════════════════
// MISC
// ══════════════════════════════════════════
function wishlist(btn) {
  btn.classList.toggle('loved');
  btn.textContent = btn.classList.contains('loved') ? '♥' : '♡';
  showToast(btn.classList.contains('loved') ? 'Added to wishlist!' : 'Removed from wishlist', '♡');
}

let toastTimer;
function showToast(msg, icon = '✓') {
  clearTimeout(toastTimer);
  const toast = document.getElementById('toast');
  document.getElementById('toast-msg').textContent = msg;
  toast.querySelector('.toast-icon').textContent = icon;
  toast.classList.add('show');
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

function openMobileNav() {
  document.getElementById('mobileNav').classList.add('open');
  document.getElementById('mobileOverlay').classList.add('show');
}

function closeMobileNav() {
  document.getElementById('mobileNav').classList.remove('open');
  document.getElementById('mobileOverlay').classList.remove('show');
}

// ══════════════════════════════════════════
// INIT
// ══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  renderFeatured();
  updateCartCount();
});