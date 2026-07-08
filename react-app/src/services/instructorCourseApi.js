import { apiFetch } from '../api/client';

export const InstructorCourseApi = {
  listCourses() {
    return apiFetch('/api/v1/instructor/courses');
  },

  getCourse(courseId) {
    return apiFetch(`/api/v1/instructor/courses/${courseId}`);
  },

  createCourse(payload) {
    return apiFetch('/api/v1/instructor/courses', {
      method: 'POST',
      body: payload,
    });
  },

  updateCourse(courseId, payload) {
    return apiFetch(`/api/v1/instructor/courses/${courseId}`, {
      method: 'PATCH',
      body: payload,
    });
  },

  deleteCourse(courseId) {
    return apiFetch(`/api/v1/instructor/courses/${courseId}`, {
      method: 'DELETE',
    });
  },

  listModules(courseId) {
    return apiFetch(`/api/v1/instructor/courses/${courseId}/modules`);
  },

  createModule(courseId, payload) {
    return apiFetch(`/api/v1/instructor/courses/${courseId}/modules`, {
      method: 'POST',
      body: payload,
    });
  },

  updateModule(moduleId, payload) {
    return apiFetch(`/api/v1/instructor/modules/${moduleId}`, {
      method: 'PATCH',
      body: payload,
    });
  },

  deleteModule(moduleId) {
    return apiFetch(`/api/v1/instructor/modules/${moduleId}`, {
      method: 'DELETE',
    });
  },
};
