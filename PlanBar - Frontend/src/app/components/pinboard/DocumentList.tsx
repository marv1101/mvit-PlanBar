import { PinboardDocument } from '../../types';
import { FileIcon } from './FileIcon';
import { ImagePreview } from './ImagePreview';
import { PdfPreview } from './PdfPreview';
import { TextPreview } from './TextPreview';
import { Download } from 'lucide-react';
import { Button } from '../ui/button';

interface DocumentListProps {
  documents: PinboardDocument[];
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentList({ documents }: DocumentListProps) {
  return (
    <div className="mt-3 space-y-2">
      {documents.map(doc => {
        if (doc.mimeType.startsWith('image/')) {
          return <ImagePreview key={doc.id} document={doc} allDocuments={documents} />;
        }

        if (doc.mimeType === 'application/pdf') {
          return <PdfPreview key={doc.id} document={doc} />;
        }

        if (doc.mimeType === 'text/plain') {
          return <TextPreview key={doc.id} document={doc} />;
        }

        return (
          <div key={doc.id} className="flex items-center gap-3 p-2 bg-gray-50 rounded-md">
            <FileIcon mimeType={doc.mimeType} className="h-5 w-5 text-blue-600 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{doc.fileName}</p>
              <p className="text-xs text-gray-500">{formatFileSize(doc.fileSize)}</p>
            </div>
            <a
              href={`/api/v1/pinboard/documents/${doc.id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="ghost" size="sm">
                <Download className="h-4 w-4" />
              </Button>
            </a>
          </div>
        );
      })}
    </div>
  );
}
