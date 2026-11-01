import { FileJson, FileSpreadsheet, FileText, type LucideIcon } from 'lucide-react';

const SPREADSHEET_EXTENSIONS = new Set(['xlsx', 'xls', 'csv']);
const JSON_EXTENSIONS = new Set(['json']);

type TrainingFileIconProps = {
  extension: string;
  className?: string;
};

export function TrainingFileIcon({ extension, className = 'h-5 w-5 shrink-0 text-zinc-500' }: TrainingFileIconProps) {
  const normalized = extension.toLowerCase();
  let Icon: LucideIcon = FileText;
  if (JSON_EXTENSIONS.has(normalized)) {
    Icon = FileJson;
  } else if (SPREADSHEET_EXTENSIONS.has(normalized)) {
    Icon = FileSpreadsheet;
  }
  return <Icon className={className} aria-hidden data-testid={`file-icon-${normalized || 'unknown'}`} />;
}
