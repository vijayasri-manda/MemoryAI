/**
 * Markdown renderer with syntax-highlighted code blocks.
 */
import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';
import { cn, copyToClipboard } from '@/lib/utils';

interface MarkdownProps {
  content: string;
  className?: string;
}

interface CodeProps {
  node?: unknown;
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const ok = await copyToClipboard(code);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="code-block">
      <div className="code-block-header">
        <span className="text-xs text-surface-400 font-mono">{language || 'plaintext'}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-surface-400 hover:text-surface-100
                     transition-colors duration-150 btn-icon py-1 px-2"
          title="Copy code"
        >
          {copied ? (
            <><Check className="w-3.5 h-3.5 text-emerald-400" /><span className="text-emerald-400">Copied!</span></>
          ) : (
            <><Copy className="w-3.5 h-3.5" /><span>Copy</span></>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={language || 'text'}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: 0,
          background: 'hsl(230, 18%, 9%)',
          fontSize: '0.8rem',
          lineHeight: '1.6',
          padding: '1rem',
        }}
        codeTagProps={{ style: { fontFamily: 'JetBrains Mono, Fira Code, monospace' } }}
      >
        {String(code).replace(/\n$/, '')}
      </SyntaxHighlighter>
    </div>
  );
}

export function MarkdownRenderer({ content, className }: MarkdownProps) {
  return (
    <div className={cn('markdown-body', className)}>
      <ReactMarkdown
        components={{
          code({ inline, className: cls, children, ...props }: CodeProps) {
            const match = /language-(\w+)/.exec(cls ?? '');
            const lang = match?.[1] ?? '';
            const code = String(children);

            if (!inline && (match || code.includes('\n'))) {
              return <CodeBlock language={lang} code={code} />;
            }
            return (
              <code className={cls} {...props}>
                {children}
              </code>
            );
          },
          // Open links in new tab
          a({ href, children }) {
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
