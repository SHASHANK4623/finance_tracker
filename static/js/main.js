// MONARCH Private Wealth - Interactive Client Engine

function openModal() {
  const modal = document.getElementById('modal');
  if (modal) {
    modal.classList.add('open');
  }
}

function closeModal() {
  const modal = document.getElementById('modal');
  if (modal) {
    modal.classList.remove('open');
  }
}

function showToast(message, isError = false) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.borderColor = isError ? 'var(--red)' : 'var(--gold)';
  toast.style.color = isError ? 'var(--red)' : 'var(--text)';
  toast.classList.add('show');
  
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3500);
}

// Client-side JavaScript Form Validation & AJAX Submission
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('transactionForm');
  
  if (form) {
    form.addEventListener('submit', function (e) {
      const titleInput = form.querySelector('[name="title"]');
      const amountInput = form.querySelector('[name="amount"]');
      const dateInput = form.querySelector('[name="date"]');
      
      const title = titleInput ? titleInput.value.trim() : '';
      const amount = amountInput ? parseFloat(amountInput.value) : 0;
      const dateVal = dateInput ? dateInput.value : '';

      // JavaScript Validation rules
      if (!title) {
        e.preventDefault();
        showToast('Please provide a valid transaction description.', true);
        if (titleInput) titleInput.focus();
        return;
      }

      if (isNaN(amount) || amount <= 0) {
        e.preventDefault();
        showToast('Transaction amount must be a positive number greater than ₹0.00.', true);
        if (amountInput) amountInput.focus();
        return;
      }

      if (!dateVal) {
        e.preventDefault();
        showToast('Please specify a transaction date.', true);
        if (dateInput) dateInput.focus();
        return;
      }

      // Check if AJAX submit is requested
      const useAjax = form.dataset.ajax === 'true';
      if (useAjax) {
        e.preventDefault();
        const formData = new FormData(form);
        formData.append('ajax', 'true');

        fetch(form.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            showToast(data.message || 'Transaction recorded successfully!');
            form.reset();
            closeModal();
            // Dynamically prepend row if ledger table exists
            const tbody = document.getElementById('rows');
            if (tbody && data.transaction) {
              const tr = document.createElement('tr');
              const t = data.transaction;
              const isIncome = t.type === 'INCOME';
              const sign = isIncome ? '+ ' : '− ';
              const cls = isIncome ? 'positive' : 'negative';

              tr.innerHTML = `
                <td>${t.title} · ${t.category}</td>
                <td>${t.asset}</td>
                <td>${t.date}</td>
                <td class="${cls}">${sign}₹ ${t.amount}</td>
                <td style="text-align:right">
                  <a href="/transactions/${t.id}/delete/?next=dashboard" class="btn danger" style="padding:4px 8px;font-size:10px" onclick="return confirm('Delete this record?');">✕</a>
                </td>
              `;
              tbody.prepend(tr);
            } else {
              setTimeout(() => window.location.reload(), 1000);
            }
          } else {
            const errs = data.errors ? Object.values(data.errors).flat().join(', ') : 'Error saving transaction';
            showToast(errs, true);
          }
        })
        .catch(err => {
          console.error(err);
          showToast('Failed to record transaction. Submitting normally...', true);
          form.submit();
        });
      }
    });
  }

  // Profile picture validation
  const avatarInput = document.querySelector('input[type="file"][name="avatar"]');
  if (avatarInput) {
    avatarInput.addEventListener('change', function () {
      const file = this.files[0];
      if (file) {
        const maxSize = 3 * 1024 * 1024; // 3MB
        if (file.size > maxSize) {
          showToast('Selected file exceeds maximum allowed size of 3MB.', true);
          this.value = '';
          return;
        }
        const allowed = ['image/jpeg', 'image/png', 'image/webp'];
        if (!allowed.includes(file.type)) {
          showToast('Only JPG, PNG, and WebP images are allowed.', true);
          this.value = '';
          return;
        }
        showToast('Image selected: ' + file.name);
      }
    });
  }
});

// Close modal when clicking on backdrop
window.addEventListener('click', (e) => {
  const modal = document.getElementById('modal');
  if (e.target === modal) {
    closeModal();
  }
});

/**
 * Matches an image's natural dimensions to its exact format (16:9, 9:16, 1:1, 3:4, 4:3, or natural)
 * and sizes the showcase stage to display it uncropped in that format.
 */
function applyOriginalAspectStage(stageEl, imgEl, badgeEl, nextSrc) {
  if (!stageEl || !imgEl) return;

  const PRESET_RATIOS = [
    { label: '16:9', css: '16 / 9', val: 16 / 9 },
    { label: '9:16', css: '9 / 16', val: 9 / 16 },
    { label: '1:1', css: '1 / 1', val: 1 },
    { label: '3:4', css: '3 / 4', val: 3 / 4 },
    { label: '4:3', css: '4 / 3', val: 4 / 3 },
  ];

  const syncStage = () => {
    const w = imgEl.naturalWidth;
    const h = imgEl.naturalHeight;
    if (!w || !h) return;

    const naturalRatio = w / h;
    let matched = null;
    for (const preset of PRESET_RATIOS) {
      if (Math.abs(naturalRatio - preset.val) / preset.val <= 0.04) {
        matched = preset;
        break;
      }
    }

    const cssRatio = matched ? matched.css : `${w} / ${h}`;
    const effectiveRatio = matched ? matched.val : naturalRatio;
    const formatLabel = matched ? matched.label : `${w}×${h}`;

    stageEl.style.aspectRatio = cssRatio;
    stageEl.style.width = `min(100%, calc(min(70vh, 580px) * ${effectiveRatio.toFixed(6)}))`;
    stageEl.style.height = 'auto';

    if (badgeEl) {
      badgeEl.textContent = `✦ Original Format · ${formatLabel}`;
    }
  };

  imgEl.onload = syncStage;
  if (nextSrc) {
    imgEl.src = nextSrc;
  }
  if (imgEl.complete && imgEl.naturalWidth > 0) {
    syncStage();
  }
}
