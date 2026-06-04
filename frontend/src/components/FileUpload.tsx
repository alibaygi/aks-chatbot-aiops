'use client';

import { useRef, useState } from 'react';
import { Paperclip, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { apiFetch } from '@/lib/api';

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

interface UploadResult {
  filename: string;
  chunk_count: number;
}

export default function FileUpload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [message, setMessage] = useState<string>('');

  const handleFile = async (file: File) => {
    const allowed = ['application/pdf', 'text/markdown', 'text/plain'];
    const allowedExts = ['.pdf', '.md', '.txt'];
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();

    if (!allowed.includes(file.type) && !allowedExts.includes(ext)) {
      setStatus('error');
      setMessage('Only PDF, Markdown (.md), and text (.txt) files are supported.');
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setStatus('error');
      setMessage('File exceeds the 20 MB limit.');
      return;
    }

    setStatus('uploading');
    setMessage('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const result: UploadResult = await apiFetch('/api/v1/documents', {
        method: 'POST',
        body: formData,
      });
      setStatus('success');
      setMessage(`"${result.filename}" ingested (${result.chunk_count} chunks).`);
    } catch (err: unknown) {
      setStatus('error');
      const detail =
        err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setMessage(detail);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset so the same file can be re-uploaded after an error
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent<HTMLButtonElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const dismiss = () => {
    setStatus('idle');
    setMessage('');
  };

  return (
    <div className="relative">
      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.md,.txt,application/pdf,text/markdown,text/plain"
        className="hidden"
        onChange={handleChange}
      />

      {/* Trigger button */}
      <button
        type="button"
        title="Upload document (PDF / MD / TXT)"
        onClick={() => inputRef.current?.click()}
        disabled={status === 'uploading'}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className="p-2 rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        style={{ color: 'var(--muted)' }}
      >
        {status === 'uploading' ? (
          <Loader2 size={18} className="animate-spin" />
        ) : (
          <Paperclip size={18} />
        )}
      </button>

      {/* Status badge */}
      {status !== 'idle' && status !== 'uploading' && (
        <div
          className="absolute bottom-full mb-2 left-0 z-20 flex items-start gap-2 rounded-lg px-3 py-2 text-xs shadow-lg max-w-xs"
          style={{
            background: status === 'success' ? 'var(--success-bg, #d1fae5)' : 'var(--error-bg, #fee2e2)',
            color: status === 'success' ? '#065f46' : '#991b1b',
            border: `1px solid ${status === 'success' ? '#6ee7b7' : '#fca5a5'}`,
          }}
        >
          {status === 'success' ? (
            <CheckCircle size={14} className="mt-0.5 shrink-0" />
          ) : (
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
          )}
          <span className="flex-1">{message}</span>
          <button onClick={dismiss} className="ml-1 shrink-0 cursor-pointer">
            <X size={12} />
          </button>
        </div>
      )}
    </div>
  );
}
