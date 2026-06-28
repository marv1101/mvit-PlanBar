import { useState, useEffect, useCallback, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { MessageSquare, Plus, ArrowLeft, Send, Paperclip, Trash2, Pin, Loader2, RotateCcw, AlertTriangle } from 'lucide-react';
import { PinboardDocument, PinboardThread, PinboardThreadDetail, PinboardMessage } from '../types';
import * as pinboardService from '../services/pinboardService';
import {
  pinboardDocumentFromResponse,
  pinboardThreadFromResponse,
  pinboardThreadDetailFromResponse,
  pinboardMessageFromResponse,
} from '../lib/mappers';
import { toast } from 'sonner';
import { usePinboardSocket } from '../hooks/usePinboardSocket';
import { DocumentList } from '../components/pinboard/DocumentList';
import { requestNotificationPermission, showPinboardNotification } from '../lib/notifications';

export function PinboardPage() {
  const { user } = useAuth();
  const { employees } = useApp();
  const [threads, setThreads] = useState<PinboardThread[]>([]);
  const [selectedThread, setSelectedThread] = useState<PinboardThreadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newThreadTitle, setNewThreadTitle] = useState('');
  const [newMessageContent, setNewMessageContent] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [deleteThreadId, setDeleteThreadId] = useState<string | null>(null);
  const [sendingMessage, setSendingMessage] = useState(false);
  const isSubmittingRef = useRef(false);

  const loadThreads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await pinboardService.getThreads();
      setThreads(data.items.map(pinboardThreadFromResponse));
    } catch {
      setError('Fehler beim Laden der Threads. Bitte versuchen Sie es erneut.');
      toast.error('Fehler beim Laden der Threads');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    loadThreads().then(() => {
      if (!mounted) return;
    });
    return () => { mounted = false; };
  }, [loadThreads]);

  const loadThread = useCallback(async (id: number) => {
    try {
      const data = await pinboardService.getThread(id);
      setSelectedThread(pinboardThreadDetailFromResponse(data));
    } catch {
      toast.error('Fehler beim Laden des Threads');
    }
  }, []);

  const handleCreateThread = async () => {
    if (!newThreadTitle.trim() || isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    try {
      const data = await pinboardService.createThread({ title: newThreadTitle.trim() });
      const thread = pinboardThreadFromResponse(data);
      setThreads(prev => [thread, ...prev]);
      setNewThreadTitle('');
      setIsCreateOpen(false);
      toast.success('Thread erstellt');
    } catch {
      toast.error('Fehler beim Erstellen des Threads');
    } finally {
      isSubmittingRef.current = false;
    }
  };

  const handleDeleteThread = async () => {
    if (!deleteThreadId || isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    try {
      await pinboardService.deleteThread(Number(deleteThreadId));
      setThreads(prev => prev.filter(t => t.id !== deleteThreadId));
      if (selectedThread?.id === deleteThreadId) {
        setSelectedThread(null);
      }
      setDeleteThreadId(null);
      toast.success('Thread gelöscht');
    } catch {
      toast.error('Fehler beim Löschen des Threads');
    } finally {
      isSubmittingRef.current = false;
    }
  };

  const handleSendMessage = async () => {
    if (!newMessageContent.trim() || !selectedThread || isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    setSendingMessage(true);
    try {
      const data = await pinboardService.createMessage(Number(selectedThread.id), {
        content: newMessageContent.trim(),
      });
      const message = pinboardMessageFromResponse(data);
      setSelectedThread(prev => prev ? {
        ...prev,
        messages: [...prev.messages, message],
      } : null);
      setNewMessageContent('');
    } catch {
      toast.error('Fehler beim Senden der Nachricht');
    } finally {
      isSubmittingRef.current = false;
      setSendingMessage(false);
    }
  };

  useEffect(() => {
    requestNotificationPermission();
  }, []);

  const handleNewMessage = useCallback((message: PinboardMessage) => {
    setSelectedThread(prev => {
      if (!prev || prev.id !== message.threadId) return prev;
      if (prev.messages.some(m => m.id === message.id)) return prev;
      showPinboardNotification(message.authorName, prev.title, message.content);
      return { ...prev, messages: [...prev.messages, message] };
    });
  }, []);

  const handleDocumentUploaded = useCallback((messageId: number, document: PinboardDocument) => {
    setSelectedThread(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        messages: prev.messages.map(m =>
          m.id === String(messageId)
            ? m.documents.some(d => d.id === document.id)
              ? m
              : { ...m, documents: [...m.documents, document] }
            : m
        ),
      };
    });
  }, []);

  usePinboardSocket({
    threadId: selectedThread?.id ?? null,
    onNewMessage: handleNewMessage,
    onDocumentUploaded: handleDocumentUploaded,
    enabled: !!selectedThread,
  });

  const handleSelectThread = async (thread: PinboardThread) => {
    await loadThread(Number(thread.id));
  };

  const handleBack = () => {
    setSelectedThread(null);
    loadThreads();
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Pinnwand</h2>
          <p className="text-gray-600">Lade Beiträge...</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
            <p className="text-gray-600">Lade Beiträge...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Pinnwand</h2>
          <p className="text-gray-600">Interne Kommunikation und Ankündigungen</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="h-8 w-8 mx-auto text-red-500 mb-4" />
            <p className="text-red-600 font-medium mb-4">{error}</p>
            <Button onClick={loadThreads} variant="outline">
              <RotateCcw className="h-4 w-4 mr-2" />
              Erneut versuchen
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (selectedThread) {
    return (
      <ThreadView
        thread={selectedThread}
        onBack={handleBack}
        newMessageContent={newMessageContent}
        onNewMessageChange={setNewMessageContent}
        onSendMessage={handleSendMessage}
        sendingMessage={sendingMessage}
        currentUserId={user?.id}
        onDocumentUploaded={handleDocumentUploaded}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Pinnwand</h2>
          <p className="text-gray-600">Interne Kommunikation und Ankündigungen</p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Neuer Thread
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Neuen Thread erstellen</DialogTitle>
              <DialogDescription>
                Geben Sie einen Titel für den neuen Pinnwand-Thread ein.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <Input
                placeholder="Titel des Threads"
                value={newThreadTitle}
                onChange={e => setNewThreadTitle(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCreateThread()}
                maxLength={255}
              />
              <Button onClick={handleCreateThread} className="w-full">
                <Plus className="h-4 w-4 mr-2" />
                Thread erstellen
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {threads.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <MessageSquare className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-600 mb-4">Noch keine Beiträge vorhanden</p>
            <Button onClick={() => setIsCreateOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Ersten Thread erstellen
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {threads.map(thread => (
            <Card
              key={thread.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => handleSelectThread(thread)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    {thread.isPinned && <Pin className="h-4 w-4 text-blue-600 shrink-0" />}
                    <CardTitle className="text-lg truncate">{thread.title}</CardTitle>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={e => {
                      e.stopPropagation();
                      setDeleteThreadId(thread.id);
                    }}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                  <span>{thread.authorName}</span>
                  <span className="flex items-center gap-1">
                    <MessageSquare className="h-3.5 w-3.5" />
                    {thread.messageCount}
                  </span>
                  {thread.lastMessageAt && (
                    <span>
                      {new Date(thread.lastMessageAt).toLocaleDateString('de-DE', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  )}
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={!!deleteThreadId} onOpenChange={open => !open && setDeleteThreadId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Thread löschen</AlertDialogTitle>
            <AlertDialogDescription>
              Möchten Sie diesen Thread wirklich löschen? Alle Nachrichten und Dokumente werden unwiderruflich gelöscht.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteThread} className="bg-red-600 text-white hover:bg-red-700">
              Löschen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function ThreadView({
  thread,
  onBack,
  newMessageContent,
  onNewMessageChange,
  onSendMessage,
  sendingMessage,
  currentUserId,
  onDocumentUploaded,
}: {
  thread: PinboardThreadDetail;
  onBack: () => void;
  newMessageContent: string;
  onNewMessageChange: (val: string) => void;
  onSendMessage: () => void;
  sendingMessage: boolean;
  currentUserId?: string;
  onDocumentUploaded: (messageId: number, document: PinboardDocument) => void;
}) {
  const [uploadingFile, setUploadingFile] = useState(false);

  const handleFileUpload = async (messageId: string, file: File) => {
    const MAX_FILE_SIZE = 10 * 1024 * 1024;
    if (file.size > MAX_FILE_SIZE) {
      toast.error('Datei zu groß. Maximale Größe ist 10 MB.');
      return;
    }
    const allowedTypes = [
      'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf',
      'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/plain',
    ];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Dateityp nicht erlaubt.');
      return;
    }
    setUploadingFile(true);
    try {
      const doc = await pinboardService.uploadDocument(Number(messageId), file);
      toast.success('Datei hochgeladen');
      onDocumentUploaded(Number(messageId), pinboardDocumentFromResponse(doc));
    } catch {
      toast.error('Fehler beim Hochladen der Datei');
    } finally {
      setUploadingFile(false);
    }
  };

  const handleSendWithFile = async () => {
    if (!newMessageContent.trim()) return;
    onSendMessage();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Zurück
        </Button>
        <div>
          <h2 className="font-semibold text-2xl">{thread.title}</h2>
          <p className="text-sm text-gray-500">
            Gestartet von {thread.authorName} am{' '}
            {new Date(thread.createdAt).toLocaleDateString('de-DE', {
              day: '2-digit',
              month: 'long',
              year: 'numeric',
            })}
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {thread.messages.map(message => (
          <MessageCard
            key={message.id}
            message={message}
            isOwn={message.authorId === currentUserId}
            onFileUpload={handleFileUpload}
            uploadingFile={uploadingFile}
          />
        ))}
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <Textarea
              placeholder="Ihre Nachricht eingeben..."
              value={newMessageContent}
              onChange={e => onNewMessageChange(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendWithFile();
                }
              }}
              className="min-h-[60px]"
              maxLength={5000}
            />
            <div className="flex flex-col gap-2">
              <Button
                onClick={handleSendWithFile}
                disabled={!newMessageContent.trim() || sendingMessage}
              >
                {sendingMessage ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
              <div className="relative">
                <Button variant="outline" size="icon" asChild>
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <Paperclip className="h-4 w-4" />
                  </label>
                </Button>
                <input
                  id="file-upload"
                  type="file"
                  className="hidden"
                  onChange={e => {
                    const file = e.target.files?.[0];
                    if (file) {
                      handleFileUpload(thread.messages[thread.messages.length - 1]?.id || '', file);
                    }
                    e.target.value = '';
                  }}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function MessageCard({
  message,
  isOwn,
  onFileUpload,
  uploadingFile,
}: {
  message: PinboardMessage;
  isOwn: boolean;
  onFileUpload: (messageId: string, file: File) => void;
  uploadingFile: boolean;
}) {
  const [deleteMsgId, setDeleteMsgId] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!deleteMsgId) return;
    try {
      await pinboardService.deleteMessage(Number(deleteMsgId));
      toast.success('Nachricht gelöscht');
      setDeleteMsgId(null);
    } catch {
      toast.error('Fehler beim Löschen der Nachricht');
    }
  };

  return (
    <Card className={isOwn ? 'border-blue-200' : ''}>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{message.authorName}</span>
            <span className="text-xs text-gray-500">
              {new Date(message.createdAt).toLocaleString('de-DE', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
          {isOwn && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setDeleteMsgId(message.id)}
            >
              <Trash2 className="h-3.5 w-3.5 text-red-500" />
            </Button>
          )}
        </div>
        <p className="text-gray-800 whitespace-pre-wrap">{message.content}</p>

        {message.documents.length > 0 && (
          <DocumentList documents={message.documents} />
        )}
      </CardContent>

      <AlertDialog open={!!deleteMsgId} onOpenChange={open => !open && setDeleteMsgId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Nachricht löschen</AlertDialogTitle>
            <AlertDialogDescription>
              Möchten Sie diese Nachricht wirklich löschen?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 text-white hover:bg-red-700">
              Löschen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
