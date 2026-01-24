/**
 * Page Transition Component
 *
 * Wraps page content with animated transitions.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { ReactNode } from 'react';
import { pageTransition, pageSlide } from '@/lib/animations';

interface PageTransitionProps {
  children: ReactNode;
  className?: string;
  mode?: 'fade' | 'slide' | 'scale';
  direction?: 'up' | 'down' | 'left' | 'right';
}

const getVariants = (mode: string, direction: string) => {
  if (mode === 'slide') {
    const offset = 30;
    const directionMap = {
      up: { y: offset },
      down: { y: -offset },
      left: { x: offset },
      right: { x: -offset },
    };
    const exitMap = {
      up: { y: -offset },
      down: { y: offset },
      left: { x: -offset },
      right: { x: offset },
    };

    return {
      initial: { opacity: 0, ...directionMap[direction as keyof typeof directionMap] },
      animate: {
        opacity: 1,
        x: 0,
        y: 0,
        transition: {
          duration: 0.4,
          ease: [0.4, 0.0, 0.2, 1],
        },
      },
      exit: {
        opacity: 0,
        ...exitMap[direction as keyof typeof exitMap],
        transition: {
          duration: 0.3,
          ease: [0.4, 0.0, 1, 1],
        },
      },
    };
  }

  if (mode === 'scale') {
    return {
      initial: { opacity: 0, scale: 0.95 },
      animate: {
        opacity: 1,
        scale: 1,
        transition: {
          duration: 0.4,
          ease: [0.4, 0.0, 0.2, 1],
        },
      },
      exit: {
        opacity: 0,
        scale: 0.95,
        transition: {
          duration: 0.3,
          ease: [0.4, 0.0, 1, 1],
        },
      },
    };
  }

  // Default fade
  return pageTransition;
};

export function PageTransition({
  children,
  className,
  mode = 'fade',
  direction = 'up',
}: PageTransitionProps) {
  const variants = getVariants(mode, direction);

  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit="exit"
      variants={variants}
      className={className}
    >
      {children}
    </motion.div>
  );
}

interface AnimatedOutletProps {
  children: ReactNode;
  className?: string;
}

export function AnimatedOutlet({ children, className }: AnimatedOutletProps) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={typeof window !== 'undefined' ? window.location.pathname : 'default'}
        initial="initial"
        animate="animate"
        exit="exit"
        variants={pageTransition}
        className={className}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
