// ══════════════════════════════════════════
// PRORENT UTILS & UI LOGIC
// ══════════════════════════════════════════

// TOAST SYSTEM
let toastTimer;
function showToast(msg, icon = '✓') {
  clearTimeout(toastTimer);
  const toast = document.getElementById('toast');
  if (!toast) return;
  
  const toastMsg = document.getElementById('toast-msg');
  const toastIcon = toast.querySelector('.toast-icon');
  
  if (toastMsg) toastMsg.textContent = msg;
  if (toastIcon) toastIcon.textContent = icon;
  
  toast.classList.add('show');
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

// MOBILE NAVIGATION
function openMobileNav() {
  const nav = document.getElementById('mobileNav');
  const overlay = document.getElementById('mobileOverlay');
  if (nav) nav.classList.add('open');
  if (overlay) overlay.classList.add('show');
}

function closeMobileNav() {
  const nav = document.getElementById('mobileNav');
  const overlay = document.getElementById('mobileOverlay');
  if (nav) nav.classList.remove('open');
  if (overlay) overlay.classList.remove('show');
}

// WISHLIST TOGGLE
function wishlist(btn) {
  btn.classList.toggle('loved');
  if (btn.classList.contains('loved')) {
    btn.textContent = '♥';
    showToast('Added to wishlist!', '♡');
  } else {
    btn.textContent = '♡';
    showToast('Removed from wishlist', '♡');
  }
}

// CART COUNTER (Placeholder for future cart system)
function updateCartCount(count = 0) {
  const cartCountEl = document.getElementById('cartCount');
  if (cartCountEl) cartCountEl.textContent = count;
}

// INITIALIZATION
document.addEventListener('DOMContentLoaded', () => {
  // Update cart count if needed
  updateCartCount(0);
  
  // Initialize any other UI components
});