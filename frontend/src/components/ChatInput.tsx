'use client';

import React, { useRef } from 'react';
import { Plus, Send } from 'lucide-react';

interface ChatInputProps {
  value: string;
  onChange: (val: string) => void;
  onSubmit: () => void;
  isLoading?: boolean;
  onAttachmentClick?: () => void;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSubmit,
  isLoading = false,
  onAttachmentClick,
  placeholder = 'Ask me anything about your career...',
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !isLoading) {
        onSubmit();
      }
    }
  };

  return (
    <div className="chat-input-box">
      <textarea
        ref={textareaRef}
        className="chat-input-field"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={1}
        disabled={isLoading}
      />

      <div className="chat-input-bottom-bar">
        <button
          type="button"
          className="chat-action-btn-plus"
          onClick={onAttachmentClick}
          title="Upload Resume or Reference Document"
          aria-label="Upload Resume or Document"
        >
          <Plus size={16} strokeWidth={2.2} />
        </button>

        <button
          type="button"
          className="chat-send-btn-gold"
          onClick={onSubmit}
          disabled={!value.trim() || isLoading}
          title="Send message"
          aria-label="Send message"
        >
          <Send size={18} strokeWidth={2.4} />
        </button>
      </div>
    </div>
  );
};
