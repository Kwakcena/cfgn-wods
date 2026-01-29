export interface WodData {
  [date: string]: string;
}

export interface Wod {
  date: string;
  content: string;
}

export interface WodCardProps {
  wod: Wod;
  searchTerm?: string;
}

export interface SearchBarProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
}

export interface WodListProps {
  wods: Wod[];
  searchTerm?: string;
}
