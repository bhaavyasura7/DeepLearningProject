import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import RecommendationCard from '../components/RecommendationCard';
import CatalogueCard from '../components/CatalogueCard';
import OnboardingModal from '../components/OnboardingModal';
import { api } from '../utils/api';
import {
  Sparkles,
  RefreshCw,
  Film,
  Sliders,
  BarChart3,
  Search,
  Filter,
  AlertTriangle,
  RotateCcw,
  CheckCircle,
  Clock,
  Zap,
} from 'lucide-react';

export default function Home() {
  // Auth state
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register'
  const [emailInput, setEmailInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [authError, setAuthError] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);

  // App UI state
  const [currentTab, setCurrentTab] = useState('recommendations');
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingSubmitting, setOnboardingSubmitting] = useState(false);

  // Data states
  const [recommendations, setRecommendations] = useState(null);
  const [recLoading, setRecLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [movies, setMovies] = useState([]);
  const [genres, setGenres] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGenre, setSelectedGenre] = useState('');
  const [moviePage, setMoviePage] = useState(1);
  const [totalMovies, setTotalMovies] = useState(0);

  const [preferences, setPreferences] = useState(null);
  const [settings, setSettings] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [statusMessage, setStatusMessage] = useState(null);

  // Check existing session
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      loadUserProfile();
    }
  }, []);

  const loadUserProfile = async () => {
    try {
      const u = await api.getMe();
      setUser(u);
      loadDashboardData();
    } catch (err) {
      console.error('Session expired', err);
      api.logout();
      setUser(null);
    }
  };

  const loadDashboardData = async () => {
    loadRecommendations();
    loadPreferences();
    loadSettings();
    loadNotifications();
    loadMoviesData(1, '', '');
    loadGenres();
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError(null);
    setAuthLoading(true);
    try {
      if (authMode === 'register') {
        await api.register(emailInput, passwordInput);
        await api.login(emailInput, passwordInput);
        const me = await api.getMe();
        setUser(me);
        setShowOnboarding(true);
      } else {
        await api.login(emailInput, passwordInput);
        const me = await api.getMe();
        setUser(me);
        loadDashboardData();
      }
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    api.logout();
    setUser(null);
    setRecommendations(null);
  };

  // Recommendations
  const loadRecommendations = async () => {
    setRecLoading(true);
    try {
      const data = await api.getRecommendations();
      setRecommendations(data);
    } catch (err) {
      console.error('Error fetching recommendations', err);
    } finally {
      setRecLoading(false);
    }
  };

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    try {
      await api.refreshRecommendations('user_manual_request');
      showBanner('Recommendation refresh queued in background...');
      // Poll or reload in 1.5 seconds to simulate background worker
      setTimeout(async () => {
        await loadRecommendations();
        await loadNotifications();
        setIsRefreshing(false);
      }, 1500);
    } catch (err) {
      console.error(err);
      setIsRefreshing(false);
    }
  };

  const handleRecFeedback = async (recItemId, feedbackType) => {
    try {
      await api.submitFeedback(recItemId, feedbackType);
      // Update locally
      if (recommendations) {
        const updatedItems = recommendations.items.map((it) =>
          it.id === recItemId ? { ...it, feedback_status: feedbackType } : it
        );
        setRecommendations({ ...recommendations, items: updatedItems });
      }
      showBanner(`Feedback recorded (${feedbackType})! Preference memory updated.`);
    } catch (err) {
      console.error('Feedback error', err);
    }
  };

  // Catalogue
  const loadMoviesData = async (page = 1, search = '', genre = '') => {
    try {
      const data = await api.getMovies({ page, page_size: 16, search, genre });
      setMovies(data.items);
      setTotalMovies(data.total);
      setMoviePage(page);
    } catch (err) {
      console.error(err);
    }
  };

  const loadGenres = async () => {
    try {
      const list = await api.getGenres();
      setGenres(list);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadMoviesData(1, searchQuery, selectedGenre);
  };

  const handleGenreFilter = (genre) => {
    const nextGenre = selectedGenre === genre ? '' : genre;
    setSelectedGenre(nextGenre);
    loadMoviesData(1, searchQuery, nextGenre);
  };

  const handleRecordRating = async (movieId, stars) => {
    try {
      await api.recordInteraction(movieId, 'rating', stars);
      showBanner(`Recorded ${stars}★ rating! Background preference worker triggered.`);
      loadPreferences();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRecordAction = async (movieId, actionType) => {
    try {
      await api.recordInteraction(movieId, actionType);
      showBanner(`Marked as ${actionType}. Dynamic preferences updated.`);
      loadPreferences();
    } catch (err) {
      console.error(err);
    }
  };

  // Preferences & Settings
  const loadPreferences = async () => {
    try {
      const data = await api.getPreferences();
      setPreferences(data);
    } catch (err) {
      console.error(err);
    }
  };

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setSettings(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleRecommendations = async () => {
    if (!settings) return;
    try {
      const nextVal = !settings.recommendations_enabled;
      const updated = await api.updateSettings({ recommendations_enabled: nextVal });
      setSettings(updated);
      showBanner(`Proactive recommendations ${nextVal ? 'resumed' : 'paused'}.`);
    } catch (err) {
      console.error(err);
    }
  };

  const handleResetPreferences = async () => {
    if (!confirm('Are you sure you want to reset your preference profile? Your taste history will be cleared.')) return;
    try {
      await api.resetPreferences();
      showBanner('Derived preference profile reset successfully.');
      loadPreferences();
      loadRecommendations();
    } catch (err) {
      console.error(err);
    }
  };

  // Notifications
  const loadNotifications = async () => {
    try {
      const data = await api.getNotifications();
      setNotifications(data.items);
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkNotificationRead = async (notifId) => {
    try {
      await api.markNotificationRead(notifId);
      setNotifications(
        notifications.map((n) => (n.id === notifId ? { ...n, status: 'read' } : n))
      );
    } catch (err) {
      console.error(err);
    }
  };

  // Onboarding completion
  const handleOnboardingComplete = async (chosenGenres) => {
    setOnboardingSubmitting(true);
    try {
      // Find candidate movies matching these genres to seed initial positive signals
      const searchRes = await api.getMovies({ page_size: 4, genre: chosenGenres[0] });
      for (const m of searchRes.items.slice(0, 3)) {
        await api.recordInteraction(m.id, 'like');
      }
      setShowOnboarding(false);
      showBanner('Onboarding complete! Initial preference memory established.');
      loadDashboardData();
    } catch (err) {
      console.error(err);
      setShowOnboarding(false);
    } finally {
      setOnboardingSubmitting(false);
    }
  };

  const showBanner = (msg) => {
    setStatusMessage(msg);
    setTimeout(() => setStatusMessage(null), 4000);
  };

  // Auth Screen if not logged in
  if (!user) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
        <div className="glass-panel" style={{ maxWidth: '440px', width: '100%', padding: '40px', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <div style={{
              background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
              width: '60px',
              height: '60px',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto',
              boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)'
            }}>
              <Sparkles size={30} color="#fff" />
            </div>
            <h1 style={{ fontSize: '1.85rem', fontWeight: 800, color: '#f8fafc', marginBottom: '6px' }}>
              AuraRec
            </h1>
            <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
              Proactive AI Movie Recommendations with Dynamic Taste Memory
            </p>
          </div>

          {authError && (
            <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', color: '#fda4af', padding: '12px', borderRadius: '8px', fontSize: '0.85rem', marginBottom: '20px' }}>
              {authError}
            </div>
          )}

          <form onSubmit={handleAuthSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '6px' }}>
                Email Address
              </label>
              <input
                id="input-auth-email"
                type="email"
                required
                className="input-field"
                placeholder="viewer@cinema.com"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '6px' }}>
                Password
              </label>
              <input
                id="input-auth-password"
                type="password"
                required
                className="input-field"
                placeholder="••••••••"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
              />
            </div>

            <button
              id="btn-auth-submit"
              type="submit"
              disabled={authLoading}
              className="btn-primary"
              style={{ width: '100%', justifyContent: 'center', padding: '12px', marginTop: '8px' }}
            >
              {authLoading ? 'Connecting...' : authMode === 'login' ? 'Sign In to Dashboard' : 'Create Free Account'}
            </button>
          </form>

          <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '0.85rem', color: '#94a3b8' }}>
            {authMode === 'login' ? (
              <>
                New viewer?{' '}
                <button
                  id="btn-switch-to-register"
                  onClick={() => setAuthMode('register')}
                  style={{ background: 'transparent', border: 'none', color: '#818cf8', fontWeight: 600, cursor: 'pointer' }}
                >
                  Create an account
                </button>
              </>
            ) : (
              <>
                Already registered?{' '}
                <button
                  id="btn-switch-to-login"
                  onClick={() => setAuthMode('login')}
                  style={{ background: 'transparent', border: 'none', color: '#818cf8', fontWeight: 600, cursor: 'pointer' }}
                >
                  Sign in
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Logged In Dashboard View
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        user={user}
        onLogout={handleLogout}
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        notifications={notifications}
        onMarkNotificationRead={handleMarkNotificationRead}
        isRefreshing={isRefreshing}
      />

      {/* Floating Status Notification Toast */}
      {statusMessage && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          background: '#0f172a',
          border: '1px solid #6366f1',
          color: '#f8fafc',
          padding: '12px 20px',
          borderRadius: '12px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.8), 0 0 15px rgba(99,102,241,0.4)',
          zIndex: 999,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '0.88rem',
          fontWeight: 600,
          animation: 'pulseGlow 2s infinite'
        }}>
          <Zap size={18} color="#67e8f9" />
          {statusMessage}
        </div>
      )}

      {/* Onboarding Modal */}
      {showOnboarding && (
        <OnboardingModal
          onComplete={handleOnboardingComplete}
          isSubmitting={onboardingSubmitting}
        />
      )}

      {/* Main Content Area */}
      <main style={{ maxWidth: '1280px', margin: '0 auto', width: '100%', padding: '32px 24px', flex: 1 }}>
        
        {/* TAB 1: RECOMMENDATIONS */}
        {currentTab === 'recommendations' && (
          <div>
            {/* Header with Proactive Agent metadata */}
            <div className="glass-panel" style={{ padding: '24px 30px', marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                  <h1 style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f8fafc' }}>
                    Proactive Recommendations
                  </h1>
                  <span className="badge badge-indigo">
                    Profile v{recommendations?.profile_version || 1}
                  </span>
                </div>
                <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                  Generated automatically by the background T-PRA agent using dynamic time-decayed preference memory.
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ textAlign: 'right', marginRight: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>Algorithm</div>
                  <div style={{ fontSize: '0.85rem', color: '#a5b4fc', fontWeight: 700 }}>
                    {recommendations?.algorithm_version || 'v1.0-dynamic-memory-t-pra'}
                  </div>
                </div>

                <button
                  id="btn-refresh-recommendations"
                  onClick={handleManualRefresh}
                  disabled={isRefreshing}
                  className="btn-primary"
                >
                  <RefreshCw size={16} className={isRefreshing ? 'pulse-active' : ''} />
                  {isRefreshing ? 'Agent Synthesizing...' : 'Request Proactive Refresh'}
                </button>
              </div>
            </div>

            {/* Recommendation Grid */}
            {recLoading ? (
              <div style={{ textAlign: 'center', padding: '60px 0', color: '#94a3b8' }}>
                <Sparkles size={36} color="#6366f1" className="pulse-active" style={{ margin: '0 auto 16px auto' }} />
                <h3>Synthesizing personalized movie batch...</h3>
              </div>
            ) : recommendations?.items?.length > 0 ? (
              <div className="movie-grid">
                {recommendations.items.map((item) => (
                  <RecommendationCard
                    key={item.id}
                    item={item}
                    onFeedback={handleRecFeedback}
                  />
                ))}
              </div>
            ) : (
              <div className="glass-panel" style={{ padding: '60px', textAlign: 'center', color: '#94a3b8' }}>
                <h3>No recommendations generated yet.</h3>
                <p style={{ marginTop: '8px', fontSize: '0.9rem' }}>
                  Rate a few movies from the Catalogue to activate your preference profile!
                </p>
                <button
                  onClick={() => setCurrentTab('catalogue')}
                  className="btn-primary"
                  style={{ marginTop: '20px' }}
                >
                  Browse Movie Catalogue
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: MOVIE CATALOGUE */}
        {currentTab === 'catalogue' && (
          <div>
            <div style={{ marginBottom: '28px' }}>
              <h1 style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f8fafc', marginBottom: '8px' }}>
                Movie Catalogue ({totalMovies} Titles)
              </h1>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                Rate movies or record your reactions. Every interaction updates your dynamic memory profile in the background.
              </p>
            </div>

            {/* Search & Genre Filters */}
            <div className="glass-panel" style={{ padding: '20px', marginBottom: '28px' }}>
              <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
                <div style={{ flex: 1, position: 'relative' }}>
                  <Search size={18} color="#64748b" style={{ position: 'absolute', left: '14px', top: '14px' }} />
                  <input
                    id="input-movie-search"
                    type="text"
                    className="input-field"
                    placeholder="Search by title (e.g. Inception, Toy Story, Pulp Fiction)..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{ paddingLeft: '44px' }}
                  />
                </div>
                <button id="btn-movie-search" type="submit" className="btn-primary">
                  Search
                </button>
              </form>

              {/* Genre filter tags */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {genres.slice(0, 15).map((g) => {
                  const active = selectedGenre === g;
                  return (
                    <button
                      key={g}
                      id={`genre-filter-${g.toLowerCase()}`}
                      onClick={() => handleGenreFilter(g)}
                      style={{
                        background: active ? '#6366f1' : 'rgba(255, 255, 255, 0.05)',
                        color: active ? '#fff' : '#cbd5e1',
                        border: active ? '1px solid #818cf8' : '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '9999px',
                        padding: '5px 12px',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {g}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Movies Grid */}
            <div className="movie-grid">
              {movies.map((m) => (
                <CatalogueCard
                  key={m.id}
                  movie={m}
                  onRate={handleRecordRating}
                  onAction={handleRecordAction}
                />
              ))}
            </div>

            {/* Pagination Controls */}
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '14px', marginTop: '36px' }}>
              <button
                id="btn-prev-page"
                disabled={moviePage <= 1}
                onClick={() => loadMoviesData(moviePage - 1, searchQuery, selectedGenre)}
                className="btn-secondary"
              >
                Previous
              </button>
              <span style={{ fontSize: '0.9rem', color: '#94a3b8', fontWeight: 600 }}>
                Page {moviePage}
              </span>
              <button
                id="btn-next-page"
                onClick={() => loadMoviesData(moviePage + 1, searchQuery, selectedGenre)}
                className="btn-secondary"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* TAB 3: DYNAMIC MEMORY & TASTE CONTROLS */}
        {currentTab === 'preferences' && (
          <div>
            <div style={{ marginBottom: '28px' }}>
              <h1 style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f8fafc', marginBottom: '8px' }}>
                Dynamic User Preference Memory
              </h1>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                Inspect your short-term (time-decayed) and long-term taste vectors. You have full transparency and control to adjust or reset your preference profile.
              </p>
            </div>

            {/* Overview Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginBottom: '32px' }}>
              <div className="glass-panel" style={{ padding: '20px' }}>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>Memory Version</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#6366f1', marginTop: '4px' }}>
                  v{preferences?.profile_version || 1}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Monotonically updating</div>
              </div>

              <div className="glass-panel" style={{ padding: '20px' }}>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>Total Interactions</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#10b981', marginTop: '4px' }}>
                  {preferences?.total_interactions_count || 0}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Ratings, likes & watched items</div>
              </div>

              <div className="glass-panel" style={{ padding: '20px' }}>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>Decay Model</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#06b6d4', marginTop: '4px' }}>
                  λ = 0.05
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Half-life ≈ 14 days</div>
              </div>
            </div>

            {/* Two-tier Profile Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px', marginBottom: '36px' }}>
              
              {/* Short-Term Memory */}
              <div className="glass-panel" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                  <Zap size={20} color="#06b6d4" />
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Short-Term Memory (Recency Weighted)</h3>
                </div>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '18px' }}>
                  Emphasizes recent shifts in interest through exponential time decay: <code>w = s · exp(-λ · Δt)</code>.
                </p>

                {preferences?.short_term_preferences && Object.keys(preferences.short_term_preferences).length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {Object.entries(preferences.short_term_preferences).slice(0, 8).map(([genre, score]) => (
                      <div key={genre}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 600 }}>{genre}</span>
                          <span style={{ color: score >= 0 ? '#10b981' : '#f43f5e', fontWeight: 700 }}>
                            {score >= 0 ? `+${score}` : score}
                          </span>
                        </div>
                        <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${Math.min(100, Math.max(5, (score + 2) * 25))}%`,
                            height: '100%',
                            background: score >= 0 ? 'linear-gradient(90deg, #06b6d4, #10b981)' : '#f43f5e',
                            borderRadius: '3px'
                          }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No recent interactions recorded.</div>
                )}
              </div>

              {/* Long-Term Memory */}
              <div className="glass-panel" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                  <Clock size={20} color="#a855f7" />
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Long-Term Taste Anchors (Cumulative)</h3>
                </div>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '18px' }}>
                  Stable historical profile preserving your foundational tastes over your lifetime.
                </p>

                {preferences?.long_term_preferences && Object.keys(preferences.long_term_preferences).length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {Object.entries(preferences.long_term_preferences).slice(0, 8).map(([genre, score]) => (
                      <div key={genre}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 600 }}>{genre}</span>
                          <span style={{ color: score >= 0 ? '#a855f7' : '#f43f5e', fontWeight: 700 }}>
                            {score >= 0 ? `+${score}` : score}
                          </span>
                        </div>
                        <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${Math.min(100, Math.max(5, (score + 2) * 25))}%`,
                            height: '100%',
                            background: score >= 0 ? 'linear-gradient(90deg, #6366f1, #a855f7)' : '#f43f5e',
                            borderRadius: '3px'
                          }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No historical taste anchors yet.</div>
                )}
              </div>
            </div>

            {/* User Controls & Privacy Reset */}
            <div className="glass-panel" style={{ padding: '28px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '16px' }}>
                Recommendation & Privacy Controls
              </h3>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 0', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>Pause Proactive Recommendations</div>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Temporarily stop the background agent from calculating new batches.</div>
                </div>
                <button
                  id="btn-toggle-recommendations"
                  onClick={handleToggleRecommendations}
                  className="btn-secondary"
                  style={{
                    color: settings?.recommendations_enabled ? '#fda4af' : '#6ee7b7',
                    borderColor: settings?.recommendations_enabled ? 'rgba(244,63,94,0.3)' : 'rgba(16,185,129,0.3)'
                  }}
                >
                  {settings?.recommendations_enabled ? 'Pause Recommendations' : 'Resume Recommendations'}
                </button>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '16px' }}>
                <div>
                  <div style={{ fontWeight: 600, color: '#fda4af' }}>Reset Preference Profile</div>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                    Removes all derived taste vectors while retaining your account history.
                  </div>
                </div>
                <button
                  id="btn-reset-preferences"
                  onClick={handleResetPreferences}
                  className="btn-outline-danger"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <RotateCcw size={15} /> Reset Derived Profile
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: RESEARCH EVALUATION DASHBOARD */}
        {currentTab === 'research' && (
          <div>
            <div style={{ marginBottom: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <h1 style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f8fafc' }}>
                  Research Benchmark & Paper Replication
                </h1>
                <span className="badge badge-emerald">Reproducible</span>
              </div>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                Evaluation on MovieLens (ml-latest-small) across 610 users using a strict 75/25 time-aware chronological split (zero future leakage).
              </p>
            </div>

            {/* Baseline Comparison Card */}
            <div className="glass-panel" style={{ padding: '24px', marginBottom: '32px' }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '16px' }}>
                Empirical Baseline Comparison
              </h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8' }}>
                      <th style={{ padding: '12px' }}>Model</th>
                      <th style={{ padding: '12px' }}>Precision@5</th>
                      <th style={{ padding: '12px' }}>Precision@10</th>
                      <th style={{ padding: '12px' }}>Recall@10</th>
                      <th style={{ padding: '12px' }}>NDCG@10</th>
                      <th style={{ padding: '12px' }}>Coverage</th>
                      <th style={{ padding: '12px' }}>Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '12px', fontWeight: 600 }}>Popularity Baseline</td>
                      <td style={{ padding: '12px' }}>0.1005</td>
                      <td style={{ padding: '12px' }}>0.0848</td>
                      <td style={{ padding: '12px' }}>0.0513</td>
                      <td style={{ padding: '12px' }}>0.1023</td>
                      <td style={{ padding: '12px', color: '#f43f5e' }}>0.86%</td>
                      <td style={{ padding: '12px' }}>0.11ms</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '12px', fontWeight: 600 }}>Content-Based (Static)</td>
                      <td style={{ padding: '12px' }}>0.0087</td>
                      <td style={{ padding: '12px' }}>0.0062</td>
                      <td style={{ padding: '12px' }}>0.0035</td>
                      <td style={{ padding: '12px' }}>0.0071</td>
                      <td style={{ padding: '12px', color: '#10b981' }}>7.15%</td>
                      <td style={{ padding: '12px' }}>4.20ms</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '12px', fontWeight: 600 }}>T-PRA Base (Static Memory)</td>
                      <td style={{ padding: '12px' }}>0.0087</td>
                      <td style={{ padding: '12px' }}>0.0062</td>
                      <td style={{ padding: '12px' }}>0.0035</td>
                      <td style={{ padding: '12px' }}>0.0071</td>
                      <td style={{ padding: '12px', color: '#10b981' }}>7.15%</td>
                      <td style={{ padding: '12px' }}>4.25ms</td>
                    </tr>
                    <tr style={{ background: 'rgba(99, 102, 241, 0.12)', borderBottom: '1px solid rgba(99, 102, 241, 0.3)' }}>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#a5b4fc' }}>
                        ★ T-PRA Dynamic Memory (Proposed)
                      </td>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#a5b4fc' }}>0.0090</td>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#a5b4fc' }}>0.0065</td>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#a5b4fc' }}>0.0039</td>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#a5b4fc' }}>0.0075</td>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#67e8f9' }}>7.30%</td>
                      <td style={{ padding: '12px', fontWeight: 700, color: '#a5b4fc' }}>4.33ms</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Research Insights Summary */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
              <div className="glass-panel" style={{ padding: '20px' }}>
                <h4 style={{ color: '#06b6d4', marginBottom: '8px', fontSize: '1rem', fontWeight: 700 }}>
                  1. Mitigation of Echo Chambers
                </h4>
                <p style={{ color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.5 }}>
                  While the popularity baseline achieves higher recall by recommending the most frequent global movies (like Star Wars or Forrest Gump), its catalog coverage is critically restricted (0.86%). The dynamic T-PRA agent achieves 8.5x greater catalog coverage (7.30%).
                </p>
              </div>

              <div className="glass-panel" style={{ padding: '20px' }}>
                <h4 style={{ color: '#10b981', marginBottom: '8px', fontSize: '1rem', fontWeight: 700 }}>
                  2. Recency Adaptation Gain
                </h4>
                <p style={{ color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.5 }}>
                  By modeling short-term interest drift with time decay (λ = 0.05) and combining it with cumulative long-term signals, the proposed extension achieves higher NDCG@10 (0.0075 vs 0.0071) and Recall@10 (0.0039 vs 0.0035) over static memory.
                </p>
              </div>

              <div className="glass-panel" style={{ padding: '20px' }}>
                <h4 style={{ color: '#a855f7', marginBottom: '8px', fontSize: '1rem', fontWeight: 700 }}>
                  3. Production Feasibility
                </h4>
                <p style={{ color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.5 }}>
                  With an average scoring latency of 4.3ms, the preference memory model readily scales to real-time background queues and async event streams without blocking the web frontend.
                </p>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
