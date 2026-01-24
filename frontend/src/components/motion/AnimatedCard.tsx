/**
 * Animated Card Component
 *
 * Card with hover and tap animations.
 */

import { motion, MotionProps } from 'framer-motion';
import { forwardRef, ReactNode } from 'react';
import { cn } from '@/lib/cn';
import { cardHover, transitions } from '@/lib/animations';

interface AnimatedCardProps extends Omit<MotionProps, 'children'> {
  children: ReactNode;
  className?: string;
  hoverEffect?: 'lift' | 'glow' | 'border' | 'scale' | 'none';
  clickable?: boolean;
  onClick?: () => void;
}

const hoverEffects = {
  lift: {
    rest: { y: 0, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' },
    hover: {
      y: -4,
      boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
      transition: transitions.spring,
    },
  },
  glow: {
    rest: { boxShadow: '0 0 0 0 rgba(99, 102, 241, 0)' },
    hover: {
      boxShadow: '0 0 20px 2px rgba(99, 102, 241, 0.3)',
      transition: transitions.ease,
    },
  },
  border: {
    rest: { borderColor: 'rgba(0,0,0,0.1)' },
    hover: {
      borderColor: 'rgba(99, 102, 241, 0.5)',
      transition: transitions.fast,
    },
  },
  scale: {
    rest: { scale: 1 },
    hover: {
      scale: 1.02,
      transition: transitions.spring,
    },
  },
  none: {
    rest: {},
    hover: {},
  },
};

export const AnimatedCard = forwardRef<HTMLDivElement, AnimatedCardProps>(
  (
    {
      children,
      className,
      hoverEffect = 'lift',
      clickable = false,
      onClick,
      ...props
    },
    ref
  ) => {
    const effect = hoverEffects[hoverEffect];

    return (
      <motion.div
        ref={ref}
        className={cn(
          'rounded-lg border bg-card text-card-foreground shadow-sm',
          clickable && 'cursor-pointer',
          className
        )}
        initial="rest"
        whileHover="hover"
        whileTap={clickable ? { scale: 0.98 } : undefined}
        variants={{
          rest: effect.rest,
          hover: effect.hover,
        }}
        onClick={onClick}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

AnimatedCard.displayName = 'AnimatedCard';

interface AnimatedCardContentProps {
  children: ReactNode;
  className?: string;
  delay?: number;
}

export function AnimatedCardContent({
  children,
  className,
  delay = 0,
}: AnimatedCardContentProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
      className={cn('p-6', className)}
    >
      {children}
    </motion.div>
  );
}
