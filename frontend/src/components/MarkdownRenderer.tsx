'use client';

import React from 'react';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  if (!content) return null;

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockContent: string[] = [];
  let codeBlockLang = '';

  const formatInline = (text: string): React.ReactNode => {
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let keyIdx = 0;

    while (remaining.length > 0) {
      // Inline code `code`
      const codeMatch = remaining.match(/^`([^`]+)`/);
      if (codeMatch) {
        parts.push(
          <code key={keyIdx++} className="markdown-inline-code">
            {codeMatch[1]}
          </code>
        );
        remaining = remaining.slice(codeMatch[0].length);
        continue;
      }

      // Markdown links [text](url)
      const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        parts.push(
          <a
            key={keyIdx++}
            href={linkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="markdown-link"
          >
            {formatInline(linkMatch[1])}
          </a>
        );
        remaining = remaining.slice(linkMatch[0].length);
        continue;
      }

      // Bold text **text**
      const boldMatch = remaining.match(/^\*\*([^*]+)\*\*/);
      if (boldMatch) {
        parts.push(
          <strong key={keyIdx++} style={{ color: 'var(--text-primary)', fontWeight: 650 }}>
            {formatInline(boldMatch[1])}
          </strong>
        );
        remaining = remaining.slice(boldMatch[0].length);
        continue;
      }

      // Italic text *text* or _text_
      const italicMatch = remaining.match(/^(\*|_)([^*_]+)\1/);
      if (italicMatch) {
        parts.push(
          <em key={keyIdx++} style={{ color: 'var(--text-secondary)' }}>
            {formatInline(italicMatch[2])}
          </em>
        );
        remaining = remaining.slice(italicMatch[0].length);
        continue;
      }

      // Plain text up to next special symbol
      const nextSpecial = remaining.search(/[`*_[\]]/);
      if (nextSpecial === -1) {
        parts.push(remaining);
        break;
      } else if (nextSpecial === 0) {
        parts.push(remaining[0]);
        remaining = remaining.slice(1);
      } else {
        parts.push(remaining.slice(0, nextSpecial));
        remaining = remaining.slice(nextSpecial);
      }
    }

    return parts.length === 1 ? parts[0] : <>{parts}</>;
  };

  const isTableSeparator = (line: string): boolean => {
    const trimmed = line.trim();
    if (!trimmed.includes('-')) return false;
    return /^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$/.test(trimmed);
  };

  const parseTableRow = (line: string): string[] => {
    let trimmed = line.trim();
    if (trimmed.startsWith('|')) trimmed = trimmed.slice(1);
    if (trimmed.endsWith('|')) trimmed = trimmed.slice(0, -1);
    return trimmed.split('|').map((c) => c.trim());
  };

  const getAlignments = (separatorLine: string): Array<'left' | 'center' | 'right'> => {
    return parseTableRow(separatorLine).map((cell) => {
      const left = cell.startsWith(':');
      const right = cell.endsWith(':');
      if (left && right) return 'center';
      if (right) return 'right';
      return 'left';
    });
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Handle code block fences
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <div
            key={`code-${i}`}
            style={{
              backgroundColor: 'rgba(10, 10, 9, 0.95)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              padding: '12px 16px',
              margin: '12px 0',
              overflowX: 'auto',
              fontFamily: 'monospace',
              fontSize: '13px',
              color: '#f5f1e8',
            }}
          >
            {codeBlockLang && (
              <div
                style={{
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  color: 'var(--primary-gold)',
                  marginBottom: '6px',
                  fontWeight: 600,
                }}
              >
                {codeBlockLang}
              </div>
            )}
            <pre style={{ margin: 0, lineHeight: 1.5 }}>{codeBlockContent.join('\n')}</pre>
          </div>
        );
        inCodeBlock = false;
        codeBlockLang = '';
        codeBlockContent = [];
      } else {
        inCodeBlock = true;
        codeBlockLang = line.trim().slice(3);
        codeBlockContent = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }

    const trimmed = line.trim();

    // Empty lines -> vertical spacing
    if (!trimmed) {
      elements.push(<div key={`space-${i}`} style={{ height: '8px' }} />);
      continue;
    }

    // Markdown Table Detection
    if (
      trimmed.includes('|') &&
      i + 1 < lines.length &&
      isTableSeparator(lines[i + 1])
    ) {
      const headerCells = parseTableRow(trimmed);
      const alignments = getAlignments(lines[i + 1]);
      const bodyRows: string[][] = [];

      i += 2; // Move past header and separator
      while (i < lines.length && lines[i].trim().includes('|') && !isTableSeparator(lines[i])) {
        bodyRows.push(parseTableRow(lines[i]));
        i++;
      }
      i--; // Step back one because loop will advance

      elements.push(
        <div key={`table-wrap-${i}`} className="markdown-table-wrapper">
          <table className="markdown-table">
            <thead>
              <tr>
                {headerCells.map((cell, cIdx) => (
                  <th
                    key={cIdx}
                    style={{ textAlign: alignments[cIdx] || 'left' }}
                  >
                    {formatInline(cell)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {headerCells.map((_, cIdx) => (
                    <td
                      key={cIdx}
                      style={{ textAlign: alignments[cIdx] || 'left' }}
                    >
                      {formatInline(row[cIdx] || '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // Horizontal Rule
    if (/^(\*\*\*|---|___)$/.test(trimmed)) {
      elements.push(
        <hr
          key={`hr-${i}`}
          style={{
            border: 'none',
            borderTop: '1px solid var(--border-subtle)',
            margin: '16px 0',
          }}
        />
      );
      continue;
    }

    // Blockquote
    if (trimmed.startsWith('>')) {
      elements.push(
        <blockquote key={`quote-${i}`} className="markdown-blockquote">
          {formatInline(trimmed.replace(/^>\s?/, ''))}
        </blockquote>
      );
      continue;
    }

    // Headers (checked in descending order of depth)
    if (trimmed.startsWith('###### ')) {
      elements.push(
        <h6
          key={`h6-${i}`}
          style={{
            fontSize: '13px',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            margin: '10px 0 4px',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}
        >
          {formatInline(trimmed.slice(7))}
        </h6>
      );
      continue;
    }

    if (trimmed.startsWith('##### ')) {
      elements.push(
        <h5
          key={`h5-${i}`}
          style={{
            fontSize: '13.5px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            margin: '11px 0 4px',
          }}
        >
          {formatInline(trimmed.slice(6))}
        </h5>
      );
      continue;
    }

    if (trimmed.startsWith('#### ')) {
      elements.push(
        <h5
          key={`h4-${i}`}
          style={{
            fontSize: '14.5px',
            fontWeight: 600,
            color: 'var(--primary-gold)',
            margin: '12px 0 5px',
            letterSpacing: '-0.01em',
          }}
        >
          {formatInline(trimmed.slice(5))}
        </h5>
      );
      continue;
    }

    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4
          key={`h3-${i}`}
          style={{
            fontSize: '16px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            margin: '14px 0 6px',
            letterSpacing: '-0.01em',
          }}
        >
          {formatInline(trimmed.slice(4))}
        </h4>
      );
      continue;
    }

    if (trimmed.startsWith('## ')) {
      elements.push(
        <h3
          key={`h2-${i}`}
          style={{
            fontSize: '18px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            margin: '16px 0 8px',
            borderBottom: '1px solid var(--border-subtle)',
            paddingBottom: '5px',
            letterSpacing: '-0.01em',
          }}
        >
          {formatInline(trimmed.slice(3))}
        </h3>
      );
      continue;
    }

    if (trimmed.startsWith('# ')) {
      elements.push(
        <h2
          key={`h1-${i}`}
          style={{
            fontSize: '21px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            margin: '18px 0 10px',
            letterSpacing: '-0.02em',
          }}
        >
          {formatInline(trimmed.slice(2))}
        </h2>
      );
      continue;
    }

    // Bullet items (- or *)
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(
        <div
          key={`bullet-${i}`}
          style={{
            display: 'flex',
            gap: '10px',
            alignItems: 'flex-start',
            margin: '4px 0',
            paddingLeft: '4px',
          }}
        >
          <span
            style={{
              color: 'var(--primary-gold)',
              fontSize: '14px',
              lineHeight: '1.6',
              userSelect: 'none',
            }}
          >
            •
          </span>
          <div style={{ color: 'var(--text-primary)', fontSize: '14px', lineHeight: '1.6', flex: 1 }}>
            {formatInline(trimmed.slice(2))}
          </div>
        </div>
      );
      continue;
    }

    // Numbered list item
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      elements.push(
        <div
          key={`num-${i}`}
          style={{
            display: 'flex',
            gap: '8px',
            alignItems: 'flex-start',
            margin: '4px 0',
            paddingLeft: '4px',
          }}
        >
          <span
            style={{
              color: 'var(--primary-gold)',
              fontWeight: 600,
              fontSize: '13.5px',
              minWidth: '22px',
              lineHeight: '1.6',
              userSelect: 'none',
            }}
          >
            {numMatch[1]}.
          </span>
          <div style={{ color: 'var(--text-primary)', fontSize: '14px', lineHeight: '1.6', flex: 1 }}>
            {formatInline(numMatch[2])}
          </div>
        </div>
      );
      continue;
    }

    // Regular paragraph
    elements.push(
      <p
        key={`p-${i}`}
        style={{
          margin: '4px 0',
          fontSize: '14px',
          color: 'var(--text-primary)',
          lineHeight: '1.65',
        }}
      >
        {formatInline(line)}
      </p>
    );
  }

  return <div style={{ width: '100%' }}>{elements}</div>;
};
