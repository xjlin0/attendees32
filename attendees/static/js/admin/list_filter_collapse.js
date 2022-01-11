;console.log("loading list_filter_collapse.js"); // Fancier version https://stackoverflow.com/a/10815237/4257237

document.addEventListener("DOMContentLoaded", function(event){
  console.log("DOM ready!");
  $=django.jQuery.noConflict();
  $('#changelist-filter > h3').each(function(){
      var $title = $(this);
      $title.next().toggle();
      $title.css("cursor","pointer");
      $title.click(function(){
          $title.next().slideToggle();
      });
  });
  var toggle_flag = false;
  $('#changelist-filter > h2').css("cursor","pointer");
  $('#changelist-filter > h2').click(function () {
      toggle_flag = ! toggle_flag;
      $('#changelist-filter > ul').each(function(){
          $(this).slideToggle(toggle_flag);
      });
  });
});
