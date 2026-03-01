const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    credentials: 'include',
    ...options,
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  // 204 No Content has no body
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  // Auth
  getMe: () => request('/auth/me'),
  logout: () => request('/auth/local-logout', { method: 'POST' }),

  // Classes
  listClasses: () => request('/classes'),
  createClass: (body) => request('/classes', { method: 'POST', body: JSON.stringify(body) }),
  getClass: (id) => request(`/classes/${id}`),
  addMember: (classId, body) =>
    request(`/classes/${classId}/members`, { method: 'POST', body: JSON.stringify(body) }),
  removeMember: (classId, userId) =>
    request(`/classes/${classId}/members/${userId}`, { method: 'DELETE' }),

  // Assignments
  listAssignments: (classId) => request(`/classes/${classId}/assignments`),
  createAssignment: (classId, body) =>
    request(`/classes/${classId}/assignments`, { method: 'POST', body: JSON.stringify(body) }),
  getAssignment: (classId, assignmentId) =>
    request(`/classes/${classId}/assignments/${assignmentId}`),
  updateAssignment: (classId, assignmentId, body) =>
    request(`/classes/${classId}/assignments/${assignmentId}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  deleteAssignment: (classId, assignmentId) =>
    request(`/classes/${classId}/assignments/${assignmentId}`, { method: 'DELETE' }),

  // Submissions
  listSubmissions: (classId, assignmentId) =>
    request(`/classes/${classId}/assignments/${assignmentId}/submissions`),
  createSubmission: (classId, assignmentId, body) =>
    request(`/classes/${classId}/assignments/${assignmentId}/submissions`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  getSubmission: (classId, assignmentId, submissionId) =>
    request(`/classes/${classId}/assignments/${assignmentId}/submissions/${submissionId}`),
}
