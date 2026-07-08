'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

interface UsePollingOptions<T> {
  fetcher: () => Promise<T>;
  interval?: number;
  enabled?: boolean;
  onSuccess?: (data: T) => void;
  onError?: (error: unknown) => void;
}

interface UsePollingResult<T> {
  data: T | null;
  error: unknown;
  isLoading: boolean;
  isPolling: boolean;
  refresh: () => Promise<void>;
  start: () => void;
  stop: () => void;
}

export function usePolling<T>({
  fetcher,
  interval = 5000,
  enabled = true,
  onSuccess,
  onError,
}: UsePollingOptions<T>): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPolling, setIsPolling] = useState(enabled);

  const fetcherRef = useRef(fetcher);
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);

  fetcherRef.current = fetcher;
  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const result = await fetcherRef.current();
      setData(result);
      onSuccessRef.current?.(result);
    } catch (err) {
      setError(err);
      onErrorRef.current?.(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const start = useCallback(() => setIsPolling(true), []);
  const stop = useCallback(() => setIsPolling(false), []);

  useEffect(() => {
    if (!isPolling) return;

    refresh();
    const timer = setInterval(refresh, interval);
    return () => clearInterval(timer);
  }, [isPolling, interval, refresh]);

  useEffect(() => {
    setIsPolling(enabled);
  }, [enabled]);

  return { data, error, isLoading, isPolling, refresh, start, stop };
}
