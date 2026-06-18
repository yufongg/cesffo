import { apiFetch } from "../api/client";

export const InstructorContentApi = {
  listMaterials(moduleId) {
    return apiFetch(`/api/v1/instructor/modules/${moduleId}/materials`);
  },

  createMaterial(moduleId, payload) {
    return apiFetch(
      `/api/v1/instructor/modules/${moduleId}/materials`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  updateMaterial(materialId, payload) {
    return apiFetch(
      `/api/v1/instructor/materials/${materialId}`,
      {
        method: "PATCH",
        body: payload,
      }
    );
  },

  deleteMaterial(materialId) {
    return apiFetch(
      `/api/v1/instructor/materials/${materialId}`,
      {
        method: "DELETE",
      }
    );
  },

  listMedia(moduleId) {
    return apiFetch(`/api/v1/instructor/modules/${moduleId}/media`);
  },

  createMedia(moduleId, payload) {
    return apiFetch(
      `/api/v1/instructor/modules/${moduleId}/media`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  updateMedia(mediaId, payload) {
    return apiFetch(
      `/api/v1/instructor/media/${mediaId}`,
      {
        method: "PATCH",
        body: payload,
      }
    );
  },

  deleteMedia(mediaId) {
    return apiFetch(
      `/api/v1/instructor/media/${mediaId}`,
      {
        method: "DELETE",
      }
    );
  },

  listActivities(moduleId) {
    return apiFetch(`/api/v1/instructor/modules/${moduleId}/activities`);
  },

  createActivity(moduleId, payload) {
    return apiFetch(
      `/api/v1/instructor/modules/${moduleId}/activities`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  updateActivity(activityId, payload) {
    return apiFetch(
      `/api/v1/instructor/activities/${activityId}`,
      {
        method: "PATCH",
        body: payload,
      }
    );
  },

  deleteActivity(activityId) {
    return apiFetch(
      `/api/v1/instructor/activities/${activityId}`,
      {
        method: "DELETE",
      }
    );
  },
};