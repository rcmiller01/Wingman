'use client';

import React from 'react';

interface PaginationProps {
    /** Current page (1-indexed) */
    page: number;
    /** Items per page */
    pageSize: number;
    /** Total number of items */
    total: number;
    /** Callback when page changes */
    onPageChange: (page: number) => void;
    /** Callback when page size changes */
    onPageSizeChange?: (pageSize: number) => void;
    /** Available page sizes */
    pageSizeOptions?: number[];
    /** Show page size selector */
    showPageSize?: boolean;
}

export function Pagination({
    page,
    pageSize,
    total,
    onPageChange,
    onPageSizeChange,
    pageSizeOptions = [10, 20, 50, 100],
    showPageSize = true,
}: PaginationProps) {
    const totalPages = Math.ceil(total / pageSize);
    const startItem = Math.min((page - 1) * pageSize + 1, total);
    const endItem = Math.min(page * pageSize, total);
    
    const canGoPrev = page > 1;
    const canGoNext = page < totalPages;
    
    // Generate page numbers to show
    const getPageNumbers = (): (number | 'ellipsis')[] => {
        const pages: (number | 'ellipsis')[] = [];
        const maxVisible = 5;
        
        if (totalPages <= maxVisible + 2) {
            // Show all pages
            for (let i = 1; i <= totalPages; i++) pages.push(i);
        } else {
            // Always show first page
            pages.push(1);
            
            if (page > 3) {
                pages.push('ellipsis');
            }
            
            // Pages around current
            const start = Math.max(2, page - 1);
            const end = Math.min(totalPages - 1, page + 1);
            
            for (let i = start; i <= end; i++) {
                if (!pages.includes(i)) pages.push(i);
            }
            
            if (page < totalPages - 2) {
                pages.push('ellipsis');
            }
            
            // Always show last page
            if (!pages.includes(totalPages)) pages.push(totalPages);
        }
        
        return pages;
    };
    
    if (total === 0) {
        return (
            <div className="flex items-center justify-center py-3 text-sm text-slate-500">
                No results found
            </div>
        );
    }
    
    return (
        <div className="flex items-center justify-between py-3 px-1">
            {/* Left: Item count and page size */}
            <div className="flex items-center gap-4">
                <span className="text-sm text-slate-400">
                    Showing <span className="font-medium text-white">{startItem}-{endItem}</span> of{' '}
                    <span className="font-medium text-white">{total}</span>
                </span>
                
                {showPageSize && onPageSizeChange && (
                    <div className="flex items-center gap-2">
                        <label className="text-sm text-slate-500">Per page:</label>
                        <select
                            value={pageSize}
                            onChange={(e) => onPageSizeChange(Number(e.target.value))}
                            className="bg-slate-800/50 border border-slate-700/50 rounded px-2 py-1 text-sm text-white focus:border-copilot-500 focus:outline-none"
                        >
                            {pageSizeOptions.map((size) => (
                                <option key={size} value={size}>
                                    {size}
                                </option>
                            ))}
                        </select>
                    </div>
                )}
            </div>
            
            {/* Right: Page navigation */}
            {totalPages > 1 && (
                <div className="flex items-center gap-1">
                    {/* Previous button */}
                    <button
                        onClick={() => canGoPrev && onPageChange(page - 1)}
                        disabled={!canGoPrev}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            canGoPrev
                                ? 'bg-slate-800/50 text-slate-300 hover:bg-slate-700/50 border border-slate-700/50'
                                : 'bg-slate-900/50 text-slate-600 cursor-not-allowed border border-slate-800/50'
                        }`}
                    >
                        ← Prev
                    </button>
                    
                    {/* Page numbers */}
                    <div className="flex items-center gap-1 mx-1">
                        {getPageNumbers().map((pageNum, idx) => {
                            if (pageNum === 'ellipsis') {
                                return (
                                    <span key={`ellipsis-${idx}`} className="px-2 text-slate-500">
                                        …
                                    </span>
                                );
                            }
                            
                            const isActive = pageNum === page;
                            return (
                                <button
                                    key={pageNum}
                                    onClick={() => !isActive && onPageChange(pageNum)}
                                    className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                                        isActive
                                            ? 'bg-copilot-500/20 text-copilot-400 border border-copilot-500/30'
                                            : 'bg-slate-800/50 text-slate-400 hover:text-white border border-slate-700/50 hover:border-slate-600'
                                    }`}
                                >
                                    {pageNum}
                                </button>
                            );
                        })}
                    </div>
                    
                    {/* Next button */}
                    <button
                        onClick={() => canGoNext && onPageChange(page + 1)}
                        disabled={!canGoNext}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            canGoNext
                                ? 'bg-slate-800/50 text-slate-300 hover:bg-slate-700/50 border border-slate-700/50'
                                : 'bg-slate-900/50 text-slate-600 cursor-not-allowed border border-slate-800/50'
                        }`}
                    >
                        Next →
                    </button>
                </div>
            )}
        </div>
    );
}

/**
 * Compact pagination for inline use (e.g., in cards)
 */
export function CompactPagination({
    page,
    pageSize,
    total,
    onPageChange,
}: Omit<PaginationProps, 'showPageSize' | 'pageSizeOptions' | 'onPageSizeChange'>) {
    const totalPages = Math.ceil(total / pageSize);
    const canGoPrev = page > 1;
    const canGoNext = page < totalPages;
    
    if (totalPages <= 1) return null;
    
    return (
        <div className="flex items-center gap-2">
            <button
                onClick={() => canGoPrev && onPageChange(page - 1)}
                disabled={!canGoPrev}
                className={`p-1.5 rounded ${canGoPrev ? 'text-slate-400 hover:text-white' : 'text-slate-600 cursor-not-allowed'}`}
            >
                ←
            </button>
            <span className="text-xs text-slate-500">
                {page} / {totalPages}
            </span>
            <button
                onClick={() => canGoNext && onPageChange(page + 1)}
                disabled={!canGoNext}
                className={`p-1.5 rounded ${canGoNext ? 'text-slate-400 hover:text-white' : 'text-slate-600 cursor-not-allowed'}`}
            >
                →
            </button>
        </div>
    );
}
