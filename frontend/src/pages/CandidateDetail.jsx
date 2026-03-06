import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Calendar, RefreshCw, Mail, Phone, FileText, BarChart3 } from 'lucide-react';
import api from '../api/client';
import StatusBadge from '../components/StatusBadge';
import ScoreRadar from '../components/ScoreRadar';

function getScoreClass(score) {
  if (score >= 7) return 'score-high';
  if (score >= 5) return 'score-mid';
  return 'score-low';
}

export default function CandidateDetail() {
  const { id } = useParams();
  const [candidate, setCandidate] = useState(null);
  const [rescoring, setRescoring] = useState(false);

  useEffect(() => {
    loadCandidate();
  }, [id]);

  async function loadCandidate() {
    try {
      const res = await api.get(`/candidates/${id}`);
      setCandidate(res.data);
    } catch (err) {
      console.error('Failed to load candidate:', err);
    }
  }

  async function handleRescore() {
    if (!candidate?.interview?.id) return;
    setRescoring(true);
    try {
      await api.post(`/interviews/${candidate.interview.id}/rescore`);
      loadCandidate();
    } catch (err) {
      console.error('Rescore failed:', err);
    } finally {
      setRescoring(false);
    }
  }

  async function handleSchedule() {
    try {
      await api.post(`/candidates/${id}/schedule`);
      loadCandidate();
    } catch (err) {
      console.error('Schedule failed:', err);
    }
  }

  if (!candidate) return <div className="page-container"><p>Loading...</p></div>;

  const { interview, score } = candidate;

  // Parse transcript into turns
  const transcriptTurns = [];
  if (interview?.transcript) {
    const lines = interview.transcript.split('\n');
    for (const line of lines) {
      const match = line.match(/^(ai|agent|assistant|candidate|user|human):\s*(.*)/i);
      if (match) {
        const role = ['ai', 'agent', 'assistant'].includes(match[1].toLowerCase()) ? 'ai' : 'candidate';
        transcriptTurns.push({ role, content: match[2] });
      } else if (line.trim()) {
        transcriptTurns.push({ role: 'candidate', content: line.trim() });
      }
    }
  }

  const scoreDimensions = score ? [
    { label: 'Communication', value: score.communication },
    { label: 'Experience', value: score.experience },
    { label: 'Motivation', value: score.motivation },
    { label: 'Availability', value: score.availability },
    { label: 'Cultural Fit', value: score.cultural_fit },
    { label: 'Role Fit', value: score.role_fit },
  ] : [];

  return (
    <div className="page-container fade-in">
      <Link to={`/jobs/${candidate.job_id}`} className="back-link">
        <ArrowLeft size={16} />
        Back to Job
      </Link>

      <div className="detail-header">
        <div className="detail-info">
          {candidate.job_title && (
            <div style={{ color: 'var(--accent-primary-hover)', fontSize: 'var(--font-sm)', fontWeight: 500, marginBottom: 'var(--space-1)' }}>
              {candidate.job_title}
            </div>
          )}
          <h2>{candidate.name}</h2>
          <div className="detail-meta">
            {candidate.email && <span><Mail size={14} /> {candidate.email}</span>}
            <span><Phone size={14} /> {candidate.phone}</span>
            <StatusBadge status={candidate.status} />
          </div>
        </div>
        <div className="detail-actions">
          {interview?.transcript && (
            <button
              className="btn btn-secondary"
              onClick={handleRescore}
              disabled={rescoring}
            >
              <RefreshCw size={16} className={rescoring ? 'spin' : ''} />
              {rescoring ? 'Rescoring...' : 'Re-score'}
            </button>
          )}
          {candidate.status === 'screened' && (
            <button className="btn btn-success" onClick={handleSchedule}>
              <Calendar size={16} />
              Schedule Interview
            </button>
          )}
        </div>
      </div>

      {/* Overall Score Banner */}
      {score && (
        <div className="card" style={{
          marginBottom: 'var(--space-6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(139,92,246,0.08))',
          borderColor: 'rgba(99,102,241,0.2)',
        }}>
          <div>
            <div style={{ fontSize: 'var(--font-sm)', color: 'var(--text-muted)', marginBottom: 'var(--space-1)' }}>
              Overall Score
            </div>
            <div style={{ fontSize: 'var(--font-4xl)', fontWeight: 800, letterSpacing: '-0.03em' }}
              className={getScoreClass(score.overall)}
            >
              {score.overall.toFixed(1)}
              <span style={{ fontSize: 'var(--font-lg)', color: 'var(--text-muted)', fontWeight: 400 }}>/10</span>
            </div>
          </div>
          {score.summary && (
            <div style={{ maxWidth: 500, color: 'var(--text-secondary)', fontSize: 'var(--font-sm)', lineHeight: 1.7 }}>
              {score.summary}
            </div>
          )}
        </div>
      )}

      {/* Score Breakdown */}
      {score && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-6)', marginBottom: 'var(--space-8)' }}>
          <div className="section">
            <div className="section-title">
              <BarChart3 size={20} />
              Score Radar
            </div>
            <div className="card">
              <ScoreRadar score={score} />
            </div>
          </div>

          <div className="section">
            <div className="section-title">
              <BarChart3 size={20} />
              Dimension Breakdown
            </div>
            <div className="score-grid">
              {scoreDimensions.map((dim) => (
                <div key={dim.label} className="score-item">
                  <div className="score-dimension">{dim.label}</div>
                  <div className={`score-value ${getScoreClass(dim.value)}`}>
                    {dim.value.toFixed(1)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Transcript */}
      {interview && (
        <div className="section">
          <div className="section-title">
            <FileText size={20} />
            Interview Transcript
          </div>

          {transcriptTurns.length > 0 ? (
            <div className="transcript-container">
              {transcriptTurns.map((turn, i) => (
                <div key={i} className="transcript-turn">
                  <span className={`turn-role ${turn.role}`}>
                    {turn.role === 'ai' ? 'Agent' : 'User'}
                  </span>
                  <span className="turn-content">{turn.content}</span>
                </div>
              ))}
            </div>
          ) : interview.transcript ? (
            <div className="transcript-container">
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                {interview.transcript}
              </p>
            </div>
          ) : (
            <div className="card empty-state">
              <FileText size={48} />
              <h3>Transcript pending</h3>
              <p>The transcript will appear once the call is completed</p>
            </div>
          )}
        </div>
      )}

      {!interview && (
        <div className="card empty-state">
          <Phone size={48} />
          <h3>Not yet screened</h3>
          <p>This candidate hasn't been called yet. Start screening from the job page.</p>
        </div>
      )}
    </div>
  );
}
