import React, { useEffect, useState } from 'react';
import { InstructorCourseApi } from '../services/instructorCourseApi';
import { InstructorContentApi } from '../services/instructorContentApi';
import { useAuth } from '../components/Security/RoleCheck';

const initialCourseForm = { course_name: '', summary: '', level: '', tags: '', xp_reward: 0 };
const initialModuleForm = { title: '', description: '', order_index: 0 };
const initialMaterialForm = { title: '', body: '', order_index: 0 };
const initialMediaForm = { title: '', media_url: '', media_type: 'video', order_index: 0 };
const initialActivityForm = {
  title: '',
  activity_type: 'mcq_single',
  prompt: '',
  order_index: 0,
  // MCQ correctness is tracked per option (matches ActivityOption.is_correct on
  // the backend) instead of re-matching free text, so an MCQ round-trips cleanly
  // through edit/save.
  options: [
    { option_text: '', is_correct: true },
    { option_text: '', is_correct: false },
  ],
  // Short-answer accepted answers, one per line.
  correct_answers_text: '',
};

export default function InstructorDashboard() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [courseForm, setCourseForm] = useState(initialCourseForm);
  const [editingCourseId, setEditingCourseId] = useState(null);
  const [selectedCourseId, setSelectedCourseId] = useState(null);

  const [modules, setModules] = useState([]);
  const [moduleForm, setModuleForm] = useState(initialModuleForm);
  const [editingModuleId, setEditingModuleId] = useState(null);
  const [moduleError, setModuleError] = useState('');
  const [selectedModuleId, setSelectedModuleId] = useState(null);

  const [materials, setMaterials] = useState([]);
  const [materialForm, setMaterialForm] = useState(initialMaterialForm);
  const [editingMaterialId, setEditingMaterialId] = useState(null);

  const [media, setMedia] = useState([]);
  const [mediaForm, setMediaForm] = useState(initialMediaForm);
  const [editingMediaId, setEditingMediaId] = useState(null);

  const [activities, setActivities] = useState([]);
  const [activityForm, setActivityForm] = useState(initialActivityForm);
  const [editingActivityId, setEditingActivityId] = useState(null);
  const [contentError, setContentError] = useState('');

  const user = useAuth();

  useEffect(() => {
    let active = true;
    InstructorCourseApi.listCourses()
      .then((data) => {
        if (!active) return;
        setCourses(data || []);
      })
      .catch((e) => { if (active) setError(e.message || 'Unable to load courses'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  function setCourseField(field, value) {
    setCourseForm((prev) => ({ ...prev, [field]: value }));
  }

  function clearCourseForm() {
    setCourseForm(initialCourseForm);
    setEditingCourseId(null);
    setError('');
  }

  function setModuleField(field, value) {
    setModuleForm((prev) => ({ ...prev, [field]: value }));
  }

  function clearModuleForm() {
    setModuleForm(initialModuleForm);
    setEditingModuleId(null);
    setModuleError('');
  }

  function setMaterialField(field, value) {
    setMaterialForm((prev) => ({ ...prev, [field]: value }));
  }

  function clearMaterialForm() {
    setMaterialForm(initialMaterialForm);
    setEditingMaterialId(null);
    setContentError('');
  }

  function setMediaField(field, value) {
    setMediaForm((prev) => ({ ...prev, [field]: value }));
  }

  function clearMediaForm() {
    setMediaForm(initialMediaForm);
    setEditingMediaId(null);
    setContentError('');
  }

  function setActivityField(field, value) {
    setActivityForm((prev) => ({ ...prev, [field]: value }));
  }

  function setActivityType(type) {
    setActivityForm((prev) => {
      // Switching to single-answer must leave at most one option marked correct.
      let options = prev.options;
      if (type === 'mcq_single') {
        let kept = false;
        options = prev.options.map((o) => {
          if (o.is_correct && !kept) { kept = true; return o; }
          return { ...o, is_correct: false };
        });
      }
      return { ...prev, activity_type: type, options };
    });
  }

  function setOptionText(index, value) {
    setActivityForm((prev) => ({
      ...prev,
      options: prev.options.map((o, i) => (i === index ? { ...o, option_text: value } : o)),
    }));
  }

  function setOptionCorrect(index, checked) {
    setActivityForm((prev) => {
      // Single-answer: selecting one option clears the rest (radio semantics).
      if (prev.activity_type === 'mcq_single') {
        return { ...prev, options: prev.options.map((o, i) => ({ ...o, is_correct: i === index })) };
      }
      return {
        ...prev,
        options: prev.options.map((o, i) => (i === index ? { ...o, is_correct: checked } : o)),
      };
    });
  }

  function addOption() {
    setActivityForm((prev) => ({
      ...prev,
      options: [...prev.options, { option_text: '', is_correct: false }],
    }));
  }

  function removeOption(index) {
    setActivityForm((prev) => ({
      ...prev,
      options: prev.options.filter((_, i) => i !== index),
    }));
  }

  function clearActivityForm() {
    setActivityForm(initialActivityForm);
    setEditingActivityId(null);
    setContentError('');
  }

  async function refreshCourses() {
    try {
      const data = await InstructorCourseApi.listCourses();
      setCourses(data || []);
    } catch (err) {
      setError(err.message || 'Failed to refresh courses');
    }
  }

  async function refreshModules(courseId) {
    if (!courseId) return;
    try {
      const data = await InstructorCourseApi.listModules(courseId);
      setModules(data || []);
    } catch (err) {
      setModuleError(err.message || 'Failed to load modules');
    }
  }

  async function refreshModuleContent(moduleId) {
    if (!moduleId) return;
    try {
      const [materialsData, mediaData, activitiesData] = await Promise.all([
        InstructorContentApi.listMaterials(moduleId),
        InstructorContentApi.listMedia(moduleId),
        InstructorContentApi.listActivities(moduleId),
      ]);
      setMaterials(materialsData || []);
      setMedia(mediaData || []);
      setActivities(activitiesData || []);
    } catch (err) {
      setContentError(err.message || 'Failed to load module content');
    }
  }

  async function handleCourseSubmit(event) {
    event.preventDefault();
    setError('');
    const payload = {
      course_name: courseForm.course_name,
      summary: courseForm.summary,
      level: courseForm.level,
      tags: courseForm.tags.split(',').map((t) => t.trim()).filter(Boolean),
      xp_reward: Number(courseForm.xp_reward) || 0,
    };

    try {
      if (editingCourseId) {
        await InstructorCourseApi.updateCourse(editingCourseId, payload);
      } else {
        await InstructorCourseApi.createCourse(payload);
      }
      await refreshCourses();
      clearCourseForm();
    } catch (err) {
      setError(err.message || 'Save failed');
    }
  }

  function handleCourseEdit(course) {
    setEditingCourseId(course.course_id);
    setCourseForm({
      course_name: course.course_name || '',
      summary: course.summary || '',
      level: course.level || '',
      tags: (course.tags || []).join(', '),
      xp_reward: course.xp_reward || 0,
    });
    setError('');
  }

  async function handleCourseDelete(courseId) {
    if (!window.confirm('Delete this course? This cannot be undone.')) {
      return;
    }
    try {
      await InstructorCourseApi.deleteCourse(courseId);
      setCourses((prev) => prev.filter((c) => c.course_id !== courseId));
      if (editingCourseId === courseId) clearCourseForm();
      if (selectedCourseId === courseId) {
        setSelectedCourseId(null);
        setModules([]);
        setSelectedModuleId(null);
        setMaterials([]);
        setMedia([]);
        setActivities([]);
      }
    } catch (err) {
      setError(err.message || 'Delete failed');
    }
  }

  async function handleCourseSelect(course) {
    setSelectedCourseId(course.course_id);
    setSelectedModuleId(null);
    setMaterials([]);
    setMedia([]);
    setActivities([]);
    clearModuleForm();
    clearMaterialForm();
    clearMediaForm();
    clearActivityForm();
    await refreshModules(course.course_id);
  }

  async function handleModuleSubmit(event) {
    event.preventDefault();
    setModuleError('');
    if (!selectedCourseId) {
      setModuleError('Select a course before adding modules');
      return;
    }
    const payload = {
      title: moduleForm.title,
      description: moduleForm.description,
      order_index: Number(moduleForm.order_index) || 0,
    };
    try {
      if (editingModuleId) {
        await InstructorCourseApi.updateModule(editingModuleId, payload);
      } else {
        await InstructorCourseApi.createModule(selectedCourseId, payload);
      }
      await refreshModules(selectedCourseId);
      clearModuleForm();
    } catch (err) {
      setModuleError(err.message || 'Module save failed');
    }
  }

  function handleModuleEdit(module) {
    setEditingModuleId(module.module_id);
    setModuleForm({
      title: module.title || '',
      description: module.description || '',
      order_index: module.order_index || 0,
    });
    setModuleError('');
  }

  async function handleModuleDelete(moduleId) {
    if (!window.confirm('Delete this module? This cannot be undone.')) {
      return;
    }
    try {
      await InstructorCourseApi.deleteModule(moduleId);
      setModules((prev) => prev.filter((m) => m.module_id !== moduleId));
      if (selectedModuleId === moduleId) {
        setSelectedModuleId(null);
        setMaterials([]);
        setMedia([]);
        setActivities([]);
      }
      if (editingModuleId === moduleId) clearModuleForm();
    } catch (err) {
      setModuleError(err.message || 'Module delete failed');
    }
  }

  async function handleModuleSelect(module) {
    setSelectedModuleId(module.module_id);
    clearMaterialForm();
    clearMediaForm();
    clearActivityForm();
    await refreshModuleContent(module.module_id);
  }

  async function handleMaterialSubmit(event) {
    event.preventDefault();
    setContentError('');
    if (!selectedModuleId) {
      setContentError('Select a module before adding reading materials');
      return;
    }
    const payload = {
      title: materialForm.title,
      body: materialForm.body,
      order_index: Number(materialForm.order_index) || 0,
    };
    try {
      if (editingMaterialId) {
        await InstructorContentApi.updateMaterial(editingMaterialId, payload);
      } else {
        await InstructorContentApi.createMaterial(selectedModuleId, payload);
      }
      await refreshModuleContent(selectedModuleId);
      clearMaterialForm();
    } catch (err) {
      setContentError(err.message || 'Reading material save failed');
    }
  }

  function handleMaterialEdit(material) {
    setEditingMaterialId(material.material_id);
    setMaterialForm({
      title: material.title || '',
      body: material.body || '',
      order_index: material.order_index || 0,
    });
    setContentError('');
  }

  async function handleMaterialDelete(materialId) {
    if (!window.confirm('Delete this reading material?')) return;
    try {
      await InstructorContentApi.deleteMaterial(materialId);
      setMaterials((prev) => prev.filter((m) => m.material_id !== materialId));
      if (editingMaterialId === materialId) clearMaterialForm();
    } catch (err) {
      setContentError(err.message || 'Reading material delete failed');
    }
  }

  async function handleMediaSubmit(event) {
    event.preventDefault();
    setContentError('');
    if (!selectedModuleId) {
      setContentError('Select a module before adding media content');
      return;
    }
    const payload = {
      title: mediaForm.title,
      media_url: mediaForm.media_url,
      media_type: mediaForm.media_type,
      order_index: Number(mediaForm.order_index) || 0,
    };
    try {
      if (editingMediaId) {
        await InstructorContentApi.updateMedia(editingMediaId, payload);
      } else {
        await InstructorContentApi.createMedia(selectedModuleId, payload);
      }
      await refreshModuleContent(selectedModuleId);
      clearMediaForm();
    } catch (err) {
      setContentError(err.message || 'Media content save failed');
    }
  }

  function handleMediaEdit(mediaItem) {
    setEditingMediaId(mediaItem.media_id);
    setMediaForm({
      title: mediaItem.title || '',
      media_url: mediaItem.media_url || '',
      media_type: mediaItem.media_type || 'video',
      order_index: mediaItem.order_index || 0,
    });
    setContentError('');
  }

  async function handleMediaDelete(mediaId) {
    if (!window.confirm('Delete this media item?')) return;
    try {
      await InstructorContentApi.deleteMedia(mediaId);
      setMedia((prev) => prev.filter((m) => m.media_id !== mediaId));
      if (editingMediaId === mediaId) clearMediaForm();
    } catch (err) {
      setContentError(err.message || 'Media delete failed');
    }
  }

  async function handleActivitySubmit(event) {
    event.preventDefault();
    setContentError('');
    if (!selectedModuleId) {
      setContentError('Select a module before adding activities');
      return;
    }
    const payload = {
      title: activityForm.title,
      activity_type: activityForm.activity_type,
      prompt: activityForm.prompt,
      order_index: Number(activityForm.order_index) || 0,
    };

    if (activityForm.activity_type === 'short_answer') {
      const answers = activityForm.correct_answers_text
        .split('\n')
        .map((a) => a.trim())
        .filter(Boolean);
      if (answers.length === 0) {
        setContentError('Add at least one accepted answer.');
        return;
      }
      payload.correct_answers = answers;
    } else {
      const options = activityForm.options
        .map((o) => ({ option_text: o.option_text.trim(), is_correct: o.is_correct }))
        .filter((o) => o.option_text);
      if (options.length < 2) {
        setContentError('Multiple-choice questions need at least 2 options.');
        return;
      }
      const correctCount = options.filter((o) => o.is_correct).length;
      if (activityForm.activity_type === 'mcq_single' && correctCount !== 1) {
        setContentError('Single-answer questions need exactly one correct option.');
        return;
      }
      if (activityForm.activity_type === 'mcq_multi' && correctCount < 1) {
        setContentError('Multiple-answer questions need at least one correct option.');
        return;
      }
      payload.options = options;
    }
    try {
      if (editingActivityId) {
        await InstructorContentApi.updateActivity(editingActivityId, payload);
      } else {
        await InstructorContentApi.createActivity(selectedModuleId, payload);
      }
      await refreshModuleContent(selectedModuleId);
      clearActivityForm();
    } catch (err) {
      setContentError(err.message || 'Activity save failed');
    }
  }

  function handleActivityEdit(activity) {
    setEditingActivityId(activity.activity_id);
    const isShort = activity.activity_type === 'short_answer';
    const existingOptions = (activity.options || []).map((o) => ({
      option_text: o.option_text || '',
      is_correct: !!o.is_correct,
    }));
    setActivityForm({
      title: activity.title || '',
      activity_type: activity.activity_type || 'mcq_single',
      prompt: activity.prompt || '',
      order_index: activity.order_index || 0,
      options: !isShort && existingOptions.length >= 2
        ? existingOptions
        : [{ option_text: '', is_correct: true }, { option_text: '', is_correct: false }],
      correct_answers_text: isShort ? (activity.correct_answers || []).join('\n') : '',
    });
    setContentError('');
  }

  async function handleActivityDelete(activityId) {
    if (!window.confirm('Delete this activity?')) return;
    try {
      await InstructorContentApi.deleteActivity(activityId);
      setActivities((prev) => prev.filter((a) => a.activity_id !== activityId));
      if (editingActivityId === activityId) clearActivityForm();
    } catch (err) {
      setContentError(err.message || 'Activity delete failed');
    }
  }

  const selectedCourse = courses.find((c) => c.course_id === selectedCourseId);
  const selectedModule = modules.find((m) => m.module_id === selectedModuleId);

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <span className="eyebrow">Instructor</span>
          <h1>Course and content authoring</h1>
          <p className="subtitle">
            {user?.username ? `${user.username},` : 'You'} can create courses, add modules, and author module content here.
          </p>
        </div>

        {(error || moduleError || contentError) && (
          <div className="alert alert--error">
            {error || moduleError || contentError}
          </div>
        )}

        <section className="section">
          <div className="section__head">
            <h2>{editingCourseId ? 'Edit course' : 'Create a new course'}</h2>
          </div>
          <form onSubmit={handleCourseSubmit} className="form-grid">
            <div className="field">
              <label htmlFor="course_name" className="label">Course name</label>
              <input
                id="course_name"
                className="input"
                value={courseForm.course_name}
                onChange={(e) => setCourseField('course_name', e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="level" className="label">Level</label>
              <input
                id="level"
                className="input"
                value={courseForm.level}
                onChange={(e) => setCourseField('level', e.target.value)}
                placeholder="Beginner, Intermediate, Advanced"
              />
            </div>
            <div className="field">
              <label htmlFor="xp_reward" className="label">XP reward</label>
              <input
                id="xp_reward"
                className="input"
                type="number"
                min="0"
                value={courseForm.xp_reward}
                onChange={(e) => setCourseField('xp_reward', e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="tags" className="label">Tags</label>
              <input
                id="tags"
                className="input"
                value={courseForm.tags}
                onChange={(e) => setCourseField('tags', e.target.value)}
                placeholder="tax, personal finance, budgeting"
              />
            </div>
            <div className="field field--full">
              <label htmlFor="summary" className="label">Summary</label>
              <textarea
                id="summary"
                className="textarea"
                rows="5"
                value={courseForm.summary}
                onChange={(e) => setCourseField('summary', e.target.value)}
              />
            </div>
            <div className="field field--actions">
              <button type="submit" className="btn btn--primary">
                {editingCourseId ? 'Save changes' : 'Create course'}
              </button>
              {editingCourseId && (
                <button type="button" className="btn btn--ghost" onClick={clearCourseForm}>
                  Cancel edit
                </button>
              )}
            </div>
          </form>
        </section>

        <section className="section">
          <div className="section__head">
            <h2>Your courses</h2>
            <span className="count">{courses.length} courses</span>
          </div>
          {loading ? (
            <p style={{ color: 'var(--color-muted)' }}>Loading your courses…</p>
          ) : courses.length === 0 ? (
            <div className="empty-state">
              <h3>No courses yet</h3>
              <p>Create your first course to start publishing learning content.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Level</th>
                    <th>XP</th>
                    <th>Tags</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {courses.map((course) => (
                    <tr key={course.course_id}>
                      <td>{course.course_name}</td>
                      <td>{course.level || '—'}</td>
                      <td>{course.xp_reward ?? 0}</td>
                      <td>{(course.tags || []).join(', ') || '—'}</td>
                      <td>
                        <div className="row-actions">
                          <button
                            type="button"
                            className="btn btn--secondary btn--sm"
                            onClick={() => handleCourseEdit(course)}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            className="btn btn--secondary btn--sm"
                            onClick={() => handleCourseSelect(course)}
                          >
                            Manage content
                          </button>
                          <button
                            type="button"
                            className="btn btn--danger btn--sm"
                            onClick={() => handleCourseDelete(course.course_id)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {selectedCourse && (
          <section className="section">
            <div className="section__head">
              <h2>Modules for {selectedCourse.course_name}</h2>
              <span className="count">{modules.length} modules</span>
            </div>
            <form onSubmit={handleModuleSubmit} className="form-grid">
              <div className="field">
                <label htmlFor="module_title" className="label">Module title</label>
                <input
                  id="module_title"
                  className="input"
                  value={moduleForm.title}
                  onChange={(e) => setModuleField('title', e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="module_order_index" className="label">Order</label>
                <input
                  id="module_order_index"
                  className="input"
                  type="number"
                  min="0"
                  value={moduleForm.order_index}
                  onChange={(e) => setModuleField('order_index', e.target.value)}
                />
              </div>
              <div className="field field--full">
                <label htmlFor="module_description" className="label">Description</label>
                <textarea
                  id="module_description"
                  className="textarea"
                  rows="3"
                  value={moduleForm.description}
                  onChange={(e) => setModuleField('description', e.target.value)}
                />
              </div>
              <div className="field field--actions">
                <button type="submit" className="btn btn--primary">
                  {editingModuleId ? 'Save module' : 'Add module'}
                </button>
                {editingModuleId && (
                  <button type="button" className="btn btn--ghost" onClick={clearModuleForm}>
                    Cancel edit
                  </button>
                )}
              </div>
            </form>

            {modules.length > 0 ? (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Title</th>
                      <th>Order</th>
                      <th>Description</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modules.map((module) => (
                      <tr key={module.module_id} className={module.module_id === selectedModuleId ? 'selected-row' : ''}>
                        <td>{module.title}</td>
                        <td>{module.order_index}</td>
                        <td>{module.description || '—'}</td>
                        <td>
                          <div className="row-actions">
                            <button type="button" className="btn btn--secondary btn--sm" onClick={() => handleModuleSelect(module)}>
                              Open
                            </button>
                            <button type="button" className="btn btn--secondary btn--sm" onClick={() => handleModuleEdit(module)}>
                              Edit
                            </button>
                            <button type="button" className="btn btn--danger btn--sm" onClick={() => handleModuleDelete(module.module_id)}>
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                <p>No modules yet. Add one to start building content.</p>
              </div>
            )}
          </section>
        )}

        {selectedModule && (
          <section className="section">
            <div className="section__head">
              <h2>Content for {selectedModule.title}</h2>
            </div>
            <div className="grid grid--2">
              <div>
                <h3>Reading materials</h3>
                <form onSubmit={handleMaterialSubmit} className="form-grid">
                  <div className="field">
                    <label htmlFor="material_title" className="label">Title</label>
                    <input
                      id="material_title"
                      className="input"
                      value={materialForm.title}
                      onChange={(e) => setMaterialField('title', e.target.value)}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="material_order_index" className="label">Order</label>
                    <input
                      id="material_order_index"
                      className="input"
                      type="number"
                      min="0"
                      value={materialForm.order_index}
                      onChange={(e) => setMaterialField('order_index', e.target.value)}
                    />
                  </div>
                  <div className="field field--full">
                    <label htmlFor="material_body" className="label">Body</label>
                    <textarea
                      id="material_body"
                      className="textarea"
                      rows="4"
                      value={materialForm.body}
                      onChange={(e) => setMaterialField('body', e.target.value)}
                      required
                    />
                  </div>
                  <div className="field field--actions">
                    <button type="submit" className="btn btn--primary">
                      {editingMaterialId ? 'Save material' : 'Add material'}
                    </button>
                    {editingMaterialId && (
                      <button type="button" className="btn btn--ghost" onClick={clearMaterialForm}>
                        Cancel edit
                      </button>
                    )}
                  </div>
                </form>
                {materials.length > 0 ? (
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Title</th>
                          <th>Order</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {materials.map((item) => (
                          <tr key={item.material_id}>
                            <td>{item.title}</td>
                            <td>{item.order_index}</td>
                            <td>
                              <div className="row-actions">
                                <button type="button" className="btn btn--secondary btn--sm" onClick={() => handleMaterialEdit(item)}>
                                  Edit
                                </button>
                                <button type="button" className="btn btn--danger btn--sm" onClick={() => handleMaterialDelete(item.material_id)}>
                                  Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="muted">No reading materials yet.</p>
                )}
              </div>

              <div>
                <h3>Media content</h3>
                <form onSubmit={handleMediaSubmit} className="form-grid">
                  <div className="field">
                    <label htmlFor="media_title" className="label">Title</label>
                    <input
                      id="media_title"
                      className="input"
                      value={mediaForm.title}
                      onChange={(e) => setMediaField('title', e.target.value)}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="media_type" className="label">Type</label>
                    <select
                      id="media_type"
                      className="select"
                      value={mediaForm.media_type}
                      onChange={(e) => setMediaField('media_type', e.target.value)}
                    >
                      <option value="video">Video</option>
                      <option value="image">Image</option>
                      <option value="audio">Audio</option>
                      <option value="document">Document</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="media_order_index" className="label">Order</label>
                    <input
                      id="media_order_index"
                      className="input"
                      type="number"
                      min="0"
                      value={mediaForm.order_index}
                      onChange={(e) => setMediaField('order_index', e.target.value)}
                    />
                  </div>
                  <div className="field field--full">
                    <label htmlFor="media_url" className="label">Media URL</label>
                    <input
                      id="media_url"
                      className="input"
                      value={mediaForm.media_url}
                      onChange={(e) => setMediaField('media_url', e.target.value)}
                      required
                    />
                  </div>
                  <div className="field field--actions">
                    <button type="submit" className="btn btn--primary">
                      {editingMediaId ? 'Save media' : 'Add media'}
                    </button>
                    {editingMediaId && (
                      <button type="button" className="btn btn--ghost" onClick={clearMediaForm}>
                        Cancel edit
                      </button>
                    )}
                  </div>
                </form>
                {media.length > 0 ? (
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Title</th>
                          <th>Type</th>
                          <th>Order</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {media.map((item) => (
                          <tr key={item.media_id}>
                            <td>{item.title}</td>
                            <td>{item.media_type}</td>
                            <td>{item.order_index}</td>
                            <td>
                              <div className="row-actions">
                                <button type="button" className="btn btn--secondary btn--sm" onClick={() => handleMediaEdit(item)}>
                                  Edit
                                </button>
                                <button type="button" className="btn btn--danger btn--sm" onClick={() => handleMediaDelete(item.media_id)}>
                                  Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="muted">No media content yet.</p>
                )}
              </div>
            </div>

            <div className="section__split">
              <h3>Interactive activities</h3>
              <form onSubmit={handleActivitySubmit} className="form-grid">
                <div className="field">
                  <label htmlFor="activity_title" className="label">Title</label>
                  <input
                    id="activity_title"
                    className="input"
                    value={activityForm.title}
                    onChange={(e) => setActivityField('title', e.target.value)}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="activity_type" className="label">Activity type</label>
                  <select
                    id="activity_type"
                    className="select"
                    value={activityForm.activity_type}
                    onChange={(e) => setActivityType(e.target.value)}
                    disabled={!!editingActivityId}
                  >
                    <option value="mcq_single">MCQ single</option>
                    <option value="mcq_multi">MCQ multi</option>
                    <option value="short_answer">Short answer</option>
                  </select>
                  {editingActivityId && (
                    <span className="field__hint">Activity type can't be changed after creation.</span>
                  )}
                </div>
                <div className="field">
                  <label htmlFor="activity_order_index" className="label">Order</label>
                  <input
                    id="activity_order_index"
                    className="input"
                    type="number"
                    min="0"
                    value={activityForm.order_index}
                    onChange={(e) => setActivityField('order_index', e.target.value)}
                  />
                </div>
                <div className="field field--full">
                  <label htmlFor="activity_prompt" className="label">Prompt</label>
                  <textarea
                    id="activity_prompt"
                    className="textarea"
                    rows="3"
                    value={activityForm.prompt}
                    onChange={(e) => setActivityField('prompt', e.target.value)}
                    required
                  />
                </div>
                {activityForm.activity_type !== 'short_answer' ? (
                  <div className="field field--full">
                    <label className="label">
                      Options
                      <span className="field__hint" style={{ display: 'inline', marginLeft: 6 }}>
                        ({activityForm.activity_type === 'mcq_single'
                          ? 'select the one correct answer'
                          : 'tick every correct answer'})
                      </span>
                    </label>
                    <div className="option-list">
                      {activityForm.options.map((option, index) => (
                        <div className="option-row" key={index}>
                          <input
                            type={activityForm.activity_type === 'mcq_single' ? 'radio' : 'checkbox'}
                            name="activity_correct_option"
                            className="option-row__mark"
                            checked={option.is_correct}
                            onChange={(e) => setOptionCorrect(index, e.target.checked)}
                            aria-label={`Mark option ${index + 1} as correct`}
                          />
                          <input
                            className="input option-row__text"
                            value={option.option_text}
                            onChange={(e) => setOptionText(index, e.target.value)}
                            placeholder={`Option ${index + 1}`}
                            required
                          />
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() => removeOption(index)}
                            disabled={activityForm.options.length <= 2}
                            aria-label={`Remove option ${index + 1}`}
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                    <button type="button" className="btn btn--secondary btn--sm" onClick={addOption}>
                      + Add option
                    </button>
                  </div>
                ) : (
                  <div className="field field--full">
                    <label htmlFor="activity_correct_answers" className="label">Accepted answers (one per line)</label>
                    <textarea
                      id="activity_correct_answers"
                      className="textarea"
                      rows="3"
                      value={activityForm.correct_answers_text}
                      onChange={(e) => setActivityField('correct_answers_text', e.target.value)}
                      placeholder={'compound interest\ncompounding'}
                      required
                    />
                    <span className="field__hint">Matching is case- and whitespace-insensitive.</span>
                  </div>
                )}
                <div className="field field--actions">
                  <button type="submit" className="btn btn--primary">
                    {editingActivityId ? 'Save activity' : 'Add activity'}
                  </button>
                  {editingActivityId && (
                    <button type="button" className="btn btn--ghost" onClick={clearActivityForm}>
                      Cancel edit
                    </button>
                  )}
                </div>
              </form>

              {activities.length > 0 ? (
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Title</th>
                        <th>Type</th>
                        <th>Order</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activities.map((activity) => (
                        <tr key={activity.activity_id}>
                          <td>{activity.title}</td>
                          <td>{activity.activity_type}</td>
                          <td>{activity.order_index}</td>
                          <td>
                            <div className="row-actions">
                              <button type="button" className="btn btn--secondary btn--sm" onClick={() => handleActivityEdit(activity)}>
                                Edit
                              </button>
                              <button type="button" className="btn btn--danger btn--sm" onClick={() => handleActivityDelete(activity.activity_id)}>
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="muted">No interactive activities yet.</p>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
