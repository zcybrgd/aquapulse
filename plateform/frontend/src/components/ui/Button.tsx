import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: ButtonVariant;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-teal text-white hover:bg-[#079393] active:bg-[#067f7f] disabled:bg-teal/40",
  secondary:
    "border border-line bg-white text-ink hover:bg-page active:bg-teal-light disabled:text-ink-muted",
  ghost: "text-teal hover:bg-teal-light active:bg-[#d7f3f1] disabled:text-ink-muted",
  danger:
    "border border-critical/30 bg-white text-critical hover:bg-critical/10 active:bg-critical/15 disabled:border-critical/15 disabled:bg-critical/5 disabled:text-critical/45",
};

export function Button({
  children,
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
