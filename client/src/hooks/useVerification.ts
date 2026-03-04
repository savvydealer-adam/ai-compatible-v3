import { useState, useEffect, useCallback } from "react";
import {
  requestVerification,
  confirmVerification,
  type VerifyRequest,
} from "../lib/api";

type Step = "info" | "code" | "verified";

const TOKEN_PREFIX = "aic_token_";

interface FormData {
  name: string;
  email: string;
  dealership: string;
  phone: string;
  method: "email" | "sms";
}

interface UseVerificationReturn {
  step: Step;
  isVerified: boolean;
  token: string;
  isSubmitting: boolean;
  error: string | null;
  formData: FormData;
  setFormData: (data: FormData) => void;
  requestCode: (data: VerifyRequest) => Promise<void>;
  confirmCode: (analysisId: string, code: string) => Promise<void>;
  editInfo: () => void;
}

function getStoredToken(analysisId: string): string {
  try {
    return localStorage.getItem(`${TOKEN_PREFIX}${analysisId}`) || "";
  } catch {
    return "";
  }
}

function storeToken(analysisId: string, token: string): void {
  try {
    localStorage.setItem(`${TOKEN_PREFIX}${analysisId}`, token);
  } catch {
    // localStorage unavailable
  }
}

export function useVerification(analysisId: string): UseVerificationReturn {
  const [step, setStep] = useState<Step>("info");
  const [token, setToken] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>({
    name: "",
    email: "",
    dealership: "",
    phone: "",
    method: "email",
  });

  // Check localStorage on mount
  useEffect(() => {
    if (analysisId) {
      const stored = getStoredToken(analysisId);
      if (stored) {
        setToken(stored);
        setStep("verified");
      }
    }
  }, [analysisId]);

  const requestCode = useCallback(
    async (data: VerifyRequest) => {
      setIsSubmitting(true);
      setError(null);
      try {
        await requestVerification(data);
        setFormData({
          name: data.name,
          email: data.email,
          dealership: data.dealership,
          phone: data.phone || "",
          method: data.method,
        });
        setStep("code");
      } catch (err: any) {
        setError(err.message || "Failed to send code");
      } finally {
        setIsSubmitting(false);
      }
    },
    []
  );

  const confirmCode = useCallback(
    async (analysisId: string, code: string) => {
      setIsSubmitting(true);
      setError(null);
      try {
        const res = await confirmVerification({ analysis_id: analysisId, code });
        if (res.success && res.token) {
          setToken(res.token);
          storeToken(analysisId, res.token);
          setStep("verified");
        } else {
          setError(res.message || "Invalid code");
        }
      } catch (err: any) {
        setError(err.message || "Verification failed");
      } finally {
        setIsSubmitting(false);
      }
    },
    []
  );

  const editInfo = useCallback(() => {
    setStep("info");
    setError(null);
  }, []);

  return {
    step,
    isVerified: step === "verified",
    token,
    isSubmitting,
    error,
    formData,
    setFormData,
    requestCode,
    confirmCode,
    editInfo,
  };
}
