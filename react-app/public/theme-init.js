// Apply the saved (or system-preferred) theme BEFORE first paint so the
// page never flashes the wrong colours on refresh. ThemeToggle reads this
// attribute back on mount, so the choice survives reloads.
// Kept as an external file (not inline) so the CSP can stay script-src 'self'.
(function () {
  try {
    var t = localStorage.getItem('theme');
    if (t !== 'light' && t !== 'dark') {
      t = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', t);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();
