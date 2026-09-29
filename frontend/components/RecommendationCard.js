import React from 'react';
import { ThumbsUp, ThumbsDown, Eye, X, Sparkles, CheckCircle2 } from 'lucide-react';

export default function RecommendationCard({ item, onFeedback }) {
  const movie = item.movie || {};
  const genres = (movie.genres || '').split('|').filter(Boolean);
  const status = item.feedback_status;

  return (
    <div className="movie-card" id={`rec-card-${item.id}`}>
      <div>
        {/* Top Header: Rank & Score */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              background: 'linear-gradient(135deg, #6366f1, #a855f7)',
              color: '#fff',
              fontWeight: 800,
              fontSize: '0.85rem',
              padding: '2px 10px',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(99, 102, 241, 0.4)'
            }}>
              #{item.rank}
            </span>
            {movie.release_year && (
              <span className="badge badge-indigo">
                {movie.release_year}
              </span>
            )}
          </div>
          <div style={{ fontSize: '0.78rem', color: '#06b6d4', fontWeight: 700 }}>
            {Math.min(99, Math.max(70, Math.round(75 + item.score * 8)))}% Match
          </div>
        </div>

        {/* Title */}
        <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '8px', color: '#f8fafc', lineHeight: 1.3 }}>
          {movie.title || 'Untitled Movie'}
        </h3>

        {/* Genre Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '14px' }}>
          {genres.map((g, idx) => (
            <span key={idx} style={{
              fontSize: '0.72rem',
              background: 'rgba(255, 255, 255, 0.05)',
              color: '#cbd5e1',
              padding: '2px 8px',
              borderRadius: '6px',
              border: '1px solid rgba(255, 255, 255, 0.08)'
            }}>
              {g}
            </span>
          ))}
        </div>

        {/* Grounded Explanation Box */}
        <div style={{
          background: 'rgba(99, 102, 241, 0.08)',
          borderLeft: '3px solid #6366f1',
          padding: '10px 12px',
          borderRadius: '4px 8px 8px 4px',
          marginBottom: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 700, color: '#a5b4fc', marginBottom: '4px' }}>
            <Sparkles size={13} />
            Why recommended:
          </div>
          <p style={{ fontSize: '0.8rem', color: '#e2e8f0', lineHeight: 1.4 }}>
            {item.explanation}
          </p>
        </div>
      </div>

      {/* Footer / Feedback Controls */}
      <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '12px' }}>
        {status ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981', fontSize: '0.82rem', fontWeight: 600 }}>
            <CheckCircle2 size={16} />
            Feedback saved: <span style={{ textTransform: 'capitalize' }}>{status}</span>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b' }}>Provide feedback:</span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                id={`btn-like-${item.id}`}
                onClick={() => onFeedback(item.id, 'liked')}
                title="Like this recommendation"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '6px',
                  padding: '6px',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <ThumbsUp size={15} />
              </button>

              <button
                id={`btn-dislike-${item.id}`}
                onClick={() => onFeedback(item.id, 'disliked')}
                title="Dislike this recommendation"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '6px',
                  padding: '6px',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <ThumbsDown size={15} />
              </button>

              <button
                id={`btn-watched-${item.id}`}
                onClick={() => onFeedback(item.id, 'watched')}
                title="Already watched"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '6px',
                  padding: '6px',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <Eye size={15} />
              </button>

              <button
                id={`btn-dismiss-${item.id}`}
                onClick={() => onFeedback(item.id, 'dismissed')}
                title="Not interested"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '6px',
                  padding: '6px',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <X size={15} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
