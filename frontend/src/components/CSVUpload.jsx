import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, CheckCircle } from 'lucide-react';

export default function CSVUpload({ onUpload, isUploading, result }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onUpload(acceptedFiles[0]);
    }
  }, [onUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    maxFiles: 1,
    disabled: isUploading,
  });

  if (result) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
        <CheckCircle size={48} style={{ color: 'var(--success)', marginBottom: 'var(--space-4)' }} />
        <h3 style={{ color: 'var(--text-primary)', marginBottom: 'var(--space-2)' }}>
          Upload Complete
        </h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-2)' }}>
          <strong>{result.created}</strong> candidates added successfully
        </p>
        {result.errors.length > 0 && (
          <div style={{ marginTop: 'var(--space-4)', textAlign: 'left' }}>
            <p style={{ color: 'var(--warning)', fontSize: 'var(--font-sm)', fontWeight: 600 }}>
              {result.errors.length} row(s) had issues:
            </p>
            <ul style={{ color: 'var(--text-muted)', fontSize: 'var(--font-xs)', marginTop: 'var(--space-2)', paddingLeft: 'var(--space-5)' }}>
              {result.errors.slice(0, 5).map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <div {...getRootProps()} className={`dropzone ${isDragActive ? 'dropzone-active' : ''}`}>
      <input {...getInputProps()} />
      {isUploading ? (
        <>
          <FileText className="dropzone-icon" />
          <p>Uploading...</p>
        </>
      ) : (
        <>
          <Upload className="dropzone-icon" />
          <p>
            {isDragActive
              ? 'Drop your CSV file here...'
              : <>Drag & drop a CSV file here, or <span className="highlight">browse</span></>
            }
          </p>
          <p style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-2)' }}>
            Required columns: name, phone &nbsp;|&nbsp; Optional: email, resume_url
          </p>
        </>
      )}
    </div>
  );
}
