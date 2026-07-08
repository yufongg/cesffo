import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import NotFound from './NotFound';

function renderPage() {
  return render(
    <MemoryRouter>
      <NotFound />
    </MemoryRouter>
  );
}

afterEach(() => {
  localStorage.clear();
});

test('renders the 404 error page', () => {
  renderPage();
  expect(screen.getByText('404')).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: /page not found/i })).toBeInTheDocument();
});

test('unauthenticated visitors are directed back to login, not into the app', () => {
  renderPage();
  const link = screen.getByRole('link', { name: /back to login/i });
  expect(link).toHaveAttribute('href', '/');
});

test('authenticated users are directed back to their learning dashboard', () => {
  localStorage.setItem('access_token', 'fake_token');
  localStorage.setItem('user_role', 'student');
  renderPage();
  const link = screen.getByRole('link', { name: /Back to My Learning/i });
  expect(link).toHaveAttribute('href', '/courses');
});
