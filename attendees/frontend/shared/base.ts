/**
 * Shared base module for Attendees frontend applications.
 * Sets client timezone cookie for backend detection and highlights active navbar navigation link.
 */

export const initBase = (): void => {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return;
  }

  // Detect and set client timezone cookie for Django backend
  try {
    const timeZoneName = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (timeZoneName) {
      document.cookie = 'timezone=' + encodeURIComponent(timeZoneName) + ';SameSite=Lax; path=/';
    }
  } catch (e) {
    console.warn('Failed to detect client timezone:', e);
  }

  // Highlight active navbar menu item based on current URL
  const highlightActiveNavbar = () => {
    try {
      const currentPath = location.pathname + location.search;
      const currentMenuItem = document.querySelector(`a[href="${currentPath}"]`);
      if (currentMenuItem) {
        currentMenuItem.classList.add('active');
        const navItem = currentMenuItem.closest('li.nav-item');
        if (navItem) {
          const navLink = navItem.querySelector('a.nav-link');
          if (navLink) {
            navLink.classList.add('active', 'text-decoration-underline');
          }
        }
      }
    } catch (e) {
      console.warn('Failed to highlight active navbar item:', e);
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', highlightActiveNavbar);
  } else {
    highlightActiveNavbar();
  }
};

// Auto-initialize when imported in browser environment
initBase();
