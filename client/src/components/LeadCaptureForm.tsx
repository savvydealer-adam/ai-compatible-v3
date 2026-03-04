import { useState, FormEvent } from "react";
import { submitLead } from "../lib/api";

interface LeadCaptureFormProps {
  analysisUrl: string;
  score: number | null;
}

export default function LeadCaptureForm({ analysisUrl, score }: LeadCaptureFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [dealership, setDealership] = useState("");
  const [phone, setPhone] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await submitLead({
        name,
        email,
        dealership,
        phone,
        analysis_url: analysisUrl,
        score: score ?? undefined,
      });
      setSubmitted(true);
    } catch {
      // Silently handle
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="p-6 rounded-lg border bg-green-50 border-green-200 text-center">
        <p className="font-medium text-green-700">Thanks! We'll be in touch soon.</p>
      </div>
    );
  }

  return (
    <div className="p-6 rounded-lg border bg-card">
      <h2 className="text-lg font-semibold mb-2">Get Expert Help</h2>
      <p className="text-sm text-muted-foreground mb-4">
        Want help improving your AI compatibility score? Let us know.
      </p>
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="text"
          placeholder="Your name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <input
          type="email"
          placeholder="Email address"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <input
          type="text"
          placeholder="Dealership name"
          value={dealership}
          onChange={(e) => setDealership(e.target.value)}
          required
          className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <input
          type="tel"
          placeholder="Phone (optional)"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "Sending..." : "Request Consultation"}
        </button>
      </form>
    </div>
  );
}
