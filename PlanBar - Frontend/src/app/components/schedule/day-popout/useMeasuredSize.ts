import { useEffect, useState, type RefObject } from 'react';

export interface MeasuredSize {
  width: number;
  height: number;
}

export function useMeasuredSize(ref: RefObject<HTMLElement | null>): MeasuredSize {
  const [size, setSize] = useState<MeasuredSize>({ width: 0, height: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const update = () => {
      const rect = el.getBoundingClientRect();
      setSize({ width: rect.width, height: rect.height });
    };

    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);

  return size;
}
