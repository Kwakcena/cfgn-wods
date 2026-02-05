import type { WodCardProps } from "../types";

export function WodCard({ wod, searchTerm }: WodCardProps) {
  const formatContent = (text: string): React.ReactNode => {
    return text.replace(/♀/g, "♀\uFE0E").replace(/♂/g, "♂\uFE0E");
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString("ko-KR", {
      weekday: "short",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const highlightText = (text: string, search: string) => {
    if (!search.trim()) {
      return text;
    }

    const regex = new RegExp(
      `(${search.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
      "gi"
    );
    const parts = text.split(regex);

    return parts.map((part, index) =>
      regex.test(part) ? (
        <mark
          key={index}
          className="bg-yellow-300 text-gray-900 rounded px-0.5"
        >
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="bg-white border-2 border-gray-200 rounded-lg p-4 md:p-6 shadow-sm hover:shadow-md transition-shadow">
      <div className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">
        {formatDate(wod.date)}
      </div>
      <div className="text-gray-900 text-base md:text-lg font-medium leading-relaxed whitespace-pre-line">
        {searchTerm
          ? highlightText(wod.content, searchTerm)
          : formatContent(wod.content)}
      </div>
    </div>
  );
}
