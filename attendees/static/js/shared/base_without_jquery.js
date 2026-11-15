((Attendees) => {
  if (typeof Attendees === 'undefined') window.Attendees = {};
  console.log("attendees/static/js/shared/base_without_jquery.js");
  const timeZoneName = Intl.DateTimeFormat().resolvedOptions().timeZone;
  document.cookie = 'timezone=' + encodeURIComponent(timeZoneName) + ';SameSite=Lax; path=/';

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
})(window.Attendees);
