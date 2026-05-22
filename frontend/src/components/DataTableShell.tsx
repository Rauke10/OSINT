import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  minWidth?: number;
  className?: string;
  footer?: ReactNode;
};

export function DataTableShell({ children, minWidth = 1200, className = "", footer }: Props) {
  return (
    <div
      className={`w-full rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 ${className}`}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm" style={{ minWidth }}>
          {children}
        </table>
      </div>
      {footer}
    </div>
  );
}
