import { useState } from 'react';
import './styles/global.css';
import './styles/navbar.css';
import './styles/home.css';
import './styles/forum.css';
import ForumPage from './pages/ForumPage';
import AppNavbar from './components/AppNavbar';

const forumCategories = [
  'Budgeting',
  'Saving',
  'Debt Management',
  'Investing',
  'Insurance',
  'Retirement Planning',
  'Course Help',
];

function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const [selectedForumCategory, setSelectedForumCategory] = useState(null);

  function changePage(page) {
    if (page === 'forum') {
      setSelectedForumCategory(null);
    }

    setCurrentPage(page);
  }

  function openForumCategory(category) {
    setSelectedForumCategory(category);
    setCurrentPage('forum');
  }

  return (
    <>
      <AppNavbar
        currentPage={currentPage}
        setCurrentPage={changePage}
      />

      {currentPage === 'home' && (
        <main className="home-page">
          <section className="home-hero">
            <div>
              <h1>Join us to learn more about financial literacy!</h1>
              <p>
                Cesffo is a secure and interactive e-learning platform designed
                to help the public learn budgeting, saving, investing,
                insurance, debt management, and retirement planning.
              </p>
            </div>
          </section>

          <section className="home-forum-section">
            <h2>Discussion Forum</h2>
            <p>Choose a topic category to join the discussion.</p>

            <div className="home-category-grid">
              {forumCategories.map((category) => (
                <button
                  key={category}
                  type="button"
                  className="home-category-button"
                  onClick={() => openForumCategory(category)}
                >
                  {category}
                </button>
              ))}
            </div>
          </section>
        </main>
      )}

      {currentPage === 'course' && (
        <main className="placeholder-page">
          <h1>Courses</h1>
          <p>Course page.</p>
        </main>
      )}

      {currentPage === 'forum' && (
        <ForumPage initialCategoryName={selectedForumCategory} />
      )}

      {currentPage === 'notifications' && (
        <main className="placeholder-page">
          <h1>Notifications</h1>
          <p>Notifications not completed yet.</p>
        </main>
      )}
    </>
  );
}

export default App;