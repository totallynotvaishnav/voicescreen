import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Briefcase, Users, CheckCircle } from 'lucide-react';
import api from '../api/client';

export default function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ title: '', department: '', description: '' });
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadJobs();
  }, []);

  async function loadJobs() {
    try {
      const res = await api.get('/jobs');
      setJobs(res.data.jobs);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setCreating(true);
    try {
      await api.post('/jobs', form);
      setShowModal(false);
      setForm({ title: '', department: '', description: '' });
      loadJobs();
    } catch (err) {
      console.error('Failed to create job:', err);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="page-container fade-in">
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h2>Job Positions</h2>
          <p>Manage roles and screen candidates</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={18} />
          New Job
        </button>
      </div>

      {jobs.length === 0 ? (
        <div className="empty-state">
          <Briefcase />
          <h3>No jobs yet</h3>
          <p>Create your first job posting to start screening candidates</p>
        </div>
      ) : (
        <div className="jobs-grid">
          {jobs.map((job) => {
            const progress = job.candidate_count > 0
              ? Math.round((job.screened_count / job.candidate_count) * 100)
              : 0;

            return (
              <div
                key={job.id}
                className="card card-clickable job-card"
                onClick={() => navigate(`/jobs/${job.id}`)}
              >
                <div className="job-dept">{job.department || 'General'}</div>
                <h3>{job.title}</h3>
                <div className="job-meta">
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Users size={14} /> {job.candidate_count} candidates
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <CheckCircle size={14} /> {job.screened_count} screened
                  </span>
                </div>
                <div className="job-progress">
                  <div className="job-progress-fill" style={{ width: `${progress}%` }} />
                </div>
                <div style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-2)' }}>
                  {progress}% screening complete
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Create New Job</h3>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Job Title *</label>
                <input
                  className="form-input"
                  placeholder="e.g. Senior Software Engineer"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>Department</label>
                <input
                  className="form-input"
                  placeholder="e.g. Engineering"
                  value={form.department}
                  onChange={(e) => setForm({ ...form, department: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Job Description</label>
                <textarea
                  className="form-input"
                  placeholder="Describe the role, requirements, and responsibilities..."
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  rows={4}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={creating || !form.title.trim()}>
                  {creating ? 'Creating...' : 'Create Job'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
