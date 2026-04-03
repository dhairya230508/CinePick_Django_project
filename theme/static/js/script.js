const navToggle = document.querySelector("[data-nav-toggle]");
const mobileNav = document.querySelector("[data-mobile-nav]");

if (navToggle && mobileNav) {
  navToggle.addEventListener("click", () => {
    mobileNav.classList.toggle("is-open");
  });
}
