import { ReactNode } from 'react';

interface PrimaryButtonProps {
  children: ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'outline';
  disabled?: boolean;
}

export function PrimaryButton({
  children,
  onClick,
  variant = 'primary',
  disabled = false
}: PrimaryButtonProps) {
  const variants = {
    primary: 'bg-[#16a34a] text-white hover:bg-[#15803d] active:bg-[#166534]',
    secondary: 'bg-[#16a34a]/10 text-[#15803d] hover:bg-[#16a34a]/15 active:bg-[#16a34a]/20',
    outline: 'bg-white/80 backdrop-blur border border-[#16a34a]/20 text-[#1d1d1f] hover:bg-[#16a34a]/5 active:bg-[#16a34a]/10',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`w-full h-14 rounded-2xl text-[15px] font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]}`}
    >
      {children}
    </button>
  );
}
