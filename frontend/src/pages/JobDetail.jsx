import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Phone, Upload, Calendar, Users } from 'lucide-react';
import api from '../api/client';
import StatusBadge from '../components/StatusBadge';
import CSVUpload from '../components/CSVUpload';

function getScoreClass(score) {
  if (score >= 7) return 'score-high';
  if (score >= 5) return 'score-mid';
  return 'score-low';
}

export default function JobDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [uploadResult, setUploadResult] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isScreening, setIsScreening] = useState(false);
  const [screeningResult, setScreeningResult] = useState(null);

  useEffect(() => {
    loadJob();
    loadCandidates();
  }, [id]);

  async function loadJob() {
    try {
      const res = await api.get(`/jobs/${id}`);
      setJob(res.data);
    } catch (err) {
      console.error('Failed to load job:', err);
    }
  }

  async function loadCandidates() {
    try {
      const res = await api.get(`/jobs/${id}/candidates?sort_by=score`);
      setCandidates(res.data.candidates);
    } catch (err) {
      console.error('Failed to load candidates:', err);
    }
  }

  async function handleUpload(file) {
    setIsUploading(true);
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post(`/jobs/${id}/candidates/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadResult(res.data);
      loadCandidates();
      loadJob();
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadResult({ created: 0, errors: ['Upload failed. Please check your CSV format.'] });
    } finally {
      setIsUploading(false);
    }
  }

  async function handleStartScreening() {
    setIsScreening(true);
    setScreeningResult(null);
    try {
      const res = await api.post(`/jobs/${id}/start-screening`);
      setScreeningResult(res.data);
      loadCandidates();
    } catch (err) {
      console.error('Screening failed:', err);
      setScreeningResult({ message: 'Failed to start screening', calls_initiated: 0, errors: [err.message] });
    } finally {
      setIsScreening(false);
    }
  }

  async function handleSchedule(candidateId) {
    try {
      await api.post(`/candidates/${candidateId}/schedule`);
      loadCandidates();
    } catch (err) {
      console.error('Schedule failed:', err);
    }
  }

  if (!job) return <div className="page-container"><p>Loading...</p></div>;

  return (
    <div className="page-container fade-in">
      <Link to="/jobs" className="back-link">
        <ArrowLeft size={16} />
        Back to Jobs
      </Link>

      <div className="detail-header">
        <div className="detail-info">
          <div style={{ color: 'var(--accent-primary-hover)', fontSize: 'var(--font-sm)', fontWeight: 500, marginBottom: 'var(--space-1)' }}>
            {job.department || 'General'}
          </div>
          <h2>{job.title}</h2>
          <div className="detail-meta">
            <span><Users size={14} /> {job.candidate_count} candidates</span>
            <span>•</span>
            <span>{job.screened_count} screened</span>
          </div>
        </div>
        <div className="detail-actions">
          <button
            className="btn btn-primary btn-lg"
            onClick={handleStartScreening}
            disabled={isScreening || candidates.length === 0}
          >
            <Phone size={18} />
            {isScreening ? 'Starting Calls...' : 'Start Screening'}
          </button>
        </div>
      </div>

      {screeningResult && (
        <div className="card" style={{ marginBottom: 'var(--space-6)', borderColor: screeningResult.calls_initiated > 0 ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)' }}>
          <p style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{screeningResult.message}</p>
          {screeningResult.calls_initiated > 0 && (
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-sm)', marginTop: 'var(--space-2)' }}>
              {screeningResult.calls_initiated} call(s) initiated. Results will appear as candidates are screened.
            </p>
          )}
          {screeningResult.errors.length > 0 && (
            <ul style={{ color: 'var(--danger)', fontSize: 'var(--font-sm)', marginTop: 'var(--space-2)', paddingLeft: 'var(--space-5)' }}>
              {screeningResult.errors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
        </div>
      )}

      {job.description && (
        <div className="section">
          <div className="section-title">Job Description</div>
          <div className="card">
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
              {job.description}
            </p>
          </div>
        </div>
      )}

      <div className="section">
        <div className="section-title">
          <Upload size={20} />
          Upload Candidates
        </div>
        <CSVUpload onUpload={handleUpload} isUploading={isUploading} result={uploadResult} />
      </div>

      <div className="section">
        <div className="section-title">
          <Users size={20} />
          Candidates ({candidates.length})
        </div>

        {candidates.length === 0 ? (
          <div className="card empty-state">
            <Users size={48} />
            <h3>No candidates yet</h3>
            <p>Upload a CSV to add candidates</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Name</th>
                  <th>Phone</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c, i) => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600, color: 'var(--text-muted)' }}>{i + 1}</td>
                    <td>
                      <span
                        className="candidate-name"
                        style={{ cursor: 'pointer' }}
                        onClick={() => navigate(`/candidates/${c.id}`)}
                      >
                        {c.name}
                      </span>
                      {c.email && (
                        <div style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)', marginTop: 2 }}>
                          {c.email}
                        </div>
                      )}
                    </td>
                    <td>{c.phone}</td>
                    <td><StatusBadge status={c.status} /></td>
                    <td>
                      {c.overall_score != null ? (
                        <span className={`score ${getScoreClass(c.overall_score)}`}>
                          {c.overall_score.toFixed(1)}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => navigate(`/candidates/${c.id}`)}
                        >
                          View
                        </button>
                        {c.status === 'screened' && c.overall_score >= 7 && (
                          <button
                            className="btn btn-sm btn-success"
                            onClick={() => handleSchedule(c.id)}
                          >
                            <Calendar size={12} />
                            Schedule
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
