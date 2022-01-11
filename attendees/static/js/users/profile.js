document.addEventListener('DOMContentLoaded', () => {
  console.log("attendees/static/js/users/profile.js");
  // if (typeof Attendees === 'undefined') window.Attendees = {};
  Attendees.usersProfile = {
    showLanguage: () => {
      document.getElementById("browser-detection").innerHTML = `Language "${navigator.languages.join(", ")}" in ${navigator.userAgent}`;
    },
  };
  Attendees.usersProfile.showLanguage();
});
