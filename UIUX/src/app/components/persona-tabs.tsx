import { useState } from 'react';

interface PersonaTabsProps {
  personas: string[];
  defaultPersona?: string;
  onPersonaChange?: (persona: string) => void;
}

export function PersonaTabs({ personas, defaultPersona, onPersonaChange }: PersonaTabsProps) {
  const [selected, setSelected] = useState(defaultPersona || personas[0]);

  const handleSelect = (persona: string) => {
    setSelected(persona);
    onPersonaChange?.(persona);
  };

  return (
    <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
      {personas.map((persona) => (
        <button
          key={persona}
          onClick={() => handleSelect(persona)}
          className={`px-4 py-1.5 rounded-full whitespace-nowrap text-sm transition-all shrink-0 ${
            selected === persona
              ? 'bg-[#16a34a] text-white'
              : 'bg-[#16a34a]/8 text-[#1d1d1f] hover:bg-[#16a34a]/15'
          }`}
        >
          {persona}
        </button>
      ))}
    </div>
  );
}
