import { useRef, useEffect, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { WodListProps } from '../types';
import { WodCard } from './WodCard';

function useWindowSize() {
  const [size, setSize] = useState({ width: window.innerWidth });

  useEffect(() => {
    const handleResize = () => setSize({ width: window.innerWidth });
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return size;
}

function getColumnCount(width: number): number {
  if (width >= 1280) return 5; // xl
  if (width >= 1024) return 3; // lg
  if (width >= 768) return 2;  // md
  return 1;
}

export function WodList({ wods, searchTerm }: WodListProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const { width } = useWindowSize();
  const columnCount = getColumnCount(width);

  const rowCount = Math.ceil(wods.length / columnCount);

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 300,
    overscan: 3,
    measureElement: (element) => {
      return element.getBoundingClientRect().height + 16; // 16px for gap
    },
  });

  // Re-measure when column count changes
  useEffect(() => {
    virtualizer.measure();
  }, [columnCount, virtualizer]);

  if (wods.length === 0) {
    return (
      <div className="text-center py-12 px-4">
        <div className="text-gray-400 mb-2">
          <svg
            className="w-16 h-16 mx-auto"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <p className="text-gray-500 text-lg font-medium">No workouts found</p>
        <p className="text-gray-400 text-sm mt-1">Try a different search term</p>
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      className="h-[calc(100vh-200px)] overflow-auto p-4"
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const startIndex = virtualRow.index * columnCount;
          const rowWods = wods.slice(startIndex, startIndex + columnCount);

          return (
            <div
              key={virtualRow.key}
              data-index={virtualRow.index}
              ref={virtualizer.measureElement}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              <div
                className="grid gap-4"
                style={{
                  gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))`,
                }}
              >
                {rowWods.map((wod) => (
                  <WodCard key={wod.date} wod={wod} searchTerm={searchTerm} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
