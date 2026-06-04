'use client';

import { useRef, type FormEvent, type KeyboardEvent } from 'react';
import { ArrowUp } from 'lucide-react';
import FileUpload from '@/components/FileUpload';

interface MessageInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function MessageInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = 'Message AI Chat…',
}: MessageInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e?: FormEvent) => {
    e?.preventDefault();
    if (!value.trim() || disabled) return;
    onSubmit();
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  return (
    <form onSubmit={handleSubmit} className="relative flex items-end gap-2">
      <div
        className="flex-1 flex items-end rounded-2xl px-4 py-3 transition"
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
        }}
      >
        {/* File upload button — sits to the left of the textarea */}
        <div className="shrink-0 self-end mb-0.5 mr-1">
          <FileUpload />
        </div>

        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            handleInput();
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 resize-none bg-transparent text-sm leading-relaxed outline-none placeholder:text-[var(--muted)]"
          style={{
            color: 'var(--foreground)',
            maxHeight: '200px',
            overflowY: 'auto',
          }}
        />

        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="ml-2 p-1.5 rounded-lg transition-colors cursor-pointer shrink-0 self-end"
          style={{
            background: !disabled && value.trim() ? 'var(--accent)' : 'var(--border)',
            color: '#fff',
          }}
        >
          <ArrowUp size={16} />
        </button>
      </div>
    </form>
  );
}
