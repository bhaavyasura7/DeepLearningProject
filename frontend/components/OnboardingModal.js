import React, { useState } from 'react';
import { Sparkles, Check, ArrowRight } from 'lucide-react';

const GENRE_CHOICES = [
  'Action', 'Adventure', 'Animation', 'Comedy', 'Crime',
  'Documentary', 'Drama', 'Fantasy', 'Horror', 'Mystery',
  'Romance', 'Sci-Fi', 'Thriller', 'Western'
];

export default function OnboardingModal({ onComplete, isSubmitting }) {
  const [selectedGenres, setSelectedGenres] = useState(['Sci-Fi', 'Action']);

  const toggleGenre = (genre) => {
    if (selectedGenres.includes(genre)) {
      setSelectedGenres(selectedGenres.filter(g => g !== genre));
    } else {
      setSelectedGenres([...selectedGenres, genre]);
    }
  };

  const handleFinish = () => {
    onComplete(selectedGenres);
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: 'rgba(5, 7, 12, 0.85)',
      backdropFilter: 'blur(16px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="glass-panel" style={{
        maxWidth: '560px',
        width: '100%',
        padding: '36px',
        border: '1px solid rgba(99, 102, 241, 0.35)',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.9), 0 0 35px -5px rgba(99, 102, 241, 0.2)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px auto',
            boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)'
          }}>
            <Sparkles size={28} color="#fff" />
          </div>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', marginBottom: '8px' }}>
            Welcome to AuraRec
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.92rem', lineHeight: 1.5 }}>
            Our agent monitors your evolving movie tastes in the background. Pick your favorite genres to seed your initial preference memory.
          </p>
        </div>

        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#cbd5e1', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Select Preferred Genres (Pick at least 2)
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {GENRE_CHOICES.map((genre) => {
              const active = selectedGenres.includes(genre);
              return (
                <button
                  key={genre}
                  id={`onboard-genre-${genre.toLowerCase()}`}
                  onClick={() => toggleGenre(genre)}
                  style={{
                    background: active ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.4), rgba(6, 182, 212, 0.3))' : 'rgba(255, 255, 255, 0.04)',
                    color: active ? '#fff' : '#94a3b8',
                    border: active ? '1px solid #6366f1' : '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '9999px',
                    padding: '8px 16px',
                    fontSize: '0.85rem',
                    fontWeight: active ? 600 : 500,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.2s ease',
                    boxShadow: active ? '0 0 15px rgba(99, 102, 241, 0.3)' : 'none'
                  }}
                >
                  {active && <Check size={14} color="#67e8f9" />}
                  {genre}
                </button>
              );
            })}
          </div>
        </div>

        <button
          id="btn-complete-onboarding"
          onClick={handleFinish}
          disabled={selectedGenres.length < 1 || isSubmitting}
          className="btn-primary"
          style={{ width: '100%', justifyContent: 'center', padding: '14px', fontSize: '1rem', opacity: selectedGenres.length < 1 ? 0.5 : 1 }}
        >
          {isSubmitting ? 'Initializing Agent Memory...' : (
            <>
              Launch Recommendation Engine <ArrowRight size={18} />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
