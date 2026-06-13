function AppNavbar({ currentPage, setCurrentPage, unreadCount = 0 }) {
  return (
    <header className="app-navbar">
      <div className="nav-left">
        <button className="brand-button" onClick={() => setCurrentPage('home')}>
          <img
            src="http://localhost:5000/static/cesffo-logo.png"
            alt="Cesffo Logo"
            className="company-logo"
          />
        </button>

        <button className={currentPage === 'home' ? 'nav-link active' : 'nav-link'} onClick={() => setCurrentPage('home')}>
          Home
        </button>

        <button className={currentPage === 'course' ? 'nav-link active' : 'nav-link'} onClick={() => setCurrentPage('course')}>
          Course
        </button>

        <button className={currentPage === 'forum' ? 'nav-link active' : 'nav-link'} onClick={() => setCurrentPage('forum')}>
          Discussion Forum
        </button>
      </div>

      <div className="nav-right">
        <button className="icon-button notification-icon-button" title="Notifications" onClick={() => setCurrentPage('notifications')}>
          🔔
          {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
        </button>

        <button className="icon-button" title="Cart">🛒</button>
        <button className="icon-button" title="User">👤</button>
      </div>
    </header>
  );
}

export default AppNavbar;