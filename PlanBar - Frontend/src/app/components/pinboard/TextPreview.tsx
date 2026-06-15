import { useState } from 'react';
import { useDocumentUrl } from './useDocumentUrl';
import { Download, Loader2, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { PinboardDocument } from '../../types';
import { Button } from '../ui/button';

interface TextPreviewProps {
  document: PinboardDocument;
}

const PREVIEW_LINES = 50;

export function TextPreview({ document }: TextPreviewProps) {
  const { url, loading } = useDocumentUrl(document.id);
  const [content, setContent] = useState<string | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleToggle = async () => {
    if (content) {
      setExpanded(prev => !prev);
      return;
    }

    setLoadingContent(true);
    try {
      const response = await fetch(url ?? '');
      const text = await response.text();
      setContent(text);
      setExpanded(true);
    } catch {
      setContent('(Vorschau nicht verfügbar)');
      setExpanded(true);
    } finally {
      setLoadingContent(false);
    }
  };

  const previewText = content
    ? content.split('\n').slice(0, expanded ? undefined : PREVIEW_LINES).join('\n')
    : null;
  const showExpandButton = content && content.split('\n').length > PREVIEW_LINES;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 p-2 bg-gray-50 rounded-md">
        <FileText className="h-5 w-5 text-gray-600 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{document.fileName}</p>
        </div>
        <div className="flex items-center gap-1">
          {!loading && (
            <Button variant="ghost" size="sm" onClick={handleToggle}>
              {loadingContent ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Vorschau'
              )}
            </Button>
          )}
          <a
            href={`/api/v1/pinboard/documents/${document.id}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="ghost" size="sm">
              <Download className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </div>
      {previewText && expanded && (
        <div className="relative">
          <pre className="text-xs bg-gray-50 p-3 rounded-md overflow-x-auto max-h-96 whitespace-pre-wrap break-words">
            {previewText}
          </pre>
          {showExpandButton && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(prev => !prev)}
              className="mt-1"
            >
              {expanded ? (
                <><ChevronUp className="h-4 w-4 mr-1" /> Weniger anzeigen</>
              ) : (
                <><ChevronDown className="h-4 w-4 mr-1" /> Mehr anzeigen ({content.split('\n').length - PREVIEW_LINES} Zeilen)</>
              )}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
