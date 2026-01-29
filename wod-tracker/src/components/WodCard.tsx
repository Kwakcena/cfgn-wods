import type { WodCardProps } from '../types';

export function WodCard({ wod }: WodCardProps) {
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="bg-white border-2 border-gray-200 rounded-lg p-4 md:p-6 shadow-sm hover:shadow-md transition-shadow">
      <div className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">
        {formatDate(wod.date)}
      </div>
      <div className="text-gray-900 text-lg md:text-xl font-medium leading-relaxed">
        {wod.content}
      </div>
    </div>
  );
}
