import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, CheckCircle, TrendingUp, Star } from 'lucide-react';
import api from '../api/client';
import StatusBadge from '../components/StatusBadge';

function getScoreClass(score) {
  if (score >= 7) return 'score-high';
  if (score >= 5) return 'score-mid';
  return 'score-low';
}

export default function Dashboard() {
  const [stats, setStats] = useState({ total_candidates: 0, screened: 0, avg_score: 0, top_rated: 0 });
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      const [statsRes, jobsRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/jobs'),
      ]);
      setStats(statsRes.data);
      setJobs(jobsRes.data.jobs);

      // Load candidates from all jobs
      const allCandidates = [];
      for (const job of jobsRes.data.jobs) {
        const res = await api.get(`/jobs/${job.id}/candidates?sort_by=score`);
        for (const c of res.data.candidates) {
          allCandidates.push({ ...c, job_title: job.title });
        }
      }
      allCandidates.sort((a, b) => (b.overall_score || 0) - (a.overall_score || 0));
      setCandidates(allCandidates);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    }
  }

  const statCards = [
    { icon: <Users size={20} />, value: stats.total_candidates, label: 'Total Candidates', color: 'var(--info)', bg: 'var(--info-bg)' },
    { icon: <CheckCircle size={20} />, value: stats.screened, label: 'Screened', color: 'var(--success)', bg: 'var(--success-bg)' },
    { icon: <TrendingUp size={20} />, value: stats.avg_score, label: 'Avg Score', color: 'var(--warning)', bg: 'var(--warning-bg)' },
    { icon: <Star size={20} />, value: stats.top_rated, label: 'Top Rated (7+)', color: 'var(--purple)', bg: 'var(--purple-bg)' },
  ];

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Overview of your AI-powered screening pipeline</p>
      </div>

      <div className="stats-grid">
        {statCards.map((stat, i) => (
          <div key={i} className="stat-card">
            <div className="stat-icon" style={{ background: stat.bg, color: stat.color }}>
              {stat.icon}
            </div>
            <div className="stat-value" style={{ color: stat.color }}>{stat.value}</div>
            <div className="stat-label">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="table-container">
        <div className="table-header">
          <h3>Ranked Candidates</h3>
          <span style={{ fontSize: 'var(--font-sm)', color: 'var(--text-muted)' }}>
            Sorted by overall score
          </span>
        </div>

        {candidates.length === 0 ? (
          <div className="empty-state">
            <Users />
            <h3>No candidates yet</h3>
            <p>Upload candidates to a job to get started</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Candidate</th>
                <th>Job</th>
                <th>Status</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c, i) => (
                <tr key={c.id} className="clickable" onClick={() => navigate(`/candidates/${c.id}`)}>
                  <td style={{ fontWeight: 600, color: 'var(--text-muted)' }}>{i + 1}</td>
                  <td>
                    <span className="candidate-name">{c.name}</span>
                    {c.email && (
                      <div style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)', marginTop: 2 }}>
                        {c.email}
                      </div>
                    )}
                  </td>
                  <td>{c.job_title}</td>
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
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
