import { FileImage, FileText, FileSpreadsheet, File } from 'lucide-react';

const mimeToIcon: Record<string, typeof File> = {
  'image/jpeg': FileImage,
  'image/png': FileImage,
  'image/gif': FileImage,
  'image/webp': FileImage,
  'application/pdf': FileText,
  'text/plain': FileText,
  'application/msword': FileText,
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileText,
  'application/vnd.ms-excel': FileSpreadsheet,
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileSpreadsheet,
};

export function FileIcon({ mimeType, className }: { mimeType: string; className?: string }) {
  const Icon = mimeToIcon[mimeType] ?? File;
  return <Icon className={className} />;
}
