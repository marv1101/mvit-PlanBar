import { useState } from 'react';
import { useDocumentUrl } from './useDocumentUrl';
import { ImageLightbox } from './ImageLightbox';
import { Download, Loader2 } from 'lucide-react';
import { PinboardDocument } from '../../types';
import { Button } from '../ui/button';

interface ImagePreviewProps {
  document: PinboardDocument;
  allDocuments: PinboardDocument[];
}

export function ImagePreview({ document, allDocuments }: ImagePreviewProps) {
  const { url, loading } = useDocumentUrl(document.id);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  if (loading) {
    return (
      <div className="flex items-center gap-3 p-2 bg-gray-50 rounded-md">
        <Loader2 className="h-5 w-5 text-blue-600 animate-spin shrink-0" />
        <span className="text-sm text-gray-500">Lade Vorschau...</span>
      </div>
    );
  }

  return (
    <>
      <div className="relative group">
        <img
          src={url ?? ''}
          alt={document.fileName}
          className="max-h-48 w-full object-contain rounded-md cursor-pointer bg-gray-50"
          onClick={() => setLightboxOpen(true)}
        />
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <a
            href={`/api/v1/pinboard/documents/${document.id}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="secondary" size="sm">
              <Download className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </div>
      {lightboxOpen && url && (
        <ImageLightbox
          images={[{ id: document.id, url, fileName: document.fileName }]}
          initialIndex={0}
          onClose={() => setLightboxOpen(false)}
        />
      )}
    </>
  );
}
