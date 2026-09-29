const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getAuthHeader() {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}/api/v1${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });
  
  if (response.status === 204) return null;
  
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const errorMsg = data.detail || `Request failed with status ${response.status}`;
    throw new Error(errorMsg);
  }
  return data;
}

export const api = {
  // Auth
  register: (email, password) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  login: async (email, password) => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (data.access_token) {
      localStorage.setItem('token', data.access_token);
    }
    return data;
  },
  logout: () => {
    localStorage.removeItem('token');
  },
  getMe: () => request('/me'),

  // Movies
  getMovies: (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.set('search', params.search);
    if (params.genre) query.set('genre', params.genre);
    if (params.page) query.set('page', params.page);
    if (params.page_size) query.set('page_size', params.page_size);
    return request(`/movies?${query.toString()}`);
  },
  getMovie: (id) => request(`/movies/${id}`),
  getGenres: () => request('/movies/genres'),

  // Interactions
  recordInteraction: (movieId, type, rating = null, idempotencyKey = null) =>
    request('/interactions', {
      method: 'POST',
      body: JSON.stringify({
        movie_id: movieId,
        interaction_type: type,
        rating: rating,
        idempotency_key: idempotencyKey,
      }),
    }),
  getInteractions: (page = 1, pageSize = 20) =>
    request(`/interactions?page=${page}&page_size=${pageSize}`),
  deleteInteraction: (id) => request(`/interactions/${id}`, { method: 'DELETE' }),

  // Recommendations
  getRecommendations: () => request('/recommendations'),
  refreshRecommendations: (reason = 'manual_refresh') =>
    request('/recommendations/refresh', {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  submitFeedback: (recId, feedback) =>
    request(`/recommendations/${recId}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ feedback }),
    }),

  // Preferences
  getPreferences: () => request('/preferences'),
  resetPreferences: () => request('/preferences/reset', { method: 'POST' }),

  // Settings
  getSettings: () => request('/settings'),
  updateSettings: (settingsUpdate) =>
    request('/settings', {
      method: 'PATCH',
      body: JSON.stringify(settingsUpdate),
    }),

  // Notifications
  getNotifications: () => request('/notifications'),
  markNotificationRead: (id) =>
    request(`/notifications/${id}/read`, { method: 'POST' }),

  // Jobs
  getJobStatus: (jobId) => request(`/jobs/${jobId}`),
};
