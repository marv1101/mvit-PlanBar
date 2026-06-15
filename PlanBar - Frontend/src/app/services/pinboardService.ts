import api from '../lib/api';

export interface ThreadCreateDTO {
  title: string;
}

export interface ThreadUpdateDTO {
  title?: string;
  is_pinned?: boolean;
}

export interface ThreadResponseDTO {
  id: number;
  title: string;
  author_id: number;
  author_name: string;
  is_pinned: boolean;
  message_count: number;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageCreateDTO {
  content: string;
}

export interface MessageUpdateDTO {
  content?: string;
}

export interface DocumentResponseDTO {
  id: number;
  message_id: number;
  file_name: string;
  file_size: number;
  mime_type: string;
  created_at: string;
}

export interface MessageResponseDTO {
  id: number;
  thread_id: number;
  author_id: number;
  author_name: string;
  content: string;
  documents: DocumentResponseDTO[];
  created_at: string;
  updated_at: string;
}

export interface ThreadDetailResponseDTO {
  id: number;
  title: string;
  author_id: number;
  author_name: string;
  is_pinned: boolean;
  messages: MessageResponseDTO[];
  created_at: string;
  updated_at: string;
}

export async function getThreads(): Promise<ThreadResponseDTO[]> {
  const { data } = await api.get('/pinboard/threads');
  return data;
}

export async function createThread(dto: ThreadCreateDTO): Promise<ThreadResponseDTO> {
  const { data } = await api.post('/pinboard/threads', dto);
  return data;
}

export async function getThread(id: number): Promise<ThreadDetailResponseDTO> {
  const { data } = await api.get(`/pinboard/threads/${id}`);
  return data;
}

export async function updateThread(id: number, dto: ThreadUpdateDTO): Promise<ThreadResponseDTO> {
  const { data } = await api.put(`/pinboard/threads/${id}`, dto);
  return data;
}

export async function deleteThread(id: number): Promise<void> {
  await api.delete(`/pinboard/threads/${id}`);
}

export async function getMessages(threadId: number): Promise<MessageResponseDTO[]> {
  const { data } = await api.get(`/pinboard/threads/${threadId}/messages`);
  return data;
}

export async function createMessage(threadId: number, dto: MessageCreateDTO): Promise<MessageResponseDTO> {
  const { data } = await api.post(`/pinboard/threads/${threadId}/messages`, dto);
  return data;
}

export async function updateMessage(id: number, dto: MessageUpdateDTO): Promise<MessageResponseDTO> {
  const { data } = await api.put(`/pinboard/messages/${id}`, dto);
  return data;
}

export async function deleteMessage(id: number): Promise<void> {
  await api.delete(`/pinboard/messages/${id}`);
}

export async function uploadDocument(messageId: number, file: File): Promise<DocumentResponseDTO> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post(`/pinboard/messages/${messageId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function getDocumentUrl(documentId: number): Promise<string> {
  return `/api/v1/pinboard/documents/${documentId}`;
}

export async function deleteDocument(documentId: number): Promise<void> {
  await api.delete(`/pinboard/documents/${documentId}`);
}
