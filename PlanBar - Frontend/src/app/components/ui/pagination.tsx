import { Button } from './button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  offset: number;
  limit: number;
  total: number;
  onPageChange: (offset: number) => void;
}

export function Pagination({ offset, limit, total, onPageChange }: PaginationProps) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  if (totalPages <= 1) return null;

  const getVisiblePages = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
      return pages;
    }

    pages.push(1);

    let start = Math.max(2, currentPage - 1);
    let end = Math.min(totalPages - 1, currentPage + 1);

    if (currentPage <= 3) {
      end = Math.min(totalPages - 1, 4);
    } else if (currentPage >= totalPages - 2) {
      start = Math.max(2, totalPages - 3);
    }

    if (start > 2) pages.push('...');
    for (let i = start; i <= end; i++) pages.push(i);
    if (end < totalPages - 1) pages.push('...');

    pages.push(totalPages);
    return pages;
  };

  const visiblePages = getVisiblePages();

  return (
    <div className="flex items-center justify-center gap-2 mt-4">
      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(Math.max(0, offset - limit))}
        disabled={offset === 0}
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>

      {visiblePages.map((page, idx) =>
        typeof page === 'string' ? (
          <span key={idx} className="px-2 text-gray-400">...</span>
        ) : (
          <Button
            key={idx}
            variant={page === currentPage ? 'default' : 'outline'}
            size="sm"
            onClick={() => onPageChange((page - 1) * limit)}
          >
            {page}
          </Button>
        )
      )}

      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(offset + limit)}
        disabled={offset + limit >= total}
      >
        <ChevronRight className="h-4 w-4" />
      </Button>

      <span className="text-sm text-gray-500 ml-2">
        {offset + 1}–{Math.min(offset + limit, total)} von {total}
      </span>
    </div>
  );
}
