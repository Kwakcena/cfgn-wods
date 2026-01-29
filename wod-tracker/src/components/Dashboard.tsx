import { useState, useMemo } from 'react';
import { SearchBar } from './SearchBar';
import { WodList } from './WodList';
import { useDebounce } from '../hooks/useDebounce';
import type { Wod, WodData } from '../types';
import wodData from '../data/wods.json';

export function Dashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  const wods = useMemo((): Wod[] => {
    const data = wodData as WodData;
    return Object.entries(data)
      .map(([date, content]) => ({ date, content }))
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  }, []);

  const filteredWods = useMemo((): Wod[] => {
    if (!debouncedSearchTerm.trim()) {
      return wods;
    }

    const searchLower = debouncedSearchTerm.toLowerCase();
    return wods.filter((wod) =>
      wod.content.toLowerCase().includes(searchLower)
    );
  }, [wods, debouncedSearchTerm]);

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-gray-900 text-white py-6 px-4">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-2xl md:text-3xl font-bold text-center">
            CrossFit WOD Tracker
          </h1>
          <p className="text-gray-400 text-center mt-1 text-sm md:text-base">
            Search and track your daily workouts
          </p>
        </div>
      </header>

      <SearchBar searchTerm={searchTerm} onSearchChange={setSearchTerm} />

      <main className="pb-8">
        <div className="px-4 py-2 text-sm text-gray-500">
          {debouncedSearchTerm ? (
            <span>
              Showing {filteredWods.length} of {wods.length} workouts
            </span>
          ) : (
            <span>{wods.length} workouts available</span>
          )}
        </div>
        <WodList wods={filteredWods} searchTerm={debouncedSearchTerm} />
      </main>
    </div>
  );
}
