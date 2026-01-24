/**
 * Animated List Component
 *
 * Staggered list animations for item reveals.
 */

import { motion, AnimatePresence, Variants } from 'framer-motion';
import { ReactNode, Children, isValidElement, cloneElement } from 'react';
import { cn } from '@/lib/cn';
import { staggerContainer, staggerItem, transitions } from '@/lib/animations';

interface AnimatedListProps {
  children: ReactNode;
  className?: string;
  staggerDelay?: number;
  initialDelay?: number;
  animation?: 'fade' | 'slide' | 'scale' | 'slideUp' | 'slideDown';
}

const animationVariants: Record<string, Variants> = {
  fade: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },
  slide: {
    initial: { opacity: 0, x: -20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -20 },
  },
  scale: {
    initial: { opacity: 0, scale: 0.8 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.8 },
  },
  slideUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 20 },
  },
  slideDown: {
    initial: { opacity: 0, y: -20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
  },
};

export function AnimatedList({
  children,
  className,
  staggerDelay = 0.05,
  initialDelay = 0.1,
  animation = 'slideUp',
}: AnimatedListProps) {
  const variants = animationVariants[animation];

  const containerVariants: Variants = {
    initial: {},
    animate: {
      transition: {
        staggerChildren: staggerDelay,
        delayChildren: initialDelay,
      },
    },
    exit: {
      transition: {
        staggerChildren: staggerDelay / 2,
        staggerDirection: -1,
      },
    },
  };

  return (
    <motion.div
      className={className}
      initial="initial"
      animate="animate"
      exit="exit"
      variants={containerVariants}
    >
      {Children.map(children, (child, index) => (
        <motion.div key={index} variants={variants}>
          {child}
        </motion.div>
      ))}
    </motion.div>
  );
}

interface AnimatedListItemProps {
  children: ReactNode;
  className?: string;
  index?: number;
}

export function AnimatedListItem({
  children,
  className,
  index = 0,
}: AnimatedListItemProps) {
  return (
    <motion.div
      className={className}
      variants={staggerItem}
      transition={{ ...transitions.spring, delay: index * 0.05 }}
    >
      {children}
    </motion.div>
  );
}

interface AnimatedPresenceListProps {
  children: ReactNode;
  className?: string;
}

export function AnimatedPresenceList({
  children,
  className,
}: AnimatedPresenceListProps) {
  return (
    <div className={className}>
      <AnimatePresence mode="popLayout">
        {Children.map(children, (child, index) => {
          if (!isValidElement(child)) return null;
          return (
            <motion.div
              key={child.key ?? index}
              layout
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={transitions.spring}
            >
              {child}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
