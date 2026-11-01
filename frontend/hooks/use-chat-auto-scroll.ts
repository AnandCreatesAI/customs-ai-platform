'use client';

import { type RefObject, useCallback, useEffect, useRef } from 'react';

const NEAR_BOTTOM_THRESHOLD_PX = 120;

export function useChatAutoScroll(
  scrollContainerRef: RefObject<HTMLElement | null>,
  scrollTrigger: number,
) {
  const stickToBottomRef = useRef(true);

  const updateStickiness = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    stickToBottomRef.current = distanceFromBottom <= NEAR_BOTTOM_THRESHOLD_PX;
  }, [scrollContainerRef]);

  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = 'smooth') => {
      const container = scrollContainerRef.current;
      if (!container) {
        return;
      }
      if (typeof container.scrollTo === 'function') {
        container.scrollTo({
          top: container.scrollHeight,
          behavior,
        });
        return;
      }
      container.scrollTop = container.scrollHeight;
    },
    [scrollContainerRef],
  );

  const forceStickToBottom = useCallback(() => {
    stickToBottomRef.current = true;
  }, []);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }
    updateStickiness();
    container.addEventListener('scroll', updateStickiness, { passive: true });
    return () => container.removeEventListener('scroll', updateStickiness);
  }, [scrollContainerRef, updateStickiness]);

  useEffect(() => {
    if (stickToBottomRef.current) {
      scrollToBottom('smooth');
    }
  }, [scrollToBottom, scrollTrigger]);

  return { forceStickToBottom, scrollToBottom };
}
