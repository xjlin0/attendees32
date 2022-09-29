(($, Attendees) => {
  if (typeof Attendees === 'undefined') window.Attendees = {};
  console.log("attendees/static/js/shared/base.js");
  const timeZoneName = Intl.DateTimeFormat().resolvedOptions().timeZone;
  document.cookie = 'timezone=' + encodeURIComponent(timeZoneName) + ';SameSite=Lax; path=/';

  // $('li.active').removeClass('active');
  const $currentMenuItem = $('a[href="' + location.pathname + location.search + '"]');
  $currentMenuItem.addClass('active');
  $currentMenuItem.closest('li.nav-item').find('a.nav-link').addClass('active');
})(window.jQuery, window.Attendees); // https://stackoverflow.com/a/18315393
