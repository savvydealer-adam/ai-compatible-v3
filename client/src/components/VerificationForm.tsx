import { useState, type FormEvent } from "react";
import { GoogleLogin, type CredentialResponse } from "@react-oauth/google";
import type { VerifyRequest } from "../lib/api";
import { googleAuth } from "../lib/api";
import { Lock, Mail, Phone, ArrowLeft, RefreshCw, UserPlus, Eye, Loader2 } from "lucide-react";

type Mode = "choose" | "form" | "google";

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
  onConfirmCode: (analysisId: string, code: string, createAccount?: boolean) => Promise<void>;
  onEditInfo: () => void;
  accountMode: boolean;
  onSetAccountMode: (mode: boolean) => void;
  onGoogleAuth?: (jwt: string) => void;
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
  accountMode,
  onSetAccountMode,
  onGoogleAuth,
}: VerificationFormProps) {
  const [code, setCode] = useState("");
  const [mode, setMode] = useState<Mode>("choose");
  const [googleSubmitting, setGoogleSubmitting] = useState(false);
  const [googleError, setGoogleError] = useState<string | null>(null);

  const handleChoose = (isAccount: boolean) => {
    onSetAccountMode(isAccount);
    setMode("form");
  };

  const handleGoogleSuccess = async (response: CredentialResponse) => {
    if (!response.credential) return;
    setGoogleSubmitting(true);
    setGoogleError(null);
    try {
      const res = await googleAuth({
        credential: response.credential,
        dealership: "",
        phone: "",
      });
      if (res.jwt && onGoogleAuth) {
        onGoogleAuth(res.jwt);
      }
    } catch (err: any) {
      setGoogleError(err.message || "Google sign-in failed");
    } finally {
      setGoogleSubmitting(false);
    }
  };

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
    await onConfirmCode(analysisId, code.trim(), accountMode);
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

  // Step 0: Choose account vs guest
  if (mode === "choose" && step === "info") {
    return (
      <div className="p-6 rounded-lg border bg-card">
        <div className="flex items-center gap-2 mb-2">
          <Lock className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold">Unlock Your Full Report</h2>
        </div>
        <p className="text-sm text-muted-foreground mb-5">
          See your bot access grid, issues, recommendations, and schema details.
        </p>

        <div className="space-y-3">
          <button
            onClick={() => setMode("google")}
            className="w-full flex items-center gap-4 p-4 rounded-lg border-2 border-primary bg-primary/5 hover:bg-primary/10 transition-colors text-left"
          >
            <svg className="w-6 h-6 flex-shrink-0" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            <div>
              <div className="font-semibold text-sm">Sign in with Google</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Fastest option. No verification code needed.
              </div>
            </div>
          </button>

          <button
            onClick={() => handleChoose(true)}
            className="w-full flex items-center gap-4 p-4 rounded-lg border hover:bg-muted/50 transition-colors text-left"
          >
            <UserPlus className="w-6 h-6 text-muted-foreground flex-shrink-0" />
            <div>
              <div className="font-semibold text-sm">Sign Up (Email/SMS)</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Create an account. All future reports auto-unlocked.
              </div>
            </div>
          </button>

          <button
            onClick={() => handleChoose(false)}
            className="w-full flex items-center gap-4 p-4 rounded-lg border hover:bg-muted/50 transition-colors text-left"
          >
            <Eye className="w-6 h-6 text-muted-foreground flex-shrink-0" />
            <div>
              <div className="font-semibold text-sm">Continue as Guest</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Verify once to see this report. Re-verify for each new analysis.
              </div>
            </div>
          </button>
        </div>
      </div>
    );
  }

  // Google sign-in flow
  if (mode === "google") {
    return (
      <div className="p-6 rounded-lg border bg-card">
        <div className="flex items-center gap-2 mb-2">
          <Lock className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold">Sign in with Google</h2>
        </div>

        {googleError && (
          <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-sm text-red-700">
            {googleError}
          </div>
        )}

        {googleSubmitting ? (
          <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" /> Signing in...
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Click below to sign in with your Google account. No verification code needed.
            </p>
            <div className="flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => setGoogleError("Google sign-in was cancelled or failed")}
                size="large"
                theme="outline"
                text="signin_with"
              />
            </div>
            <button
              type="button"
              onClick={() => { setMode("choose"); setGoogleError(null); }}
              className="w-full text-xs text-muted-foreground hover:text-foreground"
            >
              Back to options
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="p-6 rounded-lg border bg-card">
      <div className="flex items-center gap-2 mb-2">
        <Lock className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-semibold">
          {accountMode ? "Create Your Account" : "Unlock Your Full Report"}
        </h2>
      </div>
      <p className="text-sm text-muted-foreground mb-4">
        {accountMode
          ? "Verify your email or phone to create your free account."
          : "See your bot access grid, issues, recommendations, and schema details. Verify your email or phone to unlock."}
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

          <button
            type="button"
            onClick={() => setMode("choose")}
            className="w-full text-xs text-muted-foreground hover:text-foreground"
          >
            Back to options
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
            {isSubmitting ? "Verifying..." : accountMode ? "Create Account" : "Verify"}
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
