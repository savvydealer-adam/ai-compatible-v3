import { useState, type FormEvent } from "react";
import type { VerifyRequest } from "../lib/api";
import { Lock, Mail, Phone, ArrowLeft, RefreshCw } from "lucide-react";

interface VerificationFormProps {
  analysisId: string;
  step: "info" | "code";
  formData: {
    name: string;
    email: string;
    dealership: string;
    phone: string;
    method: "email" | "sms";
  };
  setFormData: (data: VerificationFormProps["formData"]) => void;
  isSubmitting: boolean;
  error: string | null;
  onRequestCode: (data: VerifyRequest) => Promise<void>;
  onConfirmCode: (analysisId: string, code: string) => Promise<void>;
  onEditInfo: () => void;
}

export default function VerificationForm({
  analysisId,
  step,
  formData,
  setFormData,
  isSubmitting,
  error,
  onRequestCode,
  onConfirmCode,
  onEditInfo,
}: VerificationFormProps) {
  const [code, setCode] = useState("");

  const handleInfoSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await onRequestCode({
      analysis_id: analysisId,
      name: formData.name,
      email: formData.email,
      dealership: formData.dealership,
      phone: formData.phone || undefined,
      method: formData.method,
    });
  };

  const handleCodeSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await onConfirmCode(analysisId, code.trim());
  };

  const handleResend = async () => {
    setCode("");
    await onRequestCode({
      analysis_id: analysisId,
      name: formData.name,
      email: formData.email,
      dealership: formData.dealership,
      phone: formData.phone || undefined,
      method: formData.method,
    });
  };

  const inputClass =
    "w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50";

  return (
    <div className="p-6 rounded-lg border bg-card">
      <div className="flex items-center gap-2 mb-2">
        <Lock className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-semibold">Unlock Your Full Report</h2>
      </div>
      <p className="text-sm text-muted-foreground mb-4">
        See your bot access grid, issues, recommendations, and schema details.
        Verify your email or phone to unlock.
      </p>

      {error && (
        <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {step === "info" && (
        <form onSubmit={handleInfoSubmit} className="space-y-3">
          <input
            type="text"
            placeholder="Your name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
            className={inputClass}
          />
          <input
            type="email"
            placeholder="Email address"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
            className={inputClass}
          />
          <input
            type="text"
            placeholder="Dealership name"
            value={formData.dealership}
            onChange={(e) => setFormData({ ...formData, dealership: e.target.value })}
            required
            className={inputClass}
          />
          <input
            type="tel"
            placeholder="Phone (required for SMS)"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            className={inputClass}
          />

          {/* Method toggle */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setFormData({ ...formData, method: "email" })}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm font-medium border transition-colors ${
                formData.method === "email"
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background text-muted-foreground border-border hover:bg-muted"
              }`}
            >
              <Mail className="w-4 h-4" /> Email
            </button>
            <button
              type="button"
              onClick={() => setFormData({ ...formData, method: "sms" })}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm font-medium border transition-colors ${
                formData.method === "sms"
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background text-muted-foreground border-border hover:bg-muted"
              }`}
            >
              <Phone className="w-4 h-4" /> SMS
            </button>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? "Sending code..." : "Send Verification Code"}
          </button>
        </form>
      )}

      {step === "code" && (
        <form onSubmit={handleCodeSubmit} className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Enter the 6-digit code sent to{" "}
            <strong>
              {formData.method === "email" ? formData.email : formData.phone}
            </strong>
          </p>
          <input
            type="text"
            placeholder="Enter 6-digit code"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            maxLength={6}
            required
            autoFocus
            className={`${inputClass} text-center text-2xl tracking-widest font-mono`}
          />
          <button
            type="submit"
            disabled={isSubmitting || code.length !== 6}
            className="w-full py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? "Verifying..." : "Verify"}
          </button>
          <div className="flex justify-between text-sm">
            <button
              type="button"
              onClick={onEditInfo}
              className="flex items-center gap-1 text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="w-3 h-3" /> Edit my info
            </button>
            <button
              type="button"
              onClick={handleResend}
              disabled={isSubmitting}
              className="flex items-center gap-1 text-muted-foreground hover:text-foreground disabled:opacity-50"
            >
              <RefreshCw className="w-3 h-3" /> Resend code
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
