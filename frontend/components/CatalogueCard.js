import React, { useState } from 'react';
import { Star, ThumbsUp, ThumbsDown, Eye, Check } from 'lucide-react';

export default function CatalogueCard({ movie, onRate, onAction }) {
  const genres = (movie.genres || '').split('|').filter(Boolean);
  const [rating, setRating] = useState(null);
  const [savedAction, setSavedAction] = useState(null);

  const handleRate = (val) => {
    setRating(val);
    setSavedAction(`Rated ${val}★`);
    onRate(movie.id, val);
  };

  const handleAction = (type) => {
    setSavedAction(type);
    onAction(movie.id, type);
  };

  return (
    <div className="movie-card" id={`cat-card-${movie.id}`}>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          {movie.release_year ? (
            <span className="badge badge-indigo">{movie.release_year}</span>
          ) : (
            <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: '#94a3b8' }}>Movie</span>
          )}
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>ID: #{movie.movielens_id}</span>
        </div>

        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '8px', color: '#f8fafc', lineHeight: 1.3 }}>
          {movie.title}
        </h3>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginBottom: '16px' }}>
          {genres.map((g, idx) => (
            <span key={idx} style={{
              fontSize: '0.7rem',
              background: 'rgba(255, 255, 255, 0.04)',
              color: '#cbd5e1',
              padding: '2px 8px',
              borderRadius: '6px',
              border: '1px solid rgba(255, 255, 255, 0.06)'
            }}>
              {g}
            </span>
          ))}
        </div>
      </div>

      <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '12px' }}>
        {savedAction ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981', fontSize: '0.8rem', fontWeight: 600 }}>
            <Check size={15} />
            Recorded: <span style={{ textTransform: 'capitalize' }}>{savedAction}</span>
          </div>
        ) : (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Rate this film:</span>
              <div style={{ display: 'flex', gap: '3px' }}>
                {[1, 2, 3, 4, 5].map((val) => (
                  <button
                    key={val}
                    id={`rate-${movie.id}-${val}`}
                    onClick={() => handleRate(val)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      padding: '2px',
                      color: rating >= val ? '#f59e0b' : 'rgba(255, 255, 255, 0.2)'
                    }}
                  >
                    <Star size={16} fill={rating >= val ? '#f59e0b' : 'transparent'} />
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
              <button
                id={`btn-cat-like-${movie.id}`}
                onClick={() => handleAction('like')}
                title="Like"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '6px',
                  padding: '6px 10px',
                  color: '#94a3b8',
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  cursor: 'pointer'
                }}
              >
                <ThumbsUp size={13} /> Like
              </button>

              <button
                id={`btn-cat-dislike-${movie.id}`}
                onClick={() => handleAction('dislike')}
                title="Dislike"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '6px',
                  padding: '6px 10px',
                  color: '#94a3b8',
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  cursor: 'pointer'
                }}
              >
                <ThumbsDown size={13} /> Dislike
              </button>

              <button
                id={`btn-cat-watched-${movie.id}`}
                onClick={() => handleAction('watched')}
                title="Watched"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '6px',
                  padding: '6px 10px',
                  color: '#94a3b8',
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  cursor: 'pointer'
                }}
              >
                <Eye size={13} /> Watched
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
