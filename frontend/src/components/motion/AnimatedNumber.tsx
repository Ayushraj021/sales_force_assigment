/**
 * Animated Number Component
 *
 * Smooth counting animation for numbers.
 */

import { useEffect, useRef, useState } from 'react';
import { motion, useSpring, useTransform, animate } from 'framer-motion';
import { cn } from '@/lib/cn';

interface AnimatedNumberProps {
  value: number;
  className?: string;
  duration?: number;
  formatValue?: (value: number) => string;
  prefix?: string;
  suffix?: string;
}

export function AnimatedNumber({
  value,
  className,
  duration = 1,
  formatValue = (v) => Math.round(v).toLocaleString(),
  prefix = '',
  suffix = '',
}: AnimatedNumberProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const controls = animate(displayValue, value, {
      duration,
      onUpdate: (latest) => {
        setDisplayValue(latest);
      },
    });

    return () => controls.stop();
  }, [value, duration]);

  return (
    <motion.span
      ref={ref}
      className={cn('tabular-nums', className)}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {prefix}
      {formatValue(displayValue)}
      {suffix}
    </motion.span>
  );
}

interface AnimatedPercentageProps {
  value: number;
  className?: string;
  duration?: number;
  showSign?: boolean;
  decimals?: number;
}

export function AnimatedPercentage({
  value,
  className,
  duration = 0.8,
  showSign = true,
  decimals = 1,
}: AnimatedPercentageProps) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const controls = animate(displayValue, value, {
      duration,
      onUpdate: (latest) => {
        setDisplayValue(latest);
      },
    });

    return () => controls.stop();
  }, [value, duration]);

  const sign = displayValue > 0 && showSign ? '+' : '';
  const formattedValue = displayValue.toFixed(decimals);

  return (
    <motion.span
      className={cn(
        'tabular-nums font-medium',
        displayValue > 0 && 'text-success',
        displayValue < 0 && 'text-destructive',
        displayValue === 0 && 'text-muted-foreground',
        className
      )}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {sign}
      {formattedValue}%
    </motion.span>
  );
}

interface AnimatedCurrencyProps {
  value: number;
  className?: string;
  duration?: number;
  currency?: string;
  locale?: string;
}

export function AnimatedCurrency({
  value,
  className,
  duration = 1,
  currency = 'USD',
  locale = 'en-US',
}: AnimatedCurrencyProps) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const controls = animate(displayValue, value, {
      duration,
      onUpdate: (latest) => {
        setDisplayValue(latest);
      },
    });

    return () => controls.stop();
  }, [value, duration]);

  const formatter = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });

  return (
    <motion.span
      className={cn('tabular-nums', className)}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {formatter.format(displayValue)}
    </motion.span>
  );
}

interface CountUpProps {
  from: number;
  to: number;
  className?: string;
  duration?: number;
  delay?: number;
  formatValue?: (value: number) => string;
}

export function CountUp({
  from,
  to,
  className,
  duration = 2,
  delay = 0,
  formatValue = (v) => Math.round(v).toLocaleString(),
}: CountUpProps) {
  const [displayValue, setDisplayValue] = useState(from);
  const [hasStarted, setHasStarted] = useState(false);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setHasStarted(true);
      const controls = animate(from, to, {
        duration,
        onUpdate: (latest) => {
          setDisplayValue(latest);
        },
      });

      return () => controls.stop();
    }, delay * 1000);

    return () => clearTimeout(timeout);
  }, [from, to, duration, delay]);

  return (
    <motion.span
      className={cn('tabular-nums', className)}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay }}
    >
      {formatValue(displayValue)}
    </motion.span>
  );
}
