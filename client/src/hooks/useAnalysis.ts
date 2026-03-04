import { useState, useEffect, useCallback, useRef } from "react";
import { startAnalysis, getResults, type AnalysisResponse } from "../lib/api";

interface UseAnalysisReturn {
  data: AnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
  progress: { step: string; percent: number } | null;
  analyze: (url: string) => Promise<string>;
  pollResults: (id: string) => void;
}

export function useAnalysis(): UseAnalysisReturn {
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ step: string; percent: number } | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cleanup = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const pollResults = useCallback(
    (id: string) => {
      setIsLoading(true);
      setError(null);

      intervalRef.current = setInterval(async () => {
        try {
          const result = await getResults(id);
          if (result.status === "complete" || result.status === "error") {
            setData(result);
            setIsLoading(false);
            setProgress(null);
            if (result.error) setError(result.error);
            cleanup();
          } else {
            setProgress(result.progress);
          }
        } catch (err) {
          setError("Failed to fetch results");
          setIsLoading(false);
          cleanup();
        }
      }, 2000);
    },
    [cleanup]
  );

  const analyze = useCallback(
    async (url: string): Promise<string> => {
      cleanup();
      setIsLoading(true);
      setError(null);
      setData(null);
      setProgress({ step: "Starting analysis...", percent: 0 });

      try {
        const { id } = await startAnalysis(url);
        pollResults(id);
        return id;
      } catch (err) {
        setError("Failed to start analysis");
        setIsLoading(false);
        throw err;
      }
    },
    [cleanup, pollResults]
  );

  return { data, isLoading, error, progress, analyze, pollResults };
}
