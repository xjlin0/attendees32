window.addEventListener('DOMContentLoaded', () => {
  if (window.location.pathname.includes('webauthn/add') || window.location.pathname.includes('mfa/add')) {
    const nameInput = document.querySelector('input[name="name"]');
    if (nameInput) {
      const ua = navigator.userAgent.toLowerCase();
      let deviceName = "device unlock"; // Fallback name

      if (/iphone/.test(ua)) {
        deviceName = "iPhone unlock";
      } else if (/ipad/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) {
        deviceName = "iPad unlock";
      } else if (/mac os/.test(ua)) {
        deviceName = "Mac unlock";
      } else if (/android/.test(ua)) {
        deviceName = "Android unlock";
      } else if (/windows/.test(ua)) {
        deviceName = "Windows unlock";
      }

      const currentValue = nameInput.value.toLowerCase();
      if (currentValue === "" || currentValue.includes("key") || currentValue.includes("master") || currentValue.includes("backup")) {
        nameInput.value = deviceName;
      }
    }

    // Auto-check the Passwordless checkbox for better user experience
    const passwordlessCheckbox = document.querySelector('input[name="passwordless"]');
    if (passwordlessCheckbox && !passwordlessCheckbox.checked) {
      passwordlessCheckbox.checked = true;
    }
  }
});

document.addEventListener('allauth.error', (event) => {
  const detail = event.detail;
  if (detail && detail.tags && detail.tags.includes('webauthn')) {
    event.preventDefault();
    const ex = detail.exception || {};
    let msg = ex.message || String(ex);

    if (ex.name === 'InvalidStateError' || msg.includes('already registered') || msg.includes('contains one of the credentials')) {
      msg = 'This security key or device is already registered to your account. You do not need to add it again. Just use the existing key.';
    } else if (ex.name === 'NotAllowedError' || msg.includes('timed out') || msg.includes('cancelled') || msg.includes('canceled')) {
      msg = 'The security key operation was cancelled or timed out. Please try again. On windows you can check if Bluetooth Support, Device Association and Windows Biometric Service are running in services.msc';
    }

    let alertContainer = document.getElementById('webauthn-error-alert');
    if (!alertContainer) {
      const targetContainer = document.querySelector('.col-md-8.offset-md-2') || document.querySelector('form') || document.querySelector('.container');
      if (targetContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'webauthn-error-alert';
        alertContainer.className = 'alert alert-danger alert-dismissible fade show mt-3';
        alertContainer.setAttribute('role', 'alert');
        targetContainer.insertBefore(alertContainer, targetContainer.firstChild);
      }
    }

    if (alertContainer) {
      alertContainer.innerHTML = `<strong>Notice:</strong> ${msg}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
      alertContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
});
