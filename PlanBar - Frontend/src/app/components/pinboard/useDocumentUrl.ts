import { useState, useEffect, useRef } from 'react';
import api from '../../lib/api';

interface UseDocumentUrlResult {
  url: string | null;
  loading: boolean;
  error: Error | null;
}

export function useDocumentUrl(documentId: string): UseDocumentUrlResult {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchDocument() {
      setLoading(true);
      setError(null);
      try {
        const { data } = await api.get(`/pinboard/documents/${documentId}`, {
          responseType: 'blob',
        });
        if (cancelled) return;
        const objectUrl = URL.createObjectURL(data as Blob);
        objectUrlRef.current = objectUrl;
        setUrl(objectUrl);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error('Failed to load document'));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchDocument();

    return () => {
      cancelled = true;
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
  }, [documentId]);

  return { url, loading, error };
}
