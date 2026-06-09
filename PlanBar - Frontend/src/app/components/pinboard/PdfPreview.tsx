import { useDocumentUrl } from './useDocumentUrl';
import { Download, Loader2, FileText } from 'lucide-react';
import { PinboardDocument } from '../../types';
import { Button } from '../ui/button';

interface PdfPreviewProps {
  document: PinboardDocument;
}

export function PdfPreview({ document }: PdfPreviewProps) {
  const { url, loading } = useDocumentUrl(document.id);

  if (loading) {
    return (
      <div className="flex items-center gap-3 p-2 bg-gray-50 rounded-md">
        <FileText className="h-5 w-5 text-red-500 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{document.fileName}</p>
          <p className="text-xs text-gray-500">Lade Vorschau...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 p-2 bg-gray-50 rounded-md">
        <FileText className="h-5 w-5 text-red-500 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{document.fileName}</p>
        </div>
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
      {url && (
        <iframe
          src={url}
          className="w-full h-96 rounded-md border"
          title={document.fileName}
        />
      )}
    </div>
  );
}
