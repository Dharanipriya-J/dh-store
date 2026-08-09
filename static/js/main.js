// DH STORE - simple front-end script

// Toggle the mobile navigation menu
var hamburgerBtn = document.getElementById("hamburgerBtn");
var navLinks = document.getElementById("navLinks");

if (hamburgerBtn && navLinks) {
  hamburgerBtn.addEventListener("click", function () {
    navLinks.classList.toggle("is-open");
  });
}

// Auto-hide flash messages after a few seconds
var flashMessages = document.querySelectorAll(".flash");
for (var i = 0; i < flashMessages.length; i++) {
  (function (el) {
    setTimeout(function () {
      el.style.display = "none";
    }, 4000);
  })(flashMessages[i]);
}

// Fill in a saved address on the checkout page when clicked
function fillAddress(name, phone, line1, line2, city, state, pincode, landmark) {
  document.getElementById("full_name").value = name;
  document.getElementById("phone").value = phone;
  document.getElementById("line1").value = line1;
  document.getElementById("line2").value = line2;
  document.getElementById("city").value = city;
  document.getElementById("state").value = state;
  document.getElementById("pincode").value = pincode;
  document.getElementById("landmark").value = landmark;
}


document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".product-card").forEach(function (card) {
    const selectors = card.querySelectorAll(".card-option");
    const forms = card.querySelectorAll(".product-actions form");
    if (!selectors.length) return;

    selectors.forEach(function (select) {
      function syncOptions() {
        forms.forEach(function (form) {
          form.querySelectorAll(".linked-option").forEach(function (hidden) {
            const target = card.querySelector(hidden.dataset.select);
            if (target) hidden.value = target.value;
          });
        });
      }
      select.addEventListener("change", syncOptions);
      syncOptions();
    });
  });
});
