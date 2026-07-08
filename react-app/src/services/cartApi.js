import { apiFetch } from '../api/client';

// --- Cart API routes ---
export const CartApi = {
  getCart() {
    return apiFetch('/api/v1/cart');
  },

  addCourse(courseId) {
    return apiFetch(`/api/v1/cart/items/${courseId}`, { method: 'POST' });
  },

  removeCourse(courseId) {
    return apiFetch(`/api/v1/cart/items/${courseId}`, { method: 'DELETE' });
  },

  checkout() {
    return apiFetch('/api/v1/cart/checkout', { method: 'POST' });
  },
};
