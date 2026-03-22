import { useState } from 'react';

interface ChipGroupProps {
  label: string;
  options: string[];
  multiSelect?: boolean;
  onSelectionChange?: (selected: string | string[]) => void;
  customPlaceholder?: string;
  onCustomChange?: (value: string) => void;
}

export function ChipGroup({ label, options, multiSelect = false, onSelectionChange, customPlaceholder, onCustomChange }: ChipGroupProps) {
  const [selected, setSelected] = useState<string[]>([]);

  const handleSelect = (option: string) => {
    let newSelected: string[];

    if (multiSelect) {
      newSelected = selected.includes(option)
        ? selected.filter(s => s !== option)
        : [...selected, option];
    } else {
      newSelected = selected.includes(option) ? [] : [option];
    }

    setSelected(newSelected);
    onSelectionChange?.(multiSelect ? newSelected : newSelected[0] || '');
  };

  return (
    <div className="space-y-2">
      <div className="text-xs text-[#6e6e73] font-medium tracking-wide">{label}</div>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option}
            onClick={() => handleSelect(option)}
            className={`px-4 py-1.5 text-sm rounded-full transition-all shrink-0 ${
              selected.includes(option)
                ? 'bg-[#16a34a] text-white shadow-sm'
                : 'bg-[#16a34a]/8 text-[#1d1d1f] hover:bg-[#16a34a]/15'
            }`}
          >
            {option}
          </button>
        ))}
      </div>
      {customPlaceholder !== undefined && (
        <input
          type="text"
          placeholder={customPlaceholder}
          onChange={(e) => onCustomChange?.(e.target.value)}
          className="w-full px-4 py-2.5 rounded-2xl bg-white/80 backdrop-blur border border-black/10 text-sm text-[#1d1d1f] focus:outline-none focus:ring-2 focus:ring-black/10 transition-all placeholder:text-[#6e6e73]"
        />
      )}
    </div>
  );
}
