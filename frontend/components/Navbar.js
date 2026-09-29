import React, { useState } from 'react';
import { Bell, Film, Sparkles, Sliders, BarChart3, LogOut, Check } from 'lucide-react';

export default function Navbar({
  user,
  onLogout,
  currentTab,
  setCurrentTab,
  notifications = [],
  onMarkNotificationRead,
  isRefreshing = false
}) {
  const [showNotifMenu, setShowNotifMenu] = useState(false);
  const unreadCount = notifications.filter(n => n.status === 'unread').length;

  return (
    <nav className="glass-nav" id="main-navigation">
      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }} onClick={() => setCurrentTab('recommendations')}>
          <div style={{
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 15px rgba(99, 102, 241, 0.4)'
          }}>
            <Sparkles size={22} color="#fff" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.25rem', letterSpacing: '-0.02em', background: 'linear-gradient(90deg, #fff, #cbd5e1)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              AuraRec
            </div>
            <div style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              T-PRA Proactive Agent
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255, 255, 255, 0.04)', padding: '4px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
            <button
              id="nav-tab-recs"
              onClick={() => setCurrentTab('recommendations')}
              style={{
                background: currentTab === 'recommendations' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                color: currentTab === 'recommendations' ? '#a5b4fc' : '#94a3b8',
                border: currentTab === 'recommendations' ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '0.88rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s ease'
              }}
            >
              <Sparkles size={16} />
              Recommendations
            </button>

            <button
              id="nav-tab-catalogue"
              onClick={() => setCurrentTab('catalogue')}
              style={{
                background: currentTab === 'catalogue' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                color: currentTab === 'catalogue' ? '#a5b4fc' : '#94a3b8',
                border: currentTab === 'catalogue' ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '0.88rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s ease'
              }}
            >
              <Film size={16} />
              Movie Catalogue
            </button>

            <button
              id="nav-tab-preferences"
              onClick={() => setCurrentTab('preferences')}
              style={{
                background: currentTab === 'preferences' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                color: currentTab === 'preferences' ? '#a5b4fc' : '#94a3b8',
                border: currentTab === 'preferences' ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '0.88rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s ease'
              }}
            >
              <Sliders size={16} />
              Memory & Taste
            </button>

            <button
              id="nav-tab-research"
              onClick={() => setCurrentTab('research')}
              style={{
                background: currentTab === 'research' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                color: currentTab === 'research' ? '#a5b4fc' : '#94a3b8',
                border: currentTab === 'research' ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '0.88rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s ease'
              }}
            >
              <BarChart3 size={16} />
              Research Evaluation
            </button>
          </div>
        )}

        {/* User profile & Notification Bell */}
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', position: 'relative' }}>
            
            {/* Background agent pulse badge */}
            <div className="badge badge-emerald pulse-active" style={{ fontSize: '0.72rem', display: 'flex', gap: '6px' }}>
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981' }} />
              {isRefreshing ? 'Agent Active' : 'Agent Proactive'}
            </div>

            {/* Notification Bell */}
            <div style={{ position: 'relative' }}>
              <button
                id="btn-notifications-toggle"
                onClick={() => setShowNotifMenu(!showNotifMenu)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '10px',
                  padding: '8px',
                  color: '#cbd5e1',
                  cursor: 'pointer',
                  position: 'relative'
                }}
              >
                <Bell size={18} />
                {unreadCount > 0 && (
                  <span style={{
                    position: 'absolute',
                    top: '-4px',
                    right: '-4px',
                    background: '#f43f5e',
                    color: '#fff',
                    borderRadius: '50%',
                    width: '18px',
                    height: '18px',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    {unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Popover */}
              {showNotifMenu && (
                <div style={{
                  position: 'absolute',
                  right: 0,
                  top: '46px',
                  width: '320px',
                  background: '#0d121f',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '14px',
                  boxShadow: '0 20px 40px rgba(0,0,0,0.8)',
                  padding: '16px',
                  zIndex: 200
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>Proactive Alerts</span>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{unreadCount} unread</span>
                  </div>

                  {notifications.length === 0 ? (
                    <div style={{ fontSize: '0.8rem', color: '#64748b', textAlign: 'center', padding: '16px 0' }}>
                      No new recommendations yet.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '240px', overflowY: 'auto' }}>
                      {notifications.map((n) => (
                        <div
                          key={n.id}
                          style={{
                            padding: '10px',
                            borderRadius: '8px',
                            background: n.status === 'unread' ? 'rgba(99, 102, 241, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                            border: '1px solid rgba(255, 255, 255, 0.06)',
                            fontSize: '0.8rem',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: 600, color: '#f1f5f9' }}>New Movie Batch Ready</div>
                            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Delivered automatically by background agent</div>
                          </div>
                          {n.status === 'unread' && (
                            <button
                              onClick={() => onMarkNotificationRead(n.id)}
                              title="Mark read"
                              style={{ background: 'transparent', border: 'none', color: '#6366f1', cursor: 'pointer' }}
                            >
                              <Check size={16} />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Logout button */}
            <button
              id="btn-logout"
              onClick={onLogout}
              className="btn-secondary"
              style={{ padding: '8px 12px' }}
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '10px' }}>
            <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Authentication required</span>
          </div>
        )}

      </div>
    </nav>
  );
}
