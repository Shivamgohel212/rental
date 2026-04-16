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

// CART COUNTER
function updateCartCount(count) {
  const cartCountEl = document.getElementById('cartCount');
  if (cartCountEl) {
    cartCountEl.textContent = count;
    // Add a small scale animation for feedback
    cartCountEl.style.transform = 'scale(1.3)';
    setTimeout(() => cartCountEl.style.transform = 'scale(1)', 200);
  }
}

// AJAX ADD TO CART
function initAddToCart() {
  const form = document.getElementById('addToCartForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerText;
    
    submitBtn.disabled = true;
    submitBtn.innerText = 'adding...';

    const formData = new FormData(form);
    
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': formData.get('csrfmiddlewaretoken')
        },
        body: formData
      });

      const data = await response.json();
      if (data.success) {
        updateCartCount(data.cart_count);
        showToast(data.message || 'Added to bag');
      } else {
        showToast(data.error || 'Could not add item', '✕');
      }
    } catch (err) {
      console.error('Cart Error:', err);
      showToast('Connection error', '✕');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = originalText;
    }
  });
}

// INITIALIZATION
document.addEventListener('DOMContentLoaded', () => {
  // Initialize Add to Cart AJAX
  initAddToCart();
  
  // Transition logic for navbar scroll
  window.addEventListener('scroll', () => {
    const nav = document.querySelector('nav');
    if (window.scrollY > 50) {
      nav.classList.add('scrolled');
    } else {
      nav.classList.remove('scrolled');
    }
  });
});