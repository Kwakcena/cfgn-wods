import type { WodListProps } from '../types';
import { WodCard } from './WodCard';

export function WodList({ wods, searchTerm }: WodListProps) {
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
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 p-4">
      {wods.map((wod) => (
        <WodCard key={wod.date} wod={wod} searchTerm={searchTerm} />
      ))}
    </div>
  );
}
