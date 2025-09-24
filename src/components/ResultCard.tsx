import { PropsWithChildren } from 'react';
import { motion } from 'framer-motion';

export interface ResultCardProps extends PropsWithChildren {
  title: string;
  description?: string;
  icon?: string;
  className?: string;
  delay?: number;
}

const ResultCard = ({
  title,
  description,
  icon,
  className = '',
  delay = 0,
  children,
}: ResultCardProps) => {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut', delay }}
    >
      <div
        className={`glass-panel card-border rounded-3xl p-6 md:p-8 bg-gradient-to-br from-white/10 via-white/5 to-white/0 ${className}`.trim()}
      >
        <div className="mb-6 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            {icon && <span className="text-2xl leading-none">{icon}</span>}
            <div>
              <h3 className="text-xl font-semibold text-gray-100">{title}</h3>
              {description && <p className="mt-1 text-sm text-gray-400">{description}</p>}
            </div>
          </div>
          <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-sap-accent">
            SAP Joule
          </span>
        </div>
        <div className="text-gray-200 text-sm md:text-base leading-relaxed">{children}</div>
      </div>
    </motion.section>
  );
};

export default ResultCard;
